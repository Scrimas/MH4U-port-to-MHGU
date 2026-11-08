/* em068_01_jet.c: Tidal Najarala's water jet, a literal translation of 4U uShell012 subtypes 52 / 53 and of the parts of 4U's handler 0x765810 (7/48-51
 * 7/62-65) GU dropped from its twin f861b0. GU kept the handler (motions 0x402 / 0x403, her turns, the aim at work+0x70), but no target choice among her
 * scales and no shot: she spat nothing. C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4. The class follows Stygian's em057_01_shell.c.
 *
 * 4U (C unless marked):
 * - Handler 0x765810(this, r9 = first shot's mode, r10 = second's, r8, [sp]): step 0: motion 0x402, target = W+0x218, 0x76c1bc(this, 0, r9). Frame 94: step 2, and
 *   with no scale chosen 0x92d0d4 + target = W+0x218 again. Frame 105: the shot (below). Frame 134, first shot only: step 3, W+0x145 = 1, motion 0x403, target =
 *   W+0x218, 0x76c1bc(this, 0, r10). Motion end in step 3: step 1, motion 0x402 from frame 90, so the second shot comes at frame 105 again.
 *   7/48 (1, 0) 7/49 (2, 2) 7/50 (0, 0) 7/51 (1, 1) 7/62 (1, 0) 7/63 (2, 2) 7/64 (0, 0) 7/65 (1, 1). f861b0 does all of it but 0x76c1bc (it writes "no scale": work+0x34
 *   = 4, work+0x80 = 0) and the shot.
 * - 0x76c1bc(this, 0, mode): work+0x2c = 4, work+0x70 = 0; mode 0 ends there. Else the first of her four scale shells that is out (0xc69ccc), of a water kind (4U 9..18:
 *   all she fires), not claimed (+0x2f1), within +-60 degrees of her yaw and over 1100 away (xz): target = its position, claimed, work+0x70 = 1; mode 2: the next
 *   other shell that is out and not claimed goes to work+0x2c, claimed too.
 * - The shot, 0x765af0..0x765e50: from joint 13 + (0, 100, 0). Target outside +-20 degrees of her yaw, or a scale nearer than 800: target = (0, 0, 3000) turned by her
 *   pitch and yaw, from her position. Velocity (0, 0, 37.5), x 1.25 when enraged (0x954e48), toward target + (0, 70, 0). Subtype 53 when this shot's mode is 2, else 52;
 *   post 0x661f6c(mgr, this, sub, &pos, &vel, &zero, u16 work+0x2c) -> event 12. Sound 218 at joint 13 (0x304c34).
 * - Init 0xc61058 / case 0xc61804: flight effect (69, 12) = em093_019, mask -1, on the shell; +0xf3 = 0, +0xf4 = the u16 (the second scale's index), +0x270 = area;
 *   the target hunter 0x92c960(owner, W+0x27a, W+0x27c) in her area -> +0x2ac = his index, +0x2ad = 1 (or the Palico 0x92c90c, +0x2ad = 2, not ported: S, the next
 *   step then flies straight on); life +620 = 300 (0x10291c8); arm 0x9ab120(records 0x1028958, volumes 0x1028904, record 36, 31, 2), group = +0x270.
 * - Per frame 0xc61b80: owner gone: slot off, state 3. Life out: state 2. Capsule end +0x120 = position, window +448 = 100. Then 0x9ab0a0 (position += velocity * dt),
 *   0xc63068, 0xc62e84 (sound 219 on the shell every 15 frames, table 0x10283a0), angles +0x110 / 114 / 118 from the velocity (0xc62514).
 * - 0xc63068: the slot's hit byte +0x16e != 255 (the attack connected): impact (69, 13) = em093_020, mask -1, at the position, sound 220 there; byte == 0 (log of 0.2.0:
 *   0 when it connected with one of her scales, 2 with a hunter, so a hunter does not turn it): a new leg: subtype 53, first leg, second scale still out -> at that scale;
 *   else the hunter of +0x2ac if there; else 1000 straight on over the ground below (0x2bb2a8). Target y + 70, the same speed, +0xf3++. So the jet bounces on until its life
 *   is out. Its effect scale z grows by 0.2 per frame after a bounce (not ported, GU's effect object not read: a deviation in looks).
 * - Her scales do not burst by her own rattle in 4U (C): all seven 0x769f80(this, 1, ..) signals (0x75ea08 0x75f3c8 0x75fdb0 0x761e28 0x762ecc 0x765144 0x765680) are behind em == 23, as GU's
 *   behind variant 0 (f7e90c f7fd1c f8046c f80b8c f838f8 f85af4 f85e58), and uShell015 detonates only on that signal (0xc69548). Blast 157 is for a Najarala beside her. A scale of hers ends by one
 *   hit, the jet's or a hunter's (+0x2ac = 1, 0xc681bc), or after 7200 frames (0xc68f40), with em093_004.
 * GU (C unless marked): the class framework as Stygian's. Family = GU's shell01 under its path (id 0x125, def file 0x8a78), HDS entry 3 / HTS group 3 = 4U record 36 /
 * volume 16 (build_em068_01_arc.py shell_data). Scale shell uShellEm068_sp_36: position +0x40, state byte +4 (1 flight, 2 planted, 3 rattle / blast, 4 end), hits left +0x1644
 * (4U +0x2ac; 0 -> state 4, 0x41aed0). The attack connects with a scale's body as in 4U (log of 0.2.0) and GU's scale counts that hit itself (+0x151e, 0x41aeb0).
 * Multiplayer: no net test in 4U's handler or class; every machine runs the handler and posts its own jet, scales are local too (as GU's). The target comes from the synced
 * target slot. All addresses through MAIN / FN; no fixed ranges. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

#define DTI_uShellEnemy    ((MtDTI *)MAIN(0x188ee88))
#define VT_uShellEnemy     MAIN(0x175b268)      /* object vtable address point */
#define DTIVT_uShellEnemy  MAIN(0x175b3bc)      /* DTI vtable address point */
#define VT_SLOTS           83
#define SIZE_uShellEnemy   0x15d0u
#define uShellEnemy_ctor   FN(ctor_t, 0x43b3f8)
#define uShellEnemy_dtor   FN(ctor_t, 0x43b488)
typedef int (*shell_setup_t)(void *self, void *param);
#define uShellEnemy_setup  FN(shell_setup_t, 0x43b4bc)
typedef void (*shell_fn_t)(void *self);
#define uShell_move        FN(shell_fn_t, 0x4a2304)
#define uShell_kill        FN(shell_fn_t, 0x4a247c)
typedef void (*shell_res_t)(void *self, void *res);
#define uShell_setResource FN(shell_res_t, 0x4a1c84)
typedef int (*selfInt_t)(void *self);
#define uShell_hasHitData  FN(selfInt_t, 0x4a2744)
typedef void *(*file_res_t)(void *unused, uint32_t file_id);
#define fileResource       FN(file_res_t, 0x152960)
typedef void (*unit_add_t)(void *mgr, uint32_t line, void *unit, uint32_t a, uint32_t b);
#define unitAdd            FN(unit_add_t, 0xc067ec)
typedef void (*shell_mgr_add_t)(void *mgr, void *shell);
#define shellMgrAdd        FN(shell_mgr_add_t, 0x48c6c8)
#define SHELL_MGR          (*(uint8_t **)MAIN(0x1892550))
#define UNIT_MGR           (*(void **)MAIN(0x2126f48))
#define DTI_PARAM          ((MtDTI *)MAIN(0x188cb88))   /* cSetupParamEmBase01 */
#define VT_PARAM           MAIN(0x17556a0)
#define SHELL_MAX_LIVE     144
#define SHELL_LIVE_LIST    0x6d8c
enum { SLOT_DEL = 1, SLOT_DTI = 5, SLOT_MOVE = 9, SLOT_KILL = 16, SLOT_SETUP = 79, SLOT_ARM = 80 };
#define SH_STATE    0xc         /* u32 unit state (& 7: 1 / 2 = alive) */
#define SH_DT       28          /* float frames this tick [4U +20] */
#define SH_POS      0x40        /* float[3] [4U +0x100] */
#define SH_ANGLES   0xfe8       /* u32[3] [4U +0x110] */
#define SH_POS2     0x1000      /* capsule end [4U +0x120] */
#define SH_AREA     0x1054      /* u8 area [4U +0x130] */
#define SH_PARAM    0x136c      /* the param the base set-up stored, owner at +0xc [4U +0x134] */
#define SH_ATK0     0x13a8      /* attack slot 0 [4U +360] */
#define ATK_HIT     0x6         /* u8 255 until the attack connects [4U +0x16e] */
#define ATK_F14     0x14        /* float passed to slot 80 */
#define ATK_TIME    0x60        /* float window length [4U +448] */

