/* em057_01_mv_d.c: Stygian Zinogre, ported 4U uEm048 handlers, batch D (the paw slams with the ground shell: 7/190
 * 191, and the G-rank 7/217, 7/218, 7/220).
 * Run by em057_01_moves_run (em057_01_moves.c, s_moves rows with the 4U dispatcher's parameters in p[]) for a
 * variant-1 Zinogre, instead of GU's same-number case (GU 7/190 191 220: no case, ends at once; GU 7/217 7/218: its own
 * move efe384). Each handler is a literal translation of the 4U function named in its comment (MH4U v1.1,
 * dump/mh4u.asm), in 4U call order with 4U frame / timer / angle values; em==49 branches take the Stygian side
 * (phase1-variant-map.md 1B / 1C: attack indices 48 / 49 and 72 / 73, uShell010 135 and 236). Verdicts and
 * parameters: notes/phase2-actions.md 2. C = confirmed in code, S = strong, G = guess.
 * Parameters (C, 4U cat-7 sub-dispatcher 0x851494, table 0x8514ac): 7/190 191 -> stubs 0x8525d4 / 0x8525e0 =
 * 0x84f744(r1 = 0 / 1, r2 = 7); 7/217 218 -> 0x852760 / 0x852768 = 0x84ff7c / 0x850714 (r1 = the number, r2 = 7,
 * both unused); 7/220 -> 0x852778 (`pop; nop`), which falls into 0x852780 (r1 r2 unused). No handler reads [sp].
 * 0x84ff7c / 0x850714 / 0x852780 read (side, r2, r3) from work+0x115..0x117 (WK_217), stored at step 0 of their
 * callers (C): 0x8489c8 (0x848310's G-rank lead-in, 7/217: side, 0x848310's r2, r3 at 0x848a78..0x848a8c; r7 / r5
 * hold the motion ids 0x23f / 0x23e only from step 1, 0x8489e4), 0x84fbe4 (7/215 216 -> 7/220: side, 0, 0 at
 * 0x84fd48..), 0x853d24 (0x853704's lead-in, 7/218: side, r2, r3 at 0x853eac..).
 *
 * 4U -> GU, beyond the batch A-C lists ("site" = GU's look-alike handler does the same call at the same place:
 * f00684 (GU 7/251 252) for 0x84f744, efd9ac (GU 7/166-169) for 0x84ff7c / 0x850714 / 0x852780):
 * - 0x2bad24(mgr *0x10574fc, from, to, area, u8 *hit, out, 64) -> float = GU 0x183ad0(mgr *(main+0x21270e0), same
 *   arguments) (C: sites f00920 efdbc0, GOT slot 0x1839320; same body: segment from (y + 100) .. to (y - 300) against
 *   the collision of 1 << area, out filled on a hit by 4U 0x2b95a4 / GU 0x1815a4, returns the hit y, else from.y).
 * - its out struct: u8 +3 = attribute bits 16-19, u32 +8 = attribute word 1 (C: same packing and getter index in
 *   0x2b95a4 / 0x1815a4); the ground normal 4U +24 = GU +32 (C: 0x1815a4 stores it at +0x20, efd9ac passes out+32 at
 *   efdbe4; GU adds a float at +20 and moves the normal 8 bytes on). The handlers read nothing else of it.
 * - 0xaad40c(m, fwd, up) = GU 0x2329b8 (C: site efdc34; same shape: both vectors normalised with the 2^-23 length
 *   guard, 4U rows norm(up x fwd), up, row0 x up, a constant row, GU's rows not re-derived); 0xd076b0(e, m) = GU
 *   0x7c6914 (C: site efdc40, same body: e[3] = 0, m[9] >= 1 / <= -1 branches with -+pi/2, else atan2 / asin /
 *   atan2). 0xaad5b0 = rot_y (em057_01.h; efd9ac inlines it with sinf / cosf of the yaw, efdbe0..efdc30, C).
 * - 0x93093c(this, j, out) = jointPos 0xc1708(self, j, out) (C: sites f0080c f008a8 efdaec efdb48); 0x910c6c(this, j,
 *   1) = camShakeJoint(self, j, 1, 0) (C: sites f008bc efdb5c).
 * - 0x933144(this, 0, idx, 8) = attackEx 0x7dc2c(self, 0, idx, 8) (C: sites f0085c efdb1c also pass 8). Flag 8 keeps
 *   the slot's hit group: 4U W+0xd3a (u16) and W+0xd38 = 1 (0x933444), GU rec+0xb0a and rec+0xb08 = 1 (0x7df30), so
 *   W+0xd3a = rec+0xb0a (C: f00958 efdc94 put rec+0xb0a in GU's shell request where 4U passes W+0xd3a to the post).
 * - W+0x14c = EN_AREA (C: sites f00904 efdba0, the ray's area).
 * - 0x69ae70 = questRank (S, em057_01.h): 0x84f744 slows to 0.6 in 80-100 below rank 5 (absent from f00684); the
 *   others turn 45 x in rank >= 6, else 30 x (efd9ac: always 30 x).
 * - frames and windows (C, sites): 0x84f744 atFrame 57 f007ec, mc 9 26-46 x 6 f00b88, mc 3 36-44 f00be4, approach
 *   -300 / 0 / 500 / 8 f00ad0; the others atFrame 18 efdabc, mc 9 2-12 efde50, mc 3 6-18 efdeac, frame 62 efded0,
 *   approach -300 / 0 / 500 / 12 efdb38.
 * - this+0xca8 |= 512 every frame in 0x84ff7c / 0x850714 / 0x852780 -> EN_MOVECLASS 9 (C: efda48); 0x84f744 does not
 *   touch it, nor does f00684 (C).
 * Shell and effect calls (one block shared by the four handlers, slam_shell): 4U 0x6639a0 = the uShell003 blast
 * (em057_01_shell.c sz_shell003) and 0xc094e8 = the hit's ground kind (sz_effect_c094e8 below). No sound in 0x84f744 /
 * 0x850714 / 0x852780; 0x84ff7c calls the class sound pair 0x8565cc = sz_snd_pair (batch B). No W+0x1d9 test in these
 * four (C). The same ground ray serves 4U vt77's paw-slam ground hit (em057_01_slam_fx_frame, end of file). */
