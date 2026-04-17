#!/usr/bin/env python3
"""
Creative Motion Engine - Agent 3
3D Simulation Movement System with Transformation Matrices

Implements three movement patterns:
- SWARM: Boids-like flocking behavior
- ORBITAL_DECAY: Spiral inward/outward motion
- KINETIC_SCULPTURE: Lissajous curve patterns
"""

import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, Qt
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math


class MovementMode(Enum):
    """Available movement patterns."""
    SWARM = auto()
    ORBITAL_DECAY = auto()
    KINETIC_SCULPTURE = auto()


@dataclass
class ObjectState:
    """Current state of a moving object."""
    object_id: str
    position: np.ndarray  # [x, y, z]
    velocity: np.ndarray  # [vx, vy, vz]
    rotation: np.ndarray  # [rx, ry, rz] in radians
    scale: float
    color_temp: float  # 0.0 = warm (center), 1.0 = cool (edge)
    # Pattern-specific data
    phase: float = 0.0
    orbit_radius: float = 0.0
    orbit_angle: float = 0.0
    boid_offset: np.ndarray = None


class MotionEngine(QObject):
    """
    Creative Motion Engine for 3D simulations.
    
    Emits transform data at 60 FPS with distance-based
    color and scale adjustments.
    
    Signal format: (object_id, x, y, z, rx, ry, rz, scale, r, g, b)
    """
    
    transform_updated = pyqtSignal(str, float, float, float, float, float, float, float, float, float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Animation timer (60 FPS = 16.67ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.setInterval(16)  # ~60 FPS
        
        # Object states
        self.objects: Dict[str, ObjectState] = {}
        self.active_ids: List[str] = []
        self.current_mode: MovementMode = MovementMode.SWARM
        
        # Timing
        self.frame_count = 0
        self.time_elapsed = 0.0
        
        # Pattern-specific parameters
        self.swarm_params = {
            'separation_radius': 2.0,
            'alignment_radius': 5.0,
            'cohesion_radius': 5.0,
            'max_speed': 0.3,
            'max_force': 0.05,
            'center_attraction': 0.02
        }
        
        self.orbital_params = {
            'base_radius': 10.0,
            'decay_rate': 0.005,
            'vertical_oscillation': 2.0,
            'rotation_speed': 0.02
        }
        
        self.kinetic_params = {
            'frequency_x': 3.0,
            'frequency_y': 2.0,
            'frequency_z': 1.0,
            'amplitude': 8.0,
            'phase_shift': np.pi / 4
        }
        
        # Visual parameters
        self.max_distance = 15.0
        self.min_scale = 0.3
        self.max_scale = 2.0
        
    def start_animation(self, object_ids: List[str], mode: MovementMode):
        """
        Start animation for a set of objects.
        
        Args:
            object_ids: List of object identifiers to animate
            mode: Movement pattern to use
        """
        self.current_mode = mode
        self.active_ids = object_ids.copy()
        self.frame_count = 0
        self.time_elapsed = 0.0
        
        # Initialize or reset object states
        for i, obj_id in enumerate(object_ids):
            if obj_id not in self.objects:
                self.objects[obj_id] = self._create_initial_state(obj_id, i, len(object_ids))
            else:
                # Reset existing object
                self.objects[obj_id] = self._create_initial_state(obj_id, i, len(object_ids))
        
        # Start the timer if not running
        if not self.timer.isActive():
            self.timer.start()
            
    def stop_animation(self):
        """Stop all animations."""
        self.timer.stop()
        
    def set_mode(self, mode: MovementMode):
        """Change movement mode (reinitializes objects)."""
        if self.active_ids:
            self.start_animation(self.active_ids, mode)
            
    def _create_initial_state(self, obj_id: str, index: int, total: int) -> ObjectState:
        """Create initial state based on movement mode."""
        mode = self.current_mode
        
        if mode == MovementMode.SWARM:
            # Random position in a sphere
            theta = np.random.uniform(0, 2 * np.pi)
            phi = np.random.uniform(0, np.pi)
            r = np.random.uniform(2, 8)
            pos = np.array([
                r * np.sin(phi) * np.cos(theta),
                r * np.sin(phi) * np.sin(theta),
                r * np.cos(phi)
            ])
            vel = np.random.randn(3) * 0.1
            
            return ObjectState(
                object_id=obj_id,
                position=pos,
                velocity=vel,
                rotation=np.random.randn(3) * 0.5,
                scale=1.0,
                color_temp=0.5,
                boid_offset=np.random.randn(3) * 0.5
            )
            
        elif mode == MovementMode.ORBITAL_DECAY:
            # Distribute evenly in a circle
            angle = (index / total) * 2 * np.pi if total > 0 else 0
            radius = self.orbital_params['base_radius']
            pos = np.array([
                radius * np.cos(angle),
                np.random.uniform(-2, 2),
                radius * np.sin(angle)
            ])
            
            return ObjectState(
                object_id=obj_id,
                position=pos,
                velocity=np.zeros(3),
                rotation=np.array([0, angle, 0]),
                scale=1.0,
                color_temp=0.5,
                orbit_radius=radius,
                orbit_angle=angle
            )
            
        elif mode == MovementMode.KINETIC_SCULPTURE:
            # Start at different phases
            phase = (index / total) * 2 * np.pi if total > 0 else 0
            pos = self._calculate_lissajous(phase)
            
            return ObjectState(
                object_id=obj_id,
                position=pos,
                velocity=np.zeros(3),
                rotation=np.array([phase, phase * 0.5, phase * 0.25]),
                scale=1.0,
                color_temp=0.5,
                phase=phase
            )
            
    def _calculate_lissajous(self, t: float) -> np.ndarray:
        """Calculate Lissajous curve position at time t."""
        p = self.kinetic_params
        amp = p['amplitude']
        return np.array([
            amp * np.sin(p['frequency_x'] * t + p['phase_shift']),
            amp * np.sin(p['frequency_y'] * t),
            amp * np.sin(p['frequency_z'] * t) * 0.5
        ])
        
    def _update_frame(self):
        """Main update loop called at 60 FPS."""
        self.frame_count += 1
        self.time_elapsed += 1/60
        
        if self.current_mode == MovementMode.SWARM:
            self._update_swarm()
        elif self.current_mode == MovementMode.ORBITAL_DECAY:
            self._update_orbital()
        elif self.current_mode == MovementMode.KINETIC_SCULPTURE:
            self._update_kinetic()
            
        # Emit updates for all active objects
        for obj_id in self.active_ids:
            if obj_id in self.objects:
                self._emit_transform(self.objects[obj_id])
                
    def _update_swarm(self):
        """Update boids-like flocking behavior."""
        states = [self.objects[oid] for oid in self.active_ids if oid in self.objects]
        if len(states) < 2:
            return
            
        positions = np.array([s.position for s in states])
        velocities = np.array([s.velocity for s in states])
        
        for i, state in enumerate(states):
            # Calculate forces
            separation = np.zeros(3)
            alignment = np.zeros(3)
            cohesion = np.zeros(3)
            
            neighbors = 0
            
            for j, other in enumerate(states):
                if i == j:
                    continue
                    
                diff = state.position - other.position
                dist = np.linalg.norm(diff)
                
                if dist > 0:
                    # Separation - avoid crowding
                    if dist < self.swarm_params['separation_radius']:
                        separation += diff / dist
                        
                    # Alignment - steer towards average heading
                    if dist < self.swarm_params['alignment_radius']:
                        alignment += other.velocity
                        
                    # Cohesion - steer towards center of mass
                    if dist < self.swarm_params['cohesion_radius']:
                        cohesion += other.position
                        neighbors += 1
                        
            if neighbors > 0:
                alignment /= neighbors
                cohesion /= neighbors
                cohesion -= state.position
                
            # Normalize and apply weights
            if np.linalg.norm(separation) > 0:
                separation = self._normalize(separation) * self.swarm_params['max_force'] * 1.5
            if np.linalg.norm(alignment) > 0:
                alignment = self._normalize(alignment) * self.swarm_params['max_force']
            if np.linalg.norm(cohesion) > 0:
                cohesion = self._normalize(cohesion) * self.swarm_params['max_force']
                
            # Center attraction
            center_force = -state.position * self.swarm_params['center_attraction']
            
            # Apply forces
            acceleration = separation + alignment + cohesion + center_force
            state.velocity += acceleration
            
            # Limit speed
            speed = np.linalg.norm(state.velocity)
            if speed > self.swarm_params['max_speed']:
                state.velocity = self._normalize(state.velocity) * self.swarm_params['max_speed']
                
            # Update position
            state.position += state.velocity
            
            # Update rotation based on velocity
            if speed > 0.01:
                state.rotation += state.velocity * 2.0
                
            # Update visual properties based on distance from center
            self._update_visual_properties(state)
            
    def _update_orbital(self):
        """Update spiral inward/outward orbital motion."""
        t = self.time_elapsed
        
        for state in [self.objects[oid] for oid in self.active_ids if oid in self.objects]:
            # Update orbit angle
            state.orbit_angle += self.orbital_params['rotation_speed']
            
            # Decay or expand radius with oscillation
            decay = np.sin(t * 0.5) * 3.0  # Oscillate between inward and outward
            current_radius = self.orbital_params['base_radius'] + decay
            
            # Calculate new position
            state.position[0] = current_radius * np.cos(state.orbit_angle)
            state.position[2] = current_radius * np.sin(state.orbit_angle)
            state.position[1] = self.orbital_params['vertical_oscillation'] * np.sin(t + state.phase)
            
            # Update rotation (tangent to orbit)
            state.rotation[1] = state.orbit_angle
            state.rotation[0] = np.sin(t * 2) * 0.5
            state.rotation[2] = np.cos(t * 1.5) * 0.3
            
            # Update visual properties
            self._update_visual_properties(state)
            
    def _update_kinetic(self):
        """Update Lissajous curve motion."""
        t = self.time_elapsed
        
        for state in [self.objects[oid] for oid in self.active_ids if oid in self.objects]:
            # Each object follows same curve but with phase offset
            phase_time = t + state.phase
            new_pos = self._calculate_lissajous(phase_time)
            
            # Calculate velocity for rotation
            velocity = new_pos - state.position
            state.position = new_pos
            
            # Rotation follows the tangent of the curve
            if np.linalg.norm(velocity) > 0.001:
                tangent = self._normalize(velocity)
                state.rotation = tangent * 2.0 + np.array([
                    np.sin(phase_time * 2),
                    np.cos(phase_time * 1.5),
                    np.sin(phase_time)
                ]) * 0.5
                
            # Update visual properties
            self._update_visual_properties(state)
            
    def _update_visual_properties(self, state: ObjectState):
        """Update scale and color based on distance from center."""
        dist = np.linalg.norm(state.position)
        
        # Normalize distance (0.0 at center, 1.0 at max)
        t = min(dist / self.max_distance, 1.0)
        state.color_temp = t
        
        # Scale: closer = smaller, farther = larger
        state.scale = self.min_scale + t * (self.max_scale - self.min_scale)
        
    def _distance_to_color(self, color_temp: float) -> Tuple[float, float, float]:
        """
        Convert distance-based color temperature to RGB.
        
        Args:
            color_temp: 0.0 = warm (center), 1.0 = cool (edge)
            
        Returns:
            RGB tuple with values in range [0, 1]
        """
        # Warm colors near center (orange/red)
        # Cool colors far from center (blue/cyan)
        
        if color_temp < 0.5:
            # Warm range: deep orange to yellow
            t = color_temp * 2
            r = 1.0
            g = 0.4 + t * 0.6
            b = 0.0 + t * 0.3
        else:
            # Cool range: yellow to cyan to blue
            t = (color_temp - 0.5) * 2
            r = 1.0 - t
            g = 1.0 - t * 0.5
            b = 0.3 + t * 0.7
            
        return (r, g, b)
        
    def _emit_transform(self, state: ObjectState):
        """Emit transform signal for an object."""
        r, g, b = self._distance_to_color(state.color_temp)
        
        self.transform_updated.emit(
            state.object_id,
            float(state.position[0]),
            float(state.position[1]),
            float(state.position[2]),
            float(state.rotation[0]),
            float(state.rotation[1]),
            float(state.rotation[2]),
            float(state.scale),
            r, g, b
        )
        
    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """Normalize a vector."""
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
        
    def get_object_state(self, object_id: str) -> Optional[ObjectState]:
        """Get current state of an object."""
        return self.objects.get(object_id)
        
    def set_swarm_params(self, **kwargs):
        """Update swarm behavior parameters."""
        self.swarm_params.update(kwargs)
        
    def set_orbital_params(self, **kwargs):
        """Update orbital motion parameters."""
        self.orbital_params.update(kwargs)
        
    def set_kinetic_params(self, **kwargs):
        """Update kinetic sculpture parameters."""
        self.kinetic_params.update(kwargs)
        
    def set_visual_params(self, max_distance: float = None, 
                         min_scale: float = None, 
                         max_scale: float = None):
        """Update visual effect parameters."""
        if max_distance is not None:
            self.max_distance = max_distance
        if min_scale is not None:
            self.min_scale = min_scale
        if max_scale is not None:
            self.max_scale = max_scale


# Demo/test code
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QCoreApplication
    
    print("🎨 Creative Motion Engine - Agent 3")
    print("=" * 50)
    
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    
    # Create motion engine
    engine = MotionEngine()
    
    # Track updates
    update_count = {mode: 0 for mode in MovementMode}
    current_mode = MovementMode.SWARM
    
    def on_transform(obj_id, x, y, z, rx, ry, rz, scale, r, g, b):
        update_count[current_mode] += 1
        if update_count[current_mode] % 60 == 0:  # Print every second
            print(f"\n[{current_mode.name}] Object {obj_id}:")
            print(f"  Position: ({x:.2f}, {y:.2f}, {z:.2f})")
            print(f"  Distance: {np.sqrt(x*x + y*y + z*z):.2f}")
            print(f"  Scale: {scale:.2f}, Color: ({r:.2f}, {g:.2f}, {b:.2f})")
    
    engine.transform_updated.connect(on_transform)
    
    # Test each mode
    object_ids = [f"obj_{i:02d}" for i in range(5)]
    
    def test_mode(mode: MovementMode, duration_ms: int = 2000):
        global current_mode
        current_mode = mode
        print(f"\n>>> Testing {mode.name} mode...")
        engine.start_animation(object_ids, mode)
        
    def next_test():
        if current_mode == MovementMode.SWARM:
            test_mode(MovementMode.ORBITAL_DECAY)
        elif current_mode == MovementMode.ORBITAL_DECAY:
            test_mode(MovementMode.KINETIC_SCULPTURE)
        else:
            print("\n✅ All modes tested successfully!")
            engine.stop_animation()
            app.quit()
    
    # Test sequence
    test_mode(MovementMode.SWARM)
    
    # Switch modes every 3 seconds
    from PyQt6.QtCore import QTimer
    mode_timer = QTimer()
    mode_timer.timeout.connect(next_test)
    mode_timer.setSingleShot(False)
    mode_timer.start(3000)
    
    print("\nRunning demo... (auto-cycles through modes)")
    print("Press Ctrl+C to exit early\n")
    
    sys.exit(app.exec())
