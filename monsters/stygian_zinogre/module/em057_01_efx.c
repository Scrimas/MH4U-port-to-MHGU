/* em057_01_efx.c: Stygian Zinogre's code-posted effects through GU's effect gateway (notes/plan.md, test 1
 * 2026-10-28: GU Zinogre effects on Stygian). C = confirmed in code, S = strong, G = guess.
 *
 * GU (C, MHGU 1.4): uEm057_00 slot 116 0xf060c4(self, id, req) posts PEL u (this+0xb624) list-2 record rec(id)
 * through 0x6ff74(self, 2, rec, req): ids >= 1000 from the class table 0x16a63f4, the others through uEnemy's 0xa3e98
 * (table 0x159fa1c); req = self+0xb640, whose byte +0xc every caller sets to EN_AREA. Its callers for any variant:
 *   eefda4, charge state change: 1004 in cat 11 for variant 0, else 1005 -> 120 / 90 = em057_00_002 joint 2;
 *   slot 129's start work (eefed0, every action) and ef41xx keep looping effects in this+0xcb08 / 0xcb0c / 0xcb10:
 *   1001 / 1002 / 1003 / 1007 -> 30 / 31 / 32 / 32 = em057_00_000 joint 2, masks 2 / 4 / 1 / 1 (1006 -> 42: no
 *   record); 1008 / 1009 -> 250 / 280: no record;
 *   uEnemy 0xa4274, every 30 s while rageOn, unless this+0xb7d2 == 0 (GU clears it for a G-rank Thunderlord only):
 *   ids 0 / 1 -> 1120 / 1121 = em057_00_011 joint 2;
 *   uFestaEnemy 0xca2b4, only when this+0xb720 is set (G: GU's Hyper state, 139 readers): 47 + k -> 1300.. (1301 =
 *   em057_00_500, Zinogre's own file).
 * 4U (C, MH4U v1.1): the class posts the charge change 0x856f0c ((58, cat 11 ? 14 : 11) = em049_005 / em049_002 at
 * joint 1 / 2, then sound 213 / 210 at that joint, 0x304c34), and the aura controller 0x322f18 (outside the class)
 * keeps one looping effect on the monster, joint 2, for its state: none (0x94d7a8), enraged (rageOn: (58, 17) =
 * em049_011, mask -1), charged (0x90f90c: (58, 9) = em049_000 mask 1), else the slot-51 query 1 answering 1 / 2:
 * em049_000 mask 2 / 4. Zinogre's are (57, 11) / (57, 0) = em048_011 / em048_000, which GU's em057_00_011 /
 * em057_00_000 records copy with the same joint and masks. Its loop sounds 201 / 202 / 203 (0x322d90) are not ported
 * here (sounds batch). 4U has no Hyper.
 * So for Stygian: the charge change takes 4U's file (1004 / 1005 -> 3205 in cat 11, else 3202, PEL list-2 records of
 * build_em057_01_arc.py SHELL_FX) and 4U's sound; the aura is 4U's controller itself (em057_01_efx_frame, every frame
 * from the slot-125 hook), so GU's aura posts (1001 / 1002 / 1003 / 1007 and the enraged ids 0 / 1) answer 0, GU's
 * own "no record" result (its slots then hold 0 and its stops skip them). Test 2026-10-28 (user: "a full ball of
 * effect", fps falling, cleared when the monster changes area): the first version swapped em049_011 into GU's 30 s
 * enraged post, which GU never stops (its em057_00_011 ends by itself; 4U's em049_011 loops until the controller
 * removes it), so one more aura stacked every 30 s. Hyper id 48 -> no effect (logged); GU's common records (cm202 /
 * cm200) stay. Not ported: the controller's loop sounds 201 / 202 / 203 (0x322d90, sounds batch).
 * Point posts (sz_efx_world, C; notes/b5-shells.md 8): 4U posts its shell and ground effects at a point (0xc08628,
 * nothing attached). GU's monster entry 0x6ff74 attaches every post to the monster's model when the request names no
 * target (req+0xd0 = vt+0x130(self), req+0x1c |= 2), so the effect takes the monster's model frame and scale (as
 * Gogmazios' ground effects, 2.5x too big); GU's own point posts (0x179d3c) leave the target empty and go through
 * 0x40978, as 0x53b500 does after filling an unset area (req+0xc = 254) with the unit's. So sz_efx_world calls
 * 0x53b500 itself (the monster's PEL u this+0xb624 and PEL-tied sounds this+0xb628, what 0x6ff74 passes through
 * slot 78 0x6fe48). Request overrides (req+0x14 bit i -> field i of the body; em089_efx.c, 0x179d90): bit 1 rotation
 * in degrees at req+0x30, bit 19 ground flags at req+0x6c. Ground flags = 4U 0xc074b8: (2 << kind) | 1, kind >= 6 ->
 * 3; an EFL element shows when its ground mask (element word 4) meets them (4U 0xafc574; GU keeps the words, its
 * records +0x4c and the request body +0x5c default to -1 = every ground set at once).
 * The posted records need GU's world transform mode (record +0x36 3 / +0x3e 6 = mode 3, efl4u2gu PEL_TAIL_WORLD): the
 * unit setup (effect slot 32 0x32aa44) attaches the root node to the target in modes 0-2 and copies a world position
 * in modes 3 / 4 (C). Test 5 with the attach tail (mode 2) and no target drew them away from the point (user:
 * "shifted towards the left of his body"); GU's own joint -1 code posts use mode 3 (notes/b5-shells.md 8e).
 * Multiplayer: each machine runs these for its own copy (the dispatcher and GU's posts run on every machine, S);
 * effects and sounds are local. */
