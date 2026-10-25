/* dala_meteor.c: Dalamadur's meteor showers (goal D5). Literal translation of
 *  (A) the head's meteor machine: set-up 4U 0x77274c (called from slot 47, em090_act.c meteors()), per frame 4U slot
 *      40 0x76da88 from 0x76db4c to 0x76de94 (GU slot 119, em090_state_frame), reset 0x772ac4;
 *  (B) the meteor shell 4U uShell029 (DTI 0x10bbe70, 648 B, vtable 0xe6df3c: slot 1 dtor 0xc7daf0, 5 getDTI
 *      0xd0f810, 22 init 0xc7cedc, 23 per frame 0xc7d268, 24 kill 0xc7da24; ctor 0xc7da60 copies the 44-byte type-29
 *      request of 0x66242c; the vtable has 26 slots, 26.. belong to the next class) as a GU uShellEnemy subclass
 *      built like em089_shell.c (Gogmazios' uShell050): our copy of the GU request 0x48c4f0, param, resource,
 *      attack slot 0 from the resource's HDS, map segment test, kill through slot 16.
 * 4U frames / timers / numbers unchanged (GU's timerDown and the shells' this+28 time scale scale them).
 *
 * Machine data (C): patterns 0xfdc934 {u8 count, ptr to {f32 x, f32 z}} x 6 and the kind 4..9 centres 0xfdc964
 * {u16 n, (x, z) first n meteors, (x, z) the rest} x 6; both filled by the static init 0xd25968 (emulated:
 * scratchpad e/helper3/emu_init.py). Patterns 0..2 are offsets around the centre, 3..5 absolute points (kind 3's
 * second meteor, pattern + 3). The random is 4U W+0x1d2 = GU this+0x73e8 (EN_ACT_SERIAL): 4U setAction writes it
 * with the RNG step 0x2b568c and sends it in the action packet (0x90f198 / 0x90f244 / 0x90f70c; receiver 0x924590
 * copies packet +74 back), GU setAction the same with 0x496f0 -> 0x3f8344 (0x76560 / packet this+0x73ee / 0x76878,
 * before the action-start slot 129 at 0x768ec): the action's random u16, equal on every machine (C; Gogmazios
 * reads it the same way, em089_act.c shell_rand). 0x2ff2b4 = __aeabi_uidivmod, the remainder (r1) is used.
 *
 * Multiplayer: 4U posts on every machine (no W+0x1d9 / controller test in 0x76db4c..0x76de94; the shell manager
 * 0x660e88 only creates the shell locally, 0x660fe0 unit add, no net send). GU replays the action on every machine,
 * so slot 129 arms the machine everywhere and each machine drops its own meteors, as in 4U. Equal on all machines:
 * kind 4..9 centres, patterns, the action random; per machine: target slot 0 (4U W+0x218 = GU rec+464, read
 * locally in both games) for kinds 1..3, the listener point of sound 210.
 *
 * Attached effect (4U 0xc0a2f8(effmgr, group 35 / Shah 81, element 3) = em024_003 / em110_003, 0xc08060 mask -1,
 * vt+0x48 attach to the shell): PEL record DALA_EFX_METEOR posted on the shell at the init (dala_efx_meteor); the
 * effect reads its target every frame, so the shell outlives it as em089_shell.c does: slot 16 stops the effect
 * and keeps the shell (attack slots off) until the effect is dead, forced after EFX_DIE_MAX frames; the dtor kills
 * a live effect at once (4U slot 24 0xc7da24 releases +0x274 / +0x278 with 0xc470dc).
 * The impact blast (0x663220 -> 0x661c5c, type 3, subtypes 113 / 126 / Shah 160 / 162) is dala_shell003.c's
 * uShellDala003; the mining meteor's scale (kinds 3 / 6: 0x6626e8 -> type 38 uShell038, its gathering point 0x9357ec)
 * is dala_shell038.c's uShellDala038.
 * Deviation: 4U kills the meteor in its init when the effect file is missing (0xc7cf1c); here a failed post means
 * the port's PEL record is missing (dala_efx.c), so the meteor always lives.
 * Resource (hit data): Dalamadur's own shell family DALA_SHELL_FILE (dala_shell.h; build_dalamadur_arc.py
 * shell_family, replacing Kushala's 0x8a02 placeholder with its 80 / 100 powers): HDS entries 0..5 = the uShell029
 * inline records 0x102dff0 + 40 * i (kinds 0..7 use {0, 1, 2, 2, 3, 4, 4, 5}; records 4 / 5 are byte-identical to
 * 2 / 3: power 60 / 45, type 2, s16 +2 = 99, byte 0x19 = 2); HTS groups 0..2 = the volume table 0x102dfe0: volume 2
 * = 0x102df8c, one sphere on bone 1001, radius 270.0 (volumes 0 / 1: radius 225 / 100). */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_meteor.h"
#include "dala_efx.h"
#include "dala_shell.h"   /* the family file, HDS entries, the blast shell */

/* ================================================================== (A) the head's machine ================== */

/* head work [this+0x8d88] (F_WORK) fields of the machine (4U offsets) */
#define W_MT_KIND   0x14   /* u8 shower kind (0 = off) */
#define W_MT_POS    0x18   /* float[4] centre (kinds 1..3: target slot 0 at the set-up; 4..9: the current centre) */
#define W_MT_RAND   0x28   /* u16 the action random 4U W+0x1d2 at the set-up */
#define W_MT_COUNT  0x2a   /* u8 meteors posted */
#define W_MT_TIME   0x2c   /* float shower duration (counted after the delay) */
#define W_MT_DELAY  0x30   /* float delay before the first meteor */
#define W_MT_GAP    0x34   /* float frames to the next meteor */
#define W_MT_PAT    0x38   /* u8 pattern 0..2 */
#define W_MT_IDX    0x39   /* u8 next offset in the pattern */
#define W_MT_COOL   0x3c   /* float kind-3 cooldown (7200), counted every frame */
#define MW(T, self, off) DALA_WORK(T, self, off)

