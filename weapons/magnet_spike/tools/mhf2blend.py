"""Blender preview of MHF Magnet Spike motions: the MHF player (FSKL skeleton + FMOD body, face, hair) holding a Magnet
Spike model, all motions on one timeline (body + weapon). A check that tools/aan.py reads the motions right before
they are converted for MHGU.
Conventions (Paxlord's mhfz-blender-plugin model_utils.py, the plugin MHF modders use): short rotations x 2 pi / 16384
(16384 = one turn), Euler XYZ (R = Rz Ry Rx, checked against the five other orders on two-hand grips, see
notes/assets.md), absolute local values; short translations / 16; Hermite keys -> Bezier handles at dt / 3 (tangents
are per frame); bones are built at the summed local positions with identity orientation, so a posed bone = parent x
T(local position) x R(local rotation), as MHF composes them; un-keyed bones keep their FSKL rest rotation. MHF is Y up,
cm: the rig is scaled to m and turned up (+90 deg about X). The skeleton's rest origin is the hips, but motions key the
hips' absolute height (bone 2 ty ~ 88 cm) above the root (bones 0 / 1, on the floor; bone 1 carries the root motion),
so the rig sits at the floor.
The weapon's root (its bone 0) follows the hand holding it, frame by frame: MHF passes the weapon between the hands
and the weapon keys are relative to the holding one (msgrip.py). The GAP frames between two motions are not MHF
transitions: the last pose holds HOLD frames, then blends into the next motion's first pose along the shortest arc.
run:  blender -b --factory-startup -P mhf2blend.py -- OUT.blend BODY_FMOD BODY_FSKL WEAPON_DIR W13.aan W13W.aan
          [--hand N] [--render DIR] MOTION[=NAME] ...
      MOTION = bank-1 motion ID (bank * 1000 + part * 100 + slot, e.g. 1049); --hand N = keep the weapon in player
      bone N (14 or 18) instead of msgrip's hand per frame; --render writes PNG frames of every motion to DIR
      (workbench) for a quick look."""
import bpy, math, os, sys
from mathutils import Matrix, Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aan, fskl, fmod, msgrip

ROT = 2 * math.pi / 16384
M = 0.01  # cm -> m
GAP, HOLD = 20, 6  # frames between two motions on the timeline; of those, frames that keep the last pose
FPS = 60  # MHF motion frames per second (S, notes/assets.md: run cadence, set-motion halving the step blends)
BODY_MESHES = (0, 32, 59)  # m_editpl: body variant 0, face 0, hair 0 (0-31 bodies, 32-58 faces, 59-76 hair)


def args():
    a = sys.argv[sys.argv.index('--') + 1:]
    out, body, bskl, wdir, w13, w13w = a[:6]
    rest = a[6:]; hand = None; render = None; motions = []
    i = 0
    while i < len(rest):
        if rest[i] == '--hand': hand = int(rest[i + 1]); i += 2
        elif rest[i] == '--render': render = rest[i + 1]; i += 2
        else:
            mid, _, name = rest[i].partition('='); motions.append((int(mid), name)); i += 1
    return out, body, bskl, wdir, w13, w13w, hand, render, motions


def rest_matrices(bones):
    """FSKL bone -> (fake rest = translation to the summed local positions, true rest = parent x T x R)"""
    by = {b['node']: b for b in bones}; fake, true = {}, {}
    def walk(n):
        b = by[n]; p = b['parent']
        local = Matrix.Translation(Vector(b['pos'])) @ Euler(b['rot'], 'XYZ').to_matrix().to_4x4()
        fake[n] = (fake[p] if p >= 0 else Matrix()) @ Matrix.Translation(Vector(b['pos']))
        true[n] = (true[p] if p >= 0 else Matrix()) @ local
        c = b['child']
        while c >= 0: walk(c); c = by[c]['sibling']
    for b in bones:
        if b['parent'] < 0: walk(b['node'])
    return by, fake, true


