import bpy, sys, os, traceback, mathutils, zipfile, re, math

try:
    argv = sys.argv[sys.argv.index("--") + 1:]
    usdz_in = argv[0]
    glb_out = argv[1]

    print(f"CONVERT_VERSION=13")
    print(f"Input: {usdz_in}")
    print(f"Output: {glb_out}")
    print(f"Input exists: {os.path.exists(usdz_in)}")
    print(f"Input size: {os.path.getsize(usdz_in)} bytes")

    # --- Extract USD metadata BEFORE Blender import ---
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

            if any(kw in path_lower for kw in ['section', 'bedroom', 'room', 'kitchen', 'bath', 'living', 'hall', 'dining', 'closet', 'laundry', 'garage']):
                if '_centertop' in path_lower or path.endswith('_grp') or path.endswith('Section_grp'):
                    continue
                print(f"  USD_PRIM {path} type={type_name}")
                for attr in prim.GetAttributes():
                    val = attr.Get()
                    if val is not None:
                        print(f"    USD_ATTR {attr.GetName()} = {val}")
                try:
                    boundable = UsdGeom.Boundable(prim)
                    ext = boundable.GetExtentAttr().Get()
                    if ext and len(ext) == 2:
                        dx = abs(ext[1][0] - ext[0][0])
                        dy = abs(ext[1][1] - ext[0][1])
                        dz = abs(ext[1][2] - ext[0][2])
                        print(f"    USD_EXTENT dx={dx:.4f} dy={dy:.4f} dz={dz:.4f}")
                        room_name = path.split('/')[-1]
                        usd_room_dims[room_name] = {'x': dx, 'y': dy, 'z': dz}
                except:
                    pass

            if 'wall' in path_lower and type_name and not path.endswith('_grp'):
                try:
                    boundable = UsdGeom.Boundable(prim)
                    ext = boundable.GetExtentAttr().Get()
                    if ext and len(ext) == 2:
                        dx = abs(ext[1][0] - ext[0][0])
                        dy = abs(ext[1][1] - ext[0][1])
                        dz = abs(ext[1][2] - ext[0][2])
                        print(f"  USD_WALL {path} extent=({dx:.4f},{dy:.4f},{dz:.4f})")
                except:
                    pass

        for rname, dims in usd_room_dims.items():
            M2FT = 3.28084
            rx = dims['x'] * meters_per_unit * M2FT
            ry = dims['y'] * meters_per_unit * M2FT
            rz = dims['z'] * meters_per_unit * M2FT
            print(f"  USD_ROOM {rname}: X={rx:.3f}ft Y={ry:.3f}ft Z={rz:.3f}ft (raw: {dims['x']:.4f} {dims['y']:.4f} {dims['z']:.4f}, mpu={meters_per_unit})")

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

    # --- v13: Capture wall world-space centers BEFORE flattening ---
    # Uses Euclidean distance between opposing wall pairs (handles rotated rooms)
    wall_world_centers = []
    for obj in bpy.context.scene.objects:
        ws = obj.matrix_world.to_scale()
        wt = obj.matrix_world.to_translation()
        print(f"  PRE  {obj.name}: scale={obj.scale[:]}, world_scale=({ws.x:.4f},{ws.y:.4f},{ws.z:.4f}), world_pos=({wt.x:.4f},{wt.y:.4f},{wt.z:.4f}), loc={obj.location[:]}, parent={obj.parent.name if obj.parent else None}")

        if obj.type == 'MESH' and 'Wall' in obj.name:
            # World-space bounding box center
            bbox_corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
            xs = [c.x for c in bbox_corners]
            ys = [c.y for c in bbox_corners]
            zs = [c.z for c in bbox_corners]
            cx = (min(xs) + max(xs)) / 2
            cy = (min(ys) + max(ys)) / 2
            world_dz = max(zs) - min(zs)

            # LOCAL bbox = true wall dimensions (not inflated by rotation)
            local_corners = [mathutils.Vector(c) for c in obj.bound_box]
            ldx = max(c.x for c in local_corners) - min(c.x for c in local_corners)
            ldy = max(c.y for c in local_corners) - min(c.y for c in local_corners)
            ldz = max(c.z for c in local_corners) - min(c.z for c in local_corners)

            # Wall thickness = smallest dimension
            thickness = min(ldx, ldy, ldz)

            wall_info = {
                'name': obj.name,
                'cx': cx, 'cy': cy,
                'thickness': thickness,
                'world_dz': world_dz,
            }
            wall_world_centers.append(wall_info)
            print(f"  WALL_GEOM {obj.name}: center=({cx*M2FT:.3f},{cy*M2FT:.3f})ft local=({ldx*M2FT:.3f},{ldy*M2FT:.3f},{ldz*M2FT:.3f})ft thickness={thickness*M2FT:.3f}ft")

    # --- v13: Pair walls by number (0↔2, 1↔3) and use Euclidean distance ---
    wall_by_num = {}
    for w in wall_world_centers:
        num = ''.join(c for c in w['name'] if c.isdigit())
        if num:
            wall_by_num[int(num)] = w

    pairs = []
    used = set()
    for n in sorted(wall_by_num.keys()):
        opp = n + 2
        if opp in wall_by_num and n not in used and opp not in used:
            pairs.append((wall_by_num[n], wall_by_num[opp]))
            used.add(n)
            used.add(opp)

    room_x_ft = None
    room_y_ft = None
    room_z_ft = None

    room_dims_ft = []
    for w0, w1 in pairs:
        dist = math.sqrt((w0['cx'] - w1['cx'])**2 + (w0['cy'] - w1['cy'])**2)
        avg_thick = (w0['thickness'] + w1['thickness']) / 2
        inner = dist - avg_thick
        dim_ft = inner * M2FT
        room_dims_ft.append(dim_ft)
        print(f"  ROOM_DIM {w0['name']}↔{w1['name']}: euclidean={dist*M2FT:.3f}ft, avg_thick={avg_thick*M2FT:.3f}ft, inner={dim_ft:.3f}ft")

    if len(room_dims_ft) >= 1:
        room_x_ft = room_dims_ft[0]
    if len(room_dims_ft) >= 2:
        room_y_ft = room_dims_ft[1]

    if wall_world_centers:
        room_z_ft = max(w['world_dz'] for w in wall_world_centers) * M2FT

    # --- Now flatten hierarchy ---
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

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

    # --- Emit ROOM lines ---
    if usd_room_dims:
        for rname, dims in usd_room_dims.items():
            rx = dims['x'] * meters_per_unit * M2FT
            ry = dims['y'] * meters_per_unit * M2FT
            rz = dims['z'] * meters_per_unit * M2FT
            print(f"  ROOM {rname}: X={rx:.3f}ft Y={ry:.3f}ft Z={rz:.3f}ft")
    elif room_x_ft is not None and room_y_ft is not None:
        print(f"  ROOM room0: X={room_x_ft:.3f}ft Y={room_y_ft:.3f}ft Z={room_z_ft:.3f}ft")
    elif wall_min and wall_max:
        room_x = (wall_max.x - wall_min.x) * M2FT
        room_y = (wall_max.y - wall_min.y) * M2FT
        room_z = (wall_max.z - wall_min.z) * M2FT
        print(f"  ROOM room0: X={room_x:.3f}ft Y={room_y:.3f}ft Z={room_z:.3f}ft")
    else:
        print("  ROOM info: no walls found, cannot compute room")

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

