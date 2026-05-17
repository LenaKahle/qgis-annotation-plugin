from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QLineEdit,
    QDoubleSpinBox,
    QMessageBox,
)
from qgis.core import QgsRectangle

from ..services.layer_service import create_tiles_and_annotation_layers


class ConfigPanel(QWidget):

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("No tiles or annotations layers found. Configure your project below.")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Annotation classes:"))

        class_row = QHBoxLayout()
        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText("Add a class name, e.g. brick")
        class_row.addWidget(self.class_input)

        add_class_btn = QPushButton("Add class")
        add_class_btn.clicked.connect(self._add_class)
        class_row.addWidget(add_class_btn)
        layout.addLayout(class_row)

        self.class_list = QListWidget()
        layout.addWidget(self.class_list)

        remove_class_btn = QPushButton("Remove selected class")
        remove_class_btn.clicked.connect(self._remove_selected_class)
        layout.addWidget(remove_class_btn)

        layout.addWidget(QLabel("Tile settings (map units):"))
        tile_row = QHBoxLayout()
        tile_row.addWidget(QLabel("Tile size:"))
        self.tile_size_spin = QDoubleSpinBox()
        self.tile_size_spin.setRange(1, 100000)
        self.tile_size_spin.setValue(50)
        self.tile_size_spin.setSingleStep(1)
        tile_row.addWidget(self.tile_size_spin)

        tile_row.addWidget(QLabel("Margin:"))
        self.tile_margin_spin = QDoubleSpinBox()
        self.tile_margin_spin.setRange(0, 10000)
        self.tile_margin_spin.setValue(5)
        self.tile_margin_spin.setSingleStep(1)
        tile_row.addWidget(self.tile_margin_spin)
        layout.addLayout(tile_row)

        preview_btn = QPushButton("Preview one tile extent")
        preview_btn.clicked.connect(self._preview_tile)
        layout.addWidget(preview_btn)

        save_btn = QPushButton("Save and create layers")
        save_btn.clicked.connect(self._save_configuration)
        save_btn.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(save_btn)

        layout.addStretch()

    def _add_class(self):
        text = self.class_input.text().strip()
        if not text:
            return
        if text in [self.class_list.item(i).text() for i in range(self.class_list.count())]:
            return
        self.class_list.addItem(text)
        self.class_input.clear()

    def _remove_selected_class(self):
        selected = self.class_list.selectedItems()
        for item in selected:
            self.class_list.takeItem(self.class_list.row(item))

    def _preview_tile(self):
        tile_size = self.tile_size_spin.value()
        if tile_size <= 0:
            QMessageBox.warning(self, "Annotation Workflow", "Tile size must be greater than zero.")
            return

        canvas = self.plugin.iface.mapCanvas()
        center = canvas.center()
        half = tile_size / 2.0
        preview_rect = QgsRectangle(
            center.x() - half,
            center.y() - half,
            center.x() + half,
            center.y() + half
        )

        margin = self.tile_margin_spin.value()
        preview_rect = QgsRectangle(
            preview_rect.xMinimum() - margin,
            preview_rect.yMinimum() - margin,
            preview_rect.xMaximum() + margin,
            preview_rect.yMaximum() + margin
        )

        canvas.setExtent(preview_rect)
        canvas.refresh()

    def _save_configuration(self):
        classes = [self.class_list.item(i).text() for i in range(self.class_list.count())]
        tile_size = self.tile_size_spin.value()
        margin = self.tile_margin_spin.value()

        created = create_tiles_and_annotation_layers(
            self.plugin.iface,
            self.plugin.layer_finder,
            self.plugin.tile_manager,
            classes,
            tile_size,
            margin
        )

        if created:
            if self.plugin.dock:
                self.plugin.dock.set_mode("annotate")
            if self.plugin.tile_manager.current_tile_fid is None:
                self.plugin.tile_manager.next_tile()
            else:
                self.plugin.update_progress()

            QMessageBox.information(
                self,
                "Annotation Workflow",
                "Tiles and annotations layers have been created. Ready to annotate!"
            )
