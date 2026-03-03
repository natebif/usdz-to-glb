import bpy, sys, os, traceback, mathutils, zipfile, re

try:
    argv = sys.argv[sys.argv.index("--") + 1:]
    usdz_in = argv[0]
    glb_out = argv[1]

    print(f"CONVERT_VERSION=6")
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

    M2FT = 3.28084

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

    wall_min = None
    wall_max = None

    if wall_objs and floor_objs:
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

        print(f"  WALL_BOUNDS: X=[{wall_min.x*M2FT:.3f}, {wall_max.x*M2FT:.3f}]ft  Y=[{wall_min.y*M2FT:.3f}, {wall_max.y*M2FT:.3f}]ft")

        margin = 0.01
        for fo in floor_objs:
            bm = bmesh.new()
            bm.from_mesh(fo.data)

            inv = fo.matrix_world.inverted()
            local_min = inv @ wall_min
            local_max = inv @ wall_max

            bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(local_min.x - margin, 0, 0), plane_no=(1, 0, 0), clear_inner=True)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(local_max.x + margin, 0, 0), plane_no=(-1, 0, 0), clear_inner=True)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(0, local_min.y - margin, 0), plane_no=(0, 1, 0), clear_inner=True)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(0, local_max.y + margin, 0), plane_no=(0, -1, 0), clear_inner=True)

            bm.to_mesh(fo.data)
            bm.free()
            print(f"  CLIPPED {fo.name} to wall bounds")

    # --- Compute interior ROOM dimensions from opposing wall pairs ---
    if wall_objs:
        wall_data = []
        for wo in wall_objs:
            verts = wo.data.vertices
            xs = [v.co.x for v in verts]
            ys = [v.co.y for v in verts]
            zs = [v.co.z for v in verts]
            wall_data.append({
                'name': wo.name,
                'cx': (min(xs) + max(xs)) / 2,
                'cy': (min(ys) + max(ys)) / 2,
                'dx': max(xs) - min(xs),
                'dy': max(ys) - min(ys),
                'dz': max(zs) - min(zs),
            })
            print(f"  WALLINFO {wo.name}: cx={wall_data[-1]['cx']*M2FT:.3f}ft cy={wall_data[-1]['cy']*M2FT:.3f}ft dx={wall_data[-1]['dx']*M2FT:.3f}ft dy={wall_data[-1]['dy']*M2FT:.3f}ft")

        # Classify: if dx > dy, wall runs along X axis (defines Y boundary)
        x_walls = [w for w in wall_data if w['dx'] > w['dy']]
        y_walls = [w for w in wall_data if w['dy'] >= w['dx']]

        room_x_ft = 0
        room_y_ft = 0
        room_z_ft = 0

        if len(y_walls) >= 2:
            y_walls.sort(key=lambda w: w['cx'])
            room_x_ft = (abs(y_walls[-1]['cx'] - y_walls[0]['cx'])
                         - (y_walls[0]['dx'] + y_walls[-1]['dx']) / 2) * M2FT

        if len(x_walls) >= 2:
            x_walls.sort(key=lambda w: w['cy'])
            room_y_ft = (abs(x_walls[-1]['cy'] - x_walls[0]['cy'])
                         - (x_walls[0]['dy'] + x_walls[-1]['dy']) / 2) * M2FT

        if wall_data:
            room_z_ft = max(w['dz'] for w in wall_data) * M2FT

        section_children = [o for o in bpy.data.objects if o.type == 'EMPTY'
                           and o.parent and 'Section' in o.parent.name
                           and '_centerTop' not in o.name]
        room_name = section_children[0].name if section_children else "room0"
        print(f"  ROOM {room_name}: X={room_x_ft:.3f}ft Y={room_y_ft:.3f}ft Z={room_z_ft:.3f}ft")
    else:
        print("  ROOM info: no walls found, cannot compute room")

    # --- Log BBOX and VERTS for all mesh objects ---
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.data.vertices:
            continue
        verts = obj.data.vertices
        xs = [v.co.x for v in verts]
        ys = [v.co.y for v in verts]
        zs = [v.co.z for v in verts]
        dx = (max(xs) - min(xs)) * M2FT
        dy = (max(ys) - min(ys)) * M2FT
        dz = (max(zs) - min(zs)) * M2FT
        print(f"  BBOX {obj.name}: X={dx:.3f}ft Y={dy:.3f}ft Z={dz:.3f}ft")
        if 'Floor' in obj.name:
            print(f"  VERTS {obj.name}: X=[{min(xs)*M2FT:.3f}, {max(xs)*M2FT:.3f}]ft  Y=[{min(ys)*M2FT:.3f}, {max(ys)*M2FT:.3f}]ft  Z=[{min(zs)*M2FT:.3f}, {max(zs)*M2FT:.3f}]ft  vtx_count={len(verts)}")

    # --- Export GLB ---
    bpy.ops.export_scene.gltf(filepath=glb_out, export_format='GLB')

    glb_size = os.path.getsize(glb_out)
    print(f"\nOK: exported {glb_size} bytes to {glb_out}")

except Exception as e:
    traceback.print_exc()
    print(f"FATAL: {e}")
    sys.exit(1)