#include "em057_01.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

typedef void *(*efx_post_t)(void *self, uint32_t mode, uint32_t rec, void *req);
#define efx_post_u  FN(efx_post_t, 0x6ff74)     /* PEL u list `mode` record, returns the effect or 0 */
typedef void *(*sndPos_t)(void *mgr, uint32_t id, void *owner, const float *pos, uint32_t area, int32_t m2);
#define sndPos      FN(sndPos_t, 0x4efb98)      /* [0x312484] */
typedef void (*efx_stop_t)(void *eff, uint32_t kill);
#define efx_stop    FN(efx_stop_t, 0x32a400)    /* 1: vt+0xa4 and state 2 (kill; GU's slot reset vt118 0xeeebb0) */
#define rageOn      FN(selfInt_t, 0x8172c)      /* [0x954e48] W+0x530 == 1 (dala_parts.c) */

#define REQ         0xb640  /* GU's effect request in the monster; its byte +0xc = the area, set before each post */
/* the aura's handle and state, in GU's type-52 material fields: the material init (vt118 0xeeed88) writes them for a
 * type-52 material only, none in em049's model, and slot 132, their only reader, is skipped for variant 1 (C;
 * em057_01_fix.c); the ctor sets the handle to 0 and the state to -1 (eee8f8 / eee950: test 3 logged "255 -> 0") */
#define AURA_EFX    0xcac4  /* uMHProofEffect * [4U controller +0x3c] */
#define AURA_STATE  0xcacc  /* u32: state 1..4 | area << 8 [4U controller +0x31] */
#define AURA_SNDA   0xcad0  /* float loop-sound timer A [4U controller +64] (type-52 fields too: written by the ctor */
#define AURA_SNDB   0xcad4  /* float timer B [+68]   and the material reset eeecd8 only, read by slot 132 only) */
#define AURA_LINES  60u

static const uint16_t s_aura_rec[5] = {0, 3250, 3225, 3200, 3211};   /* em049_000 masks 2 / 4 / 1, em049_011 */

