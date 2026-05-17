from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsRectangle,
    QgsField,
)
from qgis.PyQt.QtCore import QVariant


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
