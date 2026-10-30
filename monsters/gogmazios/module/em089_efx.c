/* em089_efx.c: Gogmazios effects on GU's proof-effect system (effects agent).
 *
 * Motion-synced effects need no code: tools/efl4u2gu.py converts the 4U LMT event group 2 (MEF id remap +
 * run-length {bits, frames}) into em089's PSL files (manifest 18..21) and the 4U MEF into PEL u (manifest 17); the
 * GU enemy framework plays them per motion like any GU monster's (PSL slot kind 4 = PEL u list 1).
 *
 * Code posts (C, GU 1.4): uEnemy 0x6ff74(this, mode 2, id, req) = PEL u (this+0xb624) list 2 record `id` (0x6fe90
 * = PEL c this+0x1358); it fills req+0xd0 = vt+0x130(this) (attach model) and req+0x1c |= 2 when req+0xd0 is 0,
 * then slot 78 0x6fe48 -> 0x53b500 -> sFestaProofEffect 0x40978 (record lookup by id 0x3267d0, uMHProofEffect
 * 848 B). The request is the 0x40b10 object (dtor 0x40b50): +0xc u8 area (254 = this+0x1054), +0x10 a copy of the
 * PEL 160-byte record layout (override bits at req+0x1c, req+0x14 bit 30), req+0xc0..0xcc world position (used
 * with req+0x1c bit 0, GU monster 0xd3f5a0). 4U em089 code never posts its MEF effects directly (the 12
 * 0x6620c4 calls create uShell016 camera/quake shells), so the post API is for the shell / gimmick owners.
 *
 * Slot 75 (4U 0x8c3ca0): per current motion the generated em089_slot75.inc sets two 4U curve tracks (time, end,
 * table at fixed motion frames); here, while the 4U gate W+0x434 == 1: track times advance by dt (clamp 999) while
 * time < end (or end < 0), values = piecewise-linear curves (4U 0xaac930), defaults 7.7 / 30 degrees; joint 200's
 * local transform = Rx(v1) * Ry(v2) * Rz(3.5 deg) (row vectors, 4U composes them on the identity matrix) with the
 * joint's own local translation (4U 0xb052ec -> GU joint +0x80), set with GU 0x72438 (= 4U 0xb05754, same
 * matrix -> quaternion body, joint +96 quat / +0x80 translation, joints this+0x494 x 160 B, id table this+0x498).
 */
#include "game.h"
#include "util.h"
#include "em089_efx.h"
#include "em089_shell016.h"   /* em089_shell016_fx hook (set by em089_efx_init) */

typedef void *(*efx_post_t)(void *self, uint32_t mode, uint32_t id, void *req);
#define efx_post_u   FN(efx_post_t, 0x6ff74)     /* PEL u (this+0xb624), returns uMHProofEffect* or 0 */
typedef void (*efx_req_t)(void *req);
#define efx_req_ctor FN(efx_req_t, 0x40b10)
#define efx_req_dtor FN(efx_req_t, 0x40b50)
typedef void (*efx_stop_t)(void *eff, uint32_t now);
#define efx_stop_fn  FN(efx_stop_t, 0x32a400)
typedef void (*joint_set_t)(void *model, uint32_t joint, const float *mtx);
#define joint_set    FN(joint_set_t, 0x72438)
/* live effect transform (C, GU beam update 0x10ab3d8 = 4U 0x1b5ba0 on [eff+0x74]): transform objects eff+0x150 /
 * +0x154, position +0x40 (0x32a45c(eff, pos, 0) writes both), scale +0x60, rotation (x, y, z) in RADIANS set with
 * 0x8a7dc4(eff+0x150 object) in its own order (+56) */
typedef void (*efx_set_pos_t)(void *eff, const float *pos, int32_t k);
#define efx_set_pos  FN(efx_set_pos_t, 0x32a45c)
typedef void (*efx_set_rot_t)(void *xf, const float *rot);
#define efx_set_rot  FN(efx_set_rot_t, 0x8a7dc4)
#define EFX_XF       0x150

#define EFX_MODE_CODE  2u       /* PEL list 2 = code posts (list 1 = PSL motion sequences) */
#define REQ_SIZE       0x100u   /* object ~0xd8 B (sub-object 0x31be70 fields up to +0xc4 at req+0x10) */
#define REQ_FLAGS      0x1c
#define REQ_POS        0xc0
#define REQ_TARGET     0xd0     /* attach model (0x6ff74 fills vt+0x130(owner) only when 0) */
#define VT_ATTACH      0x130    /* unit slot 76: attach model getter (0x6be88: this+0xfd0, shells too) */

static uint32_t s_log;

/* request field overrides (C: 0x31c280 -> 0x31c3a8 merges the request's param (req+0x10) into the effect's): param
 * +4 bit i selects struct field i of req+0x20: bit 0 offset (req+0x20), bit 1 rotation in degrees (req+0x30), bit 30
 * scale MULTIPLIER (req+0x40); GU 0x10b04c4 posts a beam this way: world position (req+0x1c bit 0, req+0xc0) +
 * rotation (pitch, yaw in degrees = u16 * 360 / 65536) + scale. */
#define REQ_FIELDS     0x14
#define REQ_ROT        0x30
#define REQ_SCALE      0x40
#define REQ_GROUND     0x6c     /* u32 ground flags = body field 19 (req+0x14 bit 19; GU's own post helper 0x179d3c) */