def armature(name, bones, fake):
    arm = bpy.data.armatures.new(name); obj = bpy.data.objects.new(name, arm)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for b in bones:
        e = arm.edit_bones.new('Bone_%d' % b['node'])
        h = fake[b['node']].translation * M
        e.head = h; e.tail = h + Vector((0, 0.04, 0)); eb[b['node']] = e
    for b in bones:
        if b['parent'] >= 0: eb[b['node']].parent = eb[b['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in obj.pose.bones: pb.rotation_mode = 'XYZ'
    return obj


def mesh(name, m, arm, fake, true, bone_ids):
    """FMOD mesh -> Blender mesh skinned to arm; vertices moved from MHF's true rest into the fake rest frame"""
    verts = []
    for i, p in enumerate(m['pos']):
        v = Vector(p)
        ws = m['weights'][i] if i < len(m['weights']) else []
        if ws:
            acc = Vector((0, 0, 0)); tot = 0
            for bi, w in ws:
                bid = bone_ids(bi)
                acc += (fake[bid] @ true[bid].inverted() @ v) * w; tot += w
            v = acc / tot if tot else v
        verts.append(v * M)
    tris = fmod.triangles(m)
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], [t[:3] for t in tris]); me.update()
    if m['uv']:
        uvl = me.uv_layers.new(name='UV')
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = m['uv'][me.loops[li].vertex_index]
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    for i, ws in enumerate(m['weights']):
        for bi, w in ws:
            g = ob.vertex_groups.get('Bone_%d' % bone_ids(bi)) or ob.vertex_groups.new(name='Bone_%d' % bone_ids(bi))
            g.add([i], w / 100.0, 'ADD')
    ob.parent = arm
    ob.modifiers.new('Armature', 'ARMATURE').object = arm
    return ob


def key_value(t, k, chan):
    """AAN key -> (frame, value, tan in, tan out, linear)"""
    if t in (17, 33): v, f = k; ti = to = 0.0; lin = True
    elif t in (18, 34): v, f, ti, to = k; lin = False
    else: flag, v, f, ti, to = k; lin = flag == 0x10000
    if t < 32:
        s = ROT if chan[0] == 'r' else (1 / 16.0) * M if chan[0] == 't' else 1 / 16.0
    else:
        s = M if chan[0] == 't' else 1.0
    return f, v * s, ti * s, to * s, lin


def add_motion(action, slot, arm_obj, motion_parts, by, offsets, t0):
    """motion_parts: [(AAN motion dict, [bone ids of that part in track order])]; offsets: bone id -> rest local pos (m);
    the motion's keys are placed from frame t0 on (motions follow each other on one timeline)"""
    cb = action.layers[0].strips[0].channelbag(slot, ensure=True)
    keyed = set()
    for mo, ids in motion_parts:
        for ti, chans in enumerate(mo['bones']):
            if ti >= len(ids): continue
            bid = ids[ti]
            for chan, (t, keys) in chans.items():
                if not keys or chan[0] not in 'rts': continue
                path = {'r': 'rotation_euler', 't': 'location', 's': 'scale'}[chan[0]]
                idx = 'xyz'.index(chan[1])
                fc = cb.fcurves.ensure('pose.bones["Bone_%d"].%s' % (bid, path), index=idx)
                ks = [key_value(t, k, chan) for k in keys]
                ks = [(f + t0, v - (offsets[bid][idx] if path == 'location' else 0), a, b, l) for f, v, a, b, l in ks]
                n0 = len(fc.keyframe_points); fc.keyframe_points.add(len(ks))
                for i, (f, v, a, b, lin) in enumerate(ks):
                    kp = fc.keyframe_points[n0 + i]; kp.co = (f, v)
                    kp.interpolation = 'LINEAR' if lin else 'BEZIER'
                    kp.handle_left_type = kp.handle_right_type = 'FREE'
                    dl = (f - ks[i - 1][0]) / 3.0 if i else 0.0
                    dr = (ks[i + 1][0] - f) / 3.0 if i + 1 < len(ks) else 0.0
                    kp.handle_left = (f - dl, v - a * dl); kp.handle_right = (f + dr, v + b * dr)
                fc.update(); keyed.add((bid, path, idx))
    # channels this motion does not key start it at their default: the FSKL rest rotation (MHF values are absolute),
    # no offset, unit scale (else an earlier motion's last value would carry over)
    for pb in arm_obj.pose.bones:
        bid = int(pb.name.split('_')[1])
        for path, default in (('rotation_euler', by[bid]['rot']), ('location', (0, 0, 0)), ('scale', (1, 1, 1))):
            for idx in range(3):
                if (bid, path, idx) in keyed: continue
                dp = 'pose.bones["%s"].%s' % (pb.name, path)
                fc = cb.fcurves.find(dp, index=idx)
                if fc is None and not (path == 'rotation_euler' and default[idx]): continue
                fc = fc or cb.fcurves.ensure(dp, index=idx)
                n0 = len(fc.keyframe_points); fc.keyframe_points.add(1)
                fc.keyframe_points[n0].co = (t0, default[idx]); fc.keyframe_points[n0].interpolation = 'CONSTANT'


