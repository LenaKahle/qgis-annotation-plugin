from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsFeatureRequest, QgsField, QgsMapLayer, QgsRectangle


CLASSIFICATION_FIELD = "Classification"
UNCLASSIFIED = "unclassified"


class VerificationService:

    def __init__(self, iface):
        self.iface = iface

    def get_active_vector_layer(self, warn=True):
        layer = self.iface.activeLayer()

        if layer and layer.type() == QgsMapLayer.VectorLayer:
            return layer

        if warn:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Detection Verification",
                "Please make a vector layer active first."
            )

        return None

    def has_classification_field(self, layer):
        return layer.fields().indexOf(CLASSIFICATION_FIELD) != -1

    def configure_layer(self, layer):
        if self.has_classification_field(layer):
            return False

        if not layer.isEditable():
            layer.startEditing()

        layer.dataProvider().addAttributes([
            QgsField(CLASSIFICATION_FIELD, QVariant.String)
        ])
        layer.updateFields()

        field_index = layer.fields().indexOf(CLASSIFICATION_FIELD)
        for feature in layer.getFeatures():
            feature[field_index] = UNCLASSIFIED
            layer.updateFeature(feature)

        if not layer.commitChanges():
            return None

        layer.triggerRepaint()
        return True

    def get_unclassified_features(self, layer):
        field_index = layer.fields().indexOf(CLASSIFICATION_FIELD)
        if field_index == -1:
            return []

        return [
            feature
            for feature in layer.getFeatures()
            if feature[field_index] in (None, "", UNCLASSIFIED)
        ]

    def classify_selected(self, layer, value):
        field_index = layer.fields().indexOf(CLASSIFICATION_FIELD)
        if field_index == -1:
            return 0

        selected_ids = list(layer.selectedFeatureIds())
        if not selected_ids:
            return 0

        if not layer.isEditable():
            layer.startEditing()

        changed = 0
        request = QgsFeatureRequest().setFilterFids(selected_ids)
        for feature in layer.getFeatures(request):
            if feature[field_index] in (None, "", UNCLASSIFIED):
                feature[field_index] = value
                layer.updateFeature(feature)
                changed += 1

        if changed and not layer.commitChanges():
            return 0

        layer.triggerRepaint()
        return changed

    def select_next_unclassified(self, layer):
        features = self.get_unclassified_features(layer)
        if not features:
            layer.removeSelection()
            return None

        feature = features[0]
        layer.selectByIds([feature.id()])

        canvas = self.iface.mapCanvas()
        extent = canvas.extent()
        center = feature.geometry().boundingBox().center()
        half_width = extent.width() / 2.0
        half_height = extent.height() / 2.0

        canvas.setExtent(QgsRectangle(
            center.x() - half_width,
            center.y() - half_height,
            center.x() + half_width,
            center.y() + half_height
        ))
        canvas.refresh()
        return feature

    def counts(self, layer):
        total = layer.featureCount()
        remaining = len(self.get_unclassified_features(layer))
        return remaining, total
