import sys
from pxr import Usd, UsdGeom
import trimesh
import numpy as np

stage = Usd.Stage.Open(sys.argv[1])
scene = trimesh.Scene()
for prim in stage.Traverse():
    if prim.IsA(UsdGeom.Mesh):
        mesh = UsdGeom.Mesh(prim)
        points = np.array(mesh.GetPointsAttr().Get())
        indices = np.array(mesh.GetFaceVertexIndicesAttr().Get())
        counts = np.array(mesh.GetFaceVertexCountsAttr().Get())
        faces = indices.reshape(-1, 3) if all(c == 3 for c in counts) else None
        if faces is not None:
            scene.add_geometry(trimesh.Trimesh(vertices=points, faces=faces))
scene.export(sys.argv[2], file_type='glb')


