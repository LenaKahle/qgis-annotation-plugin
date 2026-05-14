import os

from qgis.PyQt.QtWidgets import QAction, QMessageBox, QShortcut
from qgis.PyQt.QtGui import QIcon, QKeySequence

from qgis.core import (
    QgsProject,
    QgsFeatureRequest,
    QgsRectangle,
    QgsVectorLayer,
    QgsDefaultValue
)

from qgis.utils import iface

from .annotator_dock import AnnotatorDock


class BrickAnnotatorPlugin:

    def __init__(self, iface):

        self.iface = iface

        self.plugin_dir = os.path.dirname(__file__)

        self.tile_layer = None
        self.annotation_layer = None

        self.current_tile_fid = None
        self.tile_history = []

        self.current_class = None

        self.dock = None

    # ---------------------------------------------------------
    # GUI
    # ---------------------------------------------------------

    def initGui(self):

        icon_path = os.path.join(self.plugin_dir, "../icon.png")

        self.action_open = QAction(
            QIcon(icon_path),
            "Brick Annotator",
            self.iface.mainWindow()
        )

        self.action_open.triggered.connect(self.show_dock)

        self.iface.addToolBarIcon(self.action_open)

        self.iface.addPluginToMenu(
            "&Brick Annotator",
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
            "&Brick Annotator",
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

    def get_tile_layer(self):

        layers = QgsProject.instance().mapLayers().values()

        for layer in layers:
            if layer.name() == "tiles":
                return layer

        QMessageBox.warning(
            self.iface.mainWindow(),
            "Brick Annotator",
            "Layer 'tiles' not found."
        )

        return None

    def get_annotation_layer(self):

        layers = QgsProject.instance().mapLayers().values()

        for layer in layers:
            if layer.name() == "annotations":
                return layer

        QMessageBox.warning(
            self.iface.mainWindow(),
            "Brick Annotator",
            "Layer 'annotations' not found."
        )

        return None

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

                self.tile_history.append(feature.id())

                self.zoom_to_feature(feature)

                self.update_progress()

                return

        QMessageBox.information(
            self.iface.mainWindow(),
            "Brick Annotator",
            "No TODO tiles remaining."
        )

    def previous_tile(self):

        if len(self.tile_history) < 2:
            return

        self.tile_history.pop()

        prev_fid = self.tile_history.pop()

        feature = self.tile_layer.getFeature(prev_fid)

        self.current_tile_fid = prev_fid

        self.zoom_to_feature(feature)

        self.update_progress()

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
            "Brick Annotator",
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