#define SHELL_ID_01    0x125u   /* GU's row of em068_00_shell01 */
#define SHELL_FILE_01  0x8a78u  /* its def */
#define HDS_JET        3u       /* build_em068_01_arc.py JET_HDS (asserted there) */
#define EFX_JET_FLIGHT 3300u    /* build_em068_01_arc.py JET_FX: em093_019, follows its unit */
#define EFX_JET_IMPACT 3301u    /* em093_020, placed once */
#define SND_MGR        0x1896f5c

/* her scale shells (uShellEm068_sp_36) */
#define SC_STATE    0x4         /* u8 1 flight, 2 planted, 3 rattle / blast, 4 end */

/* GU work (this+0xcac0) of f861b0 [4U work] */
#define WK_SECOND   0x34        /* u32 second scale's index, 4 = none [+0x2c] */
#define WK_TARGET   0x70        /* float[4] where she aims [+0x60] */
#define WK_HAS      0x80        /* u8 1 = the target is a scale [+0x70] */
#define REC_TO_HUNTER 0x1d0     /* float[3] target slot position rec+464 [W+0x218] */

#define EN_AREA     0x1054
#define PL_INDEX    0x1051      /* u8 player index */
#define PL_AREA     0x1054      /* u8 area */
#define PL_POS      0x40        /* float[3] position */

