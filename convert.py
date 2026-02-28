import bpy, sys, os, traceback, mathutils

try:
    argv = sys.argv[sys.argv.index("--") + 1:]
    usdz_in = argv[0]
    glb_out = argv[1]

    print(f"Input: {usdz_in}")
    print(f"Output: {glb_out}")
    print(f"Input exists: {os.path.exists(usdz_in)}")
    print(f"Input size: {os.path.getsize(usdz_in)} bytes")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(filepath=usdz_in)

    obj_count = len(bpy.context.scene.objects)
    print(f"Imported {obj_count} objects")

    if obj_count == 0:
        print("ERROR: No objects imported")
        sys.exit(1)

    # Log transforms BEFORE flattening
    for obj in bpy.context.scene.objects:
        print(f"  PRE  {obj.name}: scale={obj.scale[:]}, loc={obj.location[:]}, parent={obj.parent.name if obj.parent else None}")

    # Bake each mesh's world matrix directly into its vertex data
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            mat = obj.matrix_world.copy()
            obj.data.transform(mat)
            obj.data.update()

    # Clear parents (plain clear, transforms already baked)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.parent_clear(type='CLEAR')

    # Reset all transforms to identity
    for obj in bpy.data.objects:
        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        obj.scale = (1, 1, 1)

    # Log transforms AFTER flattening
    for obj in bpy.context.scene.objects:
        print(f"  POST {obj.name}: scale={obj.scale[:]}, loc={obj.location[:]}")

    # Log bounding boxes to diagnose dimension issues
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bbox = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
            xs = [v.x for v in bbox]
            ys = [v.y for v in bbox]
            zs = [v.z for v in bbox]
            size_x = (max(xs) - min(xs)) * 3.28084
            size_y = (max(ys) - min(ys)) * 3.28084
            size_z = (max(zs) - min(zs)) * 3.28084
            print(f"  BBOX {obj.name}: X={size_x:.3f}ft Y={size_y:.3f}ft Z={size_z:.3f}ft")

    # Per-vertex min/max for Floor meshes to diagnose axis stretching
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and 'Floor' in obj.name:
            verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
            xs = [v.x for v in verts]
            ys = [v.y for v in verts]
            zs = [v.z for v in verts]
            print(f"  VERTS {obj.name}: X=[{min(xs)*3.28084:.3f}, {max(xs)*3.28084:.3f}]ft  Y=[{min(ys)*3.28084:.3f}, {max(ys)*3.28084:.3f}]ft  Z=[{min(zs)*3.28084:.3f}, {max(zs)*3.28084:.3f}]ft  vtx_count={len(verts)}")

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