typedef struct { float x, z; } xz_t;
/* 0x10b6590 / 0x10b6630 / 0x10b66c8: offsets around the centre */
static const xz_t k_pat0[20] = {
    {-480, -720}, {-400, 10}, {780, -340}, {500, -1020}, {1000, 300}, {280, 50}, {60, -1250}, {-860, -600},
    {-140, -610}, {-400, -380}, {600, 840}, {-30, -30}, {300, -460}, {610, 30}, {-860, 110}, {790, 640},
    {-200, 1200}, {-580, 1100}, {200, 800}, {1100, 600},
};
static const xz_t k_pat1[19] = {
    {940, -560}, {550, 1180}, {-1000, 370}, {-310, -600}, {40, 750}, {-240, 1400}, {610, -1050}, {4, -1000},
    {-1000, -300}, {-560, -1110}, {1170, -50}, {1060, 530}, {-500, 240}, {560, -80}, {-170, -1260}, {-30, -35},
    {1160, -270}, {740, -1000}, {90, -1270},
};
static const xz_t k_pat2[15] = {
    {170, -100}, {660, 20}, {540, 410}, {710, -610}, {-700, -340}, {950, 100}, {50, 900}, {-330, 420}, {-280, -210},
    {590, -1000}, {40, 20}, {120, -960}, {340, -710}, {200, 400}, {360, -110},
};
/* 0x10b6740 / 0x10b6758 / 0x10b6770: absolute points of kind 3's second meteor */
static const xz_t k_pat3[3] = {{-2112, 2087}, {-485, -92}, {-1646, 3188}};
static const xz_t k_pat4[3] = {{1551, 1167}, {-485, -92}, {799, -777}};
static const xz_t k_pat5[2] = {{751, 2981}, {-757, 3738}};
static const struct { uint8_t n; const xz_t *p; } k_pat[6] = {   /* 0xfdc934 */
    {20, k_pat0}, {19, k_pat1}, {15, k_pat2}, {3, k_pat3}, {3, k_pat4}, {2, k_pat5},
};
/* 0xfdc964: kinds 4..9, the first n meteors around c1, the rest around c2 */
static const struct { uint16_t n; xz_t c1, c2; } k_area[6] = {
    {11, {-1977, 2269}, {796, 472}},  {10, {796, 472}, {-503, 3651}},   {19, {-503, 3651}, {-1977, 2269}},
    {19, {-1977, 2269}, {-503, 3651}}, {11, {796, 472}, {-1977, 2269}}, {12, {-503, 3651}, {796, 472}},
};

static uint32_t s_mlog;

/* 4U 0x772ac4 */
void dala_meteor_reset(void *self)
{
    MW(uint8_t, self, W_MT_KIND) = 0;
    for (int i = 0; i < 4; i++) MW(float, self, W_MT_POS + 4 * i) = 0.0f;   /* zero vector 0x10e6378, w 0 */
    MW(uint16_t, self, W_MT_RAND) = 0;
    MW(uint8_t, self, W_MT_COUNT) = 0;
    MW(float, self, W_MT_TIME) = 0.0f;
    MW(float, self, W_MT_DELAY) = 0.0f;
    MW(float, self, W_MT_GAP) = 0.0f;
    MW(uint8_t, self, W_MT_PAT) = 0;
    MW(uint8_t, self, W_MT_IDX) = 0;
}

/* 4U 0x77274c */
void dala_meteor_set(void *self, uint32_t kind, uint32_t pattern, float duration, float delay)
{
    if (kind == 3 && MW(float, self, W_MT_COOL) > 0.0f) kind = 2;
    MW(uint8_t, self, W_MT_KIND) = (uint8_t)kind;
    const float *t = (const float *)(REC(self) + REC_TARGET);    /* target slot 0 W+0x218 = GU rec+464 */
    MW(float, self, W_MT_POS) = t[0];
    MW(float, self, W_MT_POS + 4) = t[1];
    MW(float, self, W_MT_POS + 8) = t[2];
    MW(float, self, W_MT_POS + 12) = 0.0f;
    uint32_t r = FIELD(uint16_t, self, EN_ACT_SERIAL);           /* 4U W+0x1d2 */
    MW(uint16_t, self, W_MT_RAND) = (uint16_t)r;
    MW(uint8_t, self, W_MT_COUNT) = 0;
    MW(float, self, W_MT_TIME) = duration;
    MW(float, self, W_MT_DELAY) = delay;
    MW(float, self, W_MT_GAP) = 0.0f;
    MW(uint8_t, self, W_MT_PAT) = (uint8_t)pattern;
    MW(uint8_t, self, W_MT_IDX) = pattern < 6 ? (uint8_t)(r % k_pat[pattern].n) : 0;   /* 0x2ff2b4 remainder */
    if (MW(uint8_t, self, W_MT_KIND) == 3) MW(float, self, W_MT_COOL) = 7200.0f;
    if (++s_mlog <= 40)
        logf("dalaport: %x meteors set kind %u (asked %u) pattern %u time %d delay %d rand %u idx %u at %d %d %d", (uint32_t)self,
             MW(uint8_t, self, W_MT_KIND), kind, pattern, (int32_t)duration, (int32_t)delay, r,
             MW(uint8_t, self, W_MT_IDX), (int32_t)t[0], (int32_t)t[1], (int32_t)t[2]);
}