#define J_KIND      (SIZE_uShellEnemy + 0x00)   /* u8 52 / 53 [+0xfd] */
#define J_ARMED     (SIZE_uShellEnemy + 0x01)
#define J_HOPS      (SIZE_uShellEnemy + 0x02)   /* u8 legs flown [+0xf3] */
#define J_SECOND    (SIZE_uShellEnemy + 0x03)   /* u8 second scale's index [+0xf4] */
#define J_GROUP     (SIZE_uShellEnemy + 0x04)   /* u16 hit group [+0x270] */
#define J_SERIAL    (SIZE_uShellEnemy + 0x08)
#define J_HUNTER    (SIZE_uShellEnemy + 0x0c)   /* void * the target hunter at the post [+0x2ac] */
#define J_LIFE      (SIZE_uShellEnemy + 0x10)   /* float [+620] */
#define J_SNDT      (SIZE_uShellEnemy + 0x14)   /* float sound timer [+680] */
#define J_EFX       (SIZE_uShellEnemy + 0x18)   /* void * flight effect [+0x274] */
#define J_VEL       (SIZE_uShellEnemy + 0x1c)   /* float[3] [+0x140] */
#define J_POS       (SIZE_uShellEnemy + 0x28)   /* float[3] start position */
#define J_SIZE      (SIZE_uShellEnemy + 0x34)
#define J_LIFE0     300.0f      /* 0x10291c8, subtypes 52 / 53 */
#define J_SND_GAP   15.0f       /* table 0x10283a0 */
#define J_SPEED     37.5f       /* 0xc633a4, 0x765ccc */
#define J_RAGE      1.25f       /* 0xc633d4 */
#define J_LIFT      70.0f       /* 0xc63390 */
#define J_LINES     120u

#define V(self, off) (&FIELD(float, self, off))

#define rageOn      FN(selfInt_t, 0x8172c)      /* [0x954e48] */
typedef int (*atFrame_t)(void *self, float f);
#define atFrame     FN(atFrame_t, 0xb0a30)      /* [0x941dbc] */
typedef void *(*tgtHunter_t)(void *self, uint32_t sub, uint32_t param);
#define tgtHunter   FN(tgtHunter_t, 0xc2eb4)    /* [0x92c960] */
typedef int (*plAbsent_t)(uint32_t index);
#define plAbsent    FN(plAbsent_t, 0x49240)
typedef uint32_t (*map_segment_t)(void *mgr, const float *from, const float *to, uint32_t area, float *out, void *info, uint32_t mask, uint32_t flags);
#define mapSegment  FN(map_segment_t, 0x1838fc) /* [0x2b96e4] */
typedef uint32_t (*shell_flags_t)(void *self);
#define colFlags    FN(shell_flags_t, 0x4a2a8c) /* [0x9aad8c] */
#define COL_MGR     (*(void **)MAIN(0x21270e0))
typedef void *(*sndPos_t)(void *mgr, uint32_t id, void *owner, const float *pos, uint32_t area, int32_t m2);
#define sndPos      FN(sndPos_t, 0x4efb98)      /* [0x312484] */
typedef void *(*snd_obj_t)(void *mgr, uint32_t id, void *obj, int32_t joint, void *owner, uint32_t area, void *obj2);
#define sndObj      FN(snd_obj_t, 0x4efe58)     /* [0x304d3c] */
/* effects, as Stygian's em057_01_efx.c */
typedef void *(*efx_post_t)(void *self, uint32_t mode, uint32_t rec, void *req);
#define efx_post_u  FN(efx_post_t, 0x6ff74)
typedef void (*efx_stop_t)(void *eff, uint32_t kill);
#define efx_stop    FN(efx_stop_t, 0x32a400)
typedef void *(*unitEfxPost_t)(void *unit, void *pel, uint32_t mode, uint32_t id, void *req, void *tied);
#define unitEfxPost FN(unitEfxPost_t, 0x53b500)
typedef void (*efx_req_t)(void *req);
#define efx_req_ctor FN(efx_req_t, 0x40b10)
#define efx_req_dtor FN(efx_req_t, 0x40b50)
#define PEL_U_OBJ   0xb624
#define PEL_SE_OBJ  0xb628
#define REQ_SIZE    0x100u
#define REQ_FLAGS   0x1c
#define REQ_POS     0xc0
#define REQ_TARGET  0xd0
#define VT_ATTACH   0x130