/* Ground sets (C, ISSUE_6.md; monsters/stygian_zinogre/notes/b5-shells.md 8b): an EFL holds one element set per
 * ground (element word 4: soil 0x22, 0x54 / 0x14, lava 0x8; here only the qe006 dust files have them) and the effect
 * keeps the elements whose word meets (2 << kind) | 1 (4U 0xc07440 / 0xafc574). 4U takes the kind from the
 * monster's ground record W+0x5f0 (attribute word +8; 0xc09908's enemy branch, the bit tests of 0xc094e8) for its
 * motion posts (0x391b50 -> 0xc09908) and 0x954e5c; Battlequarters' floor is kind 0 everywhere (soil only). GU's PEL
 * records and requests default to -1 = every set at once: the white "snow debris" of issue #6 (the 0x54 set). A
 * request overrides it with req+0x14 bit 19 + req+0x6c. GU's twin of W+0x5f0 is not identified: the attribute word
 * comes from the Stygian slam ray (0x183ad0, mask 64) down through the ground under the monster (rec+0x5b4) (S). */
typedef float (*ground_ray_t)(void *mgr, const float *from, const float *to, uint32_t area, uint8_t *hit, void *out,
                              uint32_t mask);
#define groundRay    FN(ground_ray_t, 0x183ad0)  /* [0x2bad24] */
#define COLL_MGR     (*(void **)MAIN(0x21270e0)) /* its manager [*0x10574fc] */
#define REC_GROUND_Y 0x5b4

static uint32_t ground_flags(void *self)
{
    static uint32_t s_key, s_n;
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    uint32_t out[16] = {0}, w = 0, kind;
    uint8_t hit = 0;
    float gy = FIELD(float, rec, REC_GROUND_Y);
    float from[4] = {FIELD(float, rec, REC_POS_X), gy + 100.0f, FIELD(float, rec, REC_POS_Z), 0.0f};
    float to[4] = {from[0], gy - 300.0f, from[2], 0.0f};
    void *mgr = COLL_MGR;
    if (mgr) groundRay(mgr, from, to, FIELD(uint8_t, self, 0x1054), &hit, out, 64);
    if (hit) w = out[2];
    if (w & 0x800000) kind = 5;
    else if (w & 0x200) kind = 3;
    else if (w & 6) kind = 1;
    else if (w & 0x1040) kind = 2;
    else kind = (w & 8) ? 4 : 0;
    if ((w ^ (uint32_t)!hit << 31) != s_key && ++s_n <= 20) {
        s_key = w ^ (uint32_t)!hit << 31;
        logf("gogport: em089 efx ground %s word %x -> kind %u at %d %d %d", hit ? "hit" : "none (kind 0)", w, kind,
             (int32_t)from[0], (int32_t)gy, (int32_t)from[2]);
    }
    return (2u << kind) | 1u;
}

static void *post_full(void *self, uint32_t id, const float *pos, void *unit, const float *rot, const float *scale,
                       uint32_t req8)
{
    uint32_t buf[REQ_SIZE / 4 + 4];
    void *req = (void *)(((uint32_t)buf + 15u) & ~15u);
    efx_req_ctor(req);
    /* the ground set: 4U's code-post requests default to kind 0 (flags 3); 0x954e5c (3100, qe006_000, the only
     * code-posted file with sets: no em089 / qe008 / qe016 / m19a03 EFL has them) takes the monster's. The ray stays
     * off the other posts: they come from deep shell paths (the 5101 tar splash, shell impact) */
    FIELD(uint32_t, req, REQ_FIELDS) |= 0x80000u;
    FIELD(uint32_t, req, REQ_GROUND) = id == EM089_EFX_IMPACT ? ground_flags(self) : 3u;
    if (req8) {   /* GU's own moving beam (0x10b04c4): req+8 = 3, req+0xc = the monster's area (meaning not traced) */
        FIELD(uint32_t, req, 0x8) = req8;
        FIELD(uint8_t, req, 0xc) = FIELD(uint8_t, self, 0x1054);
    }
    if (rot) {
        FIELD(uint32_t, req, REQ_FIELDS) |= 2u;
        for (int i = 0; i < 3; i++) FIELD(float, req, REQ_ROT + 4 * i) = rot[i];
        FIELD(float, req, REQ_ROT + 12) = 0.0f;
    }
    if (scale) {
        FIELD(uint32_t, req, REQ_FIELDS) |= 0x40000000u;
        for (int i = 0; i < 3; i++) FIELD(float, req, REQ_SCALE + 4 * i) = scale[i];
        FIELD(float, req, REQ_SCALE + 12) = 0.0f;
    }
    if (unit) {
        /* GU shells' own effect request (0x4a1d34, e.g. 0x3f9560): attach model = unit vt+0x130, req+0x1c |= 3
         * (world position + attach), req+0xc0 = the unit's position, req+0x4 = the unit, req+0xc = its area. Test 2
         * (flag 2 only, no position / unit) showed the blob effect under the monster instead of on the blob. */
        typedef void *(*attach_t)(void *);
        FIELD(void *, req, REQ_TARGET) = ((attach_t)((*(uint32_t **)unit)[VT_ATTACH / 4]))(unit);
        FIELD(uint32_t, req, REQ_FLAGS) |= 3u;
        if (!pos) {
            for (int i = 0; i < 3; i++) FIELD(float, req, REQ_POS + 4 * i) = FIELD(float, unit, 0x40 + 4 * i);
            FIELD(float, req, REQ_POS + 12) = 0.0f;
        }
        FIELD(void *, req, 0x4) = unit;
        FIELD(uint8_t, req, 0xc) = FIELD(uint8_t, unit, 0x1054);
    }
    if (pos) {
        FIELD(uint32_t, req, REQ_FLAGS) |= 1u;
        FIELD(float, req, REQ_POS) = pos[0];
        FIELD(float, req, REQ_POS + 4) = pos[1];
        FIELD(float, req, REQ_POS + 8) = pos[2];
        FIELD(float, req, REQ_POS + 12) = 0.0f;
    }
    void *eff = efx_post_u(self, EFX_MODE_CODE, id, req);
    efx_req_dtor(req);
    static uint32_t s_n, s_freq;              /* blob drips / splashes are frequent: own small budget */
    int freq = id == 3000 || id == 3001 || (id >= 5100 && id < 5200);
    if (freq ? ++s_freq <= 12 : ++s_n <= 80)
        logf("gogport: em089 efx post id %u%s%s%s -> %x", id, pos ? " (at pos)" : "", unit ? " (on unit)" : "",
             rot ? " (rot)" : "", (uint32_t)eff);
    return eff;
}

