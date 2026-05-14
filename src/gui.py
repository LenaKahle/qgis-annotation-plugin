import os

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon


class PluginGui:

    def __init__(self, iface, show_dock_callback, activate_bush_callback, activate_brick_callback):
        self.iface = iface
        self.show_dock_callback = show_dock_callback
        self.activate_bush_callback = activate_bush_callback
        self.activate_brick_callback = activate_brick_callback

        self.action_open = None

    def init_gui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "../icon.png")

        self.action_open = QAction(
            QIcon(icon_path),
            "Brick Annotator",
            self.iface.mainWindow()
        )
        self.action_open.triggered.connect(self.show_dock_callback)

        self.iface.addToolBarIcon(self.action_open)
        self.iface.addPluginToMenu("&Brick Annotator", self.action_open)

    def unload(self):
        if self.action_open:
            self.iface.removeToolBarIcon(self.action_open)
            self.iface.removePluginMenu("&Brick Annotator", self.action_open)
