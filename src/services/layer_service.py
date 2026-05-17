import os
import processing

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QFileDialog

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsMapLayer,
    QgsVectorFileWriter,
    QgsCoordinateTransformContext,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsFillSymbol,
    QgsEditFormConfig,
    QgsDefaultValue,
)


class LayerService:

    def __init__(self, iface):
        self.iface = iface

    def get_layer(self, layer_name, warn=True):
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == layer_name:
                return layer

        if warn:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Annotation Workflow",
                f"Layer '{layer_name}' not found."
            )

        return None

    def has_tile_layer(self):
        return any(
            layer.name() == "tiles"
            for layer in QgsProject.instance().mapLayers().values()
        )

    def has_annotation_layer(self):
        return any(
            layer.name() == "annotations"
            for layer in QgsProject.instance().mapLayers().values()
        )

    def get_tile_layer(self, warn=True):
        return self.get_layer("tiles", warn=warn)

    def get_annotation_layer(self, warn=True):
        return self.get_layer("annotations", warn=warn)


#
# Utility helpers
#

def ensure_field(layer, name, variant_type):
    if layer.fields().indexOf(name) == -1:
        layer.startEditing()

        layer.dataProvider().addAttributes([
            QgsField(name, variant_type)
        ])

        layer.updateFields()

        layer.commitChanges()


def apply_tile_symbology(tile_layer):
    """
    Categorized renderer by status:
    - todo -> red
    - skipped -> yellow
    - done -> green

    All rendered as outlines only.
    """

    categories = []

    styles = {
        "todo": "#f73718",
        "skipped": "#eac72e",
        "done": "#5cc118",
    }

    for status, color in styles.items():

        symbol = QgsFillSymbol.createSimple({
            "style": "no",
            "outline_color": color,
            "outline_width": "0.6"
        })

        category = QgsRendererCategory(
            status,
            symbol,
            status
        )

        categories.append(category)

    renderer = QgsCategorizedSymbolRenderer(
        "status",
        categories
    )

    tile_layer.setRenderer(renderer)

    tile_layer.triggerRepaint()


def apply_annotation_symbology(annotation_layer, classes):
    """
    Categorized renderer by class.
    """

    categories = []

    for cls in classes:

        symbol = QgsFillSymbol.createSimple({
            "color": cls["color"],
            "outline_color": "black",
            "outline_width": "0.3"
        })

        symbol.setOpacity(0.5)

        category = QgsRendererCategory(
            cls["name"],
            symbol,
            cls["name"]
        )

        categories.append(category)

    renderer = QgsCategorizedSymbolRenderer(
        "class",
        categories
    )

    annotation_layer.setRenderer(renderer)

    annotation_layer.triggerRepaint()


def configure_annotation_form(annotation_layer):
    """
    Hide popup attribute dialog when adding features.
    """

    form_config = annotation_layer.editFormConfig()

    form_config.setSuppress(
        QgsEditFormConfig.SuppressOn
    )

    annotation_layer.setEditFormConfig(form_config)


def set_default_values(annotation_layer):
    """
    Automatically set status='todo'
    on newly created annotations.
    """

    status_idx = annotation_layer.fields().indexOf("status")

    if status_idx != -1:
        annotation_layer.setDefaultValueDefinition(
            status_idx,
            QgsDefaultValue("'todo'")
        )


#
# Layer creation
#

def create_tile_layer(
    raster_layer,
    tile_size,
    gpkg_path
):
    """
    Create grid using QGIS native:creategrid.
    Save to GeoPackage as 'tiles'.
    """

    extent = raster_layer.extent()
    crs = raster_layer.crs()

    result = processing.run(
        "native:creategrid",
        {
            "TYPE": 2,
            "EXTENT": extent,
            "HSPACING": tile_size,
            "VSPACING": tile_size,
            "HOVERLAY": 0,
            "VOVERLAY": 0,
            "CRS": crs,
            "OUTPUT": gpkg_path
        }
    )

    output_path = result["OUTPUT"]

    tile_layer = QgsVectorLayer(
        output_path,
        "tiles",
        "ogr"
    )

    tile_layer.setName("tiles")

    #
    # Add status field
    #

    ensure_field(
        tile_layer,
        "status",
        QVariant.String
    )

    #
    # Fill all with "todo"
    #

    status_idx = tile_layer.fields().indexOf("status")

    tile_layer.startEditing()

    for feature in tile_layer.getFeatures():

        feature[status_idx] = "todo"

        tile_layer.updateFeature(feature)

    tile_layer.commitChanges()

    #
    # Symbology
    #

    apply_tile_symbology(tile_layer)

    QgsProject.instance().addMapLayer(tile_layer)

    return tile_layer


