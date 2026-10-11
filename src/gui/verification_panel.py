from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


DEFAULT_CLASSIFICATIONS = [
    ("true positive", "#5aa469"),
    ("false positive", "#d95d39"),
    ("unclassified", "#a9a9a9"),
]


class VerificationSetupPanel(QWidget):

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.selected_color = QColor("#5aa469")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Configure detection classifications"))
        layout.addWidget(QLabel("The active vector layer will receive a Classification field."))

        row = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Classification name")
        row.addWidget(self.name_input)

        self.color_button = QPushButton("Choose color")
        self.color_button.clicked.connect(self._pick_color)
        row.addWidget(self.color_button)

        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_classification)
        row.addWidget(add_button)
        layout.addLayout(row)

        self.class_list = QListWidget()
        layout.addWidget(self.class_list)

        remove_button = QPushButton("Remove selected")
        remove_button.clicked.connect(self._remove_selected)
        layout.addWidget(remove_button)

        confirm_button = QPushButton("Confirm and start verifying")
        confirm_button.clicked.connect(self._confirm)
        confirm_button.setStyleSheet("font-weight: bold; padding: 8px;")
        layout.addWidget(confirm_button)
        layout.addStretch()

        for name, color in DEFAULT_CLASSIFICATIONS:
            self._add_item(name, color)
        self._update_color_button()

    def _pick_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Choose classification color")
        if color.isValid():
            self.selected_color = color
            self._update_color_button()

    def _update_color_button(self):
        self.color_button.setStyleSheet(
            f"background-color: {self.selected_color.name()}; color: white;"
        )

    def _add_item(self, name, color):
        names = [
            self.class_list.item(index).data(Qt.UserRole)["name"]
            for index in range(self.class_list.count())
        ]
        if name in names:
            return

        item = QListWidgetItem(f"{name} ({color})")
        item.setData(Qt.UserRole, {"name": name, "color": color})
        item.setBackground(QColor(color))
        self.class_list.addItem(item)

    def _add_classification(self):
        name = self.name_input.text().strip()
        if not name:
            return
        self._add_item(name, self.selected_color.name())
        self.name_input.clear()

    def _remove_selected(self):
        for item in self.class_list.selectedItems():
            self.class_list.takeItem(self.class_list.row(item))

    def classifications(self):
        return [
            self.class_list.item(index).data(Qt.UserRole)
            for index in range(self.class_list.count())
        ]

    def _confirm(self):
        layer = self.plugin.verification_service.get_active_vector_layer()
        if not layer:
            return

        classes = self.classifications()
        if not classes or not any(item["name"] == "unclassified" for item in classes):
            QMessageBox.warning(self, "Detection Verification", "Keep an 'unclassified' classification in the list.")
            return

        result = self.plugin.verification_service.configure_layer(layer)
        if result is None:
            QMessageBox.warning(self, "Detection Verification", "Could not save the Classification field.")
            return

        self.plugin.verification_classes = classes
        self.plugin.show_verification_annotation()


class VerificationAnnotationPanel(QWidget):

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.layer_label = QLabel()
        layout.addWidget(self.layer_label)
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.progress_label)

        self.next_button = QPushButton("Focus next unclassified")
        self.next_button.clicked.connect(self.focus_next)
        layout.addWidget(self.next_button)

        self.classification_layout = QVBoxLayout()
        layout.addLayout(self.classification_layout)

        setup_button = QPushButton("Change classifications / layer")
        setup_button.clicked.connect(self.plugin.show_verification_setup)
        layout.addWidget(setup_button)
        layout.addStretch()

    def set_classifications(self, classifications):
        while self.classification_layout.count():
            item = self.classification_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for classification in classifications:
            button = QPushButton(f"Classify selected as {classification['name']}")
            color = QColor(classification["color"])
            button.setStyleSheet(
                f"background-color: {color.lighter(150).name()}; border: 1px solid {color.name()}; padding: 7px;"
            )
            button.clicked.connect(
                lambda checked=False, value=classification["name"]: self.classify_selected(value)
            )
            self.classification_layout.addWidget(button)

    def refresh(self):
        layer = self.plugin.verification_service.get_active_vector_layer(warn=False)
        if not layer or not self.plugin.verification_service.has_classification_field(layer):
            self.layer_label.setText("No configured vector layer")
            self.progress_label.setText("Configure a layer to begin")
            self.next_button.setEnabled(False)
            return

        remaining, total = self.plugin.verification_service.counts(layer)
        self.layer_label.setText(f"Layer: {layer.name()}")
        self.progress_label.setText(f"{remaining} unclassified / {total} objects")
        self.next_button.setEnabled(remaining > 0)

    def focus_next(self):
        layer = self.plugin.verification_service.get_active_vector_layer()
        if layer:
            self.plugin.verification_service.select_next_unclassified(layer)
            self.refresh()

    def classify_selected(self, value):
        layer = self.plugin.verification_service.get_active_vector_layer()
        if not layer:
            return

        changed = self.plugin.verification_service.classify_selected(layer, value)
        if not changed:
            QMessageBox.information(self, "Detection Verification", "Select an unclassified object first.")
        self.refresh()
        if changed:
            self.focus_next()