typedef void *(*unitEfxPost_t)(void *unit, void *pel, uint32_t mode, uint32_t id, void *req, void *tied);
#define unitEfxPost FN(unitEfxPost_t, 0x53b500)
typedef void (*efx_req_t)(void *req);
#define efx_req_ctor FN(efx_req_t, 0x40b10)
#define efx_req_dtor FN(efx_req_t, 0x40b50)
#define PEL_U_OBJ   0xb624  /* the monster's PEL u */
#define PEL_SE_OBJ  0xb628  /* its PEL-tied sounds */
#define REQ_SIZE    0x100u  /* request object ~0xd8 B */
#define REQ_FIELDS  0x14    /* body field-override bits */
#define REQ_ROT     0x30    /* float[4] degrees, bit 1 */
#define REQ_GROUND  0x6c    /* u32 ground flags, bit 19 */
#define REQ_FLAGS   0x1c    /* 1: world position, 2: attach */
#define REQ_POS     0xc0
#define REQ_TARGET  0xd0    /* attach model (0x6ff74 fills vt+0x130(monster) only when 0) */
#define VT_ATTACH   0x130   /* unit slot 76: the attach model getter (this+0xfd0, shells too; em089_efx.c) */
#define EFX_NODE    0x150   /* transform node, position +0x40 (0x32a45c) */

int sz_efx_alive(void *eff)                     /* unit state 1 / 2 (dala_efx.c) */
{
    return eff && (FIELD(uint32_t, eff, 0xc) & 7) - 1 < 2;
}

void sz_efx_finish(void *eff)                   /* 0x32a400 mode 0: asks it to finish (4U 0xc470dc on a one-shot) */
{
    if (sz_efx_alive(eff)) efx_stop(eff, 0);
}

int sz_efx_pos(void *eff, float *out)           /* where GU placed it: node +0x40 (0x32a45c writes it) */
{
    uint8_t *n = sz_efx_alive(eff) ? FIELD(uint8_t *, eff, EFX_NODE) : 0;
    if (!n) return 0;
    for (int i = 0; i < 3; i++) out[i] = FIELD(float, n, 0x40 + 4 * i);
    return 1;
}

uint32_t sz_ground_flags(uint32_t kind)         /* 4U 0xc074b8..0xc07524 */
{
    return (kind < 6 ? 2u << kind : 2u) | 1u;
}

void *sz_efx_world(void *self, uint32_t id, const float *pos, const float *rot, uint32_t ground)
{
    uint32_t buf[REQ_SIZE / 4 + 4];
    void *req = (void *)(((uint32_t)buf + 15u) & ~15u), *eff;
    if (!self || !pos) return 0;
    if (FIELD(uint8_t, self, EN_ACT_CAT) == 12 && FIELD(uint8_t, self, EN_ACT_NUM) == 255) return 0;   /* 0x6ff94 */
    efx_req_ctor(req);
    FIELD(uint32_t, req, REQ_FLAGS) |= 1u;
    for (int i = 0; i < 3; i++) FIELD(float, req, REQ_POS + 4 * i) = pos[i];
    FIELD(float, req, REQ_POS + 12) = 0.0f;
    if (rot) {
        FIELD(uint32_t, req, REQ_FIELDS) |= 2u;
        for (int i = 0; i < 3; i++) FIELD(float, req, REQ_ROT + 4 * i) = rot[i] * 57.2957795f;
        FIELD(float, req, REQ_ROT + 12) = 0.0f;
    }
    if (ground) {
        FIELD(uint32_t, req, REQ_FIELDS) |= 0x80000u;
        FIELD(uint32_t, req, REQ_GROUND) = ground;
    }
    eff = unitEfxPost(self, FIELD(void *, self, PEL_U_OBJ), 2, id, req, FIELD(void *, self, PEL_SE_OBJ));
    efx_req_dtor(req);
    return eff;
}