def gap_weight(g, a, b):
    """blend weight at gap frame g between a motion ending at frame a and the next one starting at b"""
    h = min(a + HOLD, b - 1)
    if g <= h: return 0.0
    s = (g - h) / (b - h)
    return s * s * (3 - 2 * s)


def blend_gaps(obj, cb, spans, skip=(), fixed=()):
    """fill the gaps between the motions (spans = [(first, last frame)]) with one CONSTANT key per frame: the last pose,
    then a blend into the next motion's first pose, rotations by quaternion slerp (Euler channels interpolated one by
    one between two unrelated poses spin), locations and scales linear; fixed = (bone, 'location', axis) channels that
    keep the last pose through the gap"""
    for (_, a), (b, _) in zip(spans, spans[1:]):
        for pb in obj.pose.bones:
            if pb.name in skip: continue
            for path in ('rotation_euler', 'location', 'scale'):
                dp = 'pose.bones["%s"].%s' % (pb.name, path)
                fcs = [cb.fcurves.find(dp, index=i) for i in range(3)]
                if not any(fcs): continue
                va, vb = ([fc.evaluate(f) if fc else getattr(pb, path)[i] for i, fc in enumerate(fcs)] for f in (a, b))
                if path == 'rotation_euler':
                    qa, qb, prev = Euler(va).to_quaternion(), Euler(vb).to_quaternion(), Euler(va)
                    vals = []
                    for g in range(a + 1, b):
                        prev = qa.slerp(qb, gap_weight(g, a, b)).to_euler('XYZ', prev); vals.append(tuple(prev))
                else:
                    vals = [tuple(x if (pb.name, path, i) in fixed else x + (y - x) * gap_weight(g, a, b)
                                  for i, (x, y) in enumerate(zip(va, vb))) for g in range(a + 1, b)]
                for i in range(3):
                    fc = fcs[i] or cb.fcurves.ensure(dp, index=i)
                    for g, v in zip(range(a + 1, b), vals):
                        fc.keyframe_points.insert(g, v[i], options={'FAST'}).interpolation = 'CONSTANT'
                    fc.update()


def bake_root(warm, cb, parm, scn, holder):
    """key the weapon's bone 0 (MHF's weapon root) on every frame to the pose of the hand holding it; holder[frame] =
    (hand, other hand, weight): across a gap between motions held in different hands, the root goes over with the blend"""
    warm.pose.bones['Bone_0'].rotation_mode = 'QUATERNION'
    rows, prev = [], None
    for f, (h, o, w) in enumerate(holder):
        scn.frame_set(f)
        Mh = parm.pose.bones['Bone_%d' % h].matrix
        loc, q, sc = (Mh.lerp(parm.pose.bones['Bone_%d' % o].matrix, w) if w else Mh).decompose()
        if prev is not None and prev.dot(q) < 0: q.negate()
        prev = q; rows.append((f, loc, q, sc))
    for path, n, k in (('location', 3, 1), ('rotation_quaternion', 4, 2), ('scale', 3, 3)):
        for i in range(n):
            fc = cb.fcurves.ensure('pose.bones["Bone_0"].%s' % path, index=i)
            fc.keyframe_points.add(len(rows))
            fc.keyframe_points.foreach_set('co', [c for r in rows for c in (r[0], r[k][i])])
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
            fc.update()