static void *post_req(void *self, uint32_t id, const float *pos, void *unit)
{
    return post_full(self, id, pos, unit, 0, 0, 0);
}

void *em089_efx_post_ex(void *self, uint32_t id, const float *pos, const float *rot_deg, const float *scale)
{
    return post_full(self, id, pos, 0, rot_deg, scale, 0);
}

void *em089_efx_post(void *self, uint32_t id) { return post_req(self, id, 0, 0); }
void *em089_efx_post_at(void *self, uint32_t id, const float *pos) { return post_req(self, id, pos, 0); }
void *em089_efx_post_on(void *owner, uint32_t id, void *unit) { return post_req(owner, id, 0, unit); }

void em089_efx_stop(void *eff)
{
    if (eff) efx_stop_fn(eff, 0);
}

/* GU slot 75 (vt+0x12c) = the PSL post 0x70028(this, list, PSL entry data, slot, req) of the motion-synced records
 * (dala_psl.c); GU's PSL player builds a fresh request per post (0x53b7e0: 0x40b10 on its stack, vt+0x12c, 0x40b50,
 * C). The ground set as 4U's motion post (0x391b50 -> 0xc09908): qe006 dust 15..17, 46..49, 1008 (walk 25, flying
 * turns 65 / 66, 2/35 motion 264, tar dash 536, reactions 771..823) */
typedef void *(*psl_post_t)(void *self, uint32_t list, const uint8_t *data, uint32_t slot, void *req);
#define pslPostBase FN(psl_post_t, 0x70028)

void *em089_psl_post(void *self, uint32_t list, const uint8_t *data, uint32_t slot, void *req)
{
    if (req) {
        FIELD(uint32_t, req, REQ_FIELDS) |= 0x80000u;
        FIELD(uint32_t, req, REQ_GROUND) = ground_flags(self);
    }
    return pslPostBase(self, list, data, slot, req);
}

void em089_efx_kill(void *eff)
{
    if (eff) efx_stop_fn(eff, 1);
}

int em089_efx_alive(void *eff)
{
    return eff && (FIELD(uint32_t, eff, 0xc) & 7) - 1 < 2;
}

static int en_dead(void *self)   /* 4U 0x94d7a8: action category 11 or 14, or 12 / 255 (death / capture) */
{
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT);
    return cat == 11 || cat == 14 || (cat == 12 && FIELD(uint8_t, self, EN_ACT_NUM) == 255);
}

static float owner_step(void *owner)   /* 4U 0x94460c: owner motion speed * dt (rec+0x398 * this+28) */
{
    return FIELD(float, FIELD(uint8_t *, owner, EN_RECORD), 0x398) * FIELD(float, owner, EN_DT);
}

/* ------------------------------------------------------------------ uShell016 uEffect002 (shell016 hook) */

/* 4U: the shell's init posts uEffect002 48 / 50 / 53 / 54 (mode 1) through 0xc0b470; the effect sits at the shell's
 * start point (joint 3 + M * offset) along the capsule every frame (0x1b5ba0, scale 2.5) and finishes when the shell
 * is gone (0x1b4074) or, for 53 / 54, at shell life <= 10 (0x1b5d68), when the shell posts the end effect (mode 2,
 * 0xc6cbd8 / 0xc6dd90 / 0xc6e8d0). GU: world records 4200 + subtype (end: 4300 + subtype) posted at the capsule start
 * with the segment's pitch / yaw (degrees, req+0x14 bit 1), then moved every frame by em089_efx_shell016_move with the
 * GU live-effect setters (as GU's own beam 0x10ab3d8); the shell end is mirrored from the 4U rule (owner motion !=
 * spawn motion or life <= 0, life -= owner motion step) and by em089_efx_shell016_end. */
typedef struct { void *shell, *owner, *eff, *end_eff; float life; uint32_t motion; uint8_t sub, efx, end_wait; } s016fx_t;
#define S016_SLOTS 8
static s016fx_t s_s016[S016_SLOTS];

static float s016_life(uint32_t sub)   /* 4U table 0x102bbbc (em089_shell016.c k_sub) */
{
    switch (sub) {
    case 36: case 53: return 120.0f;
    case 37: return 128.0f;
    case 41: return 150.0f;
    case 51: return 260.0f;
    case 54: return 139.0f;
    default: return 680.0f;   /* 52 / 55 / 56 */
    }
}

static void s016_release(s016fx_t *e, const char *why)
{
    static uint32_t s_n;
    if (em089_efx_alive(e->eff)) em089_efx_stop(e->eff);
    if (em089_efx_alive(e->end_eff)) em089_efx_stop(e->end_eff);
    if (++s_n <= 40) logf("gogport: em089 efx shell016 sub %u effect end: %s", e->sub, why);
    for (uint32_t k = 0; k < sizeof *e; k++) ((uint8_t *)e)[k] = 0;
}

/* placement from the shell's capsule (4U 0x1b5ba0; em089_shell016.c s016_place has already run): position = the
 * second point (start, 4U +0x120), rotation = (pitch, yaw) of start -> point as u16 angles (0x568c8c), pitch + 35 for
 * id 50 / + 40 for id 54 (C: 0x1b5d2c / 0x1b5cf0) */
