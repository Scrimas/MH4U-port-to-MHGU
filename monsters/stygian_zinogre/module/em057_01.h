/* em057_01.h: Stygian Zinogre (GU Zinogre variant 1, ID 0x139): the 4U -> GU map the ported 4U uEm048 handlers
 * share (em057_01_mv_*.c). [4U address or field] after each GU one; C = confirmed in code, S = strong, G = guess;
 * "site" = GU's look-alike handler does the same call at the same place (more in the em057_01_mv_a.c and
 * em057_01_mv_b.c headers). */
#ifndef EM057_01_H
#define EM057_01_H

#include <stdint.h>
#include "game.h"
#include "util.h"

#define REC(self)   FIELD(uint8_t *, self, EN_RECORD)
#define WORK(self)  FIELD(uint8_t *, self, EN_WORK)
#define RF(p, off)  FIELD(float, p, off)
#define RU(p, off)  FIELD(uint32_t, p, off)

#define REC_ACCEL_Y 0x24    /* float acceleration y [4U W+372] */
#define REC_V30     0x30    /* float[4] [4U W+392]: the backstep's saved velocity (0x84383c) */
#define REC_TIMER   0x1bc   /* float action timer [4U W+468] (C: tigerstripe 2b, site efd1d0) */
#define REC_MSPEED  0x398   /* float motion speed multiplier set by setMotionSpeed [4U W+0x410] */
#define REC_CNTUP   0x7a4   /* u32, nonzero: the 0x84b548 timer counts up [4U W+0x814] */
#define WK_ANG      0x18    /* u32 angle to the target slot (u16 value) [4U work+0x18] */
#define WK_TURN     0x1c    /* u32 turn for spinWindow, sign-extended for right turns [4U work+0x1c] */
#define WK_DIST     0x20    /* float xz distance to the target slot [4U work+0x20] */
#define WK_SNDT     0x2c    /* float sound repeat timer [4U work+44] */
#define WK_RATE     0x30    /* float backstep yaw rate [4U work+0x30] */
#define WK_217      0x115   /* u8 x3: the lead-in's side, r2, r3, for the 7/217-220 handlers [4U work+0x115..0x117] */
#define REC_STATUS  0x5e08  /* u8 status bits [4U W+0x7e80] (C: GU a1fc8 = 4U 0x936418, same body); bit 32 = 4U's rested
                             * state (meaning G), no GU setter found (S) */
#define EN_AREA     0x1054  /* u8 unit area (sound calls) [4U W+0x14c] */
#define EN_MOVECLASS 0xb5f8 /* u8 move class [4U this+0xca8 bits: bit k -> k] */
#define SND_MGR     0x1896f5c

/* ---- GU callees not in game.h */
typedef void (*spinWindow_t)(void *self, uint32_t ang, float a, float b);
#define spinWindow  FN(spinWindow_t, 0x76e8c)   /* [0x9175a8] in window a..b: yaw += (s32)ang / (b - a) * fraction
                                                   * speed (C: same body, signed angle) */
typedef float (*selfFloat_t)(void *self);
#define motionSpeed FN(selfFloat_t, 0xb09bc)    /* layer-0 motion speed this+0x50c [4U this+668, read inline] */
#define sizeFactor  FN(selfFloat_t, 0xbecf0)    /* [0x923fc8] (sites ef735c ef7908 efa3ec f0024c) */
typedef int (*selfInt_t)(void *self);
#define blendActive FN(selfInt_t, 0xb0a8c)      /* this+0x4f4 > 0 [0x91ad14: this+644 > 0] (site f00200) */
#define isCharged   FN(selfInt_t, 0x81790)      /* u8 rec+0x5df3 [0x90f90c: W+0x7e6b] (sites ef7460 ef7610 f003cc) */
#define slowState   FN(selfInt_t, 0x816d0)      /* [0x92e998] rec+0x505 in {2, 3} (4U W+0x51c in {2, 3}) */
typedef void (*self_t)(void *self);
#define pin13a0     FN(self_t, 0xc0644)         /* this+0x13a0 = 1.0f [0xb05184: this+0xd30 = 1.0f] (site efa358) */
#define moveByVel   FN(self_t, 0x7b5f8)         /* [0x955478] pos += vel * dt */
typedef int (*atFrame_t)(void *self, float f);
#define atFrame     FN(atFrame_t, 0xb0a30)      /* [0x941dbc] motionCheck(0, f, 0) (C: same thunk) */
typedef int (*landCheck_t)(void *self, float h);
#define landCheck   FN(landCheck_t, 0xbf178)    /* [0x942258(h)] ground query (4U W+0x628 = rec+0x5bc first) */
typedef void (*camShakeJoint_t)(void *self, int32_t joint, uint32_t id, uint32_t zero);
#define camShakeJoint FN(camShakeJoint_t, 0xc24d8)  /* [0x910c6c(joint, id)] */
/* [class 0x856d6c(this, norot, add, lo, hi, div)]: work+0x20 = xz distance to the target slot + add, clamped to
 * lo..hi; work+0x18 = angle to it; stopMove; vel.z = work+0x20 / div; norot != 1: vel turned by work+0x18 */
