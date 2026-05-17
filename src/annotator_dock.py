from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QLineEdit,
    QDoubleSpinBox,
    QMessageBox,
    QStackedWidget
)
from qgis.core import QgsRectangle


class AnnotatorDock(QDockWidget):

    def __init__(self, plugin):
        super().__init__("Annotation Tool")

        self.plugin = plugin

        container = QWidget()
        self.setWidget(container)

        outer_layout = QVBoxLayout()
        container.setLayout(outer_layout)

        self.stack = QStackedWidget()
        outer_layout.addWidget(self.stack)

        self._build_config_panel()
        self._build_annotate_panel()

        outer_layout.addStretch()

    def _build_config_panel(self):
        self.config_widget = QWidget()
        config_layout = QVBoxLayout()
        self.config_widget.setLayout(config_layout)

        title = QLabel("No tiles or annotations layers found. Configure your project below.")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        config_layout.addWidget(title)

        config_layout.addWidget(QLabel("Annotation classes:"))

        class_row = QHBoxLayout()
        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText("Add a class name, e.g. brick")
        class_row.addWidget(self.class_input)

        add_class_btn = QPushButton("Add class")
        add_class_btn.clicked.connect(self._add_class)
        class_row.addWidget(add_class_btn)
        config_layout.addLayout(class_row)

        self.class_list = QListWidget()
        config_layout.addWidget(self.class_list)

        remove_class_btn = QPushButton("Remove selected class")
        remove_class_btn.clicked.connect(self._remove_selected_class)
        config_layout.addWidget(remove_class_btn)

        config_layout.addWidget(QLabel("Tile settings (map units):"))
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
        config_layout.addLayout(tile_row)

        preview_btn = QPushButton("Preview one tile extent")
        preview_btn.clicked.connect(self._preview_tile)
        config_layout.addWidget(preview_btn)

        save_btn = QPushButton("Save and create layers")
        save_btn.clicked.connect(self._save_configuration)
        save_btn.setStyleSheet("font-weight: bold; padding: 10px;")
        config_layout.addWidget(save_btn)

        config_layout.addStretch()
        self.stack.addWidget(self.config_widget)

    def _build_annotate_panel(self):
        self.annotate_widget = QWidget()
        annotate_layout = QVBoxLayout()
        self.annotate_widget.setLayout(annotate_layout)

        self.progress_label = QLabel("0/0 tiles annotated")
        self.progress_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        annotate_layout.addWidget(self.progress_label)

        self.bush_btn = QPushButton("Add New Bush")
        self.bush_btn.clicked.connect(
            lambda: self.plugin.activate_annotation_class("bush")
        )
        self.bush_btn.setStyleSheet(
            "background-color: #dff0d8; font-size: 16px; padding: 12px;"
        )
        annotate_layout.addWidget(self.bush_btn)

        self.brick_btn = QPushButton("Add New Brick")
        self.brick_btn.clicked.connect(
            lambda: self.plugin.activate_annotation_class("brick")
        )
        self.brick_btn.setStyleSheet(
            "background-color: #f2dede; font-size: 16px; padding: 12px;"
        )
        annotate_layout.addWidget(self.brick_btn)

        self.done_btn = QPushButton("✓ Mark Done + Next")
        self.done_btn.clicked.connect(self.plugin.mark_done)
        annotate_layout.addWidget(self.done_btn)

        self.skip_btn = QPushButton("→ Skip Tile")
        self.skip_btn.clicked.connect(self.plugin.mark_skipped)
        annotate_layout.addWidget(self.skip_btn)

        self.prev_btn = QPushButton("⌖ Re-center Current Tile")
        self.prev_btn.clicked.connect(self.plugin.recenter_current_tile)
        annotate_layout.addWidget(self.prev_btn)

        annotate_layout.addStretch()
        self.stack.addWidget(self.annotate_widget)

    def set_mode(self, mode):
        if mode == "config":
            self.stack.setCurrentWidget(self.config_widget)
        else:
            self.stack.setCurrentWidget(self.annotate_widget)

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

        created = self.plugin.create_tiles_and_annotation_layers(classes, tile_size, margin)
        if created:
            QMessageBox.information(
                self,
                "Annotation Workflow",
                "Tiles and annotations layers have been created. Switch to the annotation tab to continue."
            )