import os

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon


class InitToolbarIcon:

    def __init__(self, iface, show_dock_callback, activate_class_callback, show_verifier_callback=None):
        self.iface = iface
        self.show_dock_callback = show_dock_callback
        self.activate_class_callback = activate_class_callback
        self.show_verifier_callback = show_verifier_callback

        self.action_open = None
        self.action_verifier = None

    def init_gui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "../../icon.png")

        self.action_open = QAction(
            QIcon(icon_path),
            "Annotation Workflow",
            self.iface.mainWindow()
        )
        self.action_open.triggered.connect(self.show_dock_callback)

        self.iface.addToolBarIcon(self.action_open)
        self.iface.addPluginToMenu("&Annotation Workflow", self.action_open)

        if self.show_verifier_callback:
            self.action_verifier = QAction(
                QIcon(icon_path),
                "Detection Verification",
                self.iface.mainWindow()
            )
            self.action_verifier.triggered.connect(self.show_verifier_callback)
            self.iface.addToolBarIcon(self.action_verifier)
            self.iface.addPluginToMenu("&Annotation Workflow", self.action_verifier)

    def unload(self):
        if self.action_open:
            self.iface.removeToolBarIcon(self.action_open)
            self.iface.removePluginMenu("&Annotation Workflow", self.action_open)
        if self.action_verifier:
            self.iface.removeToolBarIcon(self.action_verifier)
            self.iface.removePluginMenu("&Annotation Workflow", self.action_verifier)