/* the pattern offset at work+0x39 around the centre, y 10000, then the index moves on (0x76dc40 / 0x76dcf0) */
static void pick_offset(void *self, float *pos)
{
    uint32_t p = MW(uint8_t, self, W_MT_PAT), i = MW(uint8_t, self, W_MT_IDX);
    const xz_t *o = &k_pat[p].p[i];
    pos[0] = MW(float, self, W_MT_POS) + o->x;
    pos[1] = 10000.0f;
    pos[2] = MW(float, self, W_MT_POS + 8) + o->z;
    pos[3] = 0.0f;
    i = (i + 1) & 255;
    MW(uint8_t, self, W_MT_IDX) = (uint8_t)(i < k_pat[p].n ? i : 0);
}

/* 4U slot 40 0x76db4c..0x76de94 */
void dala_meteor_frame(void *self)
{
    uint32_t kind = MW(uint8_t, self, W_MT_KIND);
    if (kind && timerDown(self, &MW(float, self, W_MT_DELAY), 1.0f)) {
        if (timerDown(self, &MW(float, self, W_MT_GAP), 1.0f)) {
            uint32_t n = MW(uint8_t, self, W_MT_COUNT), p = MW(uint8_t, self, W_MT_PAT);
            float pos[4] = {0.0f, 0.0f, 0.0f, 0.0f};
            int ok = p < 3 && kind <= 9;            /* port guard: 4U only arms patterns 0..2 and kinds 1..9 */
            if (!ok) {
                if (++s_mlog <= 40) logf("dalaport: %x meteors: kind %u pattern %u out of the 4U tables", (uint32_t)self,
                                         kind, p);
            } else if (kind == 1 || kind == 2 || kind == 3) {
                if (n == 0) {                       /* 0x76dc0c: right above the centre */
                    pos[0] = MW(float, self, W_MT_POS);
                    pos[1] = MW(float, self, W_MT_POS + 4) + 9000.0f;
                    pos[2] = MW(float, self, W_MT_POS + 8);
                } else if (kind == 3 && n == 1) {   /* 0x76dca4: absolute point of pattern + 3, by the action random */
                    uint32_t r = MW(uint16_t, self, W_MT_RAND) % k_pat[p + 3].n;
                    pos[0] = k_pat[p + 3].p[r].x;
                    pos[1] = 10000.0f;
                    pos[2] = k_pat[p + 3].p[r].z;
                } else pick_offset(self, pos);
            } else {                                /* kinds 4..9: centre c1 for the first n meteors, then c2 */
                const xz_t *c = k_area[kind - 4].n > n ? &k_area[kind - 4].c1 : &k_area[kind - 4].c2;
                MW(float, self, W_MT_POS) = c->x;
                MW(float, self, W_MT_POS + 4) = 0.0f;
                MW(float, self, W_MT_POS + 8) = c->z;
                MW(float, self, W_MT_POS + 12) = 0.0f;
                pick_offset(self, pos);
            }
            if (ok) {
                uint32_t shah = FIELD(uint8_t, self, EN_VARIANT) != 0;   /* 4U W+0x1c0 != 24 */
                uint32_t sub = kind == 2 ? (shah ? 5 : 2) : kind == 3 ? (n == 1 ? (shah ? 6 : 3) : (shah ? 5 : 2))
                                                                      : (shah ? 7 : 4);
                dala_meteor_post(self, sub, pos, FIELD(uint8_t, self, 0x1054), 0xffff, 0.0f);   /* area W+0x14c */
                MW(uint8_t, self, W_MT_COUNT) = (uint8_t)(n + 1);
            }
            MW(float, self, W_MT_GAP) = (kind == 2 || kind == 3) ? 80.0f : (kind >= 4 && kind <= 9) ? 90.0f : 150.0f;
        }
        if (timerDown(self, &MW(float, self, W_MT_TIME), 1.0f)) {
            if (++s_mlog <= 40) logf("dalaport: %x meteors end kind %u after %u meteors", (uint32_t)self, kind,
                                     MW(uint8_t, self, W_MT_COUNT));
            dala_meteor_reset(self);
        }
    }
    timerDown(self, &MW(float, self, W_MT_COOL), 1.0f);
    /* 0x76de94..0x76df08 (Shah only, W+0x1c0 == 110): effect slots work+120 + 48 i timers -> 0x775f2c (goal D8) */
}

/* ================================================================== (B) the meteor shell (4U uShell029) ====== */

/* ---- GU shell framework (main offsets; evidence in em089_shell.c / Gogmazios' port-checklist.md) ---- */
#define DTI_uShellEnemy      ((MtDTI *)MAIN(0x188ee88))
#define VT_uShellEnemy       MAIN(0x175b268)
#define VT_uShellEnemy_SLOTS 83
#define DTIVT_uShellEnemy    MAIN(0x175b3bc)
#define SIZE_uShellEnemy     0x15d0u
#define uShellEnemy_ctor     FN(ctor_t, 0x43b3f8)
#define uShellEnemy_dtor     FN(ctor_t, 0x43b488)
typedef int (*shell_setup_t)(void *self, void *param);
#define uShellEnemy_setup    FN(shell_setup_t, 0x43b4bc)   /* slot 79 base */
typedef void (*shell_fn_t)(void *self);
#define uShell_move          FN(shell_fn_t, 0x4a2304)      /* slot 9 base: kill when the owner is gone [0x917620] */
#define uShell_kill          FN(shell_fn_t, 0x4a247c)      /* slot 16 base: attack slots off, unit kill (em089_shell.c) */
typedef void (*shell_res_t)(void *self, void *res);
#define uShell_setResource   FN(shell_res_t, 0x4a1c84)
typedef int (*shell_hashit_t)(void *self);
#define uShell_hasHitData    FN(shell_hashit_t, 0x4a2744)
typedef uint32_t (*shell_flags_t)(void *self);
#define uShell_colFlags      FN(shell_flags_t, 0x4a2a8c)   /* = 4U 0x9aad8c (64 | flag bit << 24 / << 18) */
typedef void *(*file_res_t)(void *unused, uint32_t file_id);
#define fileResource         FN(file_res_t, 0x152960)
typedef void (*unit_add_t)(void *mgr, uint32_t line, void *unit, uint32_t a, uint32_t b);
#define unitAdd              FN(unit_add_t, 0xc067ec)      /* = 4U 0x64608c(mgr, 18, shell) */
typedef void (*shell_mgr_add_t)(void *mgr, void *shell);
#define shellMgrAdd          FN(shell_mgr_add_t, 0x48c6c8)
typedef uint32_t (*map_segment_t)(void *mgr, const float *from, const float *to, uint32_t area, float *out,
                                  void *info, uint32_t mask, uint32_t flags);