#define S016_POINT 0x40      /* em089_shell016.c SH_POS  [4U +0x100] */
#define S016_START 0x1000    /* em089_shell016.c SH_POS2 [4U +0x120] */
#define A16_DEG    (360.0f / 65536.0f)
#define A16_RAD    (6.28318531f / 65536.0f)

static float a16_deg(uint32_t a) { a &= 0xffffu; return (float)(int32_t)(a >= 0x8000u ? (int32_t)a - 0x10000 : (int32_t)a) * A16_DEG; }
static uint32_t rad_a16(float r) { return (uint32_t)(int32_t)(r * (65536.0f / 6.28318531f)) & 0xffffu; }

static void s016_seg(void *shell, uint32_t efx, float *q, uint32_t *pitch, uint32_t *yaw)
{
    const float *p = &FIELD(float, shell, S016_POINT), *s = &FIELD(float, shell, S016_START);
    float dx = p[0] - s[0], dy = p[1] - s[1], dz = p[2] - s[2], h = dx * dx + dz * dz, hs;
    __asm__("vsqrt.f32 %0, %1" : "=t"(hs) : "t"(h));
    for (int i = 0; i < 3; i++) q[i] = s[i];
    q[3] = 0.0f;
    *yaw = rad_a16(atan2f_gu(dx, dz));
    *pitch = (rad_a16(atan2f_gu(-dy, hs)) + (efx == 54 ? 40u : efx == 50 ? 35u : 0u)) & 0xffffu;
}

/* post 4200 / 4300 + subtype at the capsule start with the segment angles (request rotation = degrees) */
static void *s016_post(void *owner, void *shell, uint32_t id, uint32_t efx)
{
    float q[4], rot[3];
    uint32_t pa, ya;
    s016_seg(shell, efx, q, &pa, &ya);
    rot[0] = a16_deg(pa); rot[1] = a16_deg(ya); rot[2] = 0.0f;
    void *eff = post_full(owner, id, q, 0, rot, 0, 3);
    static uint32_t s_n;   /* test 5: does the transform carry the owner's 2.5 scale? (record scale is 1.0 now) */
    void *xf = eff ? FIELD(void *, eff, EFX_XF) : 0;
    if (xf && ++s_n <= 12)
        logf("gogport: em089 efx beam %u transform scale x1000 %d %d %d pos %d %d %d (req %d %d %d) rot order %u", id,
             (int32_t)(FIELD(float, xf, 0x60) * 1000.0f), (int32_t)(FIELD(float, xf, 0x64) * 1000.0f),
             (int32_t)(FIELD(float, xf, 0x68) * 1000.0f), (int32_t)FIELD(float, xf, 0x40),
             (int32_t)FIELD(float, xf, 0x44), (int32_t)FIELD(float, xf, 0x48), (int32_t)q[0], (int32_t)q[1],
             (int32_t)q[2], FIELD(uint16_t, xf, 0x38));
    return eff;
}

void em089_efx_shell016_fx(void *shell, void *owner, uint32_t subtype, uint32_t efx_id)
{
    s016fx_t *e = 0, *free_slot = 0;
    for (int i = 0; i < S016_SLOTS; i++) {
        if (s_s016[i].shell == shell) e = &s_s016[i];
        else if (!s_s016[i].shell && !free_slot) free_slot = &s_s016[i];
    }
    if (e && e->life > 40.0f) { s016_release(e, "shell address reused"); free_slot = e; e = 0; }
    if (e) {                                  /* second call: the end effect at life <= 10 */
        if (em089_efx_alive(e->eff)) em089_efx_stop(e->eff);   /* 0x1b5d68: 53 / 54 finish at life <= 10 */
        e->eff = 0;
        e->end_eff = s016_post(owner, shell, 4300 + subtype, efx_id);
        e->end_wait = 2;                      /* 4U: finishes on its first update (life already <= 10) */
        return;
    }
    if (!free_slot) { free_slot = &s_s016[0]; s016_release(free_slot, "slot recycled"); }
    e = free_slot;
    e->shell = shell; e->owner = owner; e->sub = (uint8_t)subtype; e->efx = (uint8_t)efx_id;
    e->life = s016_life(subtype); e->motion = curMotion(owner);
    {   /* test-2 diagnostics: effect origin (joint id 3) vs head (id 4) and jaw tip (id 202) */
        static uint32_t s_n;
        if (++s_n <= 20) {
            float a[4], b[4], c[4];
            jointPos(owner, 3, a); jointPos(owner, 4, b); jointPos(owner, 202, c);
            logf("gogport: em089 efx shell016 sub %u joints 3 %d %d %d / 4 %d %d %d / 202 %d %d %d", subtype,
                 (int32_t)a[0], (int32_t)a[1], (int32_t)a[2], (int32_t)b[0], (int32_t)b[1], (int32_t)b[2],
                 (int32_t)c[0], (int32_t)c[1], (int32_t)c[2]);
        }
    }
    e->eff = s016_post(owner, shell, 4200 + subtype, efx_id);   /* 36 / 53 never move: placed once, as in 4U */
}

void em089_efx_shell016_end(void *shell)
{
    for (int i = 0; i < S016_SLOTS; i++)
        if (s_s016[i].shell == shell) s016_release(&s_s016[i], "shell ended");
}

/* 4U 0x1b5ba0 every frame: the effects sit at the capsule start along the capsule (GU setters as 0x10ab3d8; the
 * record's scale 2.5 stays) */
