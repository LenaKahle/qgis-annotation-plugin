from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QSizePolicy,
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
        self.stack.setMinimumWidth(0)
        self.stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        outer_layout.addWidget(self.stack)

        self.config_panel = ConfigPanel(plugin)
        self.annotation_panel = AnnotationPanel(plugin)

        self.stack.addWidget(self.config_panel)
        self.stack.addWidget(self.annotation_panel)

        self.progress_label = self.annotation_panel.progress_label

        outer_layout.addStretch()
        self.setMinimumWidth(240)
        self.resize(320, self.sizeHint().height())
        self._decide_mode()


    def set_mode(self, mode):
        if mode == "config":
            self.stack.setCurrentWidget(self.config_panel)
        else:
            self.stack.setCurrentWidget(self.annotation_panel)


    def _decide_mode(self):
        self.config_panel.refresh_existing_packages()
        self.set_mode("config")