static float vsqrt(float d)
{
    float r;
    __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(d));
    return r;
}

static uint32_t atan_u16(float y, float x)
{
    return (uint32_t)(int32_t)(atan2f_gu(y, x) * 10430.378f + 0.5f) & 0xffff;
}

static void sincos_u16(uint32_t a, float *s, float *c)
{
    float r = (float)(a & 0xffff) * 0x1.921fb6p-14f;
    *s = sinf_gu(r);
    *c = cosf_gu(r);
}

/* 4U 0xaad5b0 */
static void rot_y(float *v, uint32_t ang)
{
    float s, c, x = v[0], z = v[2];
    sincos_u16(ang, &s, &c);
    v[0] = c * x + s * z;
    v[2] = c * z - s * x;
}

static void copy3(float *d, const float *s) { d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; }

static int efx_alive(void *eff) { return eff && (FIELD(uint32_t, eff, 0xc) & 7) - 1 < 2; }
static void efx_finish(void *eff) { if (efx_alive(eff)) efx_stop(eff, 0); }

/* a point post: Stygian's sz_efx_world */
static void *efx_world(void *self, uint32_t id, const float *pos)
{
    uint32_t buf[REQ_SIZE / 4 + 4];
    void *req = (void *)(((uint32_t)buf + 15u) & ~15u), *eff;
    if (!self || !pos) return 0;
    if (FIELD(uint8_t, self, EN_ACT_CAT) == 12 && FIELD(uint8_t, self, EN_ACT_NUM) == 255) return 0;   /* 0x6ff94: dead */
    efx_req_ctor(req);
    FIELD(uint32_t, req, REQ_FLAGS) |= 1u;
    for (int i = 0; i < 3; i++) FIELD(float, req, REQ_POS + 4 * i) = pos[i];
    FIELD(float, req, REQ_POS + 12) = 0.0f;
    eff = unitEfxPost(self, FIELD(void *, self, PEL_U_OBJ), 2, id, req, FIELD(void *, self, PEL_SE_OBJ));
    efx_req_dtor(req);
    return eff;
}

/* an effect that rides the shell: Stygian's sz_efx_on */
static void *efx_on(void *self, uint32_t id, void *unit)
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
    FIELD(uint8_t, req, 0xc) = FIELD(uint8_t, unit, SH_AREA);
    eff = efx_post_u(self, 2, id, req);
    efx_req_dtor(req);
    return eff;
}

static void snd_at(void *self, uint32_t id, const float *pos, uint32_t area)
{
    void *mgr = *(void **)MAIN(SND_MGR);
    if (mgr && self && pos) sndPos(mgr, id, self, pos, area & 0xff, -2);
}

/* ---- the class */
static struct {
    MtDTI dti;
    uint32_t dti_vt[2 + 3];
    uint32_t vt[2 + VT_SLOTS];
    uint8_t registered;
} s_cls;
static uint32_t s_serial, s_lines;

static int line_ok(void)
{
    if (s_lines >= J_LINES) return 0;
    s_lines++;
    return 1;
}