void em089_efx_shell016_move(void *shell)
{
    for (int i = 0; i < S016_SLOTS; i++) {
        s016fx_t *e = &s_s016[i];
        if (e->shell != shell) continue;
        float q[4];
        uint32_t pa, ya;
        s016_seg(shell, e->efx, q, &pa, &ya);
        float rot[4] = {(float)pa * A16_RAD, (float)ya * A16_RAD, 0.0f, 0.0f};
        void *effs[2] = {e->eff, e->end_eff};
        for (int k = 0; k < 2; k++) {
            if (!em089_efx_alive(effs[k])) continue;
            efx_set_pos(effs[k], q, 0);
            void *xf = FIELD(void *, effs[k], EFX_XF);
            if (xf) efx_set_rot(xf, rot);
        }
    }
}

static void s016_tick(void *self)
{
    for (int i = 0; i < S016_SLOTS; i++) {
        s016fx_t *e = &s_s016[i];
        if (!e->shell || e->owner != self) continue;
        if (e->eff && !em089_efx_alive(e->eff)) e->eff = 0;
        if (e->end_eff && !em089_efx_alive(e->end_eff)) e->end_eff = 0;
        if (e->end_eff && e->end_wait && !--e->end_wait) em089_efx_stop(e->end_eff);
        e->life -= owner_step(self);
        if ((e->efx == 53 || e->efx == 54) && e->life <= 10.0f && e->eff) { em089_efx_stop(e->eff); e->eff = 0; }
        if (curMotion(self) != e->motion) s016_release(e, "owner motion changed");
        else if (e->life <= 0.0f) s016_release(e, "life out");
    }
}

/* ------------------------------------------------------------------ uEffect002 57 (phase-2 aura) */

/* 4U: posted by the 1/25 / 1/31 roar when work+0xca is first set (0xc0bd38: id 57, joint 1, mode 1), by slot 39
 * (0x8ba1a0) and by the 0x8c5768 tail when work+0xe4 is reset; its update 0x1b6520 finishes it when work+0xca == 0,
 * work+0xe4 == 1 or the monster is dead (0x94d7a8), and re-posts itself in another mode: 4 while W+0x1c8 != 0
 * (GU rec+0x1ba), else 2 while W+0x1c9 == 1 (flying, rec+0x1bb), else 1. Mode = EFL element mask of em089_050
 * (PEL 5701 / 5702 / 5704). Here: wanted = ca && e4 != 1 && alive; (re)posted when it becomes wanted or the mode
 * changes, stopped when it is not wanted any more. */
typedef struct { void *self; const uint8_t *ca, *e4; void *eff; uint8_t mode, on; } aura_t;
#define AURA_SLOTS 4
static aura_t s_aura[AURA_SLOTS];

static uint32_t aura_mode(void *self)
{
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    if (FIELD(uint8_t, rec, REC_STATE)) return 4;
    return FIELD(uint8_t, rec, REC_MODE) == 1 ? 2 : 1;
}

void em089_efx_aura(void *self, const uint8_t *ca, const uint8_t *e4)
{
    aura_t *a = 0;
    for (int i = 0; i < AURA_SLOTS && !a; i++) if (s_aura[i].self == self) a = &s_aura[i];
    for (int i = 0; i < AURA_SLOTS && !a; i++) if (!s_aura[i].self) a = &s_aura[i];
    if (!a) a = &s_aura[0];
    if (a->self != self) { a->self = self; a->eff = 0; a->on = 0; a->mode = 0; }
    a->ca = ca; a->e4 = e4;
    em089_efx_init();
}

static void aura_tick(void *self)
{
    for (int i = 0; i < AURA_SLOTS; i++) {
        aura_t *a = &s_aura[i];
        if (a->self != self) continue;
        if (a->eff && !em089_efx_alive(a->eff)) a->eff = 0;   /* children ended: 4U object stays until a change */
        int want = *a->ca && *a->e4 != 1 && !en_dead(self);
        uint32_t mode = aura_mode(self);
        if (!want) {
            if (a->on) {
                static uint32_t s_n;
                if (++s_n <= 20) logf("gogport: em089 efx aura 57 off (ca %u e4 %u dead %u)", *a->ca, *a->e4,
                                      en_dead(self));
                em089_efx_stop(a->eff);
                a->eff = 0; a->on = 0;
            }
            continue;
        }
        if (a->on && a->mode == mode) continue;
        if (a->eff) em089_efx_stop(a->eff);
        a->eff = em089_efx_post(self, 5700 + mode);
        a->on = 1; a->mode = (uint8_t)mode;
        static uint32_t s_n;
        if (++s_n <= 20) logf("gogport: em089 efx aura 57 mode %u -> %x", mode, (uint32_t)a->eff);
    }
}

/* ------------------------------------------------------------------ 0x954e5c ground impact */

/* 4U 0x954e5c(this, kind, ?, &offset, s0 scale, s1 height): nothing when W+412 (pos y) > W+0x624 (ground y under
 * the monster, GU rec+0x5b4, shell agent's Rathian match) + s1; pos = (W+0x198, W+0x624, W+0x1a0) + yaw-rotated
 * offset * size factor (0x923fc8 = GU 0xbecf0) * s0; kind 1: tremor shell (em089_shell005.c) + qe006_000 dust
 * (0xc08628 group 1 file 64, scale s0 * 0.8, material variant 0xc094e8) = PEL 3100 (scale 0.64 baked). */
/* test 4: the converted qe013_002 loops in GU (white smoke every ~2 s after the break, forever); 4U's request flags
 * (+0x60 / +0x61 of the 0xc088d8 request) have no PEL field, so the port finishes it after one cycle (120 frames) */
static void *s_tail_eff;
static float s_tail_t;

void em089_efx_tail_break(void *self)
{
    s_tail_eff = post_full(self, EM089_EFX_TAIL_BREAK, 0, 0, 0, 0, 0);   /* attach model = owner, joint from record */
    s_tail_t = 120.0f;
}

