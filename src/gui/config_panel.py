import os

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QFileDialog,
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

from qgis.core import (
    QgsMapLayer,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from ..services.layer_service import (
    ANNOTATOR_PACKAGE_SUFFIX,
    apply_annotation_symbology,
    apply_tile_symbology,
    create_tiles_and_annotation_layers,
    estimate_tile_count,
)

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
        self._initialize_area_layer()
        self.refresh_existing_packages()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel(
            "Choose an existing annotation package or create a new one."
        )

        title.setStyleSheet(
            "font-size: 16px; font-weight: bold;"
        )

        layout.addWidget(title)

        layout.addWidget(QLabel("Continue with an existing annotator package:"))
        package_row = QHBoxLayout()
        self.package_combo = QComboBox()
        package_row.addWidget(self.package_combo)

        use_package_button = QPushButton("Use selected")
        use_package_button.clicked.connect(self._use_selected_package)
        package_row.addWidget(use_package_button)

        browse_package_button = QPushButton("Browse...")
        browse_package_button.clicked.connect(self._browse_existing_package)
        package_row.addWidget(browse_package_button)
        layout.addLayout(package_row)
        layout.addWidget(QLabel(
            "Or configure a new package and annotation layer below:"
        ))

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

        layout.addWidget(QLabel(
            "Optional tile areas (draw one or more freehand polygons):"
        ))
        area_row = QHBoxLayout()
        self.draw_areas_button = QPushButton("Draw tile areas")
        self.draw_areas_button.setCheckable(True)
        self.draw_areas_button.toggled.connect(self._toggle_area_drawing)
        area_row.addWidget(self.draw_areas_button)

        clear_areas_button = QPushButton("Clear areas")
        clear_areas_button.clicked.connect(self._clear_areas)
        area_row.addWidget(clear_areas_button)
        layout.addLayout(area_row)

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

    def refresh_existing_packages(self):
        selected_path = self.package_combo.currentData()
        packages = {}
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() != QgsMapLayer.VectorLayer or not layer.isValid():
                continue
            path = self.plugin.layer_finder.source_package_path(layer)
            if path.lower().endswith(ANNOTATOR_PACKAGE_SUFFIX):
                packages[os.path.abspath(path)] = os.path.basename(path)
        project_dir = QgsProject.instance().homePath()
        if project_dir and os.path.isdir(project_dir):
            for filename in os.listdir(project_dir):
                if filename.lower().endswith(ANNOTATOR_PACKAGE_SUFFIX):
                    path = os.path.abspath(os.path.join(project_dir, filename))
                    packages[path] = filename

        self.package_combo.clear()
        for path, label in sorted(packages.items(), key=lambda item: item[1].lower()):
            self.package_combo.addItem(label, path)

        if selected_path:
            index = self.package_combo.findData(selected_path)
            if index != -1:
                self.package_combo.setCurrentIndex(index)

    def _browse_existing_package(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose an annotator package",
            QgsProject.instance().homePath() or "",
            f"Annotator packages (*{ANNOTATOR_PACKAGE_SUFFIX})"
        )
        if not path:
            return
        if not path.lower().endswith(ANNOTATOR_PACKAGE_SUFFIX):
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                f"Choose a GeoPackage ending in {ANNOTATOR_PACKAGE_SUFFIX}."
            )
            return
        self._activate_package(path)

    def _use_selected_package(self):
        path = self.package_combo.currentData()
        if path:
            self._activate_package(path)

    def _activate_package(self, path):
        layers = self.plugin.layer_finder.load_package_layers(path)
        if layers is None:
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                "The selected GeoPackage must contain both 'tiles' and 'annotations' layers."
            )
            self.plugin.layer_finder.set_package_path(None)
            return

        classes = (
            self.plugin.dock.annotation_panel.load_classes_from_layer()
            if self.plugin.dock
            else []
        )
        apply_tile_symbology(layers["tiles"])
        if classes:
            apply_annotation_symbology(layers["annotations"], classes)
        self.plugin.tile_manager.current_tile_fid = None
        self.plugin.set_annotation_classes(classes)
        if self.plugin.dock:
            self.plugin.dock.set_mode("annotate")
            self.plugin.tile_manager.next_tile()

    def _initialize_area_layer(self):
        project = QgsProject.instance()
        for layer in project.mapLayers().values():
            if (
                layer.customProperty("annotation_workflow/tile_areas", False)
                and layer.isValid()
            ):
                self.area_layer = layer
                return

        crs = self.plugin.iface.mapCanvas().mapSettings().destinationCrs()
        self.area_layer = QgsVectorLayer(
            f"Polygon?crs={crs.authid()}",
            "Tile generation areas (temporary)",
            "memory"
        )
        self.area_layer.setCustomProperty(
            "annotation_workflow/tile_areas",
            True
        )
        project.addMapLayer(self.area_layer)

    def _toggle_area_drawing(self, enabled):
        if enabled:
            self.draw_areas_button.setText("Finish drawing areas")
            self.plugin.start_area_drawing(self.area_layer)
        else:
            self.draw_areas_button.setText("Draw tile areas")
            self.plugin.stop_area_drawing()

    def _clear_areas(self):
        feature_ids = [feature.id() for feature in self.area_layer.getFeatures()]
        if not feature_ids:
            return

        self.area_layer.startEditing()
        self.area_layer.deleteFeatures(feature_ids)
        if not self.area_layer.commitChanges():
            QMessageBox.critical(
                self,
                "Annotation Workflow",
                "Could not clear the temporary tile areas layer."
            )
            return
        self.area_layer.updateExtents()
        self.area_layer.triggerRepaint()

    def _get_raster_layer(self):
        return self.plugin.get_target_raster_layer()

    def _tile_count(self, raster_layer):
        return estimate_tile_count(
            raster_layer,
            self.tile_size_spin.value(),
            self.area_layer
        )

    def _warn_for_tile_count(self, count, confirm=False):
        if count > 50000:
            message = (
                f"This will create {count:,} tiles, which is an extremely "
                "large number and may take a long time or use substantial "
                "resources. Continue?"
            )
            if confirm:
                return QMessageBox.warning(
                    self,
                    "Strong warning: very large tile generation",
                    message,
                    QMessageBox.Yes | QMessageBox.Cancel,
                    QMessageBox.Cancel
                ) == QMessageBox.Yes
            QMessageBox.warning(
                self,
                "Strong warning: very large tile generation",
                message
            )
        elif count > 30000:
            message = (
                f"This will create {count:,} tiles. Tile generation may take "
                "a long time. Continue?"
            )
            if confirm:
                return QMessageBox.warning(
                    self,
                    "Large tile generation",
                    message,
                    QMessageBox.Yes | QMessageBox.Cancel,
                    QMessageBox.Cancel
                ) == QMessageBox.Yes
            QMessageBox.warning(self, "Large tile generation", message)
        elif confirm:
            return True
        return not confirm

    def _preview_tile(self):
        if self.plugin.area_map_tool:
            QMessageBox.information(
                self,
                "Annotation Workflow",
                "Finish drawing tile areas before previewing tile counts."
            )
            return

        tile_size = self.tile_size_spin.value()

        if tile_size <= 0:
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                "Tile size must be greater than zero."
            )

            return

        raster_layer = self._get_raster_layer()
        if raster_layer is None:
            return

        num_tiles = self._tile_count(raster_layer)
        self._warn_for_tile_count(num_tiles)

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
            (
                "Previewing one tile extent. "
                f"Estimated number of tiles: {num_tiles:,}."
            )
        )

    #
    # Save configuration
    #

    def _save_configuration(self):
        if self.plugin.area_map_tool:
            QMessageBox.information(
                self,
                "Annotation Workflow",
                "Finish drawing tile areas before creating tiles."
            )
            return

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
        raster_layer = self._get_raster_layer()
        if raster_layer is None:
            return

        tile_count = self._tile_count(raster_layer)
        if tile_count == 0:
            QMessageBox.warning(
                self,
                "Annotation Workflow",
                "No tiles intersect the selected areas. Adjust or clear the areas and try again."
            )
            return
        if not self._warn_for_tile_count(tile_count, confirm=True):
            return

        config = {
            "classes": classes,
            "tile_size": tile_size,
            "raster_layer": raster_layer,
        }

        created = create_tiles_and_annotation_layers(
            self.plugin.iface,
            self.plugin.layer_finder,
            self.plugin.tile_manager,
            config,
            self.area_layer
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