typedef void (*approach_t)(void *self, uint32_t norot, float add, float lo, float hi, float div);
#define approach    FN(approach_t, 0xefc550)
typedef void (*attack_t)(void *self, uint32_t slot, uint32_t index);
#define attack      FN(attack_t, 0x7df94)       /* [0x914dfc] attackEx with param 0 (site f003b8) */
typedef int32_t (*questRank_t)(void *quest);
#define questRank   FN(questRank_t, 0x3a8d68)   /* [0x69ae70(*0xfbeffc)]: rank class, >= 5 = G (GU's own remap
                                                   * uses it so) */
#define QUEST_GLOBAL (*(void **)MAIN(0x188ad90)) /* its argument (GU 0xeef398: GOT slot 0x1838d28) */
typedef uint32_t (*targetSide_t)(void *self, uint32_t zero);
#define targetSide  FN(targetSide_t, 0xc7ef8)   /* [0x91e130(this, slot)] 1: target slot within +0..0x7fff of the
                                                   * yaw (C: same body) */
typedef void *(*sndJoint_t)(void *mgr, uint32_t id, void *owner, uint32_t joint, uint32_t area, int32_t m2);
#define sndJoint    FN(sndJoint_t, 0x4efd74)    /* [0x2fcc50] */

static inline void chain(void *self, uint32_t cat, uint32_t num) { setActionNext(self, cat, num); }
static inline void end_action(void *self) { VCALL0(self, SLOT_ACTION_END); }

/* 4U `vcvt.s32.f32` + `uxth`: a computed turn step */
static inline uint32_t u16_of(float v) { return (uint32_t)(int32_t)v & 0xffff; }

/* 4U 0xaacda4(a, b): sqrt(dx^2 + 0 + dz^2) (GU inlines it, site ef7164) */
static inline float dist_xz(const float *a, const float *b)
{
    float dx = b[0] - a[0], dz = b[2] - a[2], d = dx * dx + dz * dz, r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(d));
    return r;
}

/* 4U 0x568c8c(y, x) -> u16 angle; GU's counterpart computes atan2f(y, x) * 65536 / 2pi + 0.5 (sites efa2ac ef71d0) */
static inline uint32_t atan_u16(float y, float x)
{
    return (uint32_t)(int32_t)(atan2f_gu(y, x) * 10430.378f + 0.5f) & 0xffff;
}

/* 4U 0xaad5b0(v, ang): turn the xz of v by the u16 angle, 4U table sin / cos (GU inlines it with sinf / cosf on
 * ang * 2pi / 65536, site efa408..efa458) */
static inline void rot_y(float *v, uint32_t ang)
{
    float a = (float)(ang & 0xffff) * 0x1.921fb6p-14f, s = sinf_gu(a), c = cosf_gu(a), x = v[0], z = v[2];
    v[0] = c * x + s * z;
    v[2] = c * z - s * x;
}

/* angle from the position to target slot 0 [4U W+408 -> W+536] */
static inline uint32_t angle_to_target(const uint8_t *rec)
{
    const float *pos = &RF(rec, REC_POS_X), *t = &RF(rec, REC_TARGET);
    return atan_u16(t[0] - pos[0], t[2] - pos[2]);
}

/* em057_01_mv_b.c: a 4U sound post 0x2fcc50 with 4U's request id (G), site = the 4U call */
void sz_snd(void *self, uint32_t id, uint32_t joint, uint32_t site);
/* em057_01_mv_b.c: 4U class helper 0x8565cc(this, sel, unused): ids 209 then 225 at joint 13 (sel != 0) or 9 */
void sz_snd_pair(void *self, uint32_t sel);
/* em057_01_shell.c: 4U 0x6639a0(mgr *0xef3cf0, owner, id, pos, [sp] rot, kind, area, grp, sub) = the uShell003 slam
 * blast (message 3; notes/b5-shells.md 0): pos / rot = float[4] position and euler angles (radians), kind = ground
 * kind (sz_effect_c094e8) & 255, area = EN_AREA, grp = u16 attack hit group (rec+0xb0a), sub = u8 hit attribute bits
 * 16-19; site = the 4U call */
void sz_shell003(void *self, uint32_t shell_id, uint32_t site, const float *pos, const float *rot, uint32_t kind,
                 uint32_t area, uint32_t grp, uint32_t sub);
/* em057_01_mv_d.c: 4U 0xc094e8(unused, flags): ground kind 0..5 of a hit from its attribute word (it becomes the
 * effect's ground flags, sz_ground_flags); logs the first calls per 4U site */
uint32_t sz_effect_c094e8(void *self, uint32_t flags, uint32_t site);
/* em057_01_mv_d.c: 4U vt77 0x8582b0..0x85849c, the paw-slam ground hit em049_003 (charged: mask 2 + sound 205), every
 * frame from the slot-125 hook */