#include "em057_01.h"

/* GU callees and fields used only here */
typedef float (*groundRay_t)(void *mgr, const float *from, const float *to, uint32_t area, uint8_t *hit, void *out,
                             uint32_t mask);
#define groundRay   FN(groundRay_t, 0x183ad0)   /* [0x2bad24] */
#define COLL_MGR    (*(void **)MAIN(0x21270e0)) /* its manager [*0x10574fc] (GU f0090c: GOT slot 0x1839320) */
typedef void (*basisUp_t)(float *m, const float *fwd, const float *up);
#define basisUp     FN(basisUp_t, 0x2329b8)     /* [0xaad40c] */
typedef void (*mtxEuler_t)(float *e, const float *m);
#define mtxEuler    FN(mtxEuler_t, 0x7c6914)    /* [0xd076b0] */
#define HIT_SUB     3       /* u8 attribute bits 16-19 [4U out+3] */
#define HIT_FLAGS   8       /* u32 attribute word 1 [4U out+8] */
#define HIT_NORMAL  32      /* float[4] ground normal [4U out+24] */
#define REC_HITGRP  0xb0a   /* u16 hit group kept by attackEx flag 8 [4U W+0xd3a] */
typedef uint32_t (*playerArea_t)(void);
#define playerArea  FN(playerArea_t, 0x4971c)   /* the local player's area (em089_efx.c) [*0xfb6b7c +0xc90] */

#define STUB_SITES  16
#define SLAM_FX_LINES 40u
#define EFX_SLAM_HIT    3203u   /* em049_003 mask 1 (SHELL_FX) */
#define EFX_SLAM_HIT_CH 3253u   /* em049_003 mask 2 */

