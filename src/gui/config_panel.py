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

from qgis.core import QgsRectangle
from ..services.layer_service import create_tiles_and_annotation_layers


class ConfigPanel(QWidget):
    
    def __init__(self, plugin):
        super().__init__()

        self.plugin = plugin
        self.selected_class_color = QColor("red")

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

        tile_row.addWidget(QLabel("Margin:"))

        self.tile_margin_spin = QDoubleSpinBox()
        self.tile_margin_spin.setRange(0, 10000)
        self.tile_margin_spin.setValue(5)
        self.tile_margin_spin.setSingleStep(1)

        tile_row.addWidget(self.tile_margin_spin)

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

        brightness = (
            self.selected_class_color.red()
            + self.selected_class_color.green()
            + self.selected_class_color.blue()
        ) / 3

        if brightness < 128:
            item.setForeground(QColor("white"))
        else:
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

        margin = self.tile_margin_spin.value()

        config = {
            "classes": classes,
            "tile_size": tile_size,
            "margin": margin,
        }

        created = create_tiles_and_annotation_layers(
            self.plugin.iface,
            self.plugin.layer_finder,
            self.plugin.tile_manager,
            config
        )

        if not created:
            return

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