import bpy, sys, os, zipfile

input_path = sys.argv[-2]
output_path = sys.argv[-1]

# USDZ is a ZIP — extract the .usdc/.usda inside
extract_dir = input_path + "_extracted"
os.makedirs(extract_dir, exist_ok=True)
usd_file = input_path  # fallback

if zipfile.is_zipfile(input_path):
    with zipfile.ZipFile(input_path, 'r') as z:
        z.extractall(extract_dir)
        for f in z.namelist():
            if f.endswith(('.usdc', '.usda', '.usd')):
                usd_file = os.path.join(extract_dir, f)
                break

bpy.ops.wm.read_factory_settings(use_empty=True)

try:
    bpy.ops.import_scene.usd(filepath=usd_file)
except Exception as e:
    print(f"import_scene.usd failed: {e}")
    try:
        bpy.ops.wm.usd_open(filepath=usd_file)
    except Exception as e2:
        print(f"wm.usd_open also failed: {e2}")
        sys.exit(1)

if len(bpy.context.scene.objects) == 0:
    print("ERROR: No objects imported")
    sys.exit(1)

bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB')

if not os.path.exists(output_path):
    print("ERROR: GLB not created")
    sys.exit(1)

print(f"OK: exported {os.path.getsize(output_path)} bytes")