/* 4U 0xc08698 with request +0x5c = a shell (an effect that rides the shell): GU shells' own request (0x4a1d34, as
 * em089_efx.c post_full, tested on Gogmazios' flying blobs): attach model = the unit's vt+0x130, flags 1 | 2, world
 * position = the unit's (+0x40), req+4 = the unit, req+0xc = its area; posted through the monster's PEL (0x6ff74) */
void *sz_efx_on(void *self, uint32_t id, void *unit)
{
    typedef void *(*attach_t)(void *);
    uint32_t buf[REQ_SIZE / 4 + 4];
    void *req = (void *)(((uint32_t)buf + 15u) & ~15u), *eff;
    if (!self || !unit) return 0;
    efx_req_ctor(req);
    FIELD(void *, req, REQ_TARGET) = ((attach_t)((*(uint32_t **)unit)[VT_ATTACH / 4]))(unit);
    FIELD(uint32_t, req, REQ_FLAGS) |= 3u;
    for (int i = 0; i < 3; i++) FIELD(float, req, REQ_POS + 4 * i) = FIELD(float, unit, 0x40 + 4 * i);
    FIELD(float, req, REQ_POS + 12) = 0.0f;
    FIELD(void *, req, 0x4) = unit;
    FIELD(uint8_t, req, 0xc) = FIELD(uint8_t, unit, 0x1054);
    eff = efx_post_u(self, 2, id, req);
    efx_req_dtor(req);
    return eff;
}

/* 4U 0x312484(mgr, id, owner, pos, area, -2) = GU 0x4efb98 (dala_shell.h, C) */
void sz_snd_at(void *self, uint32_t id, const float *pos, uint32_t area)
{
    void *mgr = *(void **)MAIN(SND_MGR);
    if (mgr && self && pos) sndPos(mgr, id, self, pos, area & 0xff, -2);
}

/* 4U aura controller 0x322f18 (C): 0 = none (0x94d7a8: action category 11 or 14, or the death action 12 / 255),
 * 4 = enraged (rageOn), 3 = charged (0x90f90c), else uEm048 slot 51 query 1 (0x857a5c): charge work+0 < 25 -> 0,
 * < 50 -> 1, < 75 -> 2, else 3. GU keeps action, rage, charge flag and work+0 where 4U's code reads them (C:
 * em057_01_start.c, game.h). */
static uint32_t aura_state(void *self)
{
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_NUM);
    int32_t c;
    if (cat == 11 || cat == 14 || (cat == 12 && num == 255)) return 0;
    if (rageOn(self)) return 4;
    if (isCharged(self)) return 3;
    c = FIELD(int16_t, WORK(self), 0);
    return c < 25 ? 0 : c < 50 ? 1 : c < 75 ? 2 : 3;
}

/* 4U 0xb0709c(unit, &timer): 1 when the timer is or reaches 0 (then 0), else counts it down by the unit's dt */
static int aura_timer(void *self, uint32_t off)
{
    float *t = &FIELD(float, self, off);
    if (*t > 0.0f) {
        *t -= FIELD(float, self, EN_DT);
        if (*t > 0.0f) return 0;
    }
    *t = 0.0f;
    return 1;
}

/* 4U 0x322d90(controller, state) (C), every frame after the state step: two repeating sounds at joint 2 (0x2fcc50
 * with the unit's area and -2 = sz_snd). Timer A (+64): states 1 / 2 -> 201 every 58, 3 -> 202 every 62, 4 -> 203
 * every 46; timer B (+68): state 2 -> 208, 3 / 4 -> 206, every 48. A timer that runs out in state 0 (or B in state 1)
 * stays at 0 and fires as soon as a state that plays comes. */
static void aura_sounds(void *self, uint32_t st)
{
    static const uint16_t a_id[5] = {0, 201, 201, 202, 203}, b_id[5] = {0, 0, 208, 206, 206};
    static const float a_gap[5] = {0, 58.0f, 58.0f, 62.0f, 46.0f};
    if (aura_timer(self, AURA_SNDA) && a_id[st]) {
        sz_snd(self, a_id[st], 2, 0x322e14);
        FIELD(float, self, AURA_SNDA) = a_gap[st];
    }
    if (aura_timer(self, AURA_SNDB) && b_id[st]) {
        sz_snd(self, b_id[st], 2, 0x322ec8);
        FIELD(float, self, AURA_SNDB) = 48.0f;
    }
}

