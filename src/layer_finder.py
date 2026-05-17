from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QMessageBox


class LayerFinder:

    def __init__(self, iface):
        self.iface = iface

    def get_layer(self, layer_name, warn=True):
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == layer_name:
                return layer

        if warn:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Annotation Workflow",
                f"Layer '{layer_name}' not found."
            )

        return None

    def has_tile_layer(self):
        return any(layer.name() == "tiles" for layer in QgsProject.instance().mapLayers().values())

    def has_annotation_layer(self):
        return any(layer.name() == "annotations" for layer in QgsProject.instance().mapLayers().values())

    def get_tile_layer(self, warn=True):
        return self.get_layer("tiles", warn=warn)

    def get_annotation_layer(self, warn=True):
        return self.get_layer("annotations", warn=warn)