static void *alloc_dti(MtDTI *dti, uint32_t size)
{
    void *a = get_allocator(dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    return alloc(a, size, 16, dti->w[7]);
}

static void *jet_new(MtDTI *dti)
{
    (void)dti;
    void *mem = alloc_dti(&s_cls.dti, J_SIZE);
    if (!mem) return 0;
    uShellEnemy_ctor(mem);
    FIELD(uint32_t, mem, 0) = (uint32_t)&s_cls.vt[2];
    for (uint32_t o = SIZE_uShellEnemy; o < J_SIZE; o++) FIELD(uint8_t, mem, o) = 0;
    return mem;
}

static MtDTI *jet_dti(void *self) { (void)self; return &s_cls.dti; }

static void jet_delete(void *self)
{
    void *h = FIELD(void *, self, J_EFX);
    efx_finish(h);
    FIELD(void *, self, J_EFX) = 0;
    uShellEnemy_dtor(self);
    void *a = get_allocator(&s_cls.dti);
    ((void (*)(void *, void *))(*(void ***)a)[0x34 / 4])(a, self);
}

/* slot 16 = 4U slot 24 0xc6362c (base kill; sound 219's stop 0x311814 not ported: it is a short sound repeated every 15 frames) */
static void jet_kill(void *self)
{
    void *h = FIELD(void *, self, J_EFX);
    uShell_kill(self);
    efx_finish(h);
    FIELD(void *, self, J_EFX) = 0;
}

static void jet_end(void *self, const char *why)
{
    if (line_ok())
        logf("tnport: jet %u end after %u leg(s): %s", FIELD(uint32_t, self, J_SERIAL), FIELD(uint8_t, self, J_HOPS), why);
    VCALL0(self, SLOT_KILL);
}

/* the velocity toward `to` + the lift: 4U 0x765cc8..0x765dbc = 0xc6338c..0xc634e0 */
static void aim_vel(void *owner, const float *from, const float *to, float *v)
{
    float dx = to[0] - from[0], dz = to[2] - from[2], dy = to[1] + J_LIFT - from[1], s, c;
    float speed = J_SPEED * (rageOn(owner) ? J_RAGE : 1.0f);
    uint32_t pitch = atan_u16(-dy, vsqrt(dx * dx + dz * dz)), yaw = atan_u16(dx, dz);
    sincos_u16(pitch, &s, &c);
    v[0] = 0.0f;
    v[1] = -s * speed;
    v[2] = c * speed;
    rot_y(v, yaw);
}

/* 0xc69ccc for a scale in her slots: out and alive */
static void *scale_at(void *owner, uint32_t i)
{
    uint8_t *work = FIELD(uint8_t *, owner, EN_WORK), *sc;
    if (!work || i >= 4) return 0;
    sc = FIELD(uint8_t *, work, 4 + 4 * i);
    if (!sc || (FIELD(uint32_t, sc, SH_STATE) & 7) - 1 >= 2) return 0;
    return (sc[SC_STATE] == 1 || sc[SC_STATE] == 2) ? sc : 0;
}

/* 4U 0xc63068's new leg */
static void jet_leg(void *self, void *owner)
{
    float *pos = V(self, SH_POS), t[3];
    uint32_t hops = FIELD(uint8_t, self, J_HOPS);
    void *next = 0, *pl = FIELD(void *, self, J_HUNTER);
    const char *what;
    if (FIELD(uint8_t, self, J_KIND) == 53 && !hops) next = scale_at(owner, FIELD(uint8_t, self, J_SECOND));
    if (next) {
        copy3(t, V(next, SH_POS));
        what = "scale";
    } else if (pl && !plAbsent(FIELD(uint8_t, pl, PL_INDEX)) && FIELD(uint8_t, pl, PL_AREA) == FIELD(uint8_t, self, SH_AREA)) {
        copy3(t, V(pl, PL_POS));
        what = "hunter";
    } else {                                                /* 0xc632e4: 1000 straight on, the ground below (0x2bb2a8) */
        float a[3], b[3], out[4] = {0, 0, 0, 0}, d[3] = {0.0f, 0.0f, 1000.0f};
        void *col = COL_MGR;
        rot_y(d, FIELD(uint32_t, self, SH_ANGLES + 4));
        for (int i = 0; i < 3; i++) t[i] = pos[i] + d[i];
        copy3(a, t);
        copy3(b, t);
        a[1] += 1000.0f;
        b[1] -= 1000.0f;
        if (col && mapSegment(col, a, b, FIELD(uint8_t, self, SH_AREA), out, 0, 16, colFlags(self))) t[1] = out[1];
        what = "ahead";
    }
    aim_vel(owner, pos, t, V(self, J_VEL));
    FIELD(uint8_t, self, J_HOPS) = (uint8_t)(hops + 1);
    if (line_ok())
        logf("tnport: jet %u leg %u to %s at %d %d %d", FIELD(uint32_t, self, J_SERIAL), hops + 1, what, (int32_t)t[0], (int32_t)t[1], (int32_t)t[2]);
}

static void jet_angles(void *self)                          /* 0xc62514 */
{
    const float *vel = V(self, J_VEL);
    FIELD(uint32_t, self, SH_ANGLES) = atan_u16(-vel[1], vsqrt(vel[0] * vel[0] + vel[2] * vel[2]));
    FIELD(uint32_t, self, SH_ANGLES + 4) = atan_u16(vel[0], vel[2]);
    FIELD(uint32_t, self, SH_ANGLES + 8) = atan_u16(-vel[0], vel[1]);
}

static int timer_out(void *self, float *t)                  /* 0x9aad4c */
{
    if (*t > 0.0f) {
        *t -= FIELD(float, self, SH_DT);
        if (*t > 0.0f) return 0;
    }
    *t = 0.0f;
    return 1;
}

/* slot 9 = 4U slot 23 0xc61b80, subtypes 52 / 53 */
static void jet_move(void *self)
{
    void *owner;
    float *pos = V(self, SH_POS), *vel = V(self, J_VEL), dt;
    uint32_t hit;
    uShell_move(self);
    if ((FIELD(uint32_t, self, SH_STATE) & 7) - 1 >= 2) return;
    owner = FIELD(void *, FIELD(uint8_t *, self, SH_PARAM), 0xc);
    dt = FIELD(float, self, SH_DT);
    if (timer_out(self, V(self, J_LIFE))) {
        jet_end(self, "life out");
        return;
    }
    copy3(V(self, SH_POS2), pos);
    FIELD(float, self, SH_ATK0 + ATK_TIME) = 100.0f;
    for (int i = 0; i < 3; i++) pos[i] += vel[i] * dt;
    hit = FIELD(uint8_t, self, SH_ATK0 + ATK_HIT);
    if (hit != 255) {
        void *h = efx_world(owner, EFX_JET_IMPACT, pos);
        snd_at(owner, 220, pos, FIELD(uint8_t, self, SH_AREA));
        if (line_ok())
            logf("tnport: jet %u impact (byte %u) at %d %d %d: efx %x", FIELD(uint32_t, self, J_SERIAL), hit,
                 (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2], (uint32_t)h);
        if (hit == 0) jet_leg(self, owner);
    }
    if (timer_out(self, V(self, J_SNDT))) {
        void *mgr = *(void **)MAIN(SND_MGR);
        if (mgr) sndObj(mgr, 219, self, -1, owner, FIELD(uint8_t, self, SH_AREA), self);
        FIELD(float, self, J_SNDT) = J_SND_GAP;
    }
    jet_angles(self);
}

/* slot 79: base set-up, then 4U init 0xc61058 / 0xc61804 / 0xc61a84 */
static int jet_setup(void *self, void *param)
{
    typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
    void *owner;
    float *pos = V(self, SH_POS);
    if (uShellEnemy_setup(self, param) != 1) return 0;
    owner = FIELD(void *, param, 0xc);
    copy3(pos, V(self, J_POS));
    copy3(V(self, SH_POS2), pos);
    jet_angles(self);
    FIELD(uint16_t, self, J_GROUP) = FIELD(uint8_t, self, SH_AREA);   /* 0xc61820: +0x270 = the area */
    FIELD(void *, self, J_EFX) = efx_on(owner, EFX_JET_FLIGHT, self);
    if (uShell_hasHitData(self) == 1) {
        ((arm_t)((*(uint32_t **)self)[SLOT_ARM]))(self, 0, (int32_t)HDS_JET, -1, 31, 2, FIELD(uint16_t, self, J_GROUP), FIELD(float, self, SH_ATK0 + ATK_F14));
        FIELD(uint8_t, self, J_ARMED) = 1;
    }
    FIELD(float, self, J_LIFE) = J_LIFE0;
    FIELD(float, self, J_SNDT) = 0.0f;
    if (line_ok())
        logf("tnport: jet %u kind %u at %d %d %d vel %d %d %d second %u hunter %x hit %u efx %x", FIELD(uint32_t, self, J_SERIAL), FIELD(uint8_t, self, J_KIND),
             (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2], (int32_t)V(self, J_VEL)[0], (int32_t)V(self, J_VEL)[1], (int32_t)V(self, J_VEL)[2],
             FIELD(uint8_t, self, J_SECOND), (uint32_t)FIELD(void *, self, J_HUNTER), FIELD(uint8_t, self, J_ARMED),
             (uint32_t)FIELD(void *, self, J_EFX));
    return 1;
}

static void jet_register(void)
{
    const uint32_t *bv = (const uint32_t *)VT_uShellEnemy, *bd = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + VT_SLOTS; i++) s_cls.vt[i] = bv[i - 2];
    s_cls.vt[2 + SLOT_DEL] = (uint32_t)jet_delete;
    s_cls.vt[2 + SLOT_DTI] = (uint32_t)jet_dti;
    s_cls.vt[2 + SLOT_MOVE] = (uint32_t)jet_move;
    s_cls.vt[2 + SLOT_SETUP] = (uint32_t)jet_setup;
    s_cls.vt[2 + SLOT_KILL] = (uint32_t)jet_kill;
    for (int i = 0; i < 2 + 3; i++) s_cls.dti_vt[i] = bd[i - 2];
    s_cls.dti_vt[2 + 2] = (uint32_t)jet_new;
    MtDTI_ctor(&s_cls.dti, "uShellEm068_01Jet", DTI_uShellEnemy, J_SIZE, 0, 0, 0);
    s_cls.dti.w[0] = (uint32_t)&s_cls.dti_vt[2];
    s_cls.registered = 1;
}