/* B5 stub sites: a 4U site logs its first 4 calls */
static int stub_line(uint32_t site)
{
    static uint32_t s_site[STUB_SITES];
    static uint8_t s_lines[STUB_SITES];
    uint32_t i = 0;
    while (i < STUB_SITES && s_site[i] && s_site[i] != site) i++;
    if (i == STUB_SITES || s_lines[i] >= 4) return 0;
    s_site[i] = site;
    s_lines[i]++;
    return 1;
}

/* ---- 4U 0xc094e8(r0 = *0x10572a4, unused; flags): not an effect post but the ground kind of the hit from its
 * attribute word (out+8): 0x800000 -> 5, 0x200 -> 3, 6 -> 1, 0x1040 -> 2, 8 -> 4, else 0 (C: 4U body, no side
 * effect). 4U passes it to the blast shell (+0x274) and to the vt77 effect as the request's ground kind (+0x18), which
 * picks the EFL's ground set (notes/b5-shells.md 8b). The bits are 4U's: exact on stages converted from 4U (their
 * collision keeps the 4U attribute words, tools/sbc.py); GU has no twin of these tests (S on GU's own stages), so each
 * site logs the word and the kind. site = the 4U call. */
uint32_t sz_effect_c094e8(void *self, uint32_t flags, uint32_t site)
{
    uint32_t r;
    (void)self;
    if (flags & 0x800000) r = 5;
    else if (flags & 0x200) r = 3;
    else if (flags & 6) r = 1;
    else if (flags & 0x1040) r = 2;
    else r = (flags & 8) ? 4 : 0;
    if (stub_line(site))
        logf("szport: c094e8 flags %x -> ground kind %u (4U %x)", flags, r, site);
    return r;
}

/* the ground under the paw joint (y + 100 .. y - 300 against the area's collision) and, on a hit, the point at the
 * ground's height with the euler angles of the basis turned to it: forward = (0, 0, 1) turned by the yaw, up = the
 * ground normal (4U: the handlers' 0x84f7bc.. blocks below, vt77 0x8582ec..0x8583d0); out = the ray's hit record.
 * 0 = no ground (4U posts nothing then) */
static int slam_ground(void *self, uint32_t joint, float *pos, float *rot, uint32_t *out)
{
    float v[4] = { 0.0f, 0.0f, 1.0f, 0.0f }, m[16], e[4], to[4];
    uint8_t hit = 0;
    void *mgr = COLL_MGR;
    jointPos(self, joint, pos);
    to[0] = pos[0];
    to[1] = pos[1] - 300.0f;
    to[2] = pos[2];
    to[3] = 0.0f;
    pos[1] = pos[1] + 100.0f;
    if (!mgr) return 0;                                     /* no manager: no hit (GU f00684 does not check) */
    pos[1] = groundRay(mgr, pos, to, FIELD(uint8_t, self, EN_AREA), &hit, out, 64);
    if (!hit) return 0;
    rot_y(v, RU(REC(self), REC_YAW));
    basisUp(m, v, (const float *)((uint8_t *)out + HIT_NORMAL));
    mtxEuler(e, m);
    rot[0] = e[0];
    rot[1] = e[1];
    rot[2] = e[2];
    rot[3] = 0.0f;
    return 1;
}

/* 4U hit-frame block of the four handlers (0x84f7bc..0x84f900; 0x850010..0x850164, 0x8507a8..0x8508fc,
 * 0x852814..0x852968): camera shake at the paw joint, then on ground the blast shell there, turned to the ground */
static void slam_shell(void *self, uint32_t joint, uint32_t id, uint32_t site_kind, uint32_t site_post)
{
    float pos[4] = { 0.0f, 0.0f, 0.0f, 0.0f }, rot[4];
    uint32_t out[16] = { 0 };
    camShakeJoint(self, joint, 1, 0);
    if (!slam_ground(self, joint, pos, rot, out)) return;
    uint32_t kind = sz_effect_c094e8(self, out[HIT_FLAGS / 4], site_kind);
    sz_shell003(self, id, site_post, pos, rot, kind & 255, FIELD(uint8_t, self, EN_AREA),
                FIELD(uint16_t, REC(self), REC_HITGRP), ((const uint8_t *)out)[HIT_SUB]);
}

