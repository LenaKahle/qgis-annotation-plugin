import os

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon


class InitToolbarIcon:

    def __init__(self, iface, show_dock_callback, activate_class_callback):
        self.iface = iface
        self.show_dock_callback = show_dock_callback
        self.activate_class_callback = activate_class_callback

        self.action_open = None

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

    def unload(self):
        if self.action_open:
            self.iface.removeToolBarIcon(self.action_open)
            self.iface.removePluginMenu("&Annotation Workflow", self.action_open)
