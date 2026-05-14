from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QHBoxLayout
)

from qgis.PyQt.QtCore import Qt


class AnnotatorDock(QDockWidget):

    def __init__(self, plugin):

        super().__init__("Annotation Tool")

        self.plugin = plugin

        self.container = QWidget()

        self.setWidget(self.container)

        self.layout = QVBoxLayout()

        self.container.setLayout(self.layout)

        self.build_ui()

    # ---------------------------------------------------------
    # BUILD UI
    # ---------------------------------------------------------

    def clear_layout(self):

        while self.layout.count():

            item = self.layout.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

    def build_ui(self):

        self.clear_layout()

        if not self.plugin.layers_exist():

            self.build_setup_ui()

        else:

            self.build_annotation_ui()

    # ---------------------------------------------------------
    # SETUP UI
    # ---------------------------------------------------------

    def build_setup_ui(self):

        title = QLabel("Initial Project Setup")
        title.setStyleSheet("font-size:18px;font-weight:bold;")

        self.layout.addWidget(title)

        # -----------------------------------------
        # classes
        # -----------------------------------------

        self.layout.addWidget(QLabel("Classes"))

        self.class_list = QListWidget()

        self.class_list.addItem("brick")
        self.class_list.addItem("bush")

        self.layout.addWidget(self.class_list)

        # -----------------------------------------
        # tile size
        # -----------------------------------------

        self.layout.addWidget(QLabel("Tile Size (meters)"))

        self.tile_size_input = QLineEdit("500")

        self.layout.addWidget(self.tile_size_input)

        # -----------------------------------------
        # margin
        # -----------------------------------------

        self.layout.addWidget(QLabel("Margin (meters)"))

        self.margin_input = QLineEdit("20")

        self.layout.addWidget(self.margin_input)

        # -----------------------------------------
        # preview
        # -----------------------------------------

        preview_btn = QPushButton("Preview Zoom Level")

        preview_btn.clicked.connect(
            self.plugin.preview_zoom
        )

        self.layout.addWidget(preview_btn)

        # -----------------------------------------
        # create
        # -----------------------------------------

        create_btn = QPushButton("Create Annotation Layers")

        create_btn.clicked.connect(
            self.plugin.create_project_layers
        )

        self.layout.addWidget(create_btn)

        self.layout.addStretch()

    # ---------------------------------------------------------
    # ANNOTATION UI
    # ---------------------------------------------------------

    def build_annotation_ui(self):

        self.progress_label = QLabel("0/0 tiles annotated")

        self.progress_label.setStyleSheet("""
            font-size:16px;
            font-weight:bold;
        """)

        self.layout.addWidget(self.progress_label)

        # -----------------------------------------
        # class buttons
        # -----------------------------------------

        bush_btn = QPushButton("Add Bush (Ctrl+1)")

        bush_btn.clicked.connect(
            lambda: self.plugin.activate_annotation_class("bush")
        )

        self.layout.addWidget(bush_btn)

        brick_btn = QPushButton("Add Brick (Ctrl+2)")

        brick_btn.clicked.connect(
            lambda: self.plugin.activate_annotation_class("brick")
        )

        self.layout.addWidget(brick_btn)

        # -----------------------------------------
        # navigation
        # -----------------------------------------

        done_btn = QPushButton("✓ Done + Next")

        done_btn.clicked.connect(
            self.plugin.mark_done
        )

        self.layout.addWidget(done_btn)

        skip_btn = QPushButton("→ Skip Tile")

        skip_btn.clicked.connect(
            self.plugin.mark_skipped
        )

        self.layout.addWidget(skip_btn)

        center_btn = QPushButton("⌖ Re-center Tile")

        center_btn.clicked.connect(
            self.plugin.recenter_current_tile
        )

        self.layout.addWidget(center_btn)

        self.layout.addStretch()