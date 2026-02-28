import bpy, sys, os, traceback

try:
    argv = sys.argv[sys.argv.index("--") + 1:]
    usdz_in = argv[0]
    glb_out = argv[1]

    print(f"Input: {usdz_in}")
    print(f"Output: {glb_out}")
    print(f"Input exists: {os.path.exists(usdz_in)}")
    print(f"Input size: {os.path.getsize(usdz_in)} bytes")

    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import USD — Blender respects metersPerUnit automatically
    bpy.ops.wm.usd_import(filepath=usdz_in)

    obj_count = len(bpy.context.scene.objects)
    print(f"Imported {obj_count} objects")

    if obj_count == 0:
        print("ERROR: No objects imported")
        sys.exit(1)

    # Log scale of each object for debugging
    for obj in bpy.context.scene.objects:
        print(f"  {obj.name}: scale={obj.scale[:]}, location={obj.location[:]}")

    # Do NOT apply transforms — the GLTF exporter preserves
    # the hierarchy and scale correctly without baking.

    export_path = glb_out
    if export_path.endswith(".glb"):
        export_path = export_path[:-4]

    bpy.ops.export_scene.gltf(
        filepath=export_path,
        export_format='GLB',
        export_yup=True,
    )

    if os.path.exists(glb_out):
        print(f"OK: exported {os.path.getsize(glb_out)} bytes to {glb_out}")
    elif os.path.exists(export_path + ".glb"):
        print(f"OK: exported {os.path.getsize(export_path + '.glb')} bytes to {export_path}.glb")
    else:
        print("ERROR: GLB not found")
        sys.exit(1)

except Exception as e:
    traceback.print_exc()
    sys.exit(1)
