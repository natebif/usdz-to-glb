import bpy
import sys
import os

argv = sys.argv
args = argv[argv.index("--") + 1:]
input_path = args[0]
output_path = args[1]

bpy.ops.wm.read_factory_settings(use_empty=True)

# Try both import methods
try:
    bpy.ops.wm.usd_open(filepath=input_path)
except Exception as e:
    print(f"wm.usd_open failed: {e}, trying import_scene.usd")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.usd(filepath=input_path)

print(f"Objects in scene: {len(bpy.context.scene.objects)}")
if len(bpy.context.scene.objects) == 0:
    print("ERROR: No objects imported from USD file!")
    sys.exit(1)

for obj in bpy.context.scene.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = bpy.context.scene.objects[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

bpy.ops.export_scene.gltf(
    filepath=output_path.replace('.glb', ''),
    export_format='GLB',
    export_apply=True,
    export_yup=True,
)

if not os.path.exists(output_path):
    print(f"ERROR: GLB not found at {output_path}")
    sys.exit(1)

print("Export complete.")
