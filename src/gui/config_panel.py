from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QDoubleSpinBox,
    QMessageBox,
    QColorDialog,
)

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt

import math

from qgis.core import QgsMapLayer, QgsProject, QgsRectangle
from ..services.layer_service import create_tiles_and_annotation_layers

# Default muted annotation classes (user can remove them)
DEFAULT_ANNOTATION_CLASSES = [
    ("brick", "#c07b4b"),
    ("bush", "#6aa84f"),
    ("marker", "#5b9bd5"),
    ("looting pit", "#c94b4b"),
    ("otherwise interesting", "#8e7cc3"),
]


class ConfigPanel(QWidget):
    
    def __init__(self, plugin):
        super().__init__()

        self.plugin = plugin
        self.selected_class_color = QColor("#7d79c8")

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel(
            "No tiles or annotations layers found. Configure your project below."
        )

        title.setStyleSheet(
            "font-size: 16px; font-weight: bold;"
        )

        layout.addWidget(title)

        #
        # Annotation classes
        #

        layout.addWidget(QLabel("Annotation classes:"))

        class_row = QHBoxLayout()

        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText(
            "Add a class name, e.g. brick"
        )

        class_row.addWidget(self.class_input)

        self.color_btn = QPushButton("Choose color")
        self.color_btn.clicked.connect(self._pick_color)

        self._update_color_button()

        class_row.addWidget(self.color_btn)

        add_class_btn = QPushButton("Add class")
        add_class_btn.clicked.connect(self._add_class)

        class_row.addWidget(add_class_btn)

        layout.addLayout(class_row)

        self.class_list = QListWidget()

        layout.addWidget(self.class_list)

        # Populate sensible defaults (user can remove them)
        self._populate_default_classes()

        remove_class_btn = QPushButton("Remove selected class")
        remove_class_btn.clicked.connect(
            self._remove_selected_class
        )

        layout.addWidget(remove_class_btn)

        #
        # Tile settings
        #

        layout.addWidget(
            QLabel("Tile settings (map units):")
        )

        tile_row = QHBoxLayout()

        tile_row.addWidget(QLabel("Tile size:"))

        self.tile_size_spin = QDoubleSpinBox()
        self.tile_size_spin.setRange(1, 100000)
        self.tile_size_spin.setValue(50)
        self.tile_size_spin.setSingleStep(1)

        tile_row.addWidget(self.tile_size_spin)

        tile_row.addWidget(QLabel("Margin shown: 10%"))

        layout.addLayout(tile_row)

        #
        # Buttons
        #

        preview_btn = QPushButton(
            "Preview one tile extent"
        )

        preview_btn.clicked.connect(
            self._preview_tile
        )

        layout.addWidget(preview_btn)

        save_btn = QPushButton(
            "Save and create layers"
        )

        save_btn.clicked.connect(
            self._save_configuration
        )

        save_btn.setStyleSheet(
            "font-weight: bold; padding: 10px;"
        )

        layout.addWidget(save_btn)

        layout.addStretch()

    #
    # Color picker
    #

    def _pick_color(self):
        color = QColorDialog.getColor(
            self.selected_class_color,
            self,
            "Choose class color"
        )

        if not color.isValid():
            return

        self.selected_class_color = color

        self._update_color_button()

    def _update_color_button(self):
        self.color_btn.setStyleSheet(
            f"""
            background-color: {self.selected_class_color.name()};
            color: white;
            font-weight: bold;
            """
        )

    def _add_class_item(self, name, color_hex):
        """Add a class item programmatically with the given muted color."""
        # Avoid duplicates
        existing = [
            self.class_list.item(i).data(Qt.UserRole)["name"]
            for i in range(self.class_list.count())
        ]

        if name in existing:
            return

        color = QColor(color_hex)

        item = QListWidgetItem(f"{name} ({color.name()})")

        item.setData(
            Qt.UserRole,
            {
                "name": name,
                "color": color.name()
            }
        )

        item.setBackground(color)
        item.setForeground(QColor("black"))

        self.class_list.addItem(item)

    def _populate_default_classes(self):
        for name, hexcol in DEFAULT_ANNOTATION_CLASSES:
            self._add_class_item(name, hexcol)

    #
    # Class management
    #

    def _add_class(self):
        text = self.class_input.text().strip()

        if not text:
            return

        existing = [
            self.class_list.item(i)
            .data(Qt.UserRole)["name"]
            for i in range(self.class_list.count())
        ]

        if text in existing:
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                f'Class "{text}" already exists.'
            )
            return

        item = QListWidgetItem(
            f"{text} ({self.selected_class_color.name()})"
        )

        item.setData(
            Qt.UserRole,
            {
                "name": text,
                "color": self.selected_class_color.name()
            }
        )

        item.setBackground(self.selected_class_color)
        item.setForeground(QColor("black"))

        self.class_list.addItem(item)

        self.class_input.clear()

    def _remove_selected_class(self):
        selected = self.class_list.selectedItems()

        for item in selected:
            self.class_list.takeItem(
                self.class_list.row(item)
            )

    #
    # Tile preview
    #

    def _preview_tile(self):
        tile_size = self.tile_size_spin.value()

        if tile_size <= 0:
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                "Tile size must be greater than zero."
            )

            return

        raster_layer = self.plugin.iface.activeLayer()

        if not raster_layer or raster_layer.type() != QgsMapLayer.RasterLayer:
            rasters = [
                layer
                for layer in QgsProject.instance().mapLayers().values()
                if layer.type() == QgsMapLayer.RasterLayer
            ]

            raster_layer = rasters[0] if len(rasters) == 1 else None

        if raster_layer is None:
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                (
                    "Please select a raster layer or make a raster layer "
                    "active before previewing tiles."
                )
            )
            return

        extent = raster_layer.extent()
        width = extent.xMaximum() - extent.xMinimum()
        height = extent.yMaximum() - extent.yMinimum()

        columns = max(1, int(math.ceil(width / tile_size)))
        rows = max(1, int(math.ceil(height / tile_size)))
        num_tiles = columns * rows

        canvas = self.plugin.iface.mapCanvas()
        center = canvas.center()
        half = tile_size / 2.0

        preview_rect = QgsRectangle(
            center.x() - half,
            center.y() - half,
            center.x() + half,
            center.y() + half
        )

        margin = tile_size * 0.1

        preview_rect = QgsRectangle(
            preview_rect.xMinimum() - margin,
            preview_rect.yMinimum() - margin,
            preview_rect.xMaximum() + margin,
            preview_rect.yMaximum() + margin
        )

        canvas.setExtent(preview_rect)
        canvas.refresh()

        QMessageBox.information(
            self,
            "Annotation Workflow",
            f"Previewing one tile extent. Estimated number of tiles: {num_tiles}."
        )

    #
    # Save configuration
    #

    def _save_configuration(self):
        classes = [
            self.class_list.item(i).data(Qt.UserRole)
            for i in range(self.class_list.count())
        ]

        if not classes:
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                "Please add at least one annotation class."
            )

            return

        tile_size = self.tile_size_spin.value()

        config = {
            "classes": classes,
            "tile_size": tile_size,
        }

        created = create_tiles_and_annotation_layers(
            self.plugin.iface,
            self.plugin.layer_finder,
            self.plugin.tile_manager,
            config
        )

        if not created:
            return

        self.plugin.set_annotation_classes(classes)

        if self.plugin.dock:
            self.plugin.dock.set_mode("annotate")

        if self.plugin.tile_manager.current_tile_fid is None:
            self.plugin.tile_manager.next_tile()
        else:
            self.plugin.update_progress()

        QMessageBox.information(
            self,
            "Annotation Workflow",
            (
                "Tiles and annotations layers have "
                "been created.\n\n"
                "Ready to annotate!"
            )
        )