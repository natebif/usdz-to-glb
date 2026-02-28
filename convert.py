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

    bpy.ops.wm.usd_open(filepath=usdz_in)

    obj_count = len(bpy.context.scene.objects)
    print(f"Imported {obj_count} objects")

    if obj_count == 0:
        print("ERROR: No objects imported")
        sys.exit(1)

    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    export_path = glb_out
    if export_path.endswith(".glb"):
        export_path = export_path[:-4]

    bpy.ops.export_scene.gltf(filepath=export_path, export_format='GLB', export_yup=True)

    if os.path.exists(glb_out):
        print(f"OK: exported {os.path.getsize(glb_out)} bytes to {glb_out}")
    elif os.path.exists(export_path + ".glb"):
        print(f"OK: exported {os.path.getsize(export_path + '.glb')} bytes to {export_path}.glb")
    else:
        print("ERROR: GLB not found. Files in /tmp:")
        for f in os.listdir("/tmp"):
            if argv[0].split("/")[-1].replace(".usdz","") in f:
                print(f"  {f}")
        sys.exit(1)

except Exception as e:
    traceback.print_exc()
    sys.exit(1)