def main():
    out, body, bskl, wdir, w13, w13w, hand, render, motions = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene; scn.render.fps = FPS
    # player
    _, pbones = fskl.parse(open(bskl, 'rb').read())
    pby, pfake, ptrue = rest_matrices(pbones)
    parm = armature('MHF_player', pbones, pfake)
    parm.rotation_euler = (math.radians(90), 0, 0)
    bm = fmod.parse(open(body, 'rb').read())
    for i in BODY_MESHES:
        mesh('body_%d' % i, bm[i], parm, pfake, ptrue, lambda bi, m=bm[i]: m['bones'][bi] if m['bones'] else bi)
    # weapon, in the player armature's space; its root bone is keyed to the holding hand at the end (bake_root)
    wfm, wsk = open(os.path.join(wdir, '0.fmod'), 'rb').read(), open(os.path.join(wdir, '1.fskl'), 'rb').read()
    _, wbones = fskl.parse(wsk)
    wby, wfake, wtrue = rest_matrices(wbones)
    warm = armature('MHF_weapon', wbones, wfake)
    warm.parent = parm
    for i, m in enumerate(fmod.parse(wfm)):
        mesh('weapon_%d' % i, m, warm, wfake, wtrue, lambda bi, m=m: m['bones'][bi] if m['bones'] else bi)
    grip, fist = msgrip.Weapon(wfm, wsk), msgrip.fists(open(body, 'rb').read(), open(bskl, 'rb').read())
    # motions
    body_parts = aan.parse(open(w13, 'rb').read()); wp_parts = aan.parse(open(w13w, 'rb').read())
    pids = [[b['node'] for b in pbones if b['part'] == k] for k in (0, 1)]
    wids = [b['node'] for b in wbones]
    poff = {b['node']: Vector(b['pos']) * M for b in pbones}; woff = {b['node']: Vector(b['pos']) * M for b in wbones}
    # one action per armature, the motions one after another (GAP frames apart), a timeline marker at each start
    acts = {}
    for obj in (parm, warm):
        act = bpy.data.actions.new('MS motions [%s]' % ('body' if obj is parm else 'weapon'))
        sl = act.slots.new(id_type='OBJECT', name=obj.name); act.layers.new('Layer').strips.new(type='KEYFRAME')
        obj.animation_data_create(); obj.animation_data.action = act; obj.animation_data.action_slot = sl
        acts[obj] = (act, sl)
    made = []; held = []; t0 = 0
    for mid, name in motions:
        part, slot = (mid % 1000) // 100, mid % 100
        lo, up = body_parts[part].get(slot), body_parts[part + 1].get(slot)
        wmo = wp_parts[part].get(slot) if part < len(wp_parts) else None
        if not (lo or up): print('motion %d: not in the bank' % mid); continue
        label = '%d %s' % (mid, name.replace('_', ' ')) if name else str(mid)
        frames = int(max(x['frames'] for x in (lo, up) if x))
        for obj, parts, by, off in ((parm, [(x, pids[k]) for k, x in ((0, lo), (1, up)) if x], pby, poff),
                                    (warm, [(wmo, wids)] if wmo else [], wby, woff)):
            add_motion(acts[obj][0], acts[obj][1], obj, parts, by, off, t0)
        hs = ([hand] * (frames + 1) if hand else msgrip.holders(grip, msgrip.tracks_of(wmo, wbones), frames, fist)
              if wmo else [msgrip.HANDS[0]] * (frames + 1))
        scn.timeline_markers.new(label, frame=t0)
        made.append((label, t0, frames)); held.append(hs)
        print('motion %s: frames %d..%d, weapon motion %s, hand %d%s' % (
            label, t0, t0 + frames, 'yes' if wmo else 'no', hs[0],
            ''.join(', from f%d %d' % (f, hs[f]) for f in range(1, len(hs)) if hs[f] != hs[f - 1])))
        t0 += frames + GAP
    scn.frame_start, scn.frame_end = 0, max(0, t0 - GAP)
    spans = [(s, s + n) for _, s, n in made]
    cbp, cbw = (acts[o][0].layers[0].strips[0].channelbag(acts[o][1]) for o in (parm, warm))
    root = (('Bone_1', 'location', 0), ('Bone_1', 'location', 2))
    blend_gaps(parm, cbp, spans, ('Bone_0',), root); blend_gaps(warm, cbw, spans, ('Bone_0',))
    # root motion chained as in game: each motion starts where the last one ended (MHF's root motion = bone 1's x / z;
    # bone 0, which MHF never keys, carries the offset; the gaps keep bone 1's x / z, so nothing slides back)
    ev = lambda i, f: (lambda fc: fc.evaluate(f) if fc else 0.0)(cbp.fcurves.find('pose.bones["Bone_1"].location', index=i))
    off = [0.0, 0.0, 0.0]
    for k, (s, _) in enumerate(spans):
        if k:
            for i in (0, 2): off[i] += ev(i, spans[k - 1][1]) - ev(i, s)
        for i in (0, 2):
            cbp.fcurves.ensure('pose.bones["Bone_0"].location', index=i).keyframe_points.insert(
                s, off[i]).interpolation = 'CONSTANT'
    holder = []
    for k, ((_, e), hs) in enumerate(zip(spans, held)):
        holder += [(h, h, 0.0) for h in hs]
        if k + 1 < len(spans):
            b, ha, hb = spans[k + 1][0], hs[-1], held[k + 1][0]
            holder += [(ha, hb, gap_weight(g, e, b) if ha != hb else 0.0) for g in range(e + 1, b)]
    bake_root(warm, cbw, parm, scn, holder)
    # floor, camera, light (for --render and a nicer first look); the camera rides on a rig that follows the root
    print('root travels %.1f m over the timeline' % (math.hypot(off[0], off[2])))
    bpy.ops.mesh.primitive_plane_add(size=2 * math.ceil(math.hypot(off[0], off[2])) + 10)
    rig = bpy.data.objects.new('CameraRig', None); scn.collection.objects.link(rig)
    cl = rig.constraints.new('COPY_LOCATION'); cl.target = parm; cl.subtarget = 'Bone_1'; cl.use_z = False
    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera')); scn.collection.objects.link(cam)
    aim = bpy.data.objects.new('CameraTarget', None); scn.collection.objects.link(aim); aim.location = (0, -0.6, 0.9)
    cam.location = (4.2, -6.0, 2.0); scn.camera = cam; cam.parent = aim.parent = rig
    tr = cam.constraints.new('TRACK_TO'); tr.target = aim; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    lamp = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); scn.collection.objects.link(lamp)
    lamp.rotation_euler = (math.radians(40), 0, math.radians(30))
    scn.render.engine = 'BLENDER_WORKBENCH'
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    print('saved', out, len(made), 'motions')
    if render:
        os.makedirs(render, exist_ok=True)
        scn.render.resolution_x = 480; scn.render.resolution_y = 480
        for label, start, frames in made:
            for f in sorted(set([0, frames // 4, frames // 2, 3 * frames // 4, frames])):
                scn.frame_set(start + f)
                scn.render.filepath = os.path.join(render, '%s_f%03d.png' % (label.split()[0], f))
                bpy.ops.render.render(write_still=True)


main()
