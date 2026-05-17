import os

from qgis.core import (
    QgsProject,
    QgsMapLayer
)
from qgis.PyQt.QtWidgets import QMessageBox
from .gui.init_toolbar_icon import InitToolbarIcon

from .annotator_dock import AnnotatorDock
from .services.annotation_service import AnnotationService
from .services.layer_service import LayerService
from .services.tile_service import TileService

class AnnotatorPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.layer_finder = LayerService(iface)
        self.tile_manager = TileService(iface, self.layer_finder, self.update_progress)
        self.annotation_manager = AnnotationService(iface, self.layer_finder)
        self.gui = InitToolbarIcon(
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

        self.dock._decide_mode()
        self.dock.show()

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