#define mapSegment           FN(map_segment_t, 0x1838fc)   /* = 4U 0x2b96e4 */
#define SHELL_MGR            (*(uint8_t **)MAIN(0x1892550))
#define UNIT_MGR             (*(void **)MAIN(0x2126f48))
#define COL_MGR              (*(void **)MAIN(0x21270e0))
#define DTI_PARAM            ((MtDTI *)MAIN(0x188cb88))
#define VT_PARAM             MAIN(0x17556a0)
#define ZERO_VEC             MAIN(0x191e850)
/* sounds: 4U 0x304d3c (follows an object) = GU 0x4efe58, 4U 0x312484 (at a point) = GU 0x4efb98, mgr 4U *0xfccd6c =
 * GU *(main + 0x1896f5c) (C, em089_snd.h); ids = the 4U request ids, as em090_act7.c */
typedef void *(*snd_obj_t)(void *mgr, uint32_t id, void *obj, int32_t joint, void *owner, uint32_t area, void *obj2);
typedef void *(*snd_pos_t)(void *mgr, uint32_t id, void *owner, const float *pos, uint32_t area, int32_t m2);
#define snd_req_obj          FN(snd_obj_t, 0x4efe58)
#define snd_req_pos          FN(snd_pos_t, 0x4efb98)
#define SND_MGR              (*(void **)MAIN(0x1896f5c))

#define SHELL_MAX_LIVE   144
#define SHELL_LIVE_LIST  0x6d8c
#define SLOT_KILL        16
#define SLOT_MOVE        9
#define SLOT_SETUP       79
#define SLOT_ARM_ATTACK  80
#define SH_POS           0x40     /* float x, y, z [4U +0x100] */
#define SH_POS2          0x1000   /* bone-1001 hit capsule second point (= previous position, 4U +0x120) */
#define SH_ANGLES        0xfe8    /* u32 x, y, z [4U +0x110 / +0x114 / +0x118] */
#define SH_DT            28       /* float time scale [4U +20] */
#define SH_AREA          0x1054   /* u8 area [4U +0x130] */
#define SH_ATK0          0x13a8   /* attack slot 0, 184 B [4U +360, 0x9a9624's slot] */
#define ATK_F14          0x14     /* float passed to slot 80 (EmBase01 does the same) */
/* attack slot float loaded from the attack record's s16 +2: 4U slot +88 (0xb7015c), GU slot +96 (0x168ef0) (C) */
#define ATK_TIME_4U88    0x60

/* Dalamadur's own shell family (dala_shell.h; was Kushala's 0x8a02 placeholder, see the header) */
#define DALA_METEOR_FILE DALA_SHELL_FILE
#define DALA_METEOR_ID   DALA_SHELL_ID

/* ---- our fields after the uShellEnemy object (4U uShell029 offset in brackets) ---- */
#define S_KIND    (SIZE_uShellEnemy + 0x00)   /* u8 kind 0..7 [+0xfd] */
#define S_STATE   (SIZE_uShellEnemy + 0x01)   /* u8 0 new, 1 falling, 2 done [+0xf1] */
#define S_ARMED   (SIZE_uShellEnemy + 0x02)   /* u8 attack slot armed */
#define S_AREA    (SIZE_uShellEnemy + 0x03)   /* u8 request area [+0x130] (the owner's W+0x14c) */
#define S_GROUP   (SIZE_uShellEnemy + 0x04)   /* u16 request hit group, 0xffff = none [+0x270] */
#define S_LIFE    (SIZE_uShellEnemy + 0x08)   /* float lifetime [+0x26c] */
#define S_SND_T   (SIZE_uShellEnemy + 0x0c)   /* float falling-sound timer [+0x27c] */
#define S_ARM_T   (SIZE_uShellEnemy + 0x10)   /* float attack arm delay (request f32) [+0x280] */
#define S_VEL     (SIZE_uShellEnemy + 0x14)   /* float[3] velocity [+0x140] */
#define S_ACC     (SIZE_uShellEnemy + 0x20)   /* float[3] acceleration [+0x150] */
#define S_PREV    (SIZE_uShellEnemy + 0x2c)   /* float[3] previous position [+0x120] */
#define S_START   (SIZE_uShellEnemy + 0x38)   /* float[3] request position [+0x100 at the ctor] */
#define S_SERIAL  (SIZE_uShellEnemy + 0x44)   /* u32 spawn number (log) */
#define S_EFX     (SIZE_uShellEnemy + 0x48)   /* void * attached effect [4U +0x274] (dropped when dead) */
#define S_DIE_T   (SIZE_uShellEnemy + 0x4c)   /* float frames spent waiting for the effect to end */
#define S_DYING   (SIZE_uShellEnemy + 0x50)   /* u8 1 = killed, waiting for the effect */
#define SHELL_SIZE (SIZE_uShellEnemy + 0x60)
#define EFX_DIE_MAX 300.0f                    /* em089_shell.c's bound before a forced stop */
#define METEOR_KINDS 8

#define VEC(p, off) (&FIELD(float, p, off))

