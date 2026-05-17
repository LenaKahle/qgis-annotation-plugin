from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsRectangle,
    QgsField,
    QgsMapLayer
)
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import QVariant

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
        return any(layer.name() == "tiles" for layer in QgsProject.instance().mapLayers().values())

    def has_annotation_layer(self):
        return any(layer.name() == "annotations" for layer in QgsProject.instance().mapLayers().values())

    def get_tile_layer(self, warn=True):
        return self.get_layer("tiles", warn=warn)

    def get_annotation_layer(self, warn=True):
        return self.get_layer("annotations", warn=warn)


def ensure_field(layer, name, variant_type):
    """Ensure `name` field exists on an existing layer. Commits changes if needed."""
    if layer.fields().indexOf(name) == -1:
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField(name, variant_type)])
        layer.updateFields()
        layer.commitChanges()


def create_tile_layer(raster_layer, tile_size):
    """Create an in-memory tile polygon layer covering the raster extent."""
    tile_layer = QgsVectorLayer(
        f"Polygon?crs={raster_layer.crs().authid()}",
        "tiles",
        "memory"
    )
    tile_provider = tile_layer.dataProvider()
    tile_provider.addAttributes([QgsField("status", QVariant.String)])
    tile_layer.updateFields()

    features = []
    extent = raster_layer.extent()
    x = extent.xMinimum()
    while x < extent.xMaximum():
        y = extent.yMinimum()
        while y < extent.yMaximum():
            rect = QgsRectangle(
                x,
                y,
                min(x + tile_size, extent.xMaximum()),
                min(y + tile_size, extent.yMaximum())
            )
            feature = QgsFeature(tile_layer.fields())
            feature.setGeometry(QgsGeometry.fromRect(rect))
            feature.setAttributes(["todo"])
            features.append(feature)
            y += tile_size
        x += tile_size

    tile_provider.addFeatures(features)
    tile_layer.updateExtents()
    QgsProject.instance().addMapLayer(tile_layer)
    return tile_layer


def create_annotation_layer(raster_layer):
    """Create an in-memory annotation polygon layer."""
    annotation_layer = QgsVectorLayer(
        f"Polygon?crs={raster_layer.crs().authid()}",
        "annotations",
        "memory"
    )
    annotation_provider = annotation_layer.dataProvider()
    annotation_provider.addAttributes([QgsField("class", QVariant.String)])
    annotation_layer.updateFields()
    annotation_layer.updateExtents()
    QgsProject.instance().addMapLayer(annotation_layer)
    return annotation_layer


def create_tiles_and_annotation_layers(iface, layer_finder, tile_manager, classes, tile_size, margin):
    if not classes:
        QMessageBox.warning(
            iface.mainWindow(),
            "Annotation Workflow",
            "Add at least one annotation class before saving."
        )
        return False

    raster_layer = None
    active = iface.activeLayer()
    if active and active.type() == QgsMapLayer.RasterLayer:
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
            "Please select a raster layer or make a raster layer active before creating tiles."
        )
        return False

    tile_layer = layer_finder.get_tile_layer(warn=False)
    annotation_layer = layer_finder.get_annotation_layer(warn=False)

    if tile_layer is None:
        tile_layer = create_tile_layer(raster_layer, tile_size)
    else:
        ensure_field(tile_layer, "status", QVariant.String)

    if annotation_layer is None:
        annotation_layer = create_annotation_layer(raster_layer)
    else:
        ensure_field(annotation_layer, "class", QVariant.String)

    return True

