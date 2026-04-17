"""
UI Manager - 3D Simulation Environment
Agent 1: UI & Environment Architect

Provides the main Qt window with pyqtgraph OpenGL viewport,
coordinate grid, camera controls, and transform update handling.
"""

import sys
from typing import Dict, Optional
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.opengl as gl


class UIManager(QtWidgets.QMainWindow):
    """
    Main window for the 3D simulation environment.
    
    Features:
    - Dark-themed OpenGL viewport using pyqtgraph
    - 3D coordinate grid
    - Camera controls (orbit, zoom, pan)
    - Signal/Slot mechanism for transform updates
    - Object registration system for mesh items
    """
    
    # Signal emitted by Motion Engine: (object_id, x, y, z, rx, ry, rz, scale)
    transform_updated = QtCore.pyqtSignal(str, float, float, float, 
                                            float, float, float, float)
    
    def __init__(self, title: str = "3D Simulation Environment"):
        super().__init__()
        
        self.title = title
        self.registered_objects: Dict[str, gl.GLMeshItem] = {}
        
        self._setup_window()
        self._setup_gl_view()
        self._setup_grid()
        self._setup_lighting()
        self._setup_camera_controls()
        self._connect_signals()
        self._apply_dark_theme()
        
    def _setup_window(self):
        """Configure the main application window."""
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 1280, 900)
        
        # Central widget to hold the GL view
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout for the central widget
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
    def _setup_gl_view(self):
        """Initialize the OpenGL view widget."""
        self.gl_view = gl.GLViewWidget()
        self.gl_view.setCameraPosition(distance=20, elevation=30, azimuth=45)
        self.gl_view.setBackgroundColor('k')  # Black background
        self.layout.addWidget(self.gl_view)
        
    def _setup_grid(self):
        """Create a 3D coordinate grid for reference."""
        # Main grid on XZ plane (y=0)
        self.grid = gl.GLGridItem()
        self.grid.setSize(50, 50)
        self.grid.setSpacing(5, 5)
        self.grid.setColor((100, 100, 100, 150))  # Gray with alpha
        self.gl_view.addItem(self.grid)
        
        # Additional smaller grid for finer detail
        self.fine_grid = gl.GLGridItem()
        self.fine_grid.setSize(10, 10)
        self.fine_grid.setSpacing(1, 1)
        self.fine_grid.setColor((50, 50, 50, 100))
        self.fine_grid.setVisible(False)  # Hidden by default
        self.gl_view.addItem(self.fine_grid)
        
        # Axis lines for orientation
        self.axis_length = 10
        self.x_axis = gl.GLLinePlotItem(
            pos=[[0, 0, 0], [self.axis_length, 0, 0]],
            color=(1, 0, 0, 1),  # Red for X
            width=2
        )
        self.y_axis = gl.GLLinePlotItem(
            pos=[[0, 0, 0], [0, self.axis_length, 0]],
            color=(0, 1, 0, 1),  # Green for Y
            width=2
        )
        self.z_axis = gl.GLLinePlotItem(
            pos=[[0, 0, 0], [0, 0, self.axis_length]],
            color=(0, 0, 1, 1),  # Blue for Z
            width=2
        )
        self.gl_view.addItem(self.x_axis)
        self.gl_view.addItem(self.y_axis)
        self.gl_view.addItem(self.z_axis)
        
    def _setup_lighting(self):
        """Configure scene lighting."""
        # Add ambient and directional lighting
        self.gl_view.setOpts(
            distance=20,
            fov=60,
            elevation=30,
            azimuth=45,
        )
        
    def _setup_camera_controls(self):
        """Create UI controls for camera manipulation."""
        # Control panel
        self.control_panel = QtWidgets.QWidget()
        self.control_panel.setMaximumHeight(120)
        self.control_layout = QtWidgets.QHBoxLayout(self.control_panel)
        
        # Reset camera button
        self.btn_reset_cam = QtWidgets.QPushButton("Reset Camera")
        self.btn_reset_cam.setToolTip("Reset to default view (Alt+0)")
        self.btn_reset_cam.clicked.connect(self._reset_camera)
        self.control_layout.addWidget(self.btn_reset_cam)
        
        # Preset views
        preset_layout = QtWidgets.QVBoxLayout()
        preset_label = QtWidgets.QLabel("Presets:")
        preset_layout.addWidget(preset_label)
        
        preset_buttons = QtWidgets.QHBoxLayout()
        
        self.btn_front = QtWidgets.QPushButton("Front")
        self.btn_front.setToolTip("View from front (Ctrl+1)")
        self.btn_front.clicked.connect(lambda: self._set_preset_view("front"))
        preset_buttons.addWidget(self.btn_front)
        
        self.btn_top = QtWidgets.QPushButton("Top")
        self.btn_top.setToolTip("View from top (Ctrl+2)")
        self.btn_top.clicked.connect(lambda: self._set_preset_view("top"))
        preset_buttons.addWidget(self.btn_top)
        
        self.btn_side = QtWidgets.QPushButton("Side")
        self.btn_side.setToolTip("View from side (Ctrl+3)")
        self.btn_side.clicked.connect(lambda: self._set_preset_view("side"))
        preset_buttons.addWidget(self.btn_side)
        
        preset_layout.addLayout(preset_buttons)
        self.control_layout.addLayout(preset_layout)
        
        # Grid toggle
        self.chk_show_grid = QtWidgets.QCheckBox("Show Grid")
        self.chk_show_grid.setChecked(True)
        self.chk_show_grid.stateChanged.connect(self._toggle_grid)
        self.control_layout.addWidget(self.chk_show_grid)
        
        # Fine grid toggle
        self.chk_show_fine = QtWidgets.QCheckBox("Show Fine Grid")
        self.chk_show_fine.setChecked(False)
        self.chk_show_fine.stateChanged.connect(self._toggle_fine_grid)
        self.control_layout.addWidget(self.chk_show_fine)
        
        # Distance slider
        distance_layout = QtWidgets.QVBoxLayout()
        distance_label = QtWidgets.QLabel("Camera Distance:")
        distance_layout.addWidget(distance_label)
        
        self.slider_distance = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_distance.setRange(5, 100)
        self.slider_distance.setValue(20)
        self.slider_distance.valueChanged.connect(self._update_camera_distance)
        distance_layout.addWidget(self.slider_distance)
        
        self.control_layout.addLayout(distance_layout)
        
        # Stats display
        self.stats_label = QtWidgets.QLabel("Objects: 0 | FPS: --")
        self.control_layout.addWidget(self.stats_label)
        
        # Add control panel to main layout
        self.layout.addWidget(self.control_panel)
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
        
    def _setup_shortcuts(self):
        """Configure keyboard shortcuts for camera control."""
        shortcuts = [
            ("Alt+0", self._reset_camera),
            ("Ctrl+1", lambda: self._set_preset_view("front")),
            ("Ctrl+2", lambda: self._set_preset_view("top")),
            ("Ctrl+3", lambda: self._set_preset_view("side")),
            ("G", self._toggle_grid_shortcut),
            ("F", self._toggle_fine_grid_shortcut),
        ]
        
        for key, callback in shortcuts:
            shortcut = QtWidgets.QShortcut(
                QtGui.QKeySequence(key), self
            )
            shortcut.activated.connect(callback)
            
    def _connect_signals(self):
        """Connect the transform_updated signal to the handler."""
        self.transform_updated.connect(self._on_transform_updated)
        
    def _apply_dark_theme(self):
        """Apply a dark color scheme to the UI."""
        dark_stylesheet = """
        QMainWindow {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        QWidget {
            background-color: #2d2d2d;
            color: #e0e0e0;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QPushButton {
            background-color: #3c3c3c;
            color: #e0e0e0;
            border: 1px solid #555;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #606060;
        }
        QCheckBox {
            color: #e0e0e0;
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        QLabel {
            color: #e0e0e0;
        }
        QSlider::groove:horizontal {
            border: 1px solid #555;
            height: 6px;
            background: #3c3c3c;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #808080;
            border: 1px solid #555;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        QSlider::sub-page:horizontal {
            background: #505050;
            border-radius: 3px;
        }
        GLViewWidget {
            background-color: black;
        }
        """
        self.setStyleSheet(dark_stylesheet)
        
    def _on_transform_updated(self, object_id: str, x: float, y: float, z: float,
                                rx: float, ry: float, rz: float, scale: float):
        """
        Slot handler for transform updates from Motion Engine.
        
        Applies the received transform to the registered mesh item.
        Runs at 60 FPS from Motion Engine updates.
        
        Args:
            object_id: Unique identifier for the object
            x, y, z: Position coordinates
            rx, ry, rz: Rotation angles in degrees (Euler angles)
            scale: Uniform scale factor
        """
        if object_id not in self.registered_objects:
            return
            
        mesh_item = self.registered_objects[object_id]
        
        # Convert rotation angles from degrees to radians for matrix calc
        rx_rad = rx * 3.14159 / 180.0
        ry_rad = ry * 3.14159 / 180.0
        rz_rad = rz * 3.14159 / 180.0
        
        # Build transformation matrix
        # Order: Scale -> Rotate Z -> Rotate Y -> Rotate X -> Translate
        import numpy as np
        
        # Start with identity
        transform = np.eye(4)
        
        # Scale
        transform[0, 0] *= scale
        transform[1, 1] *= scale
        transform[2, 2] *= scale
        
        # Rotation matrices
        cx, sx = np.cos(rx_rad), np.sin(rx_rad)
        cy, sy = np.cos(ry_rad), np.sin(ry_rad)
        cz, sz = np.cos(rz_rad), np.sin(rz_rad)
        
        # Combined rotation matrix (Z * Y * X)
        rot = np.array([
            [cz*cy, cz*sy*sx - sz*cx, cz*sy*cx + sz*sx, 0],
            [sz*cy, sz*sy*sx + cz*cx, sz*sy*cx - cz*sx, 0],
            [-sy, cy*sx, cy*cx, 0],
            [0, 0, 0, 1]
        ])
        
        # Apply rotation
        transform = rot @ transform
        
        # Translation
        transform[0, 3] = x
        transform[1, 3] = y
        transform[2, 3] = z
        
        # Apply transform to mesh
        mesh_item.setTransform(transform)
        
    def register_object(self, object_id: str, mesh_item: gl.GLMeshItem) -> bool:
        """
        Register a mesh item to be managed by the UI.
        
        Called by Agent 2 (Mesh Factory) to add objects to the scene.
        
        Args:
            object_id: Unique identifier for the object
            mesh_item: The GLMeshItem to add to the scene
            
        Returns:
            True if registration succeeded, False if object_id already exists
        """
        if object_id in self.registered_objects:
            print(f"Warning: Object '{object_id}' already registered")
            return False
            
        self.registered_objects[object_id] = mesh_item
        self.gl_view.addItem(mesh_item)
        
        # Update stats
        self._update_stats()
        
        return True
        
    def unregister_object(self, object_id: str) -> bool:
        """
        Remove a registered object from the scene.
        
        Args:
            object_id: Unique identifier for the object
            
        Returns:
            True if unregistration succeeded, False if object_id not found
        """
        if object_id not in self.registered_objects:
            return False
            
        mesh_item = self.registered_objects.pop(object_id)
        self.gl_view.removeItem(mesh_item)
        
        self._update_stats()
        return True
        
    def _update_stats(self):
        """Update the statistics display."""
        count = len(self.registered_objects)
        self.stats_label.setText(f"Objects: {count} | FPS: --")
        
    def _reset_camera(self):
        """Reset camera to default position."""
        self.gl_view.setCameraPosition(distance=20, elevation=30, azimuth=45)
        self.slider_distance.setValue(20)
        
    def _set_preset_view(self, view: str):
        """Set camera to a preset view."""
        if view == "front":
            self.gl_view.setCameraPosition(distance=20, elevation=0, azimuth=0)
        elif view == "top":
            self.gl_view.setCameraPosition(distance=20, elevation=90, azimuth=0)
        elif view == "side":
            self.gl_view.setCameraPosition(distance=20, elevation=0, azimuth=90)
            
    def _update_camera_distance(self, value: int):
        """Update camera distance from slider."""
        self.gl_view.setCameraPosition(distance=value)
        
    def _toggle_grid(self, state):
        """Toggle main grid visibility."""
        self.grid.setVisible(state == QtCore.Qt.Checked)
        
    def _toggle_fine_grid(self, state):
        """Toggle fine grid visibility."""
        self.fine_grid.setVisible(state == QtCore.Qt.Checked)
        
    def _toggle_grid_shortcut(self):
        """Toggle grid via keyboard shortcut."""
        self.chk_show_grid.setChecked(not self.chk_show_grid.isChecked())
        
    def _toggle_fine_grid_shortcut(self):
        """Toggle fine grid via keyboard shortcut."""
        self.chk_show_fine.setChecked(not self.chk_show_fine.isChecked())
        
    def get_registered_objects(self) -> Dict[str, gl.GLMeshItem]:
        """Return a copy of the registered objects dictionary."""
        return self.registered_objects.copy()
        
    def clear_all_objects(self):
        """Remove all registered objects from the scene."""
        for object_id in list(self.registered_objects.keys()):
            self.unregister_object(object_id)


def main():
    """Demo entry point - creates a standalone UI for testing."""
    app = QtWidgets.QApplication(sys.argv)
    
    # Set application-wide font for dark theme
    font = QtGui.QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = UIManager()
    window.show()
    
    print("UI Manager initialized.")
    print("Available signal: transform_updated(object_id, x, y, z, rx, ry, rz, scale)")
    print("Available method: register_object(object_id, mesh_item)")
    print("")
    print("Keyboard shortcuts:")
    print("  Alt+0 - Reset camera")
    print("  Ctrl+1 - Front view")
    print("  Ctrl+2 - Top view")
    print("  Ctrl+3 - Side view")
    print("  G - Toggle grid")
    print("  F - Toggle fine grid")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
