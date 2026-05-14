from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton
)


class AnnotatorDock(QDockWidget):

    def __init__(self, plugin):

        super().__init__("Annotation Tool")

        self.plugin = plugin

        container = QWidget()
        self.setWidget(container)

        layout = QVBoxLayout()
        container.setLayout(layout)

        # -----------------------------------------
        # TITLE
        # -----------------------------------------

        self.progress_label = QLabel("0/0 tiles annotated")
        self.progress_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
        """)

        layout.addWidget(self.progress_label)

        # -----------------------------------------
        # CLASS BUTTONS
        # -----------------------------------------

        self.bush_btn = QPushButton("Add New Bush")
        self.bush_btn.clicked.connect(
            lambda: self.plugin.activate_annotation_class("bush")
        )

        self.bush_btn.setStyleSheet("""
            background-color: #dff0d8;
            font-size: 16px;
            padding: 12px;
        """)

        layout.addWidget(self.bush_btn)

        self.brick_btn = QPushButton("Add New Brick")
        self.brick_btn.clicked.connect(
            lambda: self.plugin.activate_annotation_class("brick")
        )

        self.brick_btn.setStyleSheet("""
            background-color: #f2dede;
            font-size: 16px;
            padding: 12px;
        """)

        layout.addWidget(self.brick_btn)

        # -----------------------------------------
        # NAVIGATION
        # -----------------------------------------

        self.done_btn = QPushButton("✓ Mark Done + Next")
        self.done_btn.clicked.connect(self.plugin.mark_done)

        layout.addWidget(self.done_btn)

        self.skip_btn = QPushButton("→ Skip Tile")
        self.skip_btn.clicked.connect(self.plugin.mark_skipped)

        layout.addWidget(self.skip_btn)

        self.prev_btn = QPushButton("← Previous Tile")
        self.prev_btn.clicked.connect(self.plugin.previous_tile)

        layout.addWidget(self.prev_btn)

        layout.addStretch()