/* 4U step 0 of 0x84ff7c / 0x850714 / 0x852780: motion 0x23d with attack slot 0 index 73 (hi) or 0x23c with 72
 * (Stygian; em 48 / 114: 71 / 70), flag 8, then the approach */
static void slam_start(void *self, int hi)
{
    REC(self)[REC_STEP0] = 1;
    setTargetMode(self, 0);
    if (hi) {
        setMotion(self, 0x23d, 0.0f, 0.0f);
        attackEx(self, 0, 73, 8);
    } else {
        setMotion(self, 0x23c, 0.0f, 0.0f);
        attackEx(self, 0, 72, 8);
    }
    approach(self, 0, -300.0f, 0.0f, 500.0f, 12.0f);
}

/* 4U step 1 of 0x84ff7c / 0x850714 / 0x852780 after the hit frame: turn in 2-12 (out fraction / 10, x 45 degrees in
 * rank >= 6, else x 30), move in 6-18 */
static void slam_move(void *self)
{
    uint8_t *rec = REC(self);
    float out = 0.0f;
    if (motionCheck(self, 9, &out, 2.0f, 12.0f)) {
        void *q = QUEST_GLOBAL;
        float k = (q ? questRank(q) : 0) >= 6 ? 45.0f : 30.0f;
        turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * k * (out * 0.1f) * 65536.0f * 0.0027777778f), 0);
    }
    if (motionCheck(self, 3, 0, 6.0f, 18.0f)) moveByVel(self);
}

/* ---- 7/190 7/191: 4U 0x84f744(side): paw slam (motion 0x202 (side 1) / 0x201 from frame 24, attack slot 0 index
 * 49 / 48 (Stygian; em 48 / 114: 46 / 45) with flag 8, speed 1.2 charged, approach), at frame 57 the paw shell (joint
 * 50 (side 1) / 40, uShell010 135 (em 48 / 114: 129)), turn in 26-46 (x 6), below rank 5 speed 0.6 in 80-100 (the
 * window GU's look-alike f00684 lacks), move in 36-44, end at the motion end. r2 (7) is unused. */
void szmv_84f744(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t side = p[0];
    float out = 0.0f;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 0);
        if (side == 1) {
            setMotion(self, 0x202, 0.0f, 24.0f);
            attackEx(self, 0, 49, 8);
        } else {
            setMotion(self, 0x201, 0.0f, 24.0f);
            attackEx(self, 0, 48, 8);
        }
        setMotionSpeed(self, isCharged(self) ? 1.2f : 1.0f);
        approach(self, 0, -300.0f, 0.0f, 500.0f, 8.0f);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (atFrame(self, 57.0f)) slam_shell(self, side == 1 ? 50 : 40, 135, 0x84f8bc, 0x84f900);
    if (motionCheck(self, 9, &out, 26.0f, 46.0f))
        turnToTarget(self, u16_of(0.5f + RF(rec, REC_MSPEED) * 6.0f * (out * 65536.0f) * 0.0027777778f), 0);
    void *q = QUEST_GLOBAL;
    if ((q ? questRank(q) : 0) < 5 && motionCheck(self, 3, 0, 80.0f, 100.0f)) setMotionSpeed(self, 0.6f);
    if (motionCheck(self, 3, 0, 36.0f, 44.0f)) moveByVel(self);
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 7/217: 4U 0x84ff7c, with (side, r2, r3) from work+0x115..0x117 (0x848310's): slam (slam_start, motion 0x23d
 * for side != 0), at frame 18 the paw shell (joint 50 (side 1) / 40, uShell010 236 (em 48 / 114: 235)), slam_move.
 * r2 == 0: end at the motion end (frame 62 if r3 == 4); else at frame 62 (r3 == 5: the sound pair by side == 0) the
 * follow-up by side / r2 / r3: 7/160-175, or 7/216 (side 0) / 7/215 for r3 == 5 (4U tables 0x85048c 0x850468
 * 0x8505ac 0x850420); r3 4 or >= 6 (no 4U caller passes them): no follow-up and no end, logged. */
