from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QStackedWidget
)
from .gui.config_panel import ConfigPanel
from .gui.annotation_panel import AnnotationPanel


class AnnotatorDock(QDockWidget):

    def __init__(self, plugin):
        super().__init__("Annotation Workflow")

        self.plugin = plugin

        container = QWidget()
        self.setWidget(container)

        outer_layout = QVBoxLayout()
        container.setLayout(outer_layout)

        self.stack = QStackedWidget()
        outer_layout.addWidget(self.stack)

        self.config_panel = ConfigPanel(plugin)
        self.annotate_panel = AnnotationPanel(plugin)

        self.stack.addWidget(self.config_panel)
        self.stack.addWidget(self.annotate_panel)

        self.progress_label = self.annotate_panel.progress_label

        outer_layout.addStretch()
        self._decide_mode()


    def set_mode(self, mode):
        if mode == "config":
            self.stack.setCurrentWidget(self.config_panel)
        else:
            self.stack.setCurrentWidget(self.annotate_panel)


    def _decide_mode(self):
        if not (self.plugin.layer_finder.has_tile_layer() and self.plugin.layer_finder.has_annotation_layer()):
            self.set_mode("config")
        else:
            self.set_mode("annotate")
            if self.plugin.tile_manager.current_tile_fid is None:
                self.plugin.tile_manager.next_tile()
            else:
                self.plugin.update_progress()
