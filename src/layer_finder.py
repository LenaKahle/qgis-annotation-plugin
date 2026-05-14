from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QMessageBox


class LayerFinder:

    def __init__(self, iface):
        self.iface = iface

    def get_layer(self, layer_name):
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == layer_name:
                return layer

        QMessageBox.warning(
            self.iface.mainWindow(),
            "Brick Annotator",
            f"Layer '{layer_name}' not found."
        )

        return None

    def get_tile_layer(self):
        return self.get_layer("tiles")

    def get_annotation_layer(self):
        return self.get_layer("annotations")