static void tail_tick(void *self)
{
    if (!s_tail_eff) return;
    if (!em089_efx_alive(s_tail_eff)) { s_tail_eff = 0; return; }
    s_tail_t -= owner_step(self);
    if (s_tail_t <= 0.0f) { em089_efx_stop(s_tail_eff); s_tail_eff = 0; }
}

typedef float (*size_factor_t)(void *self);
#define sizeFactor  FN(size_factor_t, 0xbecf0)
void em089_efx_ground_impact(void *self, uint32_t kind, const float *off, float scale, float height)
{
    static uint32_t s_n;
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    float gy = FIELD(float, rec, REC_GROUND_Y);
    if (FIELD(float, rec, REC_POS_X + 4) > gy + height) {
        if (++s_n <= 20) logf("gogport: em089 efx ground impact skipped: %d above ground",
                              (int32_t)(FIELD(float, rec, REC_POS_X + 4) - gy));
        return;
    }
    float k = sizeFactor(self) * scale;
    float y = (float)(FIELD(uint32_t, rec, REC_YAW) & 0xffff) * (6.28318531f / 65536.0f);
    float s = sinf_gu(y), c = cosf_gu(y), ox = off[0] * k, oy = off[1] * k, oz = off[2] * k;
    float p[3] = {FIELD(float, rec, REC_POS_X) + c * ox + s * oz, gy + oy, FIELD(float, rec, REC_POS_Z) + c * oz - s * ox};
    if (kind != 1 || scale != 0.8f) {
        if (++s_n <= 20) logf("gogport: em089 efx ground impact kind %u scale x100 %d: only the 2/35 call is baked",
                              kind, (int32_t)(scale * 100.0f));
        return;
    }
    void *eff = em089_efx_post_at(self, 3100, p);
    if (++s_n <= 20) logf("gogport: em089 efx ground impact dust at %d %d %d -> %x",
                          (int32_t)p[0], (int32_t)p[1], (int32_t)p[2], (uint32_t)eff);
}

/* ------------------------------------------------------------------ 0xc0819c roar radial blur */

/* 4U 0xc0819c(*0x10572f8, area W+0x14c, &joint 3 position): only when area == the player's area (*0x10572f8+0xc90),
 * new uMhRadialBlurFilter (move 0x3e3b14: strength 0 -> 0.035 -> 0.025 -> 0 over 74 frames, centred on the
 * position, ends early when the player leaves the area). GU: PEL 3200 = port-made em089_roarblur (one Filter entry
 * from em089_011, tools/efl4u2gu.py make_roar_blur) on joint 3. */
void em089_efx_roar_blur(void *self)
{
    static uint32_t s_n;
    typedef uint32_t (*player_area_t)(void);
    if (FIELD(uint8_t, self, 0x1054) != FN(player_area_t, 0x4971c)()) {
        if (++s_n <= 10) logf("gogport: em089 efx roar blur skipped: monster area %u, player area %u",
                              FIELD(uint8_t, self, 0x1054), FN(player_area_t, 0x4971c)());
        return;
    }
    /* NOT posted (deviation): no GU radial-blur path calibrated to 4U's code blur. The EFL Filter unit's words are a
     * colour + alpha (Capcom values (1,1,1,1) / (0.924,0.871,0.849,1) / (1,1,1,0.15) ...), only 17 Filter units in
     * all GU enemy arcs, none identifiable as a roar blur; GU code never instantiates uRadialBlurFilter. */
    if (++s_n <= 10) logf("gogport: em089 efx roar blur (4U 0xc0819c): not ported, no calibrated GU blur");
}

/* ------------------------------------------------------------------ Battlequarters stage effects */

/* 4U sEffect scheduler event CreateKowareEft (0xc0afa8): index -> table 0xe06378 (tools/efl4u2gu.py KOWARE_EFL),
 * element mask 1 << KowareEftGroup, at KowareEftPos with KowareEftScale, only when KowareEftAreaNo is the player's
 * area (or 255). GU has no such controller: the stage code posts here; the EFLs ride in em089's arc and PEL
 * (records 6000 + 4 * index + group, 6100 + n for m19a03_NNN), posted on the last em089 seen (world position). */
typedef uint32_t (*player_area_t)(void);
#define playerArea FN(player_area_t, 0x4971c)
static void *s_efx_owner;

void *em089_efx_stage_kowareeft(uint32_t index, uint32_t group, const float *pos, uint32_t area)
{
    static uint32_t s_n;
    int ok = (index == 2 || (index >= 11 && index <= 17)) && group < 3;
    if (!s_efx_owner || !pos || !ok) {
        if (++s_n <= 20) logf("gogport: em089 efx stage KowareEft %u group %u dropped (owner %x)", index, group,
                              (uint32_t)s_efx_owner);
        return 0;
    }
    if (area != 255 && area != playerArea()) return 0;   /* 0xc0b140: other area -> nothing */
    return em089_efx_post_at(s_efx_owner, 6000 + 4 * index + group, pos);
}

void *em089_efx_stage_efl(uint32_t n, const float *pos)
{
    if (!s_efx_owner || !pos || n >= 14) return 0;
    return em089_efx_post_at(s_efx_owner, 6100 + n, pos);
}

void *em089_efx_stage_efl_rot(uint32_t n, const float *pos, const float *rot_deg)
{
    if (!s_efx_owner || !pos || n >= 14) return 0;
    return post_full(s_efx_owner, 6100 + n, pos, 0, rot_deg, 0, 0);
}

void *em089_efx_stage_efl_on(uint32_t n, void *unit)
{
    if (!s_efx_owner || !unit || n >= 14) return 0;
    return em089_efx_post_on(s_efx_owner, 6100 + n, unit);
}