/* every frame (em057_01_diag.c, slot 125): one aura for the state; a new state removes the old one (4U 0xc470dc,
 * here GU's kill) and posts its own (4U 0xc08698 on the monster, joint 2: the records' joint) and restarts both
 * sound timers at 0 (0x322fe8; not for state 0); then the loop sounds (aura_sounds). An aura GU removed with the
 * monster's area change is forgotten untouched and posted again in the new area. */
void em057_01_efx_frame(void *self)
{
    static uint32_t s_lines;
    uint32_t st = aura_state(self), area = FIELD(uint8_t, self, EN_AREA), old = FIELD(uint32_t, self, AURA_STATE);
    void *h = FIELD(void *, self, AURA_EFX);
    if (h && ((old >> 8) != area || !sz_efx_alive(h))) h = 0, old = 0;
    if (h != FIELD(void *, self, AURA_EFX) || (old & 0xff) != st) {
        if (h) efx_stop(h, 1);
        h = 0;
        if (st) {
            FIELD(uint8_t, self, REQ + 0xc) = (uint8_t)area;
            h = efx_post_u(self, 2, s_aura_rec[st], (uint8_t *)self + REQ);
            FIELD(float, self, AURA_SNDA) = 0.0f;
            FIELD(float, self, AURA_SNDB) = 0.0f;
        }
        FIELD(void *, self, AURA_EFX) = h;
        FIELD(uint32_t, self, AURA_STATE) = st | area << 8;
        if (s_lines < AURA_LINES) {
            s_lines++;
            logf("szport: em057_01 aura %u -> %u (record %u, effect %x, area %u)", old & 0xff, st, s_aura_rec[st],
                 (uint32_t)(uintptr_t)h, area);
        }
    }
    aura_sounds(self, st);
}

/* 4U 0x304c34(mgr, id, owner, joint, area, -2): a point sound at the joint's position now (dala_shell.h, C) */
static void snd_at_joint(void *self, uint32_t id, uint32_t joint)
{
    float p[4];
    jointPos(self, joint, p);
    sz_snd_at(self, id, p, FIELD(uint8_t, self, EN_AREA));
}

/* GU uEm057_00 slot 116 0xf060c4(self, id, req) -> effect or 0 */
int em057_01_efx_c(uint32_t *regs)
{
    static uint8_t s_hyper;
    void *self = (void *)regs[R0];
    uint32_t id = regs[R1], cat11;
    if (!self || FIELD(uint16_t, self, EN_ID) != STYGIAN_ZINOGRE_EM_ID) return 0;
    switch (id) {
    case 1001: case 1002: case 1003: case 1007: case 0: case 1:     /* the aura: em057_01_efx_frame */
        regs[R0] = 0;
        return 1;
    case 1004: case 1005:
        cat11 = FIELD(uint8_t, self, EN_ACT_CAT) == 11;
        regs[R0] = (uint32_t)efx_post_u(self, 2, cat11 ? 3205 : 3202, (void *)regs[R2]);
        snd_at_joint(self, cat11 ? 213 : 210, cat11 ? 1 : 2);
        return 1;
    default:
        if (id < 47 || id >= 1000) return 0;
        if (s_hyper < 4) {
            s_hyper++;
            logf("szport: em057_01 GU Hyper effect id %u (cat %u/%u)%s", id, FIELD(uint8_t, self, EN_ACT_CAT),
                 FIELD(uint8_t, self, EN_ACT_NUM), id == 48 ? ": Zinogre's em057_00_500, not posted" : "");
        }
        if (id != 48) return 0;
        regs[R0] = 0;
        return 1;
    }
}
