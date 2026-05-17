from qgis.core import QgsRectangle
from qgis.PyQt.QtWidgets import QMessageBox


class TileService:

    def __init__(self, iface, layer_finder, progress_callback=None):
        self.iface = iface
        self.layer_finder = layer_finder
        self.progress_callback = progress_callback
        self.tile_layer = None
        self.current_tile_fid = None

    def _refresh_tile_layer(self):
        self.tile_layer = self.layer_finder.get_tile_layer()
        return self.tile_layer is not None

    def next_tile(self):
        if not self._refresh_tile_layer():
            return

        for feature in self.tile_layer.getFeatures():
            if feature["status"] == "todo":
                self.current_tile_fid = feature.id()
                self.zoom_to_feature(feature)
                self._update_progress()
                return

        QMessageBox.information(
            self.iface.mainWindow(),
            "Annotation Workflow",
            "Done! No TODO tiles remaining."
        )

    def recenter_current_tile(self):
        if self.current_tile_fid is None:
            return

        if not self._refresh_tile_layer():
            return

        feature = self.tile_layer.getFeature(self.current_tile_fid)
        if not feature.isValid():
            return

        self.zoom_to_feature(feature)

    def mark_done(self):
        self.update_current_tile("done")

    def mark_skipped(self):
        self.update_current_tile("skipped")

    def update_current_tile(self, new_status):
        if not self._refresh_tile_layer():
            return

        feature = self.tile_layer.getFeature(self.current_tile_fid)
        self.tile_layer.startEditing()
        feature["status"] = new_status
        self.tile_layer.updateFeature(feature)
        self.tile_layer.commitChanges()

        self.next_tile()

    def get_progress_counts(self):
        if not self._refresh_tile_layer():
            return 0, 0

        done = 0
        total = 0

        for feature in self.tile_layer.getFeatures():
            status = feature["status"]
            if status in ["todo", "done", "skipped"]:
                total += 1
            if status in ["done", "skipped"]:
                done += 1

        return done, total

    def _update_progress(self):
        if self.progress_callback:
            self.progress_callback()

    def zoom_to_feature(self, feature):
        rect = feature.geometry().boundingBox()
        margin = 20

        expanded = QgsRectangle(
            rect.xMinimum() - margin,
            rect.yMinimum() - margin,
            rect.xMaximum() + margin,
            rect.yMaximum() + margin
        )

        self.iface.mapCanvas().setExtent(expanded)
        self.iface.mapCanvas().refresh()
