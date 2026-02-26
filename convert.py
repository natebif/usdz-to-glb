import bpy
import sys

argv = sys.argv
args = argv[argv.index("--") + 1:]
input_path = args[0]
output_path = args[1]

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import USDZ (Blender handles Apple RoomPlan USD natively)
bpy.ops.wm.usd_open(filepath=input_path)

# Apply all transforms so dimensions are preserved exactly
for obj in bpy.context.scene.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = bpy.context.scene.objects[0] if bpy.context.scene.objects else None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Export as GLB — preserves geometry, materials, and real-world scale
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_apply=True,
    export_yup=True,
)

