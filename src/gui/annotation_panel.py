from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsCategorizedSymbolRenderer

class AnnotationPanel(QWidget):

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.class_buttons = []
        self._build_ui()

    def _build_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.progress_label = QLabel("0/0 tiles annotated")
        self.progress_label.setStyleSheet(
            "font-size: 16px; font-weight: bold;"
        )
        self.layout.addWidget(self.progress_label)

        # placeholder for dynamic class buttons
        self.class_button_container = QVBoxLayout()
        self.layout.addLayout(self.class_button_container)

        self.done_btn = QPushButton("✓ Mark Done + Next")
        self.done_btn.clicked.connect(self.plugin.mark_done)
        self.layout.addWidget(self.done_btn)

        self.skip_btn = QPushButton("→ Skip Tile")
        self.skip_btn.clicked.connect(self.plugin.mark_skipped)
        self.layout.addWidget(self.skip_btn)

        self.jump_btn = QPushButton("⋄ Select TODO Tile")
        self.jump_btn.clicked.connect(self._open_todo_tile_dialog)
        self.layout.addWidget(self.jump_btn)

        self.prev_btn = QPushButton("⌖ Re-center Current Tile")
        self.prev_btn.clicked.connect(self.plugin.recenter_current_tile)
        self.layout.addWidget(self.prev_btn)

        self.layout.addStretch()

    #
    # Called from plugin AFTER config is loaded
    #

    def set_annotation_classes(self, classes):
        """
        classes format:
        [
            {"name": "brick", "color": "#ff0000"},
            {"name": "bush", "color": "#00ff00"}
        ]
        """
        if not classes:
            classes = self.load_classes_from_layer()

        # clear old buttons
        for i in reversed(range(self.class_button_container.count())):
            item = self.class_button_container.itemAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.class_buttons = []

        for cls in classes:
            name = cls["name"]
            color = QColor(cls["color"])

            muted = self._muted_color(color)

            btn = QPushButton(f"Add {name}")
            btn.clicked.connect(
                lambda checked=False, n=name: self.plugin.activate_annotation_class(n)
            )

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {muted.name()};
                    border: 1px solid {color.name()};
                    font-size: 14px;
                    padding: 10px;
                }}
                QPushButton:hover {{
                    background-color: {color.name()};
                    color: white;
                }}
            """)

            self.class_button_container.addWidget(btn)
            self.class_buttons.append(btn)

    def _muted_color(self, color: QColor):
        """
        Make a softer version of the color for UI buttons.
        """

        c = QColor(color)

        c.setAlpha(80)  # transparency

        return c

    def update_progress(self, done, total):
        self.progress_label.setText(
            f"{done}/{total} tiles annotated"
        )

    def _open_todo_tile_dialog(self):
        todo_features = self.plugin.tile_manager.get_todo_features()

        if not todo_features:
            QMessageBox.information(
                self,
                "Annotation Workflow",
                "No TODO tiles available to choose from."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Select TODO Tile")

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select a tile to begin annotating from:"))

        list_widget = QListWidget(dialog)

        for feature in todo_features:
            rect = feature.geometry().boundingBox()
            label = (
                f"Tile {feature.id()}: "
                f"x=[{rect.xMinimum():.2f}, {rect.xMaximum():.2f}] "
                f"y=[{rect.yMinimum():.2f}, {rect.yMaximum():.2f}]"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, feature.id())
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return

        selected_item = list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                "Please select a tile before confirming."
            )
            return

        fid = selected_item.data(Qt.UserRole)
        if not self.plugin.select_todo_tile(fid):
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                "Could not jump to the selected tile."
            )

    def load_classes_from_layer(self):
        layer = self.plugin.layer_finder.get_annotation_layer(warn=False)

        if not layer:
            return []

        # try to read renderer colors
        renderer = layer.renderer()

        color_map = {}

        if isinstance(renderer, QgsCategorizedSymbolRenderer):
            for cat in renderer.categories():
                color_map[cat.value()] = cat.symbol().color().name()

        values = set()

        for feat in layer.getFeatures():
            val = feat["class"]
            if val:
                values.add(val)

        return [
            {
                "name": v,
                "color": color_map.get(v, "#cccccc")
            }
            for v in sorted(values)
        ]