def create_annotation_layer(
    raster_layer,
    gpkg_path,
    classes
):
    """
    Create annotation polygon layer
    inside same GeoPackage.
    """

    crs = raster_layer.crs()

    memory_layer = QgsVectorLayer(
        f"Polygon?crs={crs.authid()}",
        "annotations",
        "memory"
    )

    provider = memory_layer.dataProvider()

    provider.addAttributes([
        QgsField("class", QVariant.String),
        QgsField("status", QVariant.String),
    ])

    memory_layer.updateFields()

    #
    # Save to existing gpkg
    #

    options = QgsVectorFileWriter.SaveVectorOptions()

    options.driverName = "GPKG"

    options.layerName = "annotations"

    options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer
    )

    QgsVectorFileWriter.writeAsVectorFormatV3(
        memory_layer,
        gpkg_path,
        QgsCoordinateTransformContext(),
        options
    )

    annotation_layer = QgsVectorLayer(
        f"{gpkg_path}|layername=annotations",
        "annotations",
        "ogr"
    )

    #
    # Configure layer
    #

    apply_annotation_symbology(
        annotation_layer,
        classes
    )

    configure_annotation_form(
        annotation_layer
    )

    set_default_values(
        annotation_layer
    )

    QgsProject.instance().addMapLayer(
        annotation_layer
    )

    return annotation_layer


#
# Main entry point
#

def create_tiles_and_annotation_layers(
    iface,
    layer_finder,
    tile_manager,
    config
):
    """
    Create:
    - tiles layer
    - annotations layer

    matching manual QGIS workflow.
    """

    classes = config["classes"]
    tile_size = config["tile_size"]

    if not classes:

        QMessageBox.warning(
            iface.mainWindow(),
            "Annotation Workflow",
            "Add at least one annotation class before saving."
        )

        return False

    #
    # Find raster layer
    #

    raster_layer = None

    active = iface.activeLayer()

    if (
        active and
        active.type() == QgsMapLayer.RasterLayer
    ):
        raster_layer = active

    else:

        rasters = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.RasterLayer
        ]

        if len(rasters) == 1:
            raster_layer = rasters[0]

    if raster_layer is None:

        QMessageBox.warning(
            iface.mainWindow(),
            "Annotation Workflow",
            (
                "Please select a raster layer "
                "or make a raster layer active "
                "before creating tiles."
            )
        )

        return False

    #
    # Ask user where to save GeoPackage
    #

    default_dir = QgsProject.instance().homePath()

    if not default_dir:
        default_dir = os.path.expanduser("~")

    gpkg_path, _ = QFileDialog.getSaveFileName(
        iface.mainWindow(),
        "Save tiles GeoPackage",
        os.path.join(default_dir, "tiles.gpkg"),
        "GeoPackage (*.gpkg)"
    )

    if not gpkg_path:
        return False

    if not gpkg_path.lower().endswith(".gpkg"):
        gpkg_path += ".gpkg"


    #
    # Existing layers?
    #

    tile_layer = layer_finder.get_tile_layer(
        warn=False
    )

    annotation_layer = layer_finder.get_annotation_layer(
        warn=False
    )

    #
    # Create tiles
    #

    if tile_layer is None:

        tile_layer = create_tile_layer(
            raster_layer,
            tile_size,
            gpkg_path
        )

    else:

        ensure_field(
            tile_layer,
            "status",
            QVariant.String
        )

        apply_tile_symbology(
            tile_layer
        )

    #
    # Create annotations
    #

    if annotation_layer is None:

        annotation_layer = create_annotation_layer(
            raster_layer,
            gpkg_path,
            classes
        )

    else:

        ensure_field(
            annotation_layer,
            "class",
            QVariant.String
        )

        ensure_field(
            annotation_layer,
            "status",
            QVariant.String
        )

        apply_annotation_symbology(
            annotation_layer,
            classes
        )

        configure_annotation_form(
            annotation_layer
        )

        set_default_values(
            annotation_layer
        )

    return True