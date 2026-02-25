import sys
from pxr import Usd, UsdGeom
import trimesh
import numpy as np

usd_file = sys.argv[1]
glb_file = sys.argv[2]

stage = Usd.Stage.Open(usd_file)
scene = trimesh.Scene()

for prim in stage.Traverse():
    if prim.IsA(UsdGeom.Mesh):
        mesh = UsdGeom.Mesh(prim)
        points = np.array(mesh.GetPointsAttr().Get())
        indices = np.array(mesh.GetFaceVertexIndicesAttr().Get())
        counts = np.array(mesh.GetFaceVertexCountsAttr().Get())

        # Only handle triangle faces
        if all(c == 3 for c in counts):
            faces = indices.reshape(-1, 3)
            scene.add_geometry(trimesh.Trimesh(vertices=points, faces=faces))

scene.export(glb_file, file_type='glb')

