from qgis.core import QgsDefaultValue


class AnnotationService:

    def __init__(self, iface, layer_finder):
        self.iface = iface
        self.layer_finder = layer_finder
        self.annotation_layer = None
        self.current_class = None

    def activate_annotation_class(self, class_name):
        self.current_class = class_name
        self.annotation_layer = self.layer_finder.get_annotation_layer()

        if not self.annotation_layer:
            return

        self.iface.setActiveLayer(self.annotation_layer)
        self.annotation_layer.startEditing()

        class_idx = self.annotation_layer.fields().indexOf("class")
        self.annotation_layer.setDefaultValueDefinition(
            class_idx,
            QgsDefaultValue(f"'{class_name}'")
        )

        self.iface.actionAddFeature().trigger()
        self.iface.messageBar().pushMessage(
            "Annotation Workflow",
            f"Drawing {class_name}",
            level=0,
            duration=2
        )
