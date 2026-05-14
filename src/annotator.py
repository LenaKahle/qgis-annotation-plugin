import os

from .annotator_dock import AnnotatorDock
from .annotation_manager import AnnotationManager
from .gui import PluginGui
from .layer_finder import LayerFinder
from .tile_manager import TileManager


class BrickAnnotatorPlugin:

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

        if self.tile_manager.current_tile_fid is None:
            self.tile_manager.next_tile()
        else:
            self.update_progress()

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

    def previous_tile(self):
        self.tile_manager.previous_tile()

    def mark_done(self):
        self.tile_manager.mark_done()

    def mark_skipped(self):
        self.tile_manager.mark_skipped()
