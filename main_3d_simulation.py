#!/usr/bin/env python3
"""
3D Simulation - Integrated Application
=====================================

This is the main entry point that integrates:
- Agent 1: UI Manager (dark-themed OpenGL viewport)
- Agent 2: Asset Loader (Sketchfab assets + procedural fallbacks)
- Agent 3: Motion Engine (Swarm/Orbital/Kinetic movement patterns)

Dependencies: PyQt6, pyqtgraph, numpy, trimesh (optional)
"""

import sys
import numpy as np
from pathlib import Path

# Fix import paths to find agent modules
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.opengl as gl

# Import agent modules
import agent2_asset_loader as asset_loader
from agent3_motion_engine import MotionEngine, MovementMode


class Integrated3DSimulation(QtWidgets.QMainWindow):
    """
    Integrated 3D Simulation combining all three agents.
    
    Features:
    - Dark-themed OpenGL viewport with grid and camera controls
    - Three 3D assets (drone, crystal, satellite) with procedural fallbacks
    - Three movement modes: Swarm, Orbital Decay, Kinetic Sculpture
    - Distance-based color and scale effects
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("🎨 3D Simulation - Multi-Agent Integration")
        self.setGeometry(100, 100, 1400, 1000)
        
        # Registered objects
        self.objects = {}  # object_id -> GLMeshItem
        self.object_ids = []
        
        # Setup UI
        self._setup_ui()
        self._setup_3d_view()
        self._setup_controls()
        self._apply_dark_theme()
        
        # Initialize motion engine
        self.motion_engine = MotionEngine(self)
        self.motion_engine.transform_updated.connect(self._on_transform_updated)
        
        # Load assets and start simulation
        self._load_assets()
        
    def _setup_ui(self):
        """Setup the main UI layout."""
        # Central widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Left panel for 3D view
        self.view_container = QtWidgets.QWidget()
        self.view_layout = QtWidgets.QVBoxLayout(self.view_container)
        self.view_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view_container, stretch=1)
        
        # Right panel for controls
        self.control_panel = QtWidgets.QWidget()
        self.control_panel.setMaximumWidth(300)
        self.control_layout = QtWidgets.QVBoxLayout(self.control_panel)
        layout.addWidget(self.control_panel)
        
    def _setup_3d_view(self):
        """Initialize the OpenGL 3D view."""
        # Create GLViewWidget
        self.gl_view = gl.GLViewWidget()
        self.gl_view.setCameraPosition(distance=25, elevation=30, azimuth=45)
        self.view_layout.addWidget(self.gl_view)
        
        # Main grid
        self.grid = gl.GLGridItem()
        self.grid.setSize(50, 50)
        self.grid.setSpacing(5, 5)
        self.grid.setColor((100, 100, 100, 150))
        self.gl_view.addItem(self.grid)
        
        # Fine grid (hidden by default)
        self.fine_grid = gl.GLGridItem()
        self.fine_grid.setSize(10, 10)
        self.fine_grid.setSpacing(1, 1)
        self.fine_grid.setColor((50, 50, 50, 100))
        self.fine_grid.setVisible(False)
        self.gl_view.addItem(self.fine_grid)
        
        # Axis lines
        axis_length = 10
        self.x_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [axis_length, 0, 0]]),
            color=(1, 0, 0, 1), width=2
        )
        self.y_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, axis_length, 0]]),
            color=(0, 1, 0, 1), width=2
        )
        self.z_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, 0, axis_length]]),
            color=(0, 0, 1, 1), width=2
        )
        self.gl_view.addItem(self.x_axis)
        self.gl_view.addItem(self.y_axis)
        self.gl_view.addItem(self.z_axis)
        
    def _setup_controls(self):
        """Setup the control panel."""
        # Title
        title = QtWidgets.QLabel("🎨 3D Simulation Controls")
        title_font = QtGui.QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.control_layout.addWidget(title)
        
        # Separator
        self.control_layout.addWidget(QtWidgets.QFrame())
        
        # Movement Mode Section
        mode_group = QtWidgets.QGroupBox("Movement Mode")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)
        
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("🐦 Swarm (Flocking)", MovementMode.SWARM)
        self.mode_combo.addItem("🌌 Orbital Decay", MovementMode.ORBITAL_DECAY)
        self.mode_combo.addItem("🎭 Kinetic Sculpture", MovementMode.KINETIC_SCULPTURE)
        mode_layout.addWidget(self.mode_combo)
        
        self.btn_apply_mode = QtWidgets.QPushButton("Apply Mode")
        self.btn_apply_mode.clicked.connect(self._apply_mode)
        mode_layout.addWidget(self.btn_apply_mode)
        
        self.control_layout.addWidget(mode_group)
        
        # Animation Controls
        anim_group = QtWidgets.QGroupBox("Animation Controls")
        anim_layout = QtWidgets.QHBoxLayout(anim_group)
        
        self.btn_start = QtWidgets.QPushButton("▶ Start")
        self.btn_start.clicked.connect(self._start_animation)
        anim_layout.addWidget(self.btn_start)
        
        self.btn_stop = QtWidgets.QPushButton("⏹ Stop")
        self.btn_stop.clicked.connect(self._stop_animation)
        anim_layout.addWidget(self.btn_stop)
        
        self.btn_reset = QtWidgets.QPushButton("🔄 Reset")
        self.btn_reset.clicked.connect(self._reset_view)
        anim_layout.addWidget(self.btn_reset)
        
        self.control_layout.addWidget(anim_group)
        
        # Visual Effects
        visual_group = QtWidgets.QGroupBox("Visual Effects")
        visual_layout = QtWidgets.QVBoxLayout(visual_group)
        
        # Grid toggle
        self.chk_grid = QtWidgets.QCheckBox("Show Main Grid")
        self.chk_grid.setChecked(True)
        self.chk_grid.stateChanged.connect(self._toggle_grid)
        visual_layout.addWidget(self.chk_grid)
        
        self.chk_fine_grid = QtWidgets.QCheckBox("Show Fine Grid")
        self.chk_fine_grid.setChecked(False)
        self.chk_fine_grid.stateChanged.connect(self._toggle_fine_grid)
        visual_layout.addWidget(self.chk_fine_grid)
        
        # Camera distance
        dist_layout = QtWidgets.QHBoxLayout()
        dist_layout.addWidget(QtWidgets.QLabel("Camera Dist:"))
        self.slider_distance = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider_distance.setRange(5, 100)
        self.slider_distance.setValue(25)
        self.slider_distance.valueChanged.connect(self._update_camera_distance)
        dist_layout.addWidget(self.slider_distance)
        visual_layout.addLayout(dist_layout)
        
        self.control_layout.addWidget(visual_group)
        
        # Assets Info
        info_group = QtWidgets.QGroupBox("Loaded Assets")
        info_layout = QtWidgets.QVBoxLayout(info_group)
        
        self.asset_labels = {}
        for asset_name in ["drone", "crystal", "satellite"]:
            label = QtWidgets.QLabel(f"• {asset_name.capitalize()}: Loading...")
            info_layout.addWidget(label)
            self.asset_labels[asset_name] = label
            
        self.control_layout.addWidget(info_group)
        
        # Stats
        self.stats_label = QtWidgets.QLabel("Objects: 0 | Mode: --")
        self.stats_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.control_layout.addWidget(self.stats_label)
        
        # Spacer
        self.control_layout.addStretch()
        
        # Credits
        credits = QtWidgets.QLabel(
            "Built with PyQt6 + pyqtgraph\n"
            "Assets: Sketchfab / Procedural\n"
            "Agents: 1-UI | 2-Assets | 3-Motion"
        )
        credits.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        credits.setStyleSheet("color: #888; font-size: 10px;")
        self.control_layout.addWidget(credits)
        
    def _apply_dark_theme(self):
        """Apply dark color scheme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
                color: #eee;
            }
            QWidget {
                background-color: #16213e;
                color: #eee;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #0f3460;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #0f3460;
                color: #eee;
                border: 1px solid #e94560;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1a4a7a;
            }
            QPushButton:pressed {
                background-color: #e94560;
            }
            QComboBox {
                background-color: #0f3460;
                border: 1px solid #e94560;
                padding: 5px;
                border-radius: 3px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #0f3460;
                height: 6px;
                background: #0a192f;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                border: 1px solid #0f3460;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
        """)
        
    def _load_assets(self):
        """Load 3D assets from Agent 2."""
        asset_types = ["drone", "crystal", "satellite"]
        
        for i, asset_type in enumerate(asset_types):
            try:
                # Load asset using Agent 2's module
                vertices, faces, metadata = asset_loader.load_asset(
                    asset_type, 
                    use_mock=True,  # Use procedural meshes
                    cache_dir="./assets_cache"
                )
                
                # Create GLMeshItem
                colors = self._generate_colors(vertices, faces)
                
                mesh_item = gl.GLMeshItem(
                    vertexes=vertices,
                    faces=faces,
                    faceColors=colors,
                    smooth=False,
                    computeNormals=True,
                    drawEdges=True,
                    edgeColor=(0.3, 0.3, 0.3, 1.0)
                )
                
                # Position them initially
                offset_x = (i - 1) * 8
                mesh_item.translate(offset_x, 0, 0)
                
                # Add to scene
                self.gl_view.addItem(mesh_item)
                
                # Register
                object_id = f"{asset_type}_{i}"
                self.objects[object_id] = mesh_item
                self.object_ids.append(object_id)
                
                # Update UI
                source = metadata.get('source', 'unknown')
                self.asset_labels[asset_type].setText(
                    f"• {asset_type.capitalize()}: ✓ {source}"
                )
                
            except Exception as e:
                print(f"Error loading {asset_type}: {e}")
                self.asset_labels[asset_type].setText(
                    f"• {asset_type.capitalize()}: ✗ Failed"
                )
                
        self._update_stats()
        
    def _generate_colors(self, vertices, faces):
        """Generate initial colors for mesh faces."""
        num_faces = len(faces)
        colors = np.ones((num_faces, 4))
        
        # Calculate face centers
        for i, face in enumerate(faces):
            face_verts = vertices[face]
            center = np.mean(face_verts, axis=0)
            
            # Color based on position (cool/warm mix)
            dist = np.linalg.norm(center)
            t = min(dist / 10, 1.0)
            
            colors[i, 0] = 0.8 + t * 0.2  # R
            colors[i, 1] = 0.4 + t * 0.4  # G
            colors[i, 2] = 0.2 + t * 0.6  # B
            colors[i, 3] = 1.0  # Alpha
            
        return colors.astype(np.float32)
        
    def _on_transform_updated(self, object_id, x, y, z, rx, ry, rz, scale, r, g, b):
        """Handle transform updates from Motion Engine (Agent 3)."""
        if object_id not in self.objects:
            return
            
        mesh_item = self.objects[object_id]
        
        # Build transformation matrix
        transform = self._build_transform_matrix(x, y, z, rx, ry, rz, scale)
        mesh_item.setTransform(transform)
        
        # Update color based on distance (creative twist)
        mesh_item.setColor((r, g, b, 1.0))
        
    def _build_transform_matrix(self, x, y, z, rx, ry, rz, scale):
        """Build 4x4 transformation matrix."""
        # Convert to radians
        rx_rad = np.radians(rx)
        ry_rad = np.radians(ry)
        rz_rad = np.radians(rz)
        
        # Scale matrix
        S = np.diag([scale, scale, scale, 1.0])
        
        # Rotation matrices
        Rx = np.array([
            [1, 0, 0, 0],
            [0, np.cos(rx_rad), -np.sin(rx_rad), 0],
            [0, np.sin(rx_rad), np.cos(rx_rad), 0],
            [0, 0, 0, 1]
        ])
        
        Ry = np.array([
            [np.cos(ry_rad), 0, np.sin(ry_rad), 0],
            [0, 1, 0, 0],
            [-np.sin(ry_rad), 0, np.cos(ry_rad), 0],
            [0, 0, 0, 1]
        ])
        
        Rz = np.array([
            [np.cos(rz_rad), -np.sin(rz_rad), 0, 0],
            [np.sin(rz_rad), np.cos(rz_rad), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        
        # Translation matrix
        T = np.array([
            [1, 0, 0, x],
            [0, 1, 0, y],
            [0, 0, 1, z],
            [0, 0, 0, 1]
        ])
        
        # Combine: T * Rz * Ry * Rx * S
        transform = T @ Rz @ Ry @ Rx @ S
        return transform
        
    def _apply_mode(self):
        """Apply selected movement mode."""
        mode = self.mode_combo.currentData()
        if self.object_ids:
            self.motion_engine.start_animation(self.object_ids, mode)
            self._update_stats()
            
    def _start_animation(self):
        """Start the animation."""
        mode = self.mode_combo.currentData()
        if self.object_ids:
            self.motion_engine.start_animation(self.object_ids, mode)
            
    def _stop_animation(self):
        """Stop the animation."""
        self.motion_engine.stop_animation()
        
    def _reset_view(self):
        """Reset camera to default position."""
        self.gl_view.setCameraPosition(distance=25, elevation=30, azimuth=45)
        self.slider_distance.setValue(25)
        
    def _toggle_grid(self, state):
        """Toggle main grid visibility."""
        self.grid.setVisible(state == QtCore.Qt.CheckState.Checked.value)
        
    def _toggle_fine_grid(self, state):
        """Toggle fine grid visibility."""
        self.fine_grid.setVisible(state == QtCore.Qt.CheckState.Checked.value)
        
    def _update_camera_distance(self, value):
        """Update camera distance."""
        self.gl_view.setCameraPosition(distance=value)
        
    def _update_stats(self):
        """Update statistics display."""
        mode_text = self.mode_combo.currentText().split()[1]  # Get mode name
        self.stats_label.setText(f"Objects: {len(self.objects)} | Mode: {mode_text}")


def main():
    """Main entry point."""
    app = QtWidgets.QApplication(sys.argv)
    
    # Set application-wide font
    font = QtGui.QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show main window
    window = Integrated3DSimulation()
    window.show()
    
    print("=" * 60)
    print("🎨 3D Simulation - Multi-Agent Integration Complete!")
    print("=" * 60)
    print()
    print("Agents:")
    print("  1. UI & Environment - Dark theme, grid, camera controls")
    print("  2. Asset Acquisition - Drone, Crystal, Satellite meshes")
    print("  3. Motion Engine - Swarm, Orbital, Kinetic patterns")
    print()
    print("Controls:")
    print("  • Mouse drag = Orbit camera")
    print("  • Mouse wheel = Zoom")
    print("  • Select mode from dropdown")
    print("  • Click 'Apply Mode' or 'Start' to begin")
    print()
    print("Creative Twist:")
    print("  • Objects change color from warm (center) to cool (edge)")
    print("  • Scale increases with distance from center")
    print()
    print("Enjoy the show! 🚀")
    print("=" * 60)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