void *em089_efx_stage_efl_track(uint32_t n, const float *pos, const float *rot_deg)
{
    if (!s_efx_owner || !pos || n >= 14) return 0;
    return post_full(s_efx_owner, 6100 + n, pos, 0, rot_deg, 0, 3);
}

void em089_efx_place(void *eff, const float *pos, const float *rot_rad)
{
    if (!em089_efx_alive(eff)) return;
    float q[4] __attribute__((aligned(16))) = {pos[0], pos[1], pos[2], 0.0f};
    efx_set_pos(eff, q, 0);
    void *xf = FIELD(void *, eff, EFX_XF);
    if (xf && rot_rad) {
        float r[4] __attribute__((aligned(16))) = {rot_rad[0], rot_rad[1], rot_rad[2], 0.0f};
        efx_set_rot(xf, r);
    }
}

/* ------------------------------------------------------------------ hooks */

void em089_efx_init(void)
{
    if (!em089_shell016_fx) em089_shell016_fx = em089_efx_shell016_fx;   /* no data relocs: set at run time */
}

static void efx_tick(void *self)
{
    s_efx_owner = self;
    em089_efx_init();
    s016_tick(self);
    aura_tick(self);
    tail_tick(self);
    em089_tar_hunters_tick(self);
}

int em089_efx_present(void) { return s_efx_owner != 0; }

void *em089_efx_post_model(void *self, uint32_t id, void *model, uint32_t area)
{
    uint32_t buf[REQ_SIZE / 4 + 4];
    void *req = (void *)(((uint32_t)buf + 15u) & ~15u);
    if (!self || !model) return 0;
    efx_req_ctor(req);
    FIELD(uint32_t, req, 0x8) = 3;                    /* 0x4a1ed8 */
    FIELD(uint8_t, req, 0xc) = (uint8_t)area;         /* 0x44ce38: the owner's area */
    FIELD(void *, req, REQ_TARGET) = model;
    FIELD(uint32_t, req, REQ_FLAGS) |= 2u;
    void *eff = efx_post_u(self, EFX_MODE_CODE, id, req);
    efx_req_dtor(req);
    static uint32_t s_n;
    if (++s_n <= 40) logf("gogport: em089 efx post id %u on model %x (area %u) -> %x", id, (uint32_t)model, area,
                          (uint32_t)eff);
    return eff;
}

/* ------------------------------------------------------------------ slot 75 */

/* 4U curve tables (rodata 0xff6ea0, 0xff769c..0xff78bc): (time, value) pairs, terminated by time < 0 */
static const float c_ff6ea0[] = {-1, -7};
static const float c_ff769c[] = {0, 30, 14, 44, 28, 30, -1, 30};
static const float c_ff76bc[] = {0, 30, 20, 40, 50, 40, 70, 30, -1, 30};
static const float c_ff76e4[] = {0, 30, 20, 60, 50, 60, 70, 30, -1, 30};
static const float c_ff770c[] = {0, 30, 20, 80, 70, 80, 110, 30, -1, 30};
static const float c_ff7734[] = {0, 30, 30, 50, 60, 50, 90, 30, -1, 30};
static const float c_ff775c[] = {0, 30, 20, 14, 50, 14, 70, 30, -1, 30};
static const float c_ff7784[] = {0, 30, 20, 4, 50, 4, 70, 30, -1, 30};
static const float c_ff77ac[] = {0, 30, 30, 0, 60, 0, 90, 30, -1, 30};
static const float c_ff77d4[] = {0, 7.7f, 20, -7, 50, -7, 70, 7.7f, -1, 7.7f};
static const float c_ff77fc[] = {0, 7.7f, 20, -40, 50, -40, 70, 7.7f, -1, 7.7f};
static const float c_ff7824[] = {0, 30, 66, 0, 70, -3, 86, -6, 120, -3, -1, -3};
static const float c_ff7854[] = {0, 7.7f, 20, -7, -1, -7};
static const float c_ff786c[] = {0, -7, 16, -7, 50, -24, 80, 7.7f, -1, 7.7f};
static const float c_ff7894[] = {0, 30, 20, 40, 40, 50, 60, 30, -1, 30};
static const float c_ff78bc[] = {0, 30, 40, -30, 60, -50, 110, 30, -1, 30};

static const float *s75_curve(uint32_t a4u)
{
    switch (a4u) {
    case 0xff6ea0: return c_ff6ea0;  case 0xff769c: return c_ff769c;  case 0xff76bc: return c_ff76bc;
    case 0xff76e4: return c_ff76e4;  case 0xff770c: return c_ff770c;  case 0xff7734: return c_ff7734;
    case 0xff775c: return c_ff775c;  case 0xff7784: return c_ff7784;  case 0xff77ac: return c_ff77ac;
    case 0xff77d4: return c_ff77d4;  case 0xff77fc: return c_ff77fc;  case 0xff7824: return c_ff7824;
    case 0xff7854: return c_ff7854;  case 0xff786c: return c_ff786c;  case 0xff7894: return c_ff7894;
    case 0xff78bc: return c_ff78bc;
    }
    if (s_log < 40) { s_log++; logf("gogport: em089 efx slot75: unknown 4U curve %x\n", a4u); }
    return 0;
}

/* 4U 0xaac930 */
static float curve_eval(const float *p, float t)
{
    for (;;) {
        if (p[0] < 0.0f) return p[1];
        if (t >= p[0] && p[2] >= t)
            return p[1] + (p[3] - p[1]) * ((t - p[0]) / (p[2] - p[0]));
        p += 2;
    }
}

