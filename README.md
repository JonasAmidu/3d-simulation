# 🎨 3D Multi-Agent Simulation

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Python-based 3D simulation built with **pyqtgraph.opengl** featuring dynamic procedural movement and integrated assets from Sketchfab.

![Demo Placeholder](docs/demo.gif)

## 🎯 Overview

This project demonstrates a multi-agent architecture where three specialized agents collaborate to create a complete 3D simulation environment:

| Agent | Responsibility | Module | Features |
|-------|---------------|--------|----------|
| 🤖 **Agent 1** | UI & Environment Architect | `agent1_ui_manager.py` | Dark-themed Qt6 UI, OpenGL viewport, camera controls |
| 📦 **Agent 2** | Asset Acquisition Specialist | `agent2_asset_loader.py` | Sketchfab integration, procedural meshes, GLB/OBJ parsing |
| 🎭 **Agent 3** | Creative Motion Engine | `agent3_motion_engine.py` | 3 movement patterns, 60 FPS animation, transformation matrices |

## ✨ Features

### 🖥️ User Interface
- **Dark-themed** modern UI with custom QSS styling
- **3D OpenGL viewport** with real-time rendering
- **Coordinate grid** (50×50 units) with fine detail toggle
- **Camera controls**: Orbit, zoom, preset views (Front/Top/Side)
- **Keyboard shortcuts**: Alt+0 (reset), Ctrl+1-3 (presets), G/F (grid toggles)

### 📦 3D Assets
Three distinct assets with procedural fallbacks:
- 🚁 **Drone** - Low-poly quadcopter with rotor details
- 💎 **Crystal** - Floating geometric crystal formation
- 🛰️ **Satellite** - Low-poly orbital satellite with solar panels

All assets include Sketchfab URLs for download + procedural generation as fallback.

### 🎭 Movement Patterns
1. **🐦 SWARM** - Boids-like flocking with separation, alignment, and cohesion
2. **🌌 ORBITAL_DECAY** - Spiral motion oscillating between inward/outward
3. **🎭 KINETIC_SCULPTURE** - Lissajous curve patterns in 3D space

### 🎨 Creative Twist: Distance-Based Effects
Objects dynamically respond to their distance from the center (0,0,0):
- **Color Gradient**: Warm colors (orange/red) near center → Cool colors (blue/cyan) at edges
- **Dynamic Scaling**: Objects scale from 0.3x (center) to 2.0x (edge)

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.10 or higher
python --version
```

### Installation
```bash
# Clone the repository
git clone https://github.com/jonasamidu/3d-simulation.git
cd 3d-simulation

# Install dependencies
pip install -r requirements.txt
```

### Running the Simulation
```bash
python main_3d_simulation.py
```

## 🎮 Controls

| Action | Control |
|--------|---------|
| **Orbit Camera** | Mouse drag |
| **Zoom** | Mouse wheel |
| **Reset View** | Alt+0 |
| **Front View** | Ctrl+1 |
| **Top View** | Ctrl+2 |
| **Side View** | Ctrl+3 |
| **Toggle Grid** | G key |
| **Toggle Fine Grid** | F key |

## 📁 Project Structure

```
3d-simulation/
├── main_3d_simulation.py      # 🎯 Main entry point - Integration layer
├── agent1_ui_manager.py       # 🖥️ Agent 1: UI & Environment
├── agent2_asset_loader.py     # 📦 Agent 2: Asset Acquisition
├── agent3_motion_engine.py    # 🎭 Agent 3: Motion Engine
├── requirements.txt           # 📋 Python dependencies
├── README.md                  # 📖 This file
└── LICENSE                    # 📄 MIT License
```

## 🧩 Architecture

### Signal/Slot Communication
```python
# Motion Engine emits transforms at 60 FPS
transform_updated.emit(
    object_id, x, y, z,           # Position
    rx, ry, rz,                  # Rotation (degrees)
    scale,                        # Scale factor
    r, g, b                      # RGB color
)
```

### Transformation Pipeline
1. **Motion Engine** calculates position/rotation using NumPy
2. **Signal** emits 60 updates per second
3. **UI Manager** receives transforms, builds 4×4 matrices
4. **OpenGL** applies matrices to mesh items

### Asset Loading Flow
```
Request Asset
     ↓
Check Cache
     ↓
Download from Sketchfab (if needed)
     ↓
Parse GLB/OBJ with trimesh
     ↓
Convert to GLMeshItem format
     ↓
Add to Scene
```

## 🛠️ API Usage

### Loading Assets
```python
from agent2_asset_loader import load_asset

# Load with automatic fallback
vertices, faces, metadata = load_asset("drone", use_mock=True)
print(f"Loaded {metadata['vertex_count']} vertices from {metadata['source']}")
```

### Creating Motion
```python
from agent3_motion_engine import MotionEngine, MovementMode

engine = MotionEngine()
engine.transform_updated.connect(my_callback)

# Start animation with 3 objects
engine.start_animation(
    ["drone_0", "crystal_0", "satellite_0"],
    MovementMode.SWARM
)
```

### Building the UI
```python
from PyQt6 import QtWidgets
from main_3d_simulation import Integrated3DSimulation

app = QtWidgets.QApplication([])
window = Integrated3DSimulation()
window.show()
app.exec()
```

## 🔧 Configuration

### Motion Parameters
Each movement mode has configurable parameters:

**Swarm** (`agent3_motion_engine.py`):
```python
engine.set_swarm_params(
    separation_radius=2.0,
    alignment_radius=5.0,
    cohesion_radius=5.0,
    max_speed=0.3
)
```

**Orbital**:
```python
engine.set_orbital_params(
    base_radius=10.0,
    decay_rate=0.005,
    vertical_oscillation=2.0
)
```

**Visual Effects**:
```python
engine.set_visual_params(
    max_distance=15.0,
    min_scale=0.3,
    max_scale=2.0
)
```

## 📦 Dependencies

- **PyQt6** ≥ 6.4.0 - GUI framework
- **pyqtgraph** ≥ 0.13.0 - OpenGL visualization
- **numpy** ≥ 1.24.0 - Numerical computations
- **trimesh** ≥ 3.20.0 - Mesh loading (optional)
- **requests** ≥ 2.28.0 - Network downloads (optional)

## 🤝 Contributing

Contributions welcome! Areas for expansion:
- Additional movement patterns
- More asset types
- VR/AR integration
- Physics simulation
- Networked multi-agent collaboration

## 📜 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Credits

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) and [pyqtgraph](https://pyqtgraph.org/)
- 3D assets from [Sketchfab](https://sketchfab.com/) (CC licenses)
- Inspired by multi-agent system architecture patterns

---

**Happy simulating!** 🚀🎨