/* 4U 0x661f6c + ctor 0xc63a8c: GU's request tail as Stygian's sz_shell_param / sz_shell_start */
static void jet_post(void *owner, uint32_t kind, const float *pos, const float *vel, uint32_t second)
{
    uint8_t *mgr = SHELL_MGR, *param, *rec = FIELD(uint8_t *, owner, EN_RECORD);
    void *shell, *pl;
    uint32_t live = 0;
    if (!mgr) return;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, SH_STATE) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) return;
    if (!s_cls.registered) jet_register();
    param = alloc_dti(DTI_PARAM, 64);
    if (!param) return;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = SHELL_ID_01;
    FIELD(uint32_t, param, 8) = 0;
    FIELD(void *, param, 0xc) = owner;
    for (int i = 0; i < 3; i++) FIELD(float, param, 0x10 + 4 * i) = pos[i];
    for (int i = 0; i < 3; i++) FIELD(uint32_t, param, 0x30 + 4 * i) = FIELD(uint32_t, owner, SH_ANGLES + 4 * i);
    FIELD(uint16_t, param, 0x3c) = 0xffff;
    shell = jet_new(&s_cls.dti);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return;
    }
    FIELD(uint8_t, shell, J_KIND) = (uint8_t)kind;
    FIELD(uint8_t, shell, J_SECOND) = (uint8_t)second;
    copy3(V(shell, J_POS), pos);
    copy3(V(shell, J_VEL), vel);
    FIELD(uint32_t, shell, J_SERIAL) = ++s_serial;
    pl = tgtHunter(owner, rec[REC_TGT_KIND + 2], rec[REC_TGT_KIND + 4]);     /* 0xc61830 */
    if (pl && !plAbsent(FIELD(uint8_t, pl, PL_INDEX)) && FIELD(uint8_t, pl, PL_AREA) == FIELD(uint8_t, owner, EN_AREA)) FIELD(void *, shell, J_HUNTER) = pl;
    uShell_setResource(shell, fileResource(0, SHELL_FILE_01));
    if (((shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]))(shell, param) != 1) {
        if (line_ok()) logf("tnport: jet set-up failed");
        VCALL0(shell, SLOT_DEL);
        return;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(SHELL_MGR, shell);
}

