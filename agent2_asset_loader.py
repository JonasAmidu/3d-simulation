#!/usr/bin/env python3
"""
Asset Acquisition Specialist - Agent 2
3D Asset Loader for pyqtgraph OpenGL Visualization

Provides:
- SketchfabAssetLoader: Downloads and parses GLB/OBJ assets from Sketchfab
- MockAsset: Procedurally generated geometries (cube, sphere, pyramid)
- load_asset(): Main function returning mesh data compatible with GLMeshItem

Asset URLs:
- Drone: https://sketchfab.com/3d-models/low-poly-quadcopter-drone-fa0261d9db004dda9d4d3ff9bc985717
- Crystal: https://sketchfab.com/3d-models/crystal-bd3bea3e89fd465390792c4108762113
- Satellite: https://sketchfab.com/3d-models/simple-satellite-low-poly-free-f23b484cda664f1cb91b4f62ea5ef8bf
"""

import numpy as np
import warnings
from pathlib import Path
from typing import Tuple, Optional, Dict, List, Union
import logging

# Optional imports - gracefully handle if not installed
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    warnings.warn("trimesh not installed, procedural generation only")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    warnings.warn("requests not installed, network downloads disabled")

try:
    from pygltflib import GLTF2
    PYGLTFLIB_AVAILABLE = True
except ImportError:
    PYGLTFLIB_AVAILABLE = False

try:
    import struct
    STRUCT_AVAILABLE = True
