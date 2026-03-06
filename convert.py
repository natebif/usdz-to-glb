import bpy, sys, os, traceback, mathutils, zipfile, re

try:
    argv = sys.argv[sys.argv.index("--") + 1:]
    usdz_in = argv[0]
    glb_out = argv[1]

    print(f"CONVERT_VERSION=11")
    print(f"Input: {usdz_in}")
    print(f"Output: {glb_out}")
    print(f"Input exists: {os.path.exists(usdz_in)}")
    print(f"Input size: {os.path.getsize(usdz_in)} bytes")

    # --- Extract USD metadata ---
    meters_per_unit = 1.0
    usd_room_dims = {}

    try:
        from pxr import Usd, UsdGeom, Gf
        stage = Usd.Stage.Open(usdz_in)
        meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
        up_axis = UsdGeom.GetStageUpAxis(stage)
        print(f"  USD_STAGE metersPerUnit={meters_per_unit}, upAxis={up_axis}")

        for prim in stage.Traverse():
            path = str(prim.GetPath())
            type_name = prim.GetTypeName()
            path_lower = path.lower()

            if any(kw in path_lower for kw in ['section', 'bedroom', 'room', 'kitchen', 'bath', 'living', 'hall']):
                if '_centertop' in path_lower or path.endswith('_grp'):
                    continue
                print(f"  USD_PRIM {path} type={type_name}")
                for attr in prim.GetAttributes():
                    val = attr.Get()
                    if val is not None:
                        print(f"    USD_ATTR {attr.GetName()} = {val}")

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

    us = bpy.context.scene.unit_settings
    print(f"  UNITS system={us.system}, scale_length={us.scale_length}, length_unit={us.length_unit}")

    # --- Capture wall positions BEFORE flattening (world-space via parent chain) ---
    wall_centers = {}
    for obj in bpy.context.scene.objects:
        ws = obj.matrix_world.to_scale()
        wl = obj.matrix_world.translation
        print(f"  PRE  {obj.name}: scale={obj.scale[:]}, world_scale=({ws.x:.4f},{ws.y:.4f},{ws.z:.4f}), loc={obj.location[:]}, parent={obj.parent.name if obj.parent else None}")
        if obj.name.startswith('Wall') and obj.type == 'MESH':
            wall_centers[obj.name] = {'x': wl.x, 'y': wl.y, 'z': wl.z}
            print(f"  WALL_CENTER {obj.name}: world_x={wl.x:.4f} world_y={wl.y:.4f} world_z={wl.z:.4f}")

    # 1) Flatten hierarchy
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if abs(meters_per_unit - 1.0) > 0.001:
        scale_factor = meters_per_unit
        print(f"  SCALING all objects by {scale_factor}")
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

    # --- Compute ROOM dimensions from wall center-to-center ---
    # Group walls into pairs by orientation (X-aligned vs Y-aligned)
    # After transform_apply, compute each wall's principal axis from its bbox
    wall_info = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.name.startswith('Wall'):
            continue
        verts = obj.data.vertices
        if not verts:
            continue
        xs = [v.co.x for v in verts]
        ys = [v.co.y for v in verts]
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        cx = (max(xs) + min(xs)) / 2
        cy = (max(ys) + min(ys)) / 2
        # Wall runs along its longer dimension
        if dx > dy:
            orientation = 'x'  # runs along X, position defined by Y
            pos = cy
            length = dx
        else:
            orientation = 'y'  # runs along Y, position defined by X
            pos = cx
            length = dy
        wall_info.append({'name': obj.name, 'orientation': orientation, 'pos': pos, 'length': length, 'cx': cx, 'cy': cy})
        print(f"  WALL_GEOM {obj.name}: orient={orientation} pos={pos*M2FT:.3f}ft length={length*M2FT:.3f}ft center=({cx*M2FT:.3f},{cy*M2FT:.3f})ft")

    # Find room dimensions from opposing wall pairs
    x_walls = sorted([w for w in wall_info if w['orientation'] == 'y'], key=lambda w: w['pos'])
    y_walls = sorted([w for w in wall_info if w['orientation'] == 'x'], key=lambda w: w['pos'])

    room_x_ft = 0
    room_y_ft = 0
    room_z_ft = 0

    if len(x_walls) >= 2:
        # Distance between centers of outermost Y-oriented walls = room width
        room_x_ft = abs(x_walls[-1]['pos'] - x_walls[0]['pos']) * M2FT
        print(f"  ROOM_X from wall centers: {x_walls[0]['name']}({x_walls[0]['pos']*M2FT:.3f}ft) to {x_walls[-1]['name']}({x_walls[-1]['pos']*M2FT:.3f}ft) = {room_x_ft:.3f}ft")

    if len(y_walls) >= 2:
        room_y_ft = abs(y_walls[-1]['pos'] - y_walls[0]['pos']) * M2FT
        print(f"  ROOM_Y from wall centers: {y_walls[0]['name']}({y_walls[0]['pos']*M2FT:.3f}ft) to {y_walls[-1]['name']}({y_walls[-1]['pos']*M2FT:.3f}ft) = {room_y_ft:.3f}ft")

    if wall_min and wall_max:
        room_z_ft = (wall_max.z - wall_min.z) * M2FT

    if room_x_ft > 0 and room_y_ft > 0:
        # Use wall lengths as cross-check
        avg_x_length = sum(w['length'] for w in y_walls) / len(y_walls) * M2FT if y_walls else 0
        avg_y_length = sum(w['length'] for w in x_walls) / len(x_walls) * M2FT if x_walls else 0
        print(f"  ROOM_CROSSCHECK: x_walls avg_length={avg_x_length:.3f}ft, y_walls avg_length={avg_y_length:.3f}ft")

        section_children = [o for o in bpy.data.objects if o.type == 'EMPTY'
                           and o.parent and 'Section' in o.parent.name
                           and '_centerTop' not in o.name]
        room_name = section_children[0].name if section_children else "room0"
        print(f"  ROOM {room_name}: X={room_x_ft:.3f}ft Y={room_y_ft:.3f}ft Z={room_z_ft:.3f}ft")
    elif wall_min and wall_max:
        room_x_ft = (wall_max.x - wall_min.x) * M2FT
        room_y_ft = (wall_max.y - wall_min.y) * M2FT
        room_z_ft = (wall_max.z - wall_min.z) * M2FT
        print(f"  ROOM room0: X={room_x_ft:.3f}ft Y={room_y_ft:.3f}ft Z={room_z_ft:.3f}ft")
    else:
        print("  ROOM info: no walls found")

    # --- Log BBOX and VERTS ---
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

    bpy.ops.export_scene.gltf(filepath=glb_out, export_format='GLB')
    glb_size = os.path.getsize(glb_out)
    print(f"\nOK: exported {glb_size} bytes to {glb_out}")

except Exception as e:
    traceback.print_exc()
    print(f"FATAL: {e}")
    sys.exit(1)

