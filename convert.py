import bpy, sys, os

argv = sys.argv[sys.argv.index("--") + 1:]
usdz_in = argv[0]
glb_out = argv[1]

# Blender's gltf exporter appends .glb automatically, so strip it
if glb_out.endswith(".glb"):
    glb_out = glb_out[:-4]

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# In Blender 4.1+, USD import is built-in — no addon needed
bpy.ops.wm.usd_open(filepath=usdz_in)

if len(bpy.context.scene.objects) == 0:
    print("ERROR: No objects imported")
    sys.exit(1)

# Apply transforms for correct scale in Three.js
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Export
bpy.ops.export_scene.gltf(filepath=glb_out, export_format='GLB', export_yup=True)

final_path = glb_out + ".glb"
if not os.path.exists(final_path):
    print("ERROR: GLB not created at " + final_path)
    sys.exit(1)

print("OK: exported " + str(os.path.getsize(final_path)) + " bytes")

