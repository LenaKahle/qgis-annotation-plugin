import os

from qgis.core import (
    QgsProject,
    QgsMapLayer
)
from qgis.gui import QgsMapTool
from qgis.PyQt.QtCore import Qt
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
        self.annotation_classes = []

        self.layer_finder = LayerService(iface)
        self.tile_manager = TileService(iface, self.layer_finder, self.update_progress)
        self.annotation_manager = AnnotationService(iface, self.layer_finder)
        self.gui = InitToolbarIcon(
            iface,
            show_dock_callback=self.show_dock,
            activate_class_callback=self.activate_annotation_class
        )

        self.dock = None
        self.map_tool = None
        self.previous_tool = None

    # ---------------------------------------------------------
    # GUI
    # ---------------------------------------------------------

    def initGui(self):
        self.gui.init_gui()

    def unload(self):
        self.gui.unload()

        if self.dock:
            self.iface.removeDockWidget(self.dock)

        self._deactivate_tile_selection_mode()

    # ---------------------------------------------------------
    # DOCK
    # ---------------------------------------------------------

    def show_dock(self):
        if not self.dock:
            self.dock = AnnotatorDock(self)
            self.iface.addDockWidget(2, self.dock)

        if hasattr(self.dock, "annotation_panel"):
            self.dock.annotation_panel.set_annotation_classes(None)

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

    def set_annotation_classes(self, classes):
        self.annotation_classes = classes

        # push into UI if dock exists
        if self.dock:
            self.dock.annotation_panel.set_annotation_classes(classes)

    def change_annotation_class(self):
        self.annotation_manager.change_annotation_class_dialog(self.iface.mainWindow(), self.annotation_classes)

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

    def select_todo_tile(self, fid):
        return self.tile_manager.select_tile(fid)

    def activate_tile_selection_mode(self):
        """
        Activate mode where clicking on a tile marks it as done.
        """
        self.tile_manager.tile_selection_mode = True
        self.iface.messageBar().pushMessage(
            "Annotation Workflow",
            "Click on a tile to mark it as done.",
            level=0,
            duration=3
        )
        
        # Save current tool and set our custom tool
        canvas = self.iface.mapCanvas()
        self.previous_tool = canvas.mapTool()
        
        self.map_tool = TileSelectionMapTool(canvas, self.tile_manager, self.iface)
        canvas.setMapTool(self.map_tool)

    def _deactivate_tile_selection_mode(self):
        """
        Deactivate tile selection mode and restore previous tool.
        """
        self.tile_manager.tile_selection_mode = False
        
        if self.map_tool:
            canvas = self.iface.mapCanvas()
            if self.previous_tool:
                canvas.setMapTool(self.previous_tool)
            self.map_tool = None
            self.previous_tool = None


class TileSelectionMapTool(QgsMapTool):
    """
    Custom map tool for selecting tiles with mouse clicks.
    """
    
    def __init__(self, canvas, tile_manager, iface):
        super().__init__(canvas)
        self.tile_manager = tile_manager
        self.iface = iface
        self.setCursor(Qt.PointingHandCursor)
    
    def canvasReleaseEvent(self, event):
        """
        Handle canvas mouse release - mark clicked tile as done.
        """
        if not self.tile_manager.tile_selection_mode:
            return
        
        # Convert pixel coordinates to map coordinates
        point = self.toMapCoordinates(event.pos())
        
        # Get the tile layer
        if not self.tile_manager._refresh_tile_layer():
            return
        
        tile_layer = self.tile_manager.tile_layer
        
        # Find tile at click point
        for feature in tile_layer.getFeatures():
            if feature.geometry().contains(point):
                # Mark this tile as done
                if self.tile_manager.mark_tile_as_done(feature.id()):
                    self.iface.messageBar().pushMessage(
                        "Annotation Workflow",
                        f"Marked tile {feature.id()} as done.",
                        level=0,
                        duration=2
                    )
                    return
        
        # No tile found at click point
        self.iface.messageBar().pushMessage(
            "Annotation Workflow",
            "No tile found at clicked location.",
            level=1,
            duration=2
        )