/* ---- 4U uShell029 per-kind data (C) ---- */
/* velocity / acceleration: bss 0x10bbdb0 / 0x10bbe10 written by the static init 0xd37f20 (emulated) */
static const float k_vel_y[METEOR_KINDS] = {-120.0f, -40.0f, -90.0f, -90.0f, -70.0f, -90.0f, -90.0f, -70.0f};
static const float k_acc_y[METEOR_KINDS] = {0.0f, -1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
/* lifetime 0x102e104: 180.0 for every kind */
#define METEOR_LIFE 180.0f
/* effect 0x102e124 {group, element}: kinds 2..4 (35, 3), Shah 5..7 (81, 3); kinds 0 / 1 (60, 14) / (40, 26) */
static const uint8_t k_efx[METEOR_KINDS][2] = {{60, 14}, {40, 26}, {35, 3}, {35, 3}, {35, 3}, {81, 3}, {81, 3}, {81, 3}};
/* attack record 0x102e0e0 (u32) = {0, 1, 2, 2, 3, 4, 4, 5}: Dalamadur's family has the six records as HDS entries
 * DALA_HDS_METEOR + record (build_dalamadur_arc.py; records 4 / 5 are byte-identical to 2 / 3) */
static const uint8_t k_hds[METEOR_KINDS] = {0, 1, 2, 2, 3, 4, 4, 5};

static MtDTI s_dti;
static uint32_t s_dti_vt[2 + 3];
static uint32_t s_vt[2 + VT_uShellEnemy_SLOTS];
static uint8_t s_registered;
static uint32_t s_serial;

static void stub_once(void *owner, uint32_t *n, const char *what, uint32_t a, uint32_t b)
{
    if (++*n <= 3) dala_stub(owner, what, a, b);   /* the first few per site: keeps dala_stub's shared budget */
}

static void *shell_alloc(MtDTI *dti, uint32_t size)
{
    void *a = get_allocator(dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    return alloc(a, size, 16, dti->w[7]);
}

static void *shell_owner(void *self)
{
    void *param = FIELD(void *, self, 0x136c);
    return param ? FIELD(void *, param, 0xc) : 0;
}

/* The meteor's 4U frames per tick, in % of the shells' pace (= the monster's clock, 60 4U frames / s). History: 100
 * (test 2026-10-24 17:22: a kind-4 meteor fell 9300 in 2.19 s), user 2026-10-25: "2x too fast, this time I'm sure";
 * 50 (4.4 s), user the same evening: too slow, "something in between". 4U's code gives no value in between (C): the
 * shell's step this+20 = global step [sMain+0x5c] x its unit line's scale (0x64521c); shells go on line 18
 * (0x661000), every line is built with scale 1.0 (0x645df0) and no writer of a line scale exists (S: no store to a
 * line's +20 outside the constructor); the global step counts 60-fps frames (sMain base fps 60.0, 0x644a40), so on
 * 4U's clock a meteor falls with the monster's frames. 75 is the user's "in between" (G), DALA_METEOR_PACE_PCT
 * (install.sh switch) tunes it. Velocities stay 4U's (0xd37f20: -120 / -40 / -90 / -70 per frame, C; lifetime 180). */
#ifndef DALA_METEOR_PACE_PCT
#define DALA_METEOR_PACE_PCT 75
#endif
#define METEOR_PACE (DALA_METEOR_PACE_PCT / 100.0f)
static float meteor_dt(void *self) { return METEOR_PACE * dala_shell_dt(self); }

/* 4U 0x9aad4c(shell, &t): t -= dt; 1 once t <= 0 (clamped to 0) */
static int shell_timer(void *self, float *t)
{
    if (*t <= 0.0f) { *t = 0.0f; return 1; }
    *t -= meteor_dt(self);
    if (*t > 0.0f) return 0;
    *t = 0.0f;
    return 1;
}

/* 4U 0x9ab120(shell, records 0x102dff0, volumes 0x102dfe0, record, 31, 2) = GU slot 80 (HDS entry, -1, 31, 2,
 * group); 4U then writes the request group to slot +0x34 unless 0xffff: GU takes it as the last int argument */
static void meteor_arm(void *self)
{
    if (uShell_hasHitData(self) != 1) {
        static uint8_t s_once;
        if (!s_once) { s_once = 1; logf("dalaport: meteor shell: resource %x has no hit data, meteors do not hit",
                                         FIELD(uint32_t, self, 0x1384)); }
        return;
    }
    typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
    arm_t arm = (arm_t)((*(uint32_t **)self)[SLOT_ARM_ATTACK]);
    arm(self, 0, DALA_HDS_METEOR + k_hds[FIELD(uint8_t, self, S_KIND)], -1, 31, 2, FIELD(uint16_t, self, S_GROUP),
        FIELD(float, self, SH_ATK0 + ATK_F14));
    FIELD(uint8_t, self, S_ARMED) = 1;
}

/* the local hunter (listener stand-in for 4U 0xaf79a4(player mgr *0xfb83e8)'s object +0xe30 + 16, as
 * em089_shell016.c) */
static int listener_pos(float *out)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    if (!pl || !*(void **)((uint8_t *)pl + 0x498) || !*(void **)((uint8_t *)pl + 0x494)) return 0;
    jointPos(pl, 0, out);
    return 1;
}

static uint32_t s_n_efx, s_n_blast, s_n_mine, s_n_k01;

/* 4U slot 23 [0xc7d268] after the owner test (GU slot 9 base): 1 = the shell is done (4U state 2) */
static int meteor_step(void *self, void *owner)
{
    uint32_t kind = FIELD(uint8_t, self, S_KIND), serial = FIELD(uint32_t, self, S_SERIAL);
    float *arm_t = &FIELD(float, self, S_ARM_T);
    if (*arm_t > 0.0f) {                      /* 0xc7d2c0: delayed attack (the machine always passes 0.0) */
        if (!shell_timer(self, arm_t)) return 0;
        meteor_arm(self);
    }
    float *life = &FIELD(float, self, S_LIFE);
    shell_timer(self, life);
    if (*life <= 0.0f) {                      /* 0xc7d344: state 2, lifetime 10 */
        *life = 10.0f;
        static uint32_t s_n;
        if (++s_n <= 30) logf("dalaport: meteor %u kind %u timed out", serial, kind);
        return 1;
    }
    float *pos = VEC(self, SH_POS), *vel = VEC(self, S_VEL), *acc = VEC(self, S_ACC), *prev = VEC(self, S_PREV);
    prev[0] = pos[0]; prev[1] = pos[1]; prev[2] = pos[2];
    FIELD(float, self, SH_ATK0 + ATK_TIME_4U88) = 100.0f;   /* 4U +0x1c0 = slot 0 +88 = 100 every frame */
    if (kind < 2) {                           /* 0xc7d39c: kinds 0 / 1 (not Dalamadur's) end on their own hit */
        stub_once(owner, &s_n_k01, "meteor kinds 0/1 0xc7d39c", kind, 0);
        return 1;
    }
    float dt = meteor_dt(self), h = dt * dt * 0.5f;       /* 0x9ab0a0: 0x9a94f4 then v += a dt */
    for (int i = 0; i < 3; i++) { pos[i] += vel[i] * dt + acc[i] * h; vel[i] += acc[i] * dt; }
    float *p2 = VEC(self, SH_POS2);
    p2[0] = prev[0]; p2[1] = prev[1]; p2[2] = prev[2];
    float out[4] = {0, 0, 0, 0};
    void *col = COL_MGR;
    /* 0x2b96e4(col, pos, prev, area, out, info sp+96, 16, 0x9aad8c(this)); the info block (its byte 3 goes to the
     * mining post) is not passed: GU's layout is not checked */
    uint32_t r = col ? mapSegment(col, pos, prev, FIELD(uint8_t, self, SH_AREA), out, 0, 16, uShell_colFlags(self)) : 0;
    uint32_t area = FIELD(uint8_t, self, SH_AREA);
    if (r & 17) {                             /* 0xc7d418: impact */
        pos[0] = out[0]; pos[1] = out[1]; pos[2] = out[2];
        uint32_t shah = kind >= 5, sub = shah ? (kind == 7 ? 162 : 160) : (kind == 4 ? 126 : 113);
        static uint32_t s_n;
        if (++s_n <= 60) logf("dalaport: meteor %u kind %u impact (%x) at %d %d %d", serial, kind, r, (int32_t)pos[0],
                              (int32_t)pos[1], (int32_t)pos[2]);
        /* 0x663220(shell mgr, owner, subtype, &pos, area, group +0x19c) -> 0x661c5c: type-3 blast shell; +0x19c =
         * attack slot 0 +0x34, the hit group the arming gave the meteor (dala_shell003.c) */
        if (!dala_shell003_post(owner, sub, pos, area, FIELD(uint16_t, self, SH_ATK0 + ATK_GROUP)))
            stub_once(owner, &s_n_blast, "meteor blast uShell003 0x663220 not posted, subtype", sub, kind);
        void *m = SND_MGR;
        if (kind == 3 || kind == 6) {
            /* 0x6626e8(shell mgr, owner, 0 / Shah 1, area, &pos, +0x114, ground byte) -> type 38 uShell038: the
             * meteor scale and its mining point (dala_shell038.c; the ground byte is not known here, see there) */
            if (!dala_shell038_post(owner, kind == 6, pos, area, FIELD(uint32_t, self, SH_ANGLES + 4)))
                stub_once(owner, &s_n_mine, "meteor scale uShell038 0x6626e8 not posted, kind / area", kind, area);
            if (m && owner) snd_req_pos(m, 213, owner, pos, area, -2);
        } else if (m && owner) snd_req_pos(m, 204, owner, pos, area, -2);
        return 1;
    }
    if (shell_timer(self, &FIELD(float, self, S_SND_T))) {   /* 0xc7d484: falling sound every 12 frames */
        FIELD(float, self, S_SND_T) = 12.0f;
        void *m = SND_MGR;
        if (m && owner) snd_req_obj(m, 205, self, -1, owner, area, self);
    }
    return 0;
}

static void shell_kill(void *self)
{
    FIELD(uint8_t, self, S_STATE) = 2;
    VCALL0(self, SLOT_KILL);              /* ours: shell_slot_kill (the base 0x4a247c once the effect is dead) */
}

/* slot 16: deferred kill while the attached effect lives (em089_shell.c pattern; 4U slot 24 0xc7da24 releases the
 * effect with 0xc470dc and runs the base kill) */
static void shell_slot_kill(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    if (h && !dala_efx_alive(h)) FIELD(void *, self, S_EFX) = h = 0;
    if (!h) { FIELD(uint8_t, self, S_DYING) = 0; uShell_kill(self); return; }
    if (FIELD(uint8_t, self, S_DYING)) return;
    FIELD(uint8_t, self, S_DYING) = 1;
    FIELD(uint8_t, self, S_STATE) = 2;
    FIELD(float, self, S_DIE_T) = 0.0f;
    FIELD(uint8_t, self, 0x13ae) = 255; FIELD(uint8_t, self, 0x13ad) = 0;   /* 0x4a247c: attack slots 0..2 off */
    FIELD(uint8_t, self, 0x1466) = 255; FIELD(uint8_t, self, 0x1465) = 0;
    FIELD(uint8_t, self, 0x151e) = 255; FIELD(uint8_t, self, 0x151d) = 0;
    dala_efx_stop(h);
}

/* per frame while S_DYING: base kill once the effect is dead (forced stop after EFX_DIE_MAX frames) */
static void shell_dying(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    float *t = &FIELD(float, self, S_DIE_T);
    *t += dala_shell_dt(self);
    if (h && dala_efx_alive(h) && *t >= EFX_DIE_MAX && *t < EFX_DIE_MAX + 1000.0f) {
        static uint32_t s_n;
        if (++s_n <= 20) logf("dalaport: meteor %u: effect still alive after %d frames, forced stop",
                              FIELD(uint32_t, self, S_SERIAL), (int32_t)EFX_DIE_MAX);
        dala_efx_kill(h);
        *t = EFX_DIE_MAX + 1000.0f;           /* one more frame for the effect's own kill, then the shell goes */
        return;
    }
    if (h && dala_efx_alive(h) && *t < EFX_DIE_MAX + 1000.0f + 30.0f) return;
    FIELD(void *, self, S_EFX) = 0;
    FIELD(uint8_t, self, S_DYING) = 0;
    uShell_kill(self);
}

/* 4U slot 22 [0xc7cedc] */
static void meteor_init(void *self, void *owner)
{
    uint32_t kind = FIELD(uint8_t, self, S_KIND);
    uint32_t area = FIELD(uint8_t, self, SH_AREA);
    FIELD(uint8_t, self, S_STATE) = 1;
    /* effect: 0xc0a2f8(effmgr *0x10572a4, group, element) -> 0xc08060(effmgr, file, area, 0, -1, -1) -> +0x274,
     * +0x228 |= 8, vt+0x48(eff, this, -1) (attach), 0xc4800c(eff, 1); 4U ends the shell when the file is missing
     * (here: logged, the meteor lives, see the header) */
    FIELD(void *, self, S_EFX) = dala_efx_meteor(owner, self, kind);
    if (!FIELD(void *, self, S_EFX))
        stub_once(owner, &s_n_efx, "meteor effect: no PEL record, 4U group/element", k_efx[kind][0], k_efx[kind][1]);
    FIELD(float, self, S_LIFE) = METEOR_LIFE;
    float *vel = VEC(self, S_VEL), *acc = VEC(self, S_ACC);
    vel[0] = 0.0f; vel[1] = k_vel_y[kind]; vel[2] = 0.0f;
    acc[0] = 0.0f; acc[1] = k_acc_y[kind]; acc[2] = 0.0f;
    FIELD(uint32_t, self, SH_ANGLES) = 0x4000;      /* +0x110 = 16384 */
    FIELD(uint32_t, self, SH_ANGLES + 4) = 0;
    FIELD(uint32_t, self, SH_ANGLES + 8) = 0;
    if (FIELD(float, self, S_ARM_T) == 0.0f) meteor_arm(self);
    float *pos = VEC(self, SH_POS);
    if (kind == 0) {
        stub_once(owner, &s_n_k01, "meteor kind 0 init 0xc7d864 + sound 210", kind, 0);
    } else if (kind >= 2) {
        /* 0xc7d0cc: sound 210 at the point of the line pos .. pos - (0, 20000, 0) nearest to the listener
         * (0x1dfddc: t = dot(dir, P - pos) clamped to [0, 20000]) */
        float l[4], pt[3] = {pos[0], pos[1], pos[2]};
        if (listener_pos(l)) {
            float t = pos[1] - l[1];
            if (t >= 20000.0f) t = 20000.0f;
            if (t < 0.0f) t = 0.0f;
            pt[1] = pos[1] - t;
        }
        void *m = SND_MGR;
        if (m && owner) snd_req_pos(m, 210, owner, pt, area, -2);
    }
    FIELD(float, self, S_SND_T) = 0.0f;           /* +0x27c */
}

/* slot 79: base setup, then the 4U ctor copies and init; the init's tail call of slot 23 runs the first step here
 * (a done shell is killed by the next slot 9, the shell being registered only after the setup) */
static int shell_setup(void *self, void *param)
{
    if (uShellEnemy_setup(self, param) != 1) return 0;
    void *owner = FIELD(void *, param, 0xc);
    FIELD(uint8_t, self, SH_AREA) = FIELD(uint8_t, self, S_AREA);   /* the base copied the owner's: the same byte */
    float *pos = VEC(self, SH_POS), *st = VEC(self, S_START);
    pos[0] = st[0]; pos[1] = st[1]; pos[2] = st[2];
    float *prev = VEC(self, S_PREV), *p2 = VEC(self, SH_POS2);
    prev[0] = p2[0] = pos[0]; prev[1] = p2[1] = pos[1]; prev[2] = p2[2] = pos[2];
    meteor_init(self, owner);
    static uint32_t s_n;
    if (++s_n <= 60)
        logf("dalaport: meteor %u spawn kind %u at %d %d %d area %u hit %u", FIELD(uint32_t, self, S_SERIAL),
             FIELD(uint8_t, self, S_KIND), (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2],
             FIELD(uint8_t, self, SH_AREA), FIELD(uint8_t, self, S_ARMED));
    if (meteor_step(self, owner)) FIELD(uint8_t, self, S_STATE) = 2;
    return 1;
}

/* slot 9 = 4U slot 23 */
static void shell_move(void *self)
{
    /* drop a dead effect handle every frame (as em089_shell.c / GU EmBase shells): never read a freed effect */
    if (FIELD(void *, self, S_EFX) && !dala_efx_alive(FIELD(void *, self, S_EFX))) FIELD(void *, self, S_EFX) = 0;
    uShell_move(self);                        /* owner gone -> kill (4U: +0x16e = 255, +0x16d = 0, state 3) */
    if (FIELD(uint8_t, self, S_DYING)) { shell_dying(self); return; }
    if ((FIELD(uint32_t, self, 0xc) & 7) - 1 >= 2) return;
    if (FIELD(uint8_t, self, S_STATE) == 2) { shell_kill(self); return; }
    if (FIELD(uint8_t, self, S_STATE) != 1) return;
    if (meteor_step(self, shell_owner(self))) shell_kill(self);
}

static void *shell_new(MtDTI *dti)
{
    (void)dti;
    void *mem = shell_alloc(&s_dti, SHELL_SIZE);
    if (!mem) return 0;
    uShellEnemy_ctor(mem);
    FIELD(uint32_t, mem, 0) = (uint32_t)&s_vt[2];
    for (uint32_t o = SIZE_uShellEnemy; o < SHELL_SIZE; o++) FIELD(uint8_t, mem, o) = 0;
    return mem;
}

/* slot 1 = 4U 0xc7daf0 (4U slot 24 releases the effects +0x274 / +0x278; +0x278 is kind 0's, not Dalamadur's) */
static void shell_delete(void *self)
{
    void *h = FIELD(void *, self, S_EFX);
    if (dala_efx_alive(h)) dala_efx_kill(h);   /* deleted without our kill (area / quest teardown) */
    FIELD(void *, self, S_EFX) = 0;
    uShellEnemy_dtor(self);
    void *a = get_allocator(&s_dti);
    void (*release)(void *, void *) = (*(void ***)a)[0x34 / 4];
    release(a, self);
}

static MtDTI *shell_get_dti(void *self)
{
    (void)self;
    return &s_dti;
}

static void shell_register(void)
{
    const uint32_t *base_vt = (const uint32_t *)VT_uShellEnemy;
    for (int i = 0; i < 2 + VT_uShellEnemy_SLOTS; i++) s_vt[i] = base_vt[i - 2];
    s_vt[2 + 1] = (uint32_t)&shell_delete;
    s_vt[2 + 5] = (uint32_t)&shell_get_dti;
    s_vt[2 + SLOT_MOVE] = (uint32_t)&shell_move;
    s_vt[2 + SLOT_SETUP] = (uint32_t)&shell_setup;
    s_vt[2 + SLOT_KILL] = (uint32_t)&shell_slot_kill;
    const uint32_t *base_dvt = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + 3; i++) s_dti_vt[i] = base_dvt[i - 2];
    s_dti_vt[2 + 2] = (uint32_t)&shell_new;
    MtDTI_ctor(&s_dti, "uShellDala029", DTI_uShellEnemy, SHELL_SIZE, 0, 0, 0);
    s_dti.w[0] = (uint32_t)&s_dti_vt[2];
    s_registered = 1;
    logf("dalaport: uShellDala029 DTI %x id %x size %x, resource file %x (row %u)", (uint32_t)&s_dti, s_dti.w[7],
         SHELL_SIZE, DALA_METEOR_FILE, DALA_METEOR_ID);
}

