import math
import os
import re
import processing

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QFileDialog

from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsProject,
    QgsRectangle,
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

ANNOTATOR_PACKAGE_SUFFIX = "_annotator_plugin.gpkg"


class LayerService:

    def __init__(self, iface):
        self.iface = iface
        self.package_path = None

    @staticmethod
    def source_package_path(layer):
        return layer.source().split("|", 1)[0]

    @staticmethod
    def _normalized_path(path):
        return os.path.normcase(os.path.abspath(path))

    def set_package_path(self, path):
        self.package_path = self._normalized_path(path) if path else None

    def get_layer(self, layer_name, warn=True):
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() != layer_name:
                continue
            if self.package_path and self._normalized_path(
                self.source_package_path(layer)
            ) != self.package_path:
                continue
            if layer.isValid():
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

    def load_package_layers(self, path):
        path = os.path.abspath(path)
        layers = {}
        for name in ("tiles", "annotations"):
            layer = next(
                (
                    candidate
                    for candidate in QgsProject.instance().mapLayers().values()
                    if candidate.name() == name
                    and self._normalized_path(
                        self.source_package_path(candidate)
                    ) == self._normalized_path(path)
                    and candidate.isValid()
                ),
                None
            )
            if layer is None:
                layer = QgsVectorLayer(
                    f"{path}|layername={name}",
                    name,
                    "ogr"
                )
            if not layer.isValid():
                return None
            layers[name] = layer

        self.set_package_path(path)
        for layer in layers.values():
            if layer.id() not in QgsProject.instance().mapLayers():
                QgsProject.instance().addMapLayer(layer)
        return layers


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
    gpkg_path,
    area_layer=None
):
    """
    Create grid using QGIS native:creategrid.
    Save to GeoPackage as 'tiles'.
    """

    extent = raster_layer.extent()
    crs = raster_layer.crs()

    areas = _get_raster_area_geometries(raster_layer, area_layer)
    if area_layer is not None and area_layer.featureCount() > 0:
        output_path = _write_area_tile_grid(
            raster_layer,
            tile_size,
            gpkg_path,
            areas
        )
    else:
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


def _get_raster_area_geometries(raster_layer, area_layer):
    if area_layer is None or area_layer.featureCount() == 0:
        return []

    raster_geometry = QgsGeometry.fromRect(raster_layer.extent())
    transform = None
    if area_layer.crs() != raster_layer.crs():
        transform = QgsCoordinateTransform(
            area_layer.crs(),
            raster_layer.crs(),
            QgsProject.instance()
        )

    geometries = []
    for feature in area_layer.getFeatures():
        geometry = feature.geometry()
        if geometry.isNull() or geometry.isEmpty():
            continue
        if transform:
            geometry.transform(transform)
        geometry = geometry.intersection(raster_geometry)
        if not geometry.isNull() and not geometry.isEmpty():
            geometries.append(geometry)

    return geometries


def _iter_area_tile_geometries(raster_layer, tile_size, area_geometries):
    extent = raster_layer.extent()
    x_min = extent.xMinimum()
    y_min = extent.yMinimum()
    columns = max(1, math.ceil(extent.width() / tile_size))
    rows = max(1, math.ceil(extent.height() / tile_size))
    candidates = set()

    for area in area_geometries:
        bounds = area.boundingBox()
        first_column = max(
            0,
            math.floor((bounds.xMinimum() - x_min) / tile_size)
        )
        last_column = min(
            columns - 1,
            math.ceil((bounds.xMaximum() - x_min) / tile_size) - 1
        )
        first_row = max(
            0,
            math.floor((bounds.yMinimum() - y_min) / tile_size)
        )
        last_row = min(
            rows - 1,
            math.ceil((bounds.yMaximum() - y_min) / tile_size) - 1
        )

        for column in range(first_column, last_column + 1):
            for row in range(first_row, last_row + 1):
                candidates.add((column, row))

    for column, row in candidates:
        tile_geometry = QgsGeometry.fromRect(QgsRectangle(
            x_min + column * tile_size,
            y_min + row * tile_size,
            x_min + (column + 1) * tile_size,
            y_min + (row + 1) * tile_size
        ))
        if any(
            area.intersection(tile_geometry).area() > 0
            for area in area_geometries
        ):
            yield tile_geometry