void szmv_84ff7c(void *self, const uint8_t *p)
{
    static const uint8_t s_next[2][2][6] = {                /* [side != 0][r2 != 1][r3]; 0 = none (4U returns) */
        {{160, 161, 162, 163, 0, 216}, {168, 169, 170, 171, 0, 216}},   /* 4U tables 0x85048c 0x850468 */
        {{164, 165, 166, 167, 0, 215}, {172, 173, 174, 175, 0, 215}},   /* 4U tables 0x8505ac 0x850420 */
    };
    static uint8_t s_nolog;
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t side = work[WK_217], r2 = work[WK_217 + 1], r3 = work[WK_217 + 2];
    (void)p;
    FIELD(uint8_t, self, EN_MOVECLASS) = 9;                 /* 4U this+0xca8 |= 512 */
    if (rec[REC_STEP0] == 0) {
        slam_start(self, side != 0);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (atFrame(self, 18.0f)) slam_shell(self, side == 1 ? 50 : 40, 236, 0x85011c, 0x850164);
    slam_move(self);
    if (r2 == 0) {
        if (r3 == 4 ? atFrame(self, 62.0f) : isMotionEnd(self)) end_action(self);
        return;
    }
    if (!atFrame(self, 62.0f)) return;
    if (r3 == 5) sz_snd_pair(self, side == 0);
    uint32_t n = r3 < 6 ? s_next[side != 0][r2 != 1][r3] : 0;
    if (n) chain(self, 7, n);
    else if (s_nolog < 4) {
        s_nolog++;
        logf("szport: 7/217 frame 62, no follow-up for work+0x115 = %u %u %u", side, r2, r3);
    }
}

/* ---- 7/218: 4U 0x850714, with (side, r2, r3) from work+0x115..0x117 (0x853704's): slam (slam_start, motion 0x23d
 * for side 0: mirrored from 7/217), at frame 18 the paw shell (joint 40 (side != 0) / 50, uShell010 236), slam_move.
 * r2 == 0: end at the motion end (frame 62 if r3 == 4); r2 == 1: end at the motion end; r2 >= 2: end if the motion
 * ends first, else at frame 62 by r3: 3 -> 7/136 (side != 0) / 7/135, 0 -> 7/177 (side 1) / 7/176, 1 -> 7/0 if the
 * motion is 0x202 (never here: 0x23c / 0x23d) else 7/1, other -> 7/202. */
void szmv_850714(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t side = work[WK_217], r2 = work[WK_217 + 1], r3 = work[WK_217 + 2];
    (void)p;
    FIELD(uint8_t, self, EN_MOVECLASS) = 9;                 /* 4U this+0xca8 |= 512 */
    if (rec[REC_STEP0] == 0) {
        slam_start(self, side == 0);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (atFrame(self, 18.0f)) slam_shell(self, side ? 40 : 50, 236, 0x8508b4, 0x8508fc);
    slam_move(self);
    if (r2 == 0) {
        if (r3 == 4 ? atFrame(self, 62.0f) : isMotionEnd(self)) end_action(self);
        return;
    }
    if (!atFrame(self, 62.0f) || r2 < 2) {
        if (isMotionEnd(self)) end_action(self);
        return;
    }
    if (r3 == 3) chain(self, 7, side ? 136 : 135);
    else if (r3 == 0) chain(self, 7, side == 1 ? 177 : 176);
    else if (r3 == 1) chain(self, 7, curMotion(self) == 0x202 ? 0 : 1);
    else chain(self, 7, 202);
}

/* ---- 7/220: 4U 0x852780 (from the stub 0x852778, which falls into it), with the side from work+0x115 (0x84fbe4
 * stores side, 0, 0): slam (slam_start, motion 0x23d for side != 0), at frame 18 the paw shell (joint 50 (side != 0)
 * / 40, uShell010 236), slam_move, end at the motion end. */
void szmv_852780(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self), *work = WORK(self);
    uint32_t side = work[WK_217];
    (void)p;
    FIELD(uint8_t, self, EN_MOVECLASS) = 9;                 /* 4U this+0xca8 |= 512 */
    if (rec[REC_STEP0] == 0) {
        slam_start(self, side != 0);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (atFrame(self, 18.0f)) slam_shell(self, side ? 50 : 40, 236, 0x852920, 0x852968);
    slam_move(self);
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 4U vt77 0x857ba8, motion case 0x201 / 0x202 (0x857f68 -> 0x8582b0..0x85849c), every frame from the slot-125
 * hook (em057_01_diag.c; atFrame answers there as in the handlers): in category 7 except 190 / 191 (they post their
 * blast shell at that frame; the others are the 7/2 family's plain slams, 0x848310, and GU-kept 7/0 / 7/1), at frame
 * 57 (literal 0x858630) the ground under joint 50 (motion 0x202) / 40; no ground -> nothing. Charged (0x90f90c): sound
 * 205 at the point first (0x858410) and request mask 2 (r5 = 2 from 0x857f40), else mask 1; then 0xc08628 (58, 12) =
 * em049_003 at the point with the ground-turned euler and the ground kind (0x858454), request flags 0: only when the
 * monster's area is the local player's (0xc08640..0xc0865c). Mask 2 adds em049_003's elements 11-14, the red blast
 * the user remembers "when charged"; the ground kind picks elements 0-2 / 3-6 / 7-10 (notes/b5-shells.md 8a). No net
 * test (C): every machine posts its own from the synced action. */
void em057_01_slam_fx_frame(void *self)
{
    static uint32_t s_lines, s_wait;
    static void *s_eff;
    static float s_at[3];
    uint32_t mot = curMotion(self), num = FIELD(uint8_t, self, EN_ACT_NUM), charged, kind, area;
    float pos[4] = { 0.0f, 0.0f, 0.0f, 0.0f }, rot[4], p[3];
    uint32_t out[16] = { 0 };
    void *eff = 0;
    if (s_eff && s_wait && !--s_wait) {     /* where GU placed the last one, 4 frames on (units built after the post) */
        if (s_lines < SLAM_FX_LINES && sz_efx_pos(s_eff, p)) {
            s_lines++;
            logf("szport: slam hit fx placed at %d %d %d (asked %d %d %d)", (int32_t)p[0], (int32_t)p[1],
                 (int32_t)p[2], (int32_t)s_at[0], (int32_t)s_at[1], (int32_t)s_at[2]);
        }
        s_eff = 0;
    }
    if ((mot != 0x201 && mot != 0x202) || FIELD(uint8_t, self, EN_ACT_CAT) != 7 || num == 190 || num == 191) return;
    if (!atFrame(self, 57.0f)) return;
    if (!slam_ground(self, mot == 0x202 ? 50 : 40, pos, rot, out)) return;
    charged = isCharged(self) != 0;
    area = FIELD(uint8_t, self, EN_AREA);
    if (charged) sz_snd_at(self, 205, pos, area);
    kind = sz_effect_c094e8(self, out[HIT_FLAGS / 4], 0x858454);
    if (area == playerArea())
        eff = sz_efx_world(self, charged ? EFX_SLAM_HIT_CH : EFX_SLAM_HIT, pos, rot, sz_ground_flags(kind));
    if (s_lines < SLAM_FX_LINES) {
        s_lines++;
        logf("szport: slam hit fx 7/%u motion %x frame 57%s ground kind %u at %d %d %d rot %d %d %d mrad efx %x%s", num,
             mot, charged ? " charged (sound 205)" : "", kind, (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2],
             (int32_t)(rot[0] * 1000.0f), (int32_t)(rot[1] * 1000.0f), (int32_t)(rot[2] * 1000.0f), (uint32_t)eff,
             area == playerArea() ? "" : " (other area: no effect)");
    }
    if (eff) {
        s_eff = eff;
        s_wait = 4;
        for (int i = 0; i < 3; i++) s_at[i] = pos[i];
    }
}
