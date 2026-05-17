from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class AnnotationPanel(QWidget):

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.progress_label = QLabel("0/0 tiles annotated")
        self.progress_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.progress_label)

        self.bush_btn = QPushButton("Add New Bush")
        self.bush_btn.clicked.connect(lambda: self.plugin.activate_annotation_class("bush"))
        self.bush_btn.setStyleSheet("background-color: #dff0d8; font-size: 16px; padding: 12px;")
        layout.addWidget(self.bush_btn)

        self.brick_btn = QPushButton("Add New Brick")
        self.brick_btn.clicked.connect(lambda: self.plugin.activate_annotation_class("brick"))
        self.brick_btn.setStyleSheet("background-color: #f2dede; font-size: 16px; padding: 12px;")
        layout.addWidget(self.brick_btn)

        self.done_btn = QPushButton("✓ Mark Done + Next")
        self.done_btn.clicked.connect(self.plugin.mark_done)
        layout.addWidget(self.done_btn)

        self.skip_btn = QPushButton("→ Skip Tile")
        self.skip_btn.clicked.connect(self.plugin.mark_skipped)
        layout.addWidget(self.skip_btn)

        self.prev_btn = QPushButton("⌖ Re-center Current Tile")
        self.prev_btn.clicked.connect(self.plugin.recenter_current_tile)
        layout.addWidget(self.prev_btn)

        layout.addStretch()

    def update_progress(self, done, total):
        self.progress_label.setText(f"{done}/{total} tiles annotated")
