import bpy, sys, os, traceback, mathutils, zipfile, re

try:
    argv = sys.argv[sys.argv.index("--") + 1:]
    usdz_in = argv[0]
    glb_out = argv[1]

    print(f"Input: {usdz_in}")
    print(f"Output: {glb_out}")
    print(f"Input exists: {os.path.exists(usdz_in)}")
    print(f"Input size: {os.path.getsize(usdz_in)} bytes")

    # --- Detect metersPerUnit from the USDZ before importing ---
    meters_per_unit = 1.0
    try:
        from pxr import Usd, UsdGeom
        stage = Usd.Stage.Open(usdz_in)
        meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
        up_axis = UsdGeom.GetStageUpAxis(stage)
        print(f"  USD_STAGE metersPerUnit={meters_per_unit}, upAxis={up_axis}")
        del stage
    except Exception as pxr_err:
        print(f"  pxr not available ({pxr_err}), falling back to zip grep")
        try:
            with zipfile.ZipFile(usdz_in, 'r') as z:
                for name in z.namelist():
                    if name.endswith('.usda') or name.endswith('.usdc') or name.endswith('.usd'):
                        raw = z.read(name)
                        try:
                            text = raw.decode('utf-8', errors='ignore')
                        except:
                            text = str(raw)
                        m = re.search(r'metersPerUnit\s*=\s*([\d.eE+-]+)', text)
                        if m:
                            meters_per_unit = float(m.group(1))
                            print(f"  USD_STAGE (grep) metersPerUnit={meters_per_unit} from {name}")
                            break
        except Exception as zip_err:
            print(f"  zip grep failed: {zip_err}")

    print(f"  FINAL metersPerUnit={meters_per_unit}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(filepath=usdz_in)

    obj_count = len(bpy.context.scene.objects)
    print(f"Imported {obj_count} objects")

    if obj_count == 0:
        print("ERROR: No objects imported")
        sys.exit(1)

    # Log scene unit settings
    us = bpy.context.scene.unit_settings
    print(f"  UNITS system={us.system}, scale_length={us.scale_length}, length_unit={us.length_unit}")

    # Log transforms BEFORE flattening
    for obj in bpy.context.scene.objects:
        ws = obj.matrix_world.to_scale()
        print(f"  PRE  {obj.name}: scale={obj.scale[:]}, world_scale=({ws.x:.4f},{ws.y:.4f},{ws.z:.4f}), loc={obj.location[:]}, parent={obj.parent.name if obj.parent else None}")

    # 1) Unparent all objects while keeping their world transform
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    # 2) Apply transforms so geometry vertices are in world-space
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 3) If metersPerUnit != 1.0, scale all geometry to compensate
    if abs(meters_per_unit - 1.0) > 0.001:
        scale_factor = meters_per_unit
        print(f"  SCALING all objects by {scale_factor} to compensate metersPerUnit={meters_per_unit}")
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.transform.resize(value=(scale_factor, scale_factor, scale_factor))
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # --- Clip floor meshes to wall bounding box ---
    import bmesh
    wall_objs = [o for o in bpy.data.objects if o.type == 'MESH' and 'Wall' in o.name]
    floor_objs = [o for o in bpy.data.objects if o.type == 'MESH' and 'Floor' in o.name]

    if wall_objs and floor_objs:
        # Compute wall bounds
        wall_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
        wall_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
        for wo in wall_objs:
            for v in wo.data.vertices:
                co = wo.matrix_world @ v.co
                wall_min.x = min(wall_min.x, co.x)
                wall_min.y = min(wall_min.y, co.y)
                wall_min.z = min(wall_min.z, co.z)
                wall_max.x = max(wall_max.x, co.x)
                wall_max.y = max(wall_max.y, co.y)
                wall_max.z = max(wall_max.z, co.z)

        print(f"  WALL_BOUNDS: X=[{wall_min.x*3.28084:.3f}, {wall_max.x*3.28084:.3f}]ft  Y=[{wall_min.y*3.28084:.3f}, {wall_max.y*3.28084:.3f}]ft")

        for fo in floor_objs:
            bm = bmesh.new()
            bm.from_mesh(fo.data)

            # Clip -X: normal points INWARD (+X) to keep interior
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(wall_min.x - margin, 0, 0), plane_no=(1, 0, 0), clear_inner=True)
            # Clip +X: normal points INWARD (-X)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(wall_max.x + margin, 0, 0), plane_no=(-1, 0, 0), clear_inner=True)
            # Clip -Y: normal points INWARD (+Y)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(0, wall_min.y - margin, 0), plane_no=(0, 1, 0), clear_inner=True)
            # Clip +Y: normal points INWARD (-Y)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(0, wall_max.y + margin, 0), plane_no=(0, -1, 0), clear_inner=True)
            
            bm.to_mesh(fo.data)
            bm.free()
            fo.data.update()
            
            # Log clipped dimensions
            verts = [fo.matrix_world @ v.co for v in fo.data.vertices]
            if verts:
                xs = [v.x for v in verts]
                ys = [v.y for v in verts]
                print(f"  CLIPPED {fo.name}: X=[{min(xs)*3.28084:.3f}, {max(xs)*3.28084:.3f}]ft  Y=[{min(ys)*3.28084:.3f}, {max(ys)*3.28084:.3f}]ft")
            else:
                print(f"  CLIPPED {fo.name}: NO VERTICES REMAINING")

    # Force depsgraph update so bound_box is fresh
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()

    # Log transforms AFTER flattening
    for obj in bpy.context.scene.objects:
        print(f"  POST {obj.name}: scale={obj.scale[:]}, loc={obj.location[:]}")

    # Log bounding boxes
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

    # Per-vertex diagnostics for Floor meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and 'Floor' in obj.name:
            verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
            if verts:
                xs = [v.x for v in verts]
                ys = [v.y for v in verts]
                zs = [v.z for v in verts]
                print(f"  VERTS {obj.name}: X=[{min(xs)*3.28084:.3f}, {max(xs)*3.28084:.3f}]ft  Y=[{min(ys)*3.28084:.3f}, {max(ys)*3.28084:.3f}]ft  Z=[{min(zs)*3.28084:.3f}, {max(zs)*3.28084:.3f}]ft  vtx_count={len(verts)}")
                for i, v in enumerate(verts):
                    print(f"  V{i}: ({v.x*3.28084:.3f}, {v.y*3.28084:.3f}, {v.z*3.28084:.3f}) ft")
            else:
                print(f"  VERTS {obj.name}: NO VERTICES")

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