typedef struct { float t1, t2, e1, e2; const float *c1, *c2; void *self; uint32_t state; } s75_t;
#define S75_SLOTS 4
static s75_t s_s75[S75_SLOTS];

static s75_t *s75_of(void *self)
{
    s75_t *free_slot = 0;
    for (int i = 0; i < S75_SLOTS; i++) {
        if (s_s75[i].self == self) return &s_s75[i];
        if (!s_s75[i].self && !free_slot) free_slot = &s_s75[i];
    }
    if (!free_slot) free_slot = &s_s75[0];   /* more than 4 Gogmazios: recycle (state of slot 0 lost) */
    for (uint32_t k = 0; k < sizeof *free_slot; k++) ((uint8_t *)free_slot)[k] = 0;   /* 4U work struct starts zeroed */
    free_slot->self = self;
    return free_slot;
}

void em089_slot75_state(void *self, uint32_t state)
{
    s75_t *st = s75_of(self);
    if (st->state != state && s_log < 40) { s_log++; logf("gogport: em089 efx slot75 state %u -> %u\n", st->state, state); }
    st->state = state;
}

static void mat_mul3(float *m, const float *r)   /* m (4x4, rows) = m * r (3x3 rotation in a 4x4) */
{
    float o[12];
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++)
            o[i * 4 + j] = m[i * 4] * r[j] + m[i * 4 + 1] * r[4 + j] + m[i * 4 + 2] * r[8 + j];
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) m[i * 4 + j] = o[i * 4 + j];
}

void em089_slot75(void *self)
{
    efx_tick(self);                           /* per-frame effect bookkeeping (slot 168 runs every frame) */
    s75_t *st = s75_of(self);
    /* 4U gate W+0x434 = 0x94741c(this, 1) = break count of part 1 (rows W+0x42e + 6i); GU 0x9d428(this, 1) =
     * rec+0x3bc + 12 * 1 (C, notes/api-map.md; written by the framework break counter 0x97ddc) */
    em089_slot75_state(self, FIELD(uint8_t, FIELD(uint8_t *, self, EN_RECORD), 0x3bc + 12 * 1));
    uint32_t r0 = 0, r1 = 0, r2 = 0, r4 = 0, r5 = 0, r6 = 0, r7 = 0, r8 = 0, r9 = 0, r10 = 0;
    float s0 = 0, s1 = 0, s2 = 0, s16 = 0, s17 = 0, s19 = 0, s20 = 0, s21 = 0, s22 = 0, s23 = 0, s24 = 0, s25 = 0,
          s26 = 0, s27 = 0;
    int32_t cmpa = 0, cmpb = 0;
    float fa = 0, fb = 0;
    (void)r2; (void)r4; (void)r5; (void)r9; (void)s21; (void)s22; (void)s23; (void)s25; (void)s26; (void)s27;
#include "em089_slot75.inc"
end:
    if (st->state != 1) return;   /* 4U: W+0x434 >= 2 or == 0 -> nothing */
    float dt = FIELD(float, self, EN_DT);
    float v1 = 7.7f, v2 = s20;    /* s20 = 30 (prologue constant) */
    if ((st->e1 > st->t1 || !(st->e1 >= 0.0f)) && st->c1) {
        st->t1 += dt;
        if (st->t1 > 999.0f) st->t1 = 999.0f;
        v1 = curve_eval(st->c1, st->t1);
    }
    if ((st->t2 < st->e2 || !(0.0f <= st->e2)) && st->c2) {
        st->t2 += dt;
        if (st->t2 > 999.0f) st->t2 = 999.0f;
        v2 = curve_eval(st->c2, st->t2);
    }
    float m[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
    float a = v1 * 6.2831855f * 0.0027777778f, c = cosf_gu(a), s = sinf_gu(a);
    const float rx[12] = {1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0};
    mat_mul3(m, rx);
    a = v2 * 6.2831855f * 0.0027777778f; c = cosf_gu(a); s = sinf_gu(a);
    const float ry[12] = {c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0};
    mat_mul3(m, ry);
    a = 0.0610865f; c = cosf_gu(a); s = sinf_gu(a);
    const float rz[12] = {c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0};
    mat_mul3(m, rz);
    uint8_t *ids = FIELD(uint8_t *, self, 0x498);
    uint8_t *joints = FIELD(uint8_t *, self, 0x494);
    if (!ids || !joints || ids[200] == 255) return;
    const float *t = (const float *)(joints + 160u * ids[200] + 0x80);
    m[12] = t[0]; m[13] = t[1]; m[14] = t[2]; m[15] = 1.0f;
    joint_set(self, 200, m);
}

/* review agent: the monster object is being deleted (em089.c slot 1). Drop every handle keyed to it WITHOUT touching
 * the effects (they may already be gone at quest teardown), so a later em089 at the same address (quest retry) does
 * not stop / poll stale effect pointers, and the stage posts do not use a dead owner. */
void em089_efx_forget(void *self)
{
    for (int i = 0; i < S016_SLOTS; i++)
        if (s_s016[i].owner == self)
            for (uint32_t k = 0; k < sizeof s_s016[i]; k++) ((uint8_t *)&s_s016[i])[k] = 0;
    for (int i = 0; i < AURA_SLOTS; i++)
        if (s_aura[i].self == self)
            for (uint32_t k = 0; k < sizeof s_aura[i]; k++) ((uint8_t *)&s_aura[i])[k] = 0;
    for (int i = 0; i < S75_SLOTS; i++)
        if (s_s75[i].self == self)
            for (uint32_t k = 0; k < sizeof s_s75[i]; k++) ((uint8_t *)&s_s75[i])[k] = 0;
    if (s_efx_owner == self) { s_efx_owner = 0; em089_tar_hunters_forget(); }
}
