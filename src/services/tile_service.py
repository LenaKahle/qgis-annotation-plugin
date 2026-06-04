from qgis.core import QgsRectangle
from qgis.PyQt.QtWidgets import QMessageBox


class TileService:

    def __init__(self, iface, layer_finder, progress_callback=None):
        self.iface = iface
        self.layer_finder = layer_finder
        self.progress_callback = progress_callback
        self.tile_layer = None
        self.current_tile_fid = None
        self.tile_selection_mode = False

    def _refresh_tile_layer(self):
        self.tile_layer = self.layer_finder.get_tile_layer()
        return self.tile_layer is not None

    def next_tile(self):
        if not self._refresh_tile_layer():
            return

        features = list(self.tile_layer.getFeatures())
        
        # If no current tile, pick the first todo tile
        if self.current_tile_fid is None:
            for feature in features:
                if feature["status"] == "todo":
                    self.current_tile_fid = feature.id()
                    self.zoom_to_feature(feature)
                    self._update_progress()
                    return
        else:
            # Find current tile position and start looking after it
            current_index = None
            for i, feature in enumerate(features):
                if feature.id() == self.current_tile_fid:
                    current_index = i
                    break
            
            # If current tile was found, start searching from the next one
            if current_index is not None:
                for feature in features[current_index + 1:]:
                    if feature["status"] == "todo":
                        self.current_tile_fid = feature.id()
                        self.zoom_to_feature(feature)
                        self._update_progress()
                        return
                
                # Wrap around to beginning if no todo found after current
                for feature in features:
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

    def mark_tile_as_done(self, fid):
        """
        Mark a specific tile as done by its feature ID.
        Does not advance to next tile.
        
        Args:
            fid: The feature ID of the tile to mark as done
            
        Returns:
            True if successful, False otherwise
        """
        if not self._refresh_tile_layer():
            return False

        feature = self.tile_layer.getFeature(fid)
        
        if not feature.isValid():
            return False
        
        self.tile_layer.startEditing()
        feature["status"] = "done"
        self.tile_layer.updateFeature(feature)
        self.tile_layer.commitChanges()
        
        self._update_progress()
        
        return True

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

    def get_todo_features(self):
        if not self._refresh_tile_layer():
            return []

        return [
            feature
            for feature in self.tile_layer.getFeatures()
            if feature["status"] == "todo"
        ]

    def select_tile(self, fid):
        if not self._refresh_tile_layer():
            return False

        feature = self.tile_layer.getFeature(fid)
        if not feature.isValid():
            return False

        self.current_tile_fid = fid
        self.zoom_to_feature(feature)
        self._update_progress()
        return True

    def _update_progress(self):
        if self.progress_callback:
            self.progress_callback()

    def zoom_to_feature(self, feature):
        rect = feature.geometry().boundingBox()
        margin = (rect.xMaximum() - rect.xMinimum()) * 0.1 # Add 10% margin on each side

        expanded = QgsRectangle(
            rect.xMinimum() - margin,
            rect.yMinimum() - margin,
            rect.xMaximum() + margin,
            rect.yMaximum() + margin
        )

        self.iface.mapCanvas().setExtent(expanded)
        self.iface.mapCanvas().refresh()