def estimate_tile_count(raster_layer, tile_size, area_layer=None):
    """Return the number of grid cells intersecting selected areas."""
    areas = _get_raster_area_geometries(raster_layer, area_layer)
    if area_layer is None or area_layer.featureCount() == 0:
        return max(1, math.ceil(raster_layer.extent().width() / tile_size)) * max(
            1,
            math.ceil(raster_layer.extent().height() / tile_size)
        )
    if not areas:
        return 0
    return sum(
        1
        for _ in _iter_area_tile_geometries(
            raster_layer,
            tile_size,
            areas
        )
    )


def _write_area_tile_grid(raster_layer, tile_size, gpkg_path, areas):
    crs = raster_layer.crs()
    memory_layer = QgsVectorLayer(
        f"Polygon?crs={crs.authid()}",
        "tiles",
        "memory"
    )
    provider = memory_layer.dataProvider()
    provider.addAttributes([QgsField("status", QVariant.String)])
    memory_layer.updateFields()

    features = []
    for geometry in _iter_area_tile_geometries(
        raster_layer,
        tile_size,
        areas
    ):
        feature = QgsFeature(memory_layer.fields())
        feature.setGeometry(geometry)
        feature["status"] = "todo"
        features.append(feature)

    if features and not provider.addFeatures(features):
        raise RuntimeError("Could not add generated tiles to the temporary layer.")
    _write_memory_layer_to_gpkg(memory_layer, gpkg_path, "tiles")

    return f"{gpkg_path}|layername=tiles"


def _write_memory_layer_to_gpkg(memory_layer, gpkg_path, layer_name):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name
    package_exists = os.path.isfile(gpkg_path) and os.path.getsize(gpkg_path) > 0
    options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer
        if package_exists
        else QgsVectorFileWriter.CreateOrOverwriteFile
    )
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        memory_layer,
        gpkg_path,
        QgsCoordinateTransformContext(),
        options
    )
    if result[0] != QgsVectorFileWriter.NoError:
        details = result[1] or "No additional error details were provided."
        raise RuntimeError(
            f"Could not write '{layer_name}' layer to '{gpkg_path}': {details}"
        )


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

    _write_memory_layer_to_gpkg(memory_layer, gpkg_path, "annotations")

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
    config,
    area_layer=None
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

    raster_layer = config.get("raster_layer")
    if not raster_layer or raster_layer.type() != QgsMapLayer.RasterLayer:
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

    raster_name = re.sub(r"[^\w.-]+", "_", raster_layer.name()).strip("._")
    if not raster_name:
        raster_name = "annotations"
    gpkg_path, _ = QFileDialog.getSaveFileName(
        iface.mainWindow(),
        "Save annotation workflow GeoPackage",
        config.get("gpkg_path", os.path.join(
            default_dir,
            f"{raster_name}{ANNOTATOR_PACKAGE_SUFFIX}"
        )),
        f"Annotator GeoPackage (*{ANNOTATOR_PACKAGE_SUFFIX})"
    )

    if not gpkg_path:
        return False

    if not gpkg_path.lower().endswith(ANNOTATOR_PACKAGE_SUFFIX):
        if gpkg_path.lower().endswith(".gpkg"):
            gpkg_path = gpkg_path[:-5]
        gpkg_path += ANNOTATOR_PACKAGE_SUFFIX

    layer_finder.set_package_path(gpkg_path)

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

        try:
            tile_layer = create_tile_layer(
                raster_layer,
                tile_size,
                gpkg_path,
                area_layer
            )
        except RuntimeError as error:
            layer_finder.set_package_path(None)
            QMessageBox.critical(
                iface.mainWindow(),
                "Annotation Workflow",
                str(error)
            )
            return False

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

        try:
            annotation_layer = create_annotation_layer(
                raster_layer,
                gpkg_path,
                classes
            )
        except RuntimeError as error:
            QMessageBox.critical(
                iface.mainWindow(),
                "Annotation Workflow",
                str(error)
            )
            return False

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