/* ---- the handler's lost parts */
static void *s_claim_owner, *s_claim[4];                    /* 4U +0x2f1: the scales a jet was aimed at */

static int claimed(void *owner, uint32_t i, void *sc)
{
    if (owner != s_claim_owner) {
        s_claim_owner = owner;
        for (int k = 0; k < 4; k++) s_claim[k] = 0;
    }
    return s_claim[i] == sc;
}

/* 4U 0x76c1bc(this, 0, mode). A scale is hit once: its pointer stays claimed until the slot holds another shell */
static void choose(void *self, uint32_t mode)
{
    uint8_t *work = FIELD(uint8_t *, self, EN_WORK), *rec = FIELD(uint8_t *, self, EN_RECORD);
    const float *me = &FIELD(float, rec, REC_POS_X);
    FIELD(uint32_t, work, WK_SECOND) = 4;
    FIELD(uint8_t, work, WK_HAS) = 0;
    if (!mode) return;
    for (uint32_t i = 0; i < 4; i++) {
        uint8_t *sc = scale_at(self, i);
        if (!sc || claimed(self, i, sc)) continue;
        float dx = FIELD(float, sc, SH_POS) - me[0], dz = FIELD(float, sc, SH_POS + 8) - me[2];
        uint32_t d = (atan_u16(dx, dz) - FIELD(uint32_t, rec, REC_YAW)) & 0xffff;
        if (((d - 0x2aabu) & 0xffffffffu) <= 0xaaaau) continue;          /* outside +-60 degrees */
        if (dx * dx + dz * dz <= 1100.0f * 1100.0f) continue;
        for (int k = 0; k < 3; k++) FIELD(float, work, WK_TARGET + 4 * k) = FIELD(float, sc, SH_POS + 4 * k);
        FIELD(float, work, WK_TARGET + 12) = 0.0f;
        s_claim[i] = sc;
        FIELD(uint8_t, work, WK_HAS) = 1;
        if (mode == 2) {
            for (uint32_t j = 0; j < 4; j++) {
                uint8_t *b = j == i ? 0 : scale_at(self, j);
                if (!b || claimed(self, j, b)) continue;
                FIELD(uint32_t, work, WK_SECOND) = j;
                s_claim[j] = b;
                break;
            }
        }
        if (line_ok()) logf("tnport: spit aims at scale %u (%x), second %u, mode %u", i, (uint32_t)sc, FIELD(uint32_t, work, WK_SECOND), mode);
        return;
    }
}

