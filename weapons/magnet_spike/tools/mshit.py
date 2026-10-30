"""mshit.py : Magnet Spike hit data for MHGU: player\\hit\\pl_we05_hitdata (HDP) and pl_we05_hitsize (HTS), from MHF's
attack records (dat/mhfsdt.bin kind 0x78, tools/sdt.py) and the weapon poses at each attack's frame.

GU formats (C, notes/gu-weapon-class.md "Hit data"; reader 0x168960):
  HDP: 'HDP\\0', u32 0x20160209, u32 count, count x 56 B (28 i16): [0] frames before the hit goes live (counted
       from the motion's current frame; 0 = live now), [1] live frames, [4] attack byte (+0x3a; GU keeps it = the
       motion value, <= 250 in every class; the hit code also compares it with kind codes), [8] damage type (1 impact,
       2 cut), [16] low byte = hit shape set, [22..25] two f32 1.0 multipliers, [26] motion value (short).
       The other fields come from a GU template entry of the same damage type (GS 1 for cut, Hammer 3 for impact).
  HTS: 'HTS\\0', u32 0x20131015, u32 set count, u32 0, count x {u32 shape count, u32 offset}, shapes 48 B:
       u16 joint A, u16 joint B (player joints: 8 right hand, 12 left hand, 255 root), u16 type (1 = capsule),
       u16 flag, f32, f32 radius, vec4 A, vec4 B (cm, in the joint's frame).
MHF (C): an ATTACK event arms its attack at the event frame for raw[1] frames (MV raw[2], type raw[7] 0x20a cut /
0x10a impact, KO raw[16] / 256, shape set raw[8]); its shapes sit on weapon bones (5 / 7 blades, 4 head; flag 8) or
around the hunter (flag 0). GU shapes sit on player joints only, so each weapon shape is placed in the holding hand's
frame (GU 8 or 12, msgrip) from the weapon motion's pose at the middle of the live window, one HTS set per attack
event (the same MHF attack posed by different motions differs).
Deviation (Phase 2): KO / exhaust and the remaining fields are the template's; MHF's KO is kept in the report.

Library: hdp_entry(template, mv, dur, cut, shape), hts_bytes(sets), hdp_bytes(entries)."""
import struct

HDP_VERSION, HTS_VERSION = 0x20160209, 0x20131015
CUT, IMPACT = 2, 1


def hdp_parse(d):
    _, ver, n = struct.unpack_from('<III', d, 0)
    return [list(struct.unpack_from('<28h', d, 12 + 56 * i)) for i in range(n)]


def hdp_bytes(entries):
    out = struct.pack('<4sII', b'HDP\0', HDP_VERSION, len(entries))
    for e in entries:
        out += struct.pack('<28h', *e)
    return out


def hdp_entry(template, mv, dur, kind, shape, ko=None):
    """a GU entry from a template: live now for dur frames, motion value mv, damage type, hit shape set; ko = MHF's
    KO value into i16[2] (S: GU's KO, Hammer 22..52; the template's otherwise)"""
    e = list(template)
    e[0], e[1] = 0, dur
    if ko is not None: e[2] = int(round(ko))
    e[4] = min(mv, 250)
    e[8] = kind
    e[16] = (e[16] & ~0xff) | shape
    e[26] = mv
    return e


def hts_parse(d):
    _, ver, n, _ = struct.unpack_from('<IIII', d, 0)
    sets = []
    for i in range(n):
        cnt, off = struct.unpack_from('<II', d, 16 + 8 * i)
        sets.append([struct.unpack_from('<4H2f4f4f', d, off + 48 * k) for k in range(cnt)])
    return sets


def capsule(joint, radius, a, b):
    """one capsule shape in a joint's frame (GS's header: type 1, flag 1)"""
    return (joint, joint, 1, 1, 0.0, radius, a[0], a[1], a[2], 0.0, b[0], b[1], b[2], 0.0)


def hts_bytes(sets):
    head = struct.pack('<4sIII', b'HTS\0', HTS_VERSION, len(sets), 0)
    table, body = b'', b''
    base = 16 + 8 * len(sets)
    for s in sets:
        table += struct.pack('<II', len(s), base + len(body) if s else 0)
        for sh in s:
            body += struct.pack('<4H2f4f4f', *sh)
    return head + table + body
