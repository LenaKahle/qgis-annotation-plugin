from qgis.core import QgsDefaultValue
from qgis.PyQt.QtWidgets import (
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QDialogButtonBox,
)
from qgis.PyQt.QtCore import Qt


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

    def change_annotation_class(self, feature_id, new_class):
        """
        Change the class of an existing annotation.
        
        Args:
            feature_id: The ID of the annotation feature to modify
            new_class: The new class name
            
        Returns:
            True if successful, False otherwise
        """
        layer = self.layer_finder.get_annotation_layer()
        
        if not layer:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Annotation Workflow",
                "Annotation layer not found."
            )
            return False
        
        feature = layer.getFeature(feature_id)
        
        if not feature.isValid():
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Annotation Workflow",
                "Feature not found."
            )
            return False
        
        layer.startEditing()
        feature["class"] = new_class
        layer.updateFeature(feature)
        layer.commitChanges()
        
        self.iface.messageBar().pushMessage(
            "Annotation Workflow",
            f"Changed annotation class to '{new_class}'",
            level=0,
            duration=2
        )
        
        return True

    def get_all_annotations(self):
        """
        Get all annotation features.
        
        Returns:
            List of annotation features
        """
        layer = self.layer_finder.get_annotation_layer()
        
        if not layer:
            return []
        
        return list(layer.getFeatures())

    def change_annotation_class_dialog(self, parent_widget, available_classes):
        """
        Open a dialog to change the class of an existing annotation.
        
        Args:
            parent_widget: Parent widget for the dialog
            available_classes: List of available class definitions
        """
        annotations = self.get_all_annotations()
        
        if not annotations:
            QMessageBox.information(
                parent_widget,
                "Annotation Workflow",
                "No annotations found to reclassify."
            )
            return
        
        if not available_classes:
            QMessageBox.information(
                parent_widget,
                "Annotation Workflow",
                "No annotation classes defined."
            )
            return
        
        dialog = QDialog(parent_widget)
        dialog.setWindowTitle("Reclassify Annotation")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Select annotation
        layout.addWidget(QLabel("Select annotation to reclassify:"))
        
        annotations_list = QListWidget(dialog)
        
        for feature in annotations:
            current_class = feature.get("class", "unknown")
            geom = feature.geometry()
            bounds = geom.boundingBox()
            label = (
                f"ID {feature.id()}: {current_class} "
                f"[{bounds.xMinimum():.2f}, {bounds.yMinimum():.2f}]"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, feature.id())
            annotations_list.addItem(item)
        
        layout.addWidget(annotations_list)
        
        # Select new class
        layout.addWidget(QLabel("Select new class:"))
        
        class_combo = QComboBox(dialog)
        class_names = [cls["name"] for cls in available_classes]
        class_combo.addItems(class_names)
        
        layout.addWidget(class_combo)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        selected_item = annotations_list.currentItem()
        if not selected_item:
            QMessageBox.warning(
                parent_widget,
                "Annotation Workflow",
                "Please select an annotation to reclassify."
            )
            return
        
        feature_id = selected_item.data(Qt.UserRole)
        new_class = class_combo.currentText()
        
        self.change_annotation_class(feature_id, new_class)