/* 4U 0x765af0..0x765e50 */
static void shoot(void *self, uint32_t mode)
{
    uint8_t *work = FIELD(uint8_t *, self, EN_WORK), *rec = FIELD(uint8_t *, self, EN_RECORD);
    float pos[4] = {0, 0, 0, 0}, t[3], v[3];
    uint32_t yaw = FIELD(uint32_t, rec, REC_YAW) & 0xffff, d, has = FIELD(uint8_t, work, WK_HAS), second = FIELD(uint32_t, work, WK_SECOND);
    jointPos(self, 13, pos);
    pos[1] += 100.0f;
    copy3(t, &FIELD(float, work, WK_TARGET));
    d = (atan_u16(t[0] - pos[0], t[2] - pos[2]) - yaw) & 0xffff;
    {
        float dx = t[0] - pos[0], dy = t[1] - pos[1], dz = t[2] - pos[2];
        int forward = (d - 0xe39u) <= 0xe38eu;                           /* outside +-20 degrees */
        if (!forward && has && dx * dx + dy * dy + dz * dz <= 800.0f * 800.0f) forward = 1;
        if (forward) {                                                   /* (0, 0, 3000) by her pitch, then yaw */
            float s, c, f[3] = {0.0f, 0.0f, 3000.0f};
            sincos_u16(FIELD(uint32_t, rec, REC_ANGLES), &s, &c);
            f[1] = -s * 3000.0f;
            f[2] = c * 3000.0f;
            rot_y(f, yaw);
            for (int i = 0; i < 3; i++) t[i] = f[i] + FIELD(float, rec, REC_POS_X + 4 * i);
        }
    }
    aim_vel(self, pos, t, v);
    jet_post(self, mode == 2 ? 53 : 52, pos, v, second);
    snd_at(self, 218, pos, FIELD(uint8_t, self, EN_AREA));
}

/* every frame of her actions, before GU's handler (slot 125 hook, em068_01.c) */
void em068_01_jet_frame(void *self)
{
    static const struct { uint8_t num, first, second; } rows[] = {
        {48, 1, 0}, {49, 2, 2}, {50, 0, 0}, {51, 1, 1}, {62, 1, 0}, {63, 2, 2}, {64, 0, 0}, {65, 1, 1}};
    static void *s_self;
    static uint32_t s_act;
    static uint8_t s_done;
    uint8_t *rec;
    uint32_t act, step, shots;
    int row = -1;
    if (FIELD(uint8_t, self, EN_ACT_CAT) != 7) return;
    for (uint32_t i = 0; i < sizeof rows / sizeof rows[0]; i++)
        if (rows[i].num == FIELD(uint8_t, self, EN_ACT_NUM)) row = (int)i;
    if (row < 0) return;
    rec = FIELD(uint8_t *, self, EN_RECORD);
    if (!rec) return;
    act = FIELD(uint16_t, self, EN_ACT_SERIAL);
    if (s_self != self || s_act != act) {
        s_self = self;
        s_act = act;
        s_done = 0;
    }
    step = rec[REC_STEP0];
    shots = rec[REC_STEP1];
    /* GU's step 0 and its 2 -> 3 write "no scale" (header): the choice comes one frame later */
    if (step >= 1 && !(s_done & 1)) {
        s_done |= 1;
        choose(self, rows[row].first);
    }
    if (step == 3 && !(s_done & 2)) {
        s_done |= 2;
        choose(self, rows[row].second);
    }
    if (curMotion(self) == 0x402 && atFrame(self, 105.0f)) shoot(self, shots ? rows[row].second : rows[row].first);
}