void em057_01_slam_fx_frame(void *self);
/* em057_01_posts.c: 4U vt77 0x857ba8's seven orb events (0x855fe4, G rank), every frame from the slot-125 hook */
void em057_01_orb_event_frame(void *self);
/* em057_01_vt77.c: 4U vt77's sounds GU's vt170 lost (every frame, slot 125) */
void em057_01_vt77_frame(void *self);
/* em057_01_shell.c: 4U uShell044 post 0x662904(mgr *0xef3cf0, owner, subtype, ofs, [sp] rot, [sp+4] grp, [sp+8] b8,
 * s0 f): message 44 {owner, subtype u8 +4, b8 u8 +5, grp u16 +8, ofs +16, rot +48, f +60}; ofs = float[4] offset
 * from the owner's position (the ctor adds it), rot = u32[3] angle triple (4U this+0x8d20 = its copy of W+424..432;
 * here rec+0x50, S), grp / b8 / f = 0xffff / 0 / 0.0 at every Stygian site (rot / b8 / f read by other subtypes
 * only); subtype 3 = the dragon pillar, others dropped (logged); site = the 4U call */
void sz_shell044(void *self, uint32_t subtype, const float *ofs, const uint32_t *rot, uint32_t grp, uint32_t b8,
                 float f, uint32_t site);
/* em057_01_shell046.c: 4U uShell046 post 0x6629bc(mgr *0xef3cf0, owner, sub, &rec.off, [sp] &rec.A, &rec.B, &origin,
 * &angles, u16 grp; s0-s5 = rec.f0..f5): the dragon orb, subtype 0..4; record = an sz_orb_rec (em057_01_shelldata.h),
 * origin = float[3] the owner's position, angles = u32[3] its angle triple (x, yaw, z), seed = the wobble LCG's seed
 * (the same on every machine); site = the 4U call */
void sz_shell046(void *owner, uint32_t sub, const void *record, const float *origin, const uint32_t *angles,
                 uint32_t grp, uint32_t seed, uint32_t site);
/* em057_01_mv_f.c, B5 stub (log only); site = the 4U call.
 * 4U 0xc0819c(unused, area, pos): area-gated effect object (pos, area) posted as event 20 (not pure) */
void sz_effect_c0819c(void *self, uint32_t area, const float *pos, uint32_t site);
/* em057_01_mv_f.c: 4U sndPos 0x312484(mgr *0xfccd6c, id, owner, pos, [sp] area, [sp+4] m2) = GU 0x4efb98 (plays,
 * logged); stub (no GU site; log only): 4U 0x390f9c(this+0xc78, id, arg), the unit's sound-event component (ids
 * 1000..1032) */
void sz_snd_312484(void *self, uint32_t id, const float *pos, uint32_t area, int32_t m2, uint32_t site);
void sz_snd_390f9c(void *self, uint32_t id, int32_t arg, uint32_t site);
/* em057_01_start.c, framework stubs (no GU site found, batch S; log only; used by 1/41's start and the 1/43 handler):
 * 4U 0x939c00(this, f): W+0x7e80 (GU rec+0x5e08, C) |= f, W+0x7e81 (rec+0x5e09) &= ~f, f & 32 -> status timers
 * 0x91de40; 4U 0x94c980(this): W+0x540 = 3600.0 (G: a rested state after waking and its timer). site = the 4U call */
void sz_unmapped_939c00(void *self, uint32_t f, uint32_t site);
void sz_unmapped_94c980(void *self, uint32_t site);
/* em057_01_ai.c, AI stub (log only): 4U rest flags with no GU field (W+0x53a, W+0x544, W+0x545) read by the AI
 * (condition 11, op 0x80); answers 0 until their 4U setters and clears are ported. site = the 4U read */
uint32_t sz_rest_w4u(void *self, uint32_t field, uint32_t site);
/* em057_01_efx.c: 4U's aura controller 0x322f18 (one looping aura for the rage / charge state), every frame */
void em057_01_efx_frame(void *self);
/* em057_01_efx.c: 4U 0xc08628-style point post of PEL u list-2 record `id` (no attach: 0x53b500), rotation = euler
 * radians or 0, ground = sz_ground_flags(kind) or 0 (the record's); returns the effect or 0 */
void *sz_efx_world(void *self, uint32_t id, const float *pos, const float *rot, uint32_t ground);
/* em057_01_efx.c: 4U 0xc08698 on a shell: record `id` attached to the unit (GU shells' own request style) */
void *sz_efx_on(void *self, uint32_t id, void *unit);
uint32_t sz_ground_flags(uint32_t kind);        /* 4U 0xc074b8: (2 << kind) | 1, kind >= 6 -> 3 */
int sz_efx_alive(void *eff);
void sz_efx_finish(void *eff);                  /* 0x32a400 mode 0 (4U 0xc470dc on a one-shot) */
int sz_efx_pos(void *eff, float *out);          /* GU's placed position (transform node +0x40) */
void sz_snd_at(void *self, uint32_t id, const float *pos, uint32_t area);   /* 4U 0x312484 = GU 0x4efb98 */

#endif
