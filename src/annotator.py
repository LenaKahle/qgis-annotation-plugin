import os

from qgis.PyQt.QtWidgets import QAction, QMessageBox, QShortcut
from qgis.PyQt.QtGui import QIcon, QKeySequence

from qgis.core import (
    QgsProject,
    QgsField,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsSingleSymbolRenderer,
    QgsEditorWidgetSetup,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsFillSymbol,
    QgsRectangle,
    QgsDefaultValue,
    QgsVectorLayer,
    QgsGeometry,
    QgsFeature

)

from qgis.PyQt.QtCore import QVariant

from .annotator_dock import AnnotatorDock

applicationName = "Annotation Helper"
tilesFileName = "tiles.gpkg"

class AnnotatorPlugin:

    def __init__(self, iface):

        self.iface = iface

        self.plugin_dir = os.path.dirname(__file__)

        self.tile_layer = None
        self.annotation_layer = None

        self.current_tile_fid = None

        self.current_class = None

        self.dock = None

    # ---------------------------------------------------------
    # GUI
    # ---------------------------------------------------------

    def initGui(self):

        icon_path = os.path.join(self.plugin_dir, "icon.png")

        self.action_open = QAction(
            QIcon(icon_path),
            "Annotation Helper",
            self.iface.mainWindow()
        )
    
        self.action_open.triggered.connect(self.show_dock)

        self.iface.addToolBarIcon(self.action_open)

        self.iface.addPluginToMenu(
            applicationName,
            self.action_open
        )

        # shortcuts

        self.shortcut_bush = QShortcut(
            QKeySequence("Ctrl+1"),
            self.iface.mainWindow()
        )

        self.shortcut_bush.activated.connect(
            lambda: self.activate_annotation_class("bush")
        )

        self.shortcut_brick = QShortcut(
            QKeySequence("Ctrl+2"),
            self.iface.mainWindow()
        )

        self.shortcut_brick.activated.connect(
            lambda: self.activate_annotation_class("brick")
        )

    def unload(self):

        self.iface.removeToolBarIcon(self.action_open)

        self.iface.removePluginMenu(
            applicationName,
            self.action_open
        )

        if self.dock:
            self.iface.removeDockWidget(self.dock)

    # ---------------------------------------------------------
    # DOCK
    # ---------------------------------------------------------

    def show_dock(self):

        if not self.dock:

            self.dock = AnnotatorDock(self)

            self.iface.addDockWidget(
                2,
                self.dock
            )

        self.dock.show()

        self.tile_layer = self.get_tile_layer()

        if self.current_tile_fid is None:
            self.next_tile()
        else:
            self.update_progress()

    # ---------------------------------------------------------
    # LAYERS
    # ---------------------------------------------------------

    def get_tile_layer(self, silent=False):

        layers = QgsProject.instance().mapLayers().values()

        for layer in layers:

            if layer.name() == "tiles":

                return layer

        if not silent:

            QMessageBox.warning(
                self.iface.mainWindow(),
                applicationName,
                "Layer 'tiles' not found."
            )

        return None

    def get_annotation_layer(self, silent=False):

        layers = QgsProject.instance().mapLayers().values()

        for layer in layers:

            if layer.name() == "annotations":

                self.configure_annotation_layer(layer)

                return layer

        if not silent:

            QMessageBox.warning(
                self.iface.mainWindow(),
                applicationName,
                "Layer 'annotations' not found."
            )

        return None
    
    def layers_exist(self):

        return (
            self.get_tile_layer(silent=True) is not None
            and
            self.get_annotation_layer(silent=True) is not None
        )

    # ---------------------------------------------------------
    # TILE NAVIGATION
    # ---------------------------------------------------------

    def next_tile(self):

        self.tile_layer = self.get_tile_layer()

        if not self.tile_layer:
            return

        for feature in self.tile_layer.getFeatures():

            if feature["status"] == "todo":

                self.current_tile_fid = feature.id()

                self.zoom_to_feature(feature)

                self.update_progress()

                return

        QMessageBox.information(
            self.iface.mainWindow(),
            applicationName,
            "No TODO tiles remaining."
        )

    # ---------------------------------------------------------
    # TILE STATUS
    # ---------------------------------------------------------

    def mark_done(self):

        self.update_current_tile("done")

    def mark_skipped(self):

        self.update_current_tile("skipped")

    def update_current_tile(self, new_status):

        self.tile_layer = self.get_tile_layer()

        if not self.tile_layer:
            return

        feature = self.tile_layer.getFeature(
            self.current_tile_fid
        )

        self.tile_layer.startEditing()

        feature["status"] = new_status

        self.tile_layer.updateFeature(feature)

        self.tile_layer.commitChanges()

        self.next_tile()

    # ---------------------------------------------------------
    # PROGRESS
    # ---------------------------------------------------------

    def update_progress(self):

        done = 0
        total = 0

        for f in self.tile_layer.getFeatures():

            status = f["status"]

            if status in ["todo", "done", "skipped"]:
                total += 1

            if status in ["done", "skipped"]:
                done += 1

        if self.dock:

            self.dock.progress_label.setText(
                f"{done}/{total} tiles annotated"
            )

    # ---------------------------------------------------------
    # ANNOTATION
    # ---------------------------------------------------------

    def activate_annotation_class(self, class_name):

        self.current_class = class_name

        self.annotation_layer = self.get_annotation_layer()

        if not self.annotation_layer:
            return

        self.iface.setActiveLayer(self.annotation_layer)

        self.annotation_layer.startEditing()

        # -----------------------------------------
        # set default class value
        # -----------------------------------------

        class_idx = self.annotation_layer.fields().indexOf("class")

        self.annotation_layer.setDefaultValueDefinition(
            class_idx,
            QgsDefaultValue(f"'{class_name}'")
        )

        # -----------------------------------------
        # activate polygon drawing
        # -----------------------------------------

        self.iface.actionAddFeature().trigger()

        self.iface.messageBar().pushMessage(
            applicationName,
            f"Drawing {class_name}",
            level=0,
            duration=2
        )

    # ---------------------------------------------------------
    # VIEW
    # ---------------------------------------------------------

    def zoom_to_feature(self, feature):

        rect = feature.geometry().boundingBox()

        margin = 20

        expanded = QgsRectangle(
            rect.xMinimum() - margin,
            rect.yMinimum() - margin,
            rect.xMaximum() + margin,
            rect.yMaximum() + margin
        )

        self.iface.mapCanvas().setExtent(expanded)

        self.iface.mapCanvas().refresh()

    def preview_zoom(self):

        tile_size = float(
            self.dock.tile_size_input.text()
        )

        margin = float(
            self.dock.margin_input.text()
        )

        canvas = self.iface.mapCanvas()

        center = canvas.center()

        rect = QgsRectangle(
            center.x() - tile_size/2 - margin,
            center.y() - tile_size/2 - margin,
            center.x() + tile_size/2 + margin,
            center.y() + tile_size/2 + margin
        )

        canvas.setExtent(rect)

        canvas.refresh()

    def recenter_current_tile(self):

        if self.current_tile_fid is None:
            return

        feature = self.tile_layer.getFeature(
            self.current_tile_fid
        )

        self.zoom_to_feature(feature)

    # ---------------------------------------------------------
    # LAYER CREATION
    
    def create_project_layers(self):

        raster = self.iface.activeLayer()

        if not raster:

            QMessageBox.warning(
                self.iface.mainWindow(),
                applicationName,
                "Select orthophoto layer first."
            )

            return

        extent = raster.extent()

        crs = raster.crs()

        tile_size = float(
            self.dock.tile_size_input.text()
        )

        output_path = os.path.join(
            os.path.dirname(raster.source()),
            tilesFileName
        )

        # ---------------------------------------------------------
        # tiles layer
        # ---------------------------------------------------------

        tiles_uri = (
            f"Polygon?crs={crs.authid()}"
        )

        tiles = QgsVectorLayer(
            tiles_uri,
            "tiles",
            "memory"
        )

        provider = tiles.dataProvider()

        provider.addAttributes([
            QgsField("id", QVariant.Int),
            QgsField("status", QVariant.String)
        ])

        tiles.updateFields()

        features = []

        idx = 0

        y = extent.yMinimum()

        while y < extent.yMaximum():

            x = extent.xMinimum()

            while x < extent.xMaximum():

                rect = QgsRectangle(
                    x,
                    y,
                    x + tile_size,
                    y + tile_size
                )

                feat = QgsFeature()

                feat.setGeometry(
                    QgsGeometry.fromRect(rect)
                )

                feat.setAttributes([
                    idx,
                    "todo"
                ])

                features.append(feat)

                idx += 1

                x += tile_size

            y += tile_size

        provider.addFeatures(features)

        QgsProject.instance().addMapLayer(tiles)

        self.style_tiles_layer(tiles)

        # ---------------------------------------------------------
        # annotations layer
        # ---------------------------------------------------------

        annotations_uri = (
            f"Polygon?crs={crs.authid()}"
        )

        annotations = QgsVectorLayer(
            annotations_uri,
            "annotations",
            "memory"
        )

        provider = annotations.dataProvider()

        provider.addAttributes([
            QgsField("class", QVariant.String),
            QgsField("tile_id", QVariant.Int)
        ])

        annotations.updateFields()

        QgsProject.instance().addMapLayer(
            annotations
        )

        self.configure_annotation_layer(
            annotations
        )

        # suppress popup forms

        config = annotations.editFormConfig()

        config.setSuppress(
            config.SuppressOn
        )

        annotations.setEditFormConfig(config)

        self.dock.build_ui()

        self.next_tile()

    def style_tiles_layer(self, layer):

        categories = []

        statuses = {
            "todo": "#4488ff",
            "done": "#44aa44",
            "skipped": "#aaaaaa"
        }

        for status, color in statuses.items():

            symbol = QgsFillSymbol.createSimple({
                "color": "0,0,0,0",
                "outline_color": color,
                "outline_width": "0.8"
            })

            cat = QgsRendererCategory(
                status,
                symbol,
                status
            )

            categories.append(cat)

        renderer = QgsCategorizedSymbolRenderer(
            "status",
            categories
        )

        layer.setRenderer(renderer)

        layer.triggerRepaint()


    def configure_annotation_layer(self, layer):

        # ---------------------------------------------------------
        # CLASS DROPDOWN (VALUEMAP)
        # ---------------------------------------------------------

        class_idx = layer.fields().indexOf("class")

        if class_idx == -1:
            return

        setup = {
            "map": {
                "brick": "brick",
                "bush": "bush"
            }
        }

        layer.setEditorWidgetSetup(
            class_idx,
            QgsEditorWidgetSetup(
                "ValueMap",
                setup
            )
        )

        # ---------------------------------------------------------
        # CATEGORIZED RENDERER
        # ---------------------------------------------------------

        categories = []

        class_colors = {
            "brick": "#cc4422",
            "bush": "#44aa55"
        }

        for class_name, color in class_colors.items():

            symbol = QgsFillSymbol.createSimple({
                "color": "0,0,0,0",
                "outline_color": color,
                "outline_width": "1"
            })

            category = QgsRendererCategory(
                class_name,
                symbol,
                class_name
            )

            categories.append(category)

        renderer = QgsCategorizedSymbolRenderer(
            "class",
            categories
        )

        layer.setRenderer(renderer)

        # ---------------------------------------------------------
        # SUPPRESS ATTRIBUTE POPUPS
        # ---------------------------------------------------------

        config = layer.editFormConfig()

        config.setSuppress(
            config.SuppressOn
        )

        layer.setEditFormConfig(config)

        layer.triggerRepaint()