/* 4U 0x66242c + 0x660e88 type 29 + ctor 0xc7da60, through our copy of GU's request 0x48c4f0 (em089_shell.c) */
void *dala_meteor_post(void *owner, uint32_t kind, const float *pos, uint32_t area, uint32_t group, float arm_delay)
{
    static uint32_t s_fail;
    if (!s_registered) shell_register();
    uint8_t *mgr = SHELL_MGR;
    if (!owner || !pos || kind < 2 || kind >= METEOR_KINDS || !mgr) {
        if (++s_fail <= 20) logf("dalaport: meteor post dropped (owner %x kind %u mgr %x)", (uint32_t)owner, kind,
                                 (uint32_t)mgr);
        return 0;
    }
    uint32_t live = 0;
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, 0xc) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) {
        if (++s_fail <= 20) logf("dalaport: meteor post dropped: %u live shells", live);
        return 0;
    }
    uint8_t *rec = FIELD(uint8_t *, owner, EN_RECORD);
    uint8_t *param = shell_alloc(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = DALA_METEOR_ID;
    FIELD(uint32_t, param, 8) = 0;            /* resource entry 0 */
    FIELD(void *, param, 0xc) = owner;
    FIELD(uint32_t, param, 0x10) = FIELD(uint32_t, rec, 0x40);
    FIELD(uint32_t, param, 0x14) = FIELD(uint32_t, rec, 0x5b4);
    FIELD(uint32_t, param, 0x18) = FIELD(uint32_t, rec, 0x48);
    const uint32_t *zv = (const uint32_t *)ZERO_VEC;
    FIELD(uint32_t, param, 0x20) = zv[0]; FIELD(uint32_t, param, 0x24) = zv[1]; FIELD(uint32_t, param, 0x28) = zv[2];
    FIELD(uint32_t, param, 0x30) = FIELD(uint32_t, owner, 0xfe8);
    FIELD(uint32_t, param, 0x34) = FIELD(uint32_t, owner, 0xfec);
    FIELD(uint32_t, param, 0x38) = FIELD(uint32_t, owner, 0xff0);
    FIELD(uint16_t, param, 0x3c) = 0xffff;
    void *shell = shell_new(&s_dti);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return 0;
    }
    /* 4U ctor 0xc7da60: +0xfd kind, +0x100 pos (w 0), +0x130 area, +0x270 group, +0x280 arm delay, effects 0 */
    FIELD(uint8_t, shell, S_KIND) = (uint8_t)kind;
    float *st = VEC(shell, S_START);
    st[0] = pos[0]; st[1] = pos[1]; st[2] = pos[2];
    FIELD(uint8_t, shell, S_AREA) = (uint8_t)area;
    FIELD(uint16_t, shell, S_GROUP) = (uint16_t)group;
    FIELD(float, shell, S_ARM_T) = arm_delay;
    FIELD(uint32_t, shell, S_SERIAL) = ++s_serial;
    void *res = fileResource(0, DALA_METEOR_FILE);
    uShell_setResource(shell, res);
    shell_setup_t setup = (shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]);
    if (setup(shell, param) != 1) {
        if (++s_fail <= 20) logf("dalaport: meteor setup failed (owner type %u)", FIELD(uint8_t, owner, 0x1052));
        shell_delete(shell);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(mgr, shell);
    return shell;
}
