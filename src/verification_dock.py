from qgis.PyQt.QtWidgets import QDockWidget, QStackedWidget

from .gui.verification_panel import VerificationAnnotationPanel, VerificationSetupPanel


class VerificationDock(QDockWidget):

    def __init__(self, plugin):
        super().__init__("Detection Verification")
        self.plugin = plugin
        self.stack = QStackedWidget()
        self.setWidget(self.stack)

        self.setup_panel = VerificationSetupPanel(plugin)
        self.annotation_panel = VerificationAnnotationPanel(plugin)
        self.stack.addWidget(self.setup_panel)
        self.stack.addWidget(self.annotation_panel)

    def set_mode(self, mode):
        if mode == "setup":
            self.stack.setCurrentWidget(self.setup_panel)
        else:
            self.stack.setCurrentWidget(self.annotation_panel)
            self.annotation_panel.set_classifications(self.plugin.verification_classes)
            self.annotation_panel.refresh()
