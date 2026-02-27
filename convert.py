import bpy
import sys

argv = sys.argv
args = argv[argv.index("--") + 1:]
input_path = args[0]
output_path = args[1]

bpy.ops.wm.read_factory_settings(use_empty=True)

# Use import_scene.usd instead of wm.usd_open
bpy.ops.import_scene.usd(filepath=input_path)

for obj in bpy.context.scene.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = bpy.context.scene.objects[0] if bpy.context.scene.objects else None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

bpy.ops.export_scene.gltf(
    filepath=output_path.replace('.glb', ''),
    export_format='GLB',
    export_apply=True,
    export_yup=True,
)
