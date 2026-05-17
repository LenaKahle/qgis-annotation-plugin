import os

from qgis.core import (
    QgsProject,
    QgsMapLayer
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox

from .annotator_dock import AnnotatorDock
from .annotation_manager import AnnotationManager
from .gui import PluginGui
from .layer_finder import LayerFinder
from .tile_manager import TileManager
from .layer_creator import create_tile_layer, create_annotation_layer, ensure_field


class AnnotatorPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.layer_finder = LayerFinder(iface)
        self.tile_manager = TileManager(iface, self.layer_finder, self.update_progress)
        self.annotation_manager = AnnotationManager(iface, self.layer_finder)
        self.gui = PluginGui(
            iface,
            show_dock_callback=self.show_dock,
            activate_bush_callback=lambda: self.annotation_manager.activate_annotation_class("bush"),
            activate_brick_callback=lambda: self.annotation_manager.activate_annotation_class("brick")
        )

        self.dock = None

    # ---------------------------------------------------------
    # GUI
    # ---------------------------------------------------------

    def initGui(self):
        self.gui.init_gui()

    def unload(self):
        self.gui.unload()

        if self.dock:
            self.iface.removeDockWidget(self.dock)

    # ---------------------------------------------------------
    # DOCK
    # ---------------------------------------------------------

    def show_dock(self):
        if not self.dock:
            self.dock = AnnotatorDock(self)
            self.iface.addDockWidget(2, self.dock)

        self.dock.show()
        self.dock.set_mode("config" if self.should_show_configuration() else "annotate")

        if not self.should_show_configuration():
            if self.tile_manager.current_tile_fid is None:
                self.tile_manager.next_tile()
            else:
                self.update_progress()

    def should_show_configuration(self):
        return not (
            self.layer_finder.has_tile_layer() and
            self.layer_finder.has_annotation_layer()
        )

    def get_target_raster_layer(self):
        active = self.iface.activeLayer()
        if active and active.type() == QgsMapLayer.RasterLayer:
            return active

        rasters = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.RasterLayer
        ]

        if len(rasters) == 1:
            return rasters[0]

        QMessageBox.warning(
            self.iface.mainWindow(),
            "Annotation Workflow",
            "Please select a raster layer or make a raster layer active before creating tiles."
        )
        return None

    def create_tiles_and_annotation_layers(self, classes, tile_size, margin):
        if not classes:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Annotation Workflow",
                "Add at least one annotation class before saving."
            )
            return False

        raster_layer = self.get_target_raster_layer()
        if raster_layer is None:
            return False

        tile_layer = self.layer_finder.get_tile_layer(warn=False)
        annotation_layer = self.layer_finder.get_annotation_layer(warn=False)

        if tile_layer is None:
            tile_layer = create_tile_layer(raster_layer, tile_size)
        else:
            ensure_field(tile_layer, "status", QVariant.String)

        if annotation_layer is None:
            annotation_layer = create_annotation_layer(raster_layer)
        else:
            ensure_field(annotation_layer, "class", QVariant.String)

        if self.dock:
            self.dock.set_mode("annotate")

        self.tile_manager.next_tile()
        return True

    # ---------------------------------------------------------
    # ANNOTATION
    # ---------------------------------------------------------

    def activate_annotation_class(self, class_name):
        self.annotation_manager.activate_annotation_class(class_name)

    # ---------------------------------------------------------
    # PROGRESS
    # ---------------------------------------------------------

    def update_progress(self):
        done, total = self.tile_manager.get_progress_counts()
        if self.dock:
            self.dock.progress_label.setText(f"{done}/{total} tiles annotated")

    # ---------------------------------------------------------
    # TILE ACTIONS
    # ---------------------------------------------------------

    def next_tile(self):
        self.tile_manager.next_tile()

    def recenter_current_tile(self):
        self.tile_manager.recenter_current_tile()

    def mark_done(self):
        self.tile_manager.mark_done()

    def mark_skipped(self):
        self.tile_manager.mark_skipped()