except ImportError:
    STRUCT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SketchfabAssetLoader:
    """
    Handles downloading and parsing of Sketchfab assets.
    Requires Sketchfab API access for programmatic downloads.
    Falls back to local file loading if download fails.
    """
    
    BASE_URL = "https://api.sketchfab.com/v3"
    
    # Asset definitions with real Sketchfab URLs
    ASSETS = {
        "drone": {
            "url": "https://sketchfab.com/3d-models/low-poly-quadcopter-drone-fa0261d9db004dda9d4d3ff9bc985717",
            "uid": "fa0261d9db004dda9d4d3ff9bc985717",
            "name": "Low Poly QuadCopter Drone",
            "author": "GTKima",
            "license": "CC Attribution",
            "filename": "drone.glb"
        },
        "crystal": {
            "url": "https://sketchfab.com/3d-models/crystal-bd3bea3e89fd465390792c4108762113",
            "uid": "bd3bea3e89fd465390792c4108762113",
            "name": "Crystal",
            "author": "Albert Gregl",
            "license": "CC Attribution",
            "filename": "crystal.glb"
        },
        "satellite": {
            "url": "https://sketchfab.com/3d-models/simple-satellite-low-poly-free-f23b484cda664f1cb91b4f62ea5ef8bf",
            "uid": "f23b484cda664f1cb91b4f62ea5ef8bf",
            "name": "Simple Satellite Low Poly Free",
            "author": "DjalalxJay",
            "license": "CC Attribution",
            "filename": "satellite.glb"
        }
    }
    
    def __init__(self, cache_dir: str = "./assets_cache", api_key: Optional[str] = None):
        """
        Initialize the loader.
        
        Args:
            cache_dir: Directory to store downloaded assets
            api_key: Sketchfab API key (optional, for downloads)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key
        self.session = requests.Session() if REQUESTS_AVAILABLE else None
        if self.session and api_key:
            self.session.headers.update({"Authorization": f"Token {api_key}"})
    
    def download_asset(self, asset_type: str) -> Optional[Path]:
        """
        Attempt to download asset from Sketchfab.
        Note: Requires API key and download permissions.
        
        Args:
            asset_type: One of 'drone', 'crystal', 'satellite'
            
        Returns:
            Path to downloaded file or None if failed
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("requests not available, cannot download")
            return None
        
        if asset_type not in self.ASSETS:
            logger.error(f"Unknown asset type: {asset_type}")
            return None
        
        asset_info = self.ASSETS[asset_type]
        cache_path = self.cache_dir / asset_info["filename"]
        
        # Check if already cached
        if cache_path.exists():
            logger.info(f"Using cached {asset_type}: {cache_path}")
            return cache_path
        
        if not self.api_key:
            logger.warning("No API key provided, manual download required")
            logger.info(f"Please download from: {asset_info['url']}")
            logger.info(f"Save to: {cache_path}")
            return None
        
        # Attempt API download
        try:
            uid = asset_info["uid"]
            download_url = f"{self.BASE_URL}/models/{uid}/download"
            
            logger.info(f"Requesting download for {asset_type}...")
            response = self.session.get(download_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                glb_url = data.get("gltf", {}).get("url")
                
                if glb_url:
                    logger.info(f"Downloading {asset_type}...")
                    glb_response = self.session.get(glb_url, stream=True, timeout=60)
                    
                    if glb_response.status_code == 200:
                        with open(cache_path, 'wb') as f:
                            for chunk in glb_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        logger.info(f"Downloaded {asset_type} to {cache_path}")
                        return cache_path
                    else:
                        logger.error(f"Download failed: {glb_response.status_code}")
            else:
                logger.warning(f"API request failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Download error: {e}")
        
        return None
    
    def parse_glb(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """
        Parse GLB file and extract vertices and faces.
        
        Args:
            filepath: Path to GLB file
            
        Returns:
            Tuple of (vertices, faces) arrays
        """
        if TRIMESH_AVAILABLE:
            # Use trimesh for robust GLB parsing
            mesh = trimesh.load(str(filepath), force='mesh')
            if hasattr(mesh, 'vertices'):
                vertices = np.array(mesh.vertices, dtype=np.float32)
                faces = np.array(mesh.faces, dtype=np.uint32)
                return vertices, faces
        
        # Fallback: basic GLB parsing
        return self._parse_glb_basic(filepath)
    
    def _parse_glb_basic(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """
        Basic GLB file parser without external dependencies.
        Handles simple GLB files with embedded buffers.
        """
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # GLB header
        magic = data[:4]
        if magic != b'glTF':
            raise ValueError(f"Not a GLB file: {filepath}")
        
        version = int.from_bytes(data[4:8], 'little')
        length = int.from_bytes(data[8:12], 'little')
        
        # Parse chunks
        offset = 12
        json_data = None
        binary_data = None
        
        while offset < length:
            chunk_length = int.from_bytes(data[offset:offset+4], 'little')
            chunk_type = int.from_bytes(data[offset+4:offset+8], 'little')
            chunk_data = data[offset+8:offset+8+chunk_length]
            
            if chunk_type == 0x4E4F534A:  # JSON
                json_data = chunk_data.decode('utf-8')
            elif chunk_type == 0x004E4942:  # BIN
                binary_data = chunk_data
            
            offset += 8 + chunk_length
            # Align to 4-byte boundary
            if offset % 4 != 0:
                offset += 4 - (offset % 4)
        
        if json_data is None:
            raise ValueError("No JSON chunk found in GLB")
        
        import json
        gltf = json.loads(json_data)
        
        return self._extract_mesh_from_gltf(gltf, binary_data)
    
    def _extract_mesh_from_gltf(self, gltf: dict, binary_data: bytes) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract mesh data from parsed GLTF structure.
        """
        # Get first mesh
        if 'meshes' not in gltf or len(gltf['meshes']) == 0:
            raise ValueError("No meshes found in GLTF")
        
        mesh = gltf['meshes'][0]
        primitives = mesh.get('primitives', [])
        
        if not primitives:
            raise ValueError("No primitives found in mesh")
        
        primitive = primitives[0]
        attributes = primitive.get('attributes', {})
        indices_accessor_idx = primitive.get('indices')
        
        # Access buffer views and accessors
        accessors = gltf.get('accessors', [])
        buffer_views = gltf.get('bufferViews', [])
        buffers = gltf.get('buffers', [])
        
        def get_accessor_data(accessor_idx: int) -> np.ndarray:
            accessor = accessors[accessor_idx]
            buffer_view_idx = accessor['bufferView']
            buffer_view = buffer_views[buffer_view_idx]
            
            component_type = accessor['componentType']
            count = accessor['count']
            type_str = accessor['type']
            
            # Map GLTF types to numpy
            type_map = {
                'SCALAR': 1,
                'VEC2': 2,
                'VEC3': 3,
                'VEC4': 4
            }
            num_components = type_map.get(type_str, 1)
            
            dtype_map = {
                5120: np.int8,
                5121: np.uint8,
                5122: np.int16,
                5123: np.uint16,
                5125: np.uint32,
                5126: np.float32
            }
            dtype = dtype_map.get(component_type, np.float32)
            
            byte_offset = buffer_view.get('byteOffset', 0)
            byte_stride = buffer_view.get('byteStride', 0)
            
            if byte_stride == 0:
                byte_stride = np.dtype(dtype).itemsize * num_components
            
            # Extract data
            result = []
            for i in range(count):
                start = byte_offset + i * byte_stride
                values = []
                for j in range(num_components):
                    val_start = start + j * np.dtype(dtype).itemsize
                    val_bytes = binary_data[val_start:val_start + np.dtype(dtype).itemsize]
                    val = np.frombuffer(val_bytes, dtype=dtype)[0]
                    values.append(val)
                result.append(values)
            
            return np.array(result, dtype=np.float32 if dtype == np.float32 else np.float32)
        
        # Get positions
        pos_accessor_idx = attributes.get('POSITION')
        if pos_accessor_idx is None:
            raise ValueError("No position attribute found")
        
        vertices = get_accessor_data(pos_accessor_idx)
        
        # Get indices
        if indices_accessor_idx is not None:
            indices = get_accessor_data(indices_accessor_idx).astype(np.uint32).flatten()
            # Convert to faces (triangles)
            faces = indices.reshape(-1, 3)
        else:
            # Generate faces from vertex order (triangles assumed)
            num_vertices = len(vertices)
            faces = np.arange(num_vertices, dtype=np.uint32).reshape(-1, 3)
        
        return vertices, faces
    
    def load(self, asset_type: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Load asset - tries download first, then cached file.
        
        Returns:
            Tuple of (vertices, faces) or (None, None) if failed
        """
        # Try to download or use cached
        filepath = self.download_asset(asset_type)
        
        if filepath and filepath.exists():
            try:
                return self.parse_glb(filepath)
            except Exception as e:
                logger.error(f"Failed to parse {filepath}: {e}")
        
        return None, None


class MockAsset:
    """
    Procedurally generates geometric shapes using numpy.
    Used as fallback when network/download fails.
    """
    
    @staticmethod
    def create_cube(size: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a cube mesh.
        
        Args:
            size: Cube side length
            
        Returns:
            (vertices, faces) arrays
        """
        s = size / 2
        vertices = np.array([
            # Front face
            [-s, -s,  s], [ s, -s,  s], [ s,  s,  s], [-s,  s,  s],
            # Back face
            [-s, -s, -s], [-s,  s, -s], [ s,  s, -s], [ s, -s, -s],
            # Top face
            [-s,  s, -s], [-s,  s,  s], [ s,  s,  s], [ s,  s, -s],
            # Bottom face
            [-s, -s, -s], [ s, -s, -s], [ s, -s,  s], [-s, -s,  s],
            # Right face
            [ s, -s, -s], [ s,  s, -s], [ s,  s,  s], [ s, -s,  s],
            # Left face
            [-s, -s, -s], [-s, -s,  s], [-s,  s,  s], [-s,  s, -s],
        ], dtype=np.float32)
        
        faces = np.array([
            [0, 1, 2], [0, 2, 3],       # Front
            [4, 5, 6], [4, 6, 7],       # Back
            [8, 9, 10], [8, 10, 11],    # Top
            [12, 13, 14], [12, 14, 15], # Bottom
            [16, 17, 18], [16, 18, 19], # Right
            [20, 21, 22], [20, 22, 23], # Left
        ], dtype=np.uint32)
        
        return vertices, faces
    
    @staticmethod
    def create_sphere(radius: float = 1.0, segments: int = 16, rings: int = 16) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a UV sphere mesh.
        
        Args:
            radius: Sphere radius
            segments: Number of longitudinal segments
            rings: Number of latitudinal rings
            
        Returns:
            (vertices, faces) arrays
        """
        vertices = []
        
        # Generate vertices
        for i in range(rings + 1):
            phi = np.pi * i / rings
            for j in range(segments):
                theta = 2 * np.pi * j / segments
                
                x = radius * np.sin(phi) * np.cos(theta)
                y = radius * np.cos(phi)
                z = radius * np.sin(phi) * np.sin(theta)
                
                vertices.append([x, y, z])
        
        vertices = np.array(vertices, dtype=np.float32)
        
        # Generate faces
        faces = []
        for i in range(rings):
            for j in range(segments):
                current = i * segments + j
                next_row = (i + 1) * segments + j
                next_col = i * segments + (j + 1) % segments
                next_both = (i + 1) * segments + (j + 1) % segments
                
                # Two triangles per quad
                faces.append([current, next_row, next_both])
                faces.append([current, next_both, next_col])
        
        faces = np.array(faces, dtype=np.uint32)
        
        return vertices, faces
    
    @staticmethod
    def create_pyramid(size: float = 1.0, height: float = 1.5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a square pyramid mesh.
        
        Args:
            size: Base square side length
            height: Pyramid height
            
        Returns:
            (vertices, faces) arrays
        """
        s = size / 2
        h = height
        
        vertices = np.array([
            [ 0,  h,  0],  # Apex (0)
            [-s,  0, -s],  # Base corners
            [ s,  0, -s],
            [ s,  0,  s],
            [-s,  0,  s],
        ], dtype=np.float32)
        
        faces = np.array([
            [0, 1, 2],  # Front face
            [0, 2, 3],  # Right face
            [0, 3, 4],  # Back face
            [0, 4, 1],  # Left face
            [1, 3, 2],  # Base triangle 1
            [1, 4, 3],  # Base triangle 2
        ], dtype=np.uint32)
        
        return vertices, faces
    
    @staticmethod
    def create_crystal() -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a crystal shape (elongated octahedron/pentagonal prism).
        """
        # Crystal with pentagonal base and pointed top/bottom
        n = 5  # pentagon
        height = 2.0
        radius = 0.8
        
        vertices = []
        
        # Bottom point
        vertices.append([0, -height, 0])
        
        # Bottom pentagon
        for i in range(n):
            angle = 2 * np.pi * i / n
            x = radius * np.cos(angle)
            z = radius * np.sin(angle)
            vertices.append([x, -height/3, z])
        
        # Middle pentagon (wider)
        for i in range(n):
            angle = 2 * np.pi * i / n + np.pi / n  # rotated
            x = radius * 1.3 * np.cos(angle)
            z = radius * 1.3 * np.sin(angle)
            vertices.append([x, 0, z])
        
        # Top pentagon
        for i in range(n):
            angle = 2 * np.pi * i / n
            x = radius * 0.7 * np.cos(angle)
            z = radius * 0.7 * np.sin(angle)
            vertices.append([x, height/3, z])
        
        # Top point
        vertices.append([0, height * 1.2, 0])
        
        vertices = np.array(vertices, dtype=np.float32)
        
        # Generate faces
        faces = []
        
        # Bottom to lower pentagon (1 + n vertices)
        for i in range(n):
            next_i = (i + 1) % n
            faces.append([0, 1 + i, 1 + next_i])
        
        # Lower to middle pentagon
        for i in range(n):
            next_i = (i + 1) % n
            faces.append([1 + i, 1 + n + i, 1 + n + next_i])
            faces.append([1 + i, 1 + n + next_i, 1 + next_i])
        
        # Middle to upper pentagon
        for i in range(n):
            next_i = (i + 1) % n
            faces.append([1 + n + i, 1 + 2*n + i, 1 + 2*n + next_i])
            faces.append([1 + n + i, 1 + 2*n + next_i, 1 + n + next_i])
        
        # Upper to top point
        for i in range(n):
            next_i = (i + 1) % n
            faces.append([1 + 2*n + i, 1 + 3*n, 1 + 2*n + next_i])
        
        faces = np.array(faces, dtype=np.uint32)
        
        return vertices, faces
    
    @staticmethod
    def create_drone() -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a simple drone shape (body + 4 arms + rotors).
        """
        vertices = []
        
        # Body (central box)
        body_verts = [
            [-0.3, -0.1, -0.2], [0.3, -0.1, -0.2], [0.3, 0.1, -0.2], [-0.3, 0.1, -0.2],
            [-0.3, -0.1, 0.2], [-0.3, 0.1, 0.2], [0.3, 0.1, 0.2], [0.3, -0.1, 0.2],
        ]
        vertices.extend(body_verts)
        
        # Arm positions
        arm_positions = [
            [0.8, 0, 0.8], [-0.8, 0, 0.8], [-0.8, 0, -0.8], [0.8, 0, -0.8]
        ]
        
        arm_offset = len(vertices)
        
        for pos in arm_positions:
            # Rotor mount
            arm_verts = [
                [pos[0]-0.1, 0.1, pos[2]-0.1], [pos[0]+0.1, 0.1, pos[2]-0.1],
                [pos[0]+0.1, 0.1, pos[2]+0.1], [pos[0]-0.1, 0.1, pos[2]+0.1],
                [pos[0]-0.1, -0.05, pos[2]-0.1], [pos[0]-0.1, -0.05, pos[2]+0.1],
                [pos[0]+0.1, -0.05, pos[2]+0.1], [pos[0]+0.1, -0.05, pos[2]-0.1],
            ]
            vertices.extend(arm_verts)
        
        vertices = np.array(vertices, dtype=np.float32)
        
        # Faces for body (cube)
        body_faces = [
            [0, 1, 2], [0, 2, 3],
            [4, 5, 6], [4, 6, 7],
            [0, 4, 7], [0, 7, 1],
            [1, 7, 6], [1, 6, 2],
            [2, 6, 5], [2, 5, 3],
            [3, 5, 4], [3, 4, 0],
        ]
        
        # Faces for arms (4 rotors)
        arm_faces = []
        for i in range(4):
            base = arm_offset + i * 8
            arm_faces.extend([
                [base, base+1, base+2], [base, base+2, base+3],
                [base+4, base+5, base+6], [base+4, base+6, base+7],
                [base, base+4, base+7], [base, base+7, base+1],
                [base+1, base+7, base+6], [base+1, base+6, base+2],
                [base+2, base+6, base+5], [base+2, base+5, base+3],
                [base+3, base+5, base+4], [base+3, base+4, base],
            ])
        
        faces = np.array(body_faces + arm_faces, dtype=np.uint32)
        
        return vertices, faces
    
    @staticmethod
    def create_satellite() -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a satellite shape (body + solar panels + antenna).
        """
        vertices = []
        
        # Main body (box)
        body_verts = [
            [-0.25, -0.25, -0.4], [0.25, -0.25, -0.4], [0.25, 0.25, -0.4], [-0.25, 0.25, -0.4],
            [-0.25, -0.25, 0.4], [-0.25, 0.25, 0.4], [0.25, 0.25, 0.4], [0.25, -0.25, 0.4],
        ]
        vertices.extend(body_verts)
        
        # Solar panels (left and right)
        panel_verts = [
            # Left panel
            [-1.5, 0.05, -0.3], [-0.3, 0.05, -0.3], [-0.3, 0.05, 0.3], [-1.5, 0.05, 0.3],
            [-1.5, -0.05, -0.3], [-1.5, -0.05, 0.3], [-0.3, -0.05, 0.3], [-0.3, -0.05, -0.3],
            # Right panel
            [0.3, 0.05, -0.3], [1.5, 0.05, -0.3], [1.5, 0.05, 0.3], [0.3, 0.05, 0.3],
            [0.3, -0.05, -0.3], [0.3, -0.05, 0.3], [1.5, -0.05, 0.3], [1.5, -0.05, -0.3],
        ]
        vertices.extend(panel_verts)
        
        # Antenna (cone at top)
        antenna_base = len(vertices)
        n = 8
        radius = 0.05
        
        for i in range(n):
            angle = 2 * np.pi * i / n
            x = radius * np.cos(angle)
            z = radius * np.sin(angle)
            vertices.append([x, 0.25, z])
        
        vertices.append([0, 0.6, 0])  # Antenna tip
        
        vertices = np.array(vertices, dtype=np.float32)
        
        # Faces
        body_faces = [
            [0, 1, 2], [0, 2, 3],
            [4, 5, 6], [4, 6, 7],
            [0, 4, 7], [0, 7, 1],
            [1, 7, 6], [1, 6, 2],
            [2, 6, 5], [2, 5, 3],
            [3, 5, 4], [3, 4, 0],
        ]
        
        # Left panel faces
        left_base = 8
        left_panel_faces = [
            [left_base, left_base+1, left_base+2], [left_base, left_base+2, left_base+3],
            [left_base+4, left_base+5, left_base+6], [left_base+4, left_base+6, left_base+7],
            [left_base, left_base+4, left_base+7], [left_base, left_base+7, left_base+1],
            [left_base+1, left_base+7, left_base+6], [left_base+1, left_base+6, left_base+2],
            [left_base+2, left_base+6, left_base+5], [left_base+2, left_base+5, left_base+3],
            [left_base+3, left_base+5, left_base+4], [left_base+3, left_base+4, left_base],
        ]
        
        # Right panel faces
        right_base = 16
        right_panel_faces = [
            [right_base, right_base+1, right_base+2], [right_base, right_base+2, right_base+3],
            [right_base+4, right_base+5, right_base+6], [right_base+4, right_base+6, right_base+7],
            [right_base, right_base+4, right_base+7], [right_base, right_base+7, right_base+1],
            [right_base+1, right_base+7, right_base+6], [right_base+1, right_base+6, right_base+2],
            [right_base+2, right_base+6, right_base+5], [right_base+2, right_base+5, right_base+3],
            [right_base+3, right_base+5, right_base+4], [right_base+3, right_base+4, right_base],
        ]
        
        # Antenna faces
        antenna_faces = []
        tip = antenna_base + n
        for i in range(n):
            next_i = (i + 1) % n
            antenna_faces.append([antenna_base + i, antenna_base + next_i, tip])
        
        all_faces = body_faces + left_panel_faces + right_panel_faces + antenna_faces
        faces = np.array(all_faces, dtype=np.uint32)
        
        return vertices, faces


def load_asset(asset_type: str, use_mock: bool = False, cache_dir: str = "./assets_cache", 
               api_key: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Load a 3D asset for use with pyqtgraph.opengl.GLMeshItem.
    
    Attempts to load from Sketchfab first, falls back to procedural generation.
    
    Args:
        asset_type: One of 'drone', 'crystal', 'satellite', 'cube', 'sphere', 'pyramid'
        use_mock: Force use of procedural generation
        cache_dir: Directory for caching downloaded assets
        api_key: Sketchfab API key for downloads
        
    Returns:
        Tuple of (vertices, faces, metadata)
        - vertices: np.ndarray of shape (N, 3) with float32 coordinates
        - faces: np.ndarray of shape (M, 3) with uint32 indices
        - metadata: Dict with asset info
        
    Example:
        >>> vertices, faces, meta = load_asset("drone")
        >>> mesh_item = GLMeshItem(vertexes=vertices, faces=faces, 
        ...                        faceColors=colors, smooth=False)
    """
    asset_type = asset_type.lower()
    
    metadata = {
        "type": asset_type,
        "source": "unknown",
        "vertex_count": 0,
        "face_count": 0
    }
    
    # Map mock types to generator functions
    mock_generators = {
        "cube": MockAsset.create_cube,
        "sphere": MockAsset.create_sphere,
        "pyramid": MockAsset.create_pyramid,
        "crystal": MockAsset.create_crystal,
        "drone": MockAsset.create_drone,
        "satellite": MockAsset.create_satellite,
    }
    
    # If explicitly requesting a mock shape or use_mock is True
    if asset_type in mock_generators and use_mock:
        vertices, faces = mock_generators[asset_type]()
        metadata["source"] = "procedural"
        metadata["vertex_count"] = len(vertices)
        metadata["face_count"] = len(faces)
        return vertices, faces, metadata
    
    # Try to load from Sketchfab
    if not use_mock and asset_type in SketchfabAssetLoader.ASSETS:
        loader = SketchfabAssetLoader(cache_dir=cache_dir, api_key=api_key)
        vertices, faces = loader.load(asset_type)
        
        if vertices is not None and faces is not None:
            metadata["source"] = "sketchfab"
            metadata["url"] = SketchfabAssetLoader.ASSETS[asset_type]["url"]
            metadata["name"] = SketchfabAssetLoader.ASSETS[asset_type]["name"]
            metadata["vertex_count"] = len(vertices)
            metadata["face_count"] = len(faces)
            return vertices, faces, metadata
        else:
            logger.info(f"Failed to load {asset_type} from Sketchfab, using procedural fallback")
    
    # Fall back to procedural generation
    if asset_type in mock_generators:
        vertices, faces = mock_generators[asset_type]()
        metadata["source"] = "procedural_fallback"
        metadata["vertex_count"] = len(vertices)
        metadata["face_count"] = len(faces)
        return vertices, faces, metadata
    
    raise ValueError(f"Unknown asset type: {asset_type}. "
                     f"Available: {list(SketchfabAssetLoader.ASSETS.keys()) + list(mock_generators.keys())}")


# Convenience functions for direct access
def load_drone(**kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Load drone asset."""
    return load_asset("drone", **kwargs)


def load_crystal(**kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Load crystal asset."""
    return load_asset("crystal", **kwargs)


def load_satellite(**kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Load satellite asset."""
    return load_asset("satellite", **kwargs)


# Export list
__all__ = [
    "SketchfabAssetLoader",
    "MockAsset",
    "load_asset",
    "load_drone",
    "load_crystal",
    "load_satellite",
]


# Demo/test
if __name__ == "__main__":
    print("Asset Loader Test")
    print("=" * 50)
    
    # Test all asset types
    for asset_type in ["drone", "crystal", "satellite", "cube", "sphere", "pyramid"]:
        try:
            print(f"\nTesting {asset_type}...")
            vertices, faces, metadata = load_asset(asset_type, use_mock=True)
            print(f"  Vertices: {len(vertices)}")
            print(f"  Faces: {len(faces)}")
            print(f"  Source: {metadata['source']}")
            print(f"  Vertex shape: {vertices.shape}")
            print(f"  Face shape: {faces.shape}")
            print(f"  Vertex dtype: {vertices.dtype}")
            print(f"  Face dtype: {faces.dtype}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n" + "=" * 50)
    print("Asset URLs (for manual download):")
    for key, info in SketchfabAssetLoader.ASSETS.items():
        print(f"  {key}: {info['url']}")
        print(f"    Name: {info['name']}")
        print(f"    Author: {info['author']}")
        print(f"    License: {info['license']}")
