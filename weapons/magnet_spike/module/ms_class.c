/* ms_class.c: class 5 = the Magnet Spike (Phase 2 slice, MS_SLICE; notes/phase2.md, gu-weapon-class.md).
 *
 * Object: the factory's quest jump table sends class 5 to the Great Sword case (build.py word patch), so the object
 * is a Great Sword object (0x3340 B, base ctor 0x2990bc); the hook at the common post-construction point 0x275bc8
 * then gives it ms_vt, a copy of the Great Sword vtable in which every slot the Great Sword overrides holds a Magnet
 * Spike function or the engine's common default (the value most classes share). Slots left to GS code are listed
 * in phase2.md ("Great Sword code still used by class 5"). The village's generic class keeps GU's vtable.
 * Equipment (box type 12): GU has no type-12 tables; the base / level getters answer with this file's records (a
 * copy of Great Sword 1's, retyped), the pwl getters with Great Sword model 1's values. A test build adds one Magnet
 * Spike to the item box when the save holds none. Saves keep type 12 / class 5 raw: test on a backed-up save. */
#include "ms.h"

#define VT_GS 0x1749a88u            /* uPlayerQuest00 vtable address point */
#define VT_SLOTS 556
static uint32_t s_vt[2 + VT_SLOTS];  /* 2 words before the address point copied too */
static uint32_t *ms_vt;
static struct ms_state s_state[MS_PLAYERS];
static void forge_tables_init(void);

struct ms_state *ms_of(uint8_t *p)
{
    struct ms_state *free_ = 0;
    for (int i = 0; i < MS_PLAYERS; i++) {
        if (s_state[i].p == p) return &s_state[i];
        if (!s_state[i].p && !free_) free_ = &s_state[i];
    }
    if (!free_) free_ = &s_state[0];
    free_->p = p;
    ms_reset(free_);
    return free_;
}

void ms_reset(struct ms_state *s)   /* a new hunter object: MHF's quest-start state (gauge empty, Cutting) */
{
    uint8_t *p = s->p;
    for (uint32_t i = 0; i < sizeof *s; i++) ((uint8_t *)s)[i] = 0;
    s->p = p;
}

/* ------------------------------------------------------------------------------------------------ class slots */

/* command table pickers of the common actions (GS's slots 392 / 398 / 404-408 / 412-416): the same table ids, which
 * name tables of plcmd_w05_<style> (msbuild.py: 0 = drawn idle, 10-46 = GU's common-action tables, GS's weapon
 * commands left out). vt+0x178 picks the second table of a pair: 1 = weapon drawn (the weapon sync 0x308b3c plays
 * the sheathed pose otherwise). */
static int state178(uint8_t *p) { return ((int (*)(void *))MS_VT(p, 0x178))(p) == 1; }
static void tbl(uint8_t *p, uint32_t id, int frame) { MS_SET_TABLE(p, id, frame); }
static void pick392(uint8_t *p, int frame) { tbl(p, 2000, frame); }
static void pick398(uint8_t *p) { tbl(p, 2010, 0); }
static void pick404(uint8_t *p) { tbl(p, 2011, 0); }
static void pick412(uint8_t *p) { tbl(p, state178(p) ? 2015 : 2014, 0); }
static void pick405(uint8_t *p, int a, int b, int k)
{
    (void)a; (void)b;
    if ((uint32_t)(k - 4) < 2) { pick412(p); return; }   /* GS: vt+0x670(p, 0) = slot 412 */
    if (k == 1) tbl(p, 2013, 0); else if (k == 0) tbl(p, 2012, 0);
}
static void pick406(uint8_t *p, int k) { if ((uint32_t)k <= 2) tbl(p, 2034 + k, 0); }
static void pick407(uint8_t *p, int k) { if ((uint32_t)(k - 1) < 2) tbl(p, 2019, 0); else if (k == 0) tbl(p, 2018, 0); }
static void pick408(uint8_t *p, int k)
{
    switch (k) {
    case 0: tbl(p, state178(p) ? 2024 : 2023, 0); break;
    case 1: tbl(p, 2023, 10); break;
    case 2: tbl(p, state178(p) ? 2021 : 2020, 0); break;
    case 3: tbl(p, state178(p) ? 2026 : 2025, 0); break;
    case 4: tbl(p, state178(p) ? 2028 : 2027, 0); break;
    }
}
static void pick413(uint8_t *p, int frame) { tbl(p, 2017, frame); }
static void pick414(uint8_t *p) { tbl(p, 2037, 0); }
static void pick415(uint8_t *p, int a, int k) { if (a == 0 && (uint32_t)k <= 2) tbl(p, 2030 + k, 0); }
static void pick416(uint8_t *p) { tbl(p, state178(p) ? 2046 : 2045, 0); }

/* slot 187 (+0x2ec): the sheathed state's indirect weapon commands (common list, act_st 0x8010, act_no 0..8;
 * the command step 0x2e9d54 reads {act_st, act_no, act_param} here). MHF (0x1032d110 / 0x1032d210): tri = the shared
 * draw standing, Vertical 1 (78) moving; tri+circle = Impact Horizontal 1 (79). Indexes as GS's table: 0 / 1 = X
 * (common ids 0xb / 0xc), 3 = X + A (0x17); 2 / 4 = act_st 0x20 (S: GU's own, kept). GS picks its row by style
 * (vt+0x168, test 1: 5 = Valor); MHF by moving: GU runs a locomotion action (act_st 2: walk 2/1, run 2/9). */
static const uint16_t s_ind_stand[9][3] = {{1, 1, 0}, {1, 1, 0}, {0x20, 0, 0}, {0x10, 79, 0}, {0x20, 0, 0},
                                           {1, 0, 0}, {1, 0, 0}, {1, 0, 0}, {1, 0, 0}};
static const uint16_t s_ind_move[9][3] = {{0x10, 78, 0}, {0x10, 78, 0}, {0x20, 0, 0}, {0x10, 79, 0}, {0x20, 0, 0},
                                          {1, 0, 0}, {1, 0, 0}, {1, 0, 0}, {1, 0, 0}};
static const uint16_t *indirect(uint8_t *p, uint32_t k)
{
    int moving = FIELD(uint16_t, p, 0x2506) == 2;
    static int s_logged;
    if (s_logged++ < 16)
        logf("msport: sheathed command %u in action %u/%u (%s)", k, FIELD(uint16_t, p, 0x2506),
             FIELD(uint16_t, p, 0x250a), moving ? "moving" : "standing");
    if (k > 8) k = 8;
    return moving ? s_ind_move[k] : s_ind_stand[k];
}

static int second_mode(uint8_t *p) { return ms_of(p)->mode == 1; }      /* slot 215 (+0x35c): Impact */
static void reset_state(uint8_t *p, int k) { (void)k; ms_of(p)->fired = 0; }
/* class parameter idx of pl_w05 (Phase 2: GS's values). The result's register (r0 or s0) is not settled: the wrapper
 * returns the call's r0 and leaves s0 as the call left it, as GS's tail call does */
typedef uint32_t (*param_t)(void *p, uint32_t idx);
#define PARAM FN(param_t, 0x282870)
static uint32_t param22(uint8_t *p) { return PARAM(p, 0x22); }
static uint32_t param24(uint8_t *p) { return PARAM(p, 0x24); }
static uint32_t param2c(uint8_t *p) { return PARAM(p, 0x2c); }
static int never(void) { return 0; }
static void nothing(void) {}

/* slot -> engine common function (main offset) for the GS-own slots that have one */
static const uint32_t s_defaults[][2] = {
    {2, 0x29a314}, {4, 0x29a310}, {16, 0x29cdc8}, {102, 0x2a28ec}, {103, 0x2a29a4}, {128, 0x268948},
    {166, 0x2a1d90}, {190, 0x2ab670}, {191, 0x283208}, {351, 0x2f3314}, {362, 0x2f57e4}, {421, 0x2698d4},
    {445, 0x2ab5b8}, {447, 0x2ab5f0}, {478, 0x2ded80}, {497, 0x2b7ed0}, {498, 0x2b7ed4}, {511, 0x2699d0},
    {554, 0x269b04}};

static void vt_fn(int slot, const void *f) { ms_vt[slot] = (uint32_t)(uintptr_t)f; }

void ms_init(void)
{
    const uint32_t *gs = (const uint32_t *)MAIN(VT_GS - 8);
    for (int i = 0; i < 2 + VT_SLOTS; i++) s_vt[i] = gs[i];
    ms_vt = s_vt + 2;
    for (uint32_t i = 0; i < sizeof s_defaults / sizeof s_defaults[0]; i++) ms_vt[s_defaults[i][0]] = MAIN(s_defaults[i][1]);
    vt_fn(139, ms_input); vt_fn(201, ms_act); vt_fn(187, indirect); vt_fn(215, second_mode);
    vt_fn(290, param22); vt_fn(291, param24); vt_fn(548, param2c); vt_fn(386, reset_state);
    vt_fn(392, pick392); vt_fn(398, pick398); vt_fn(404, pick404); vt_fn(405, pick405); vt_fn(406, pick406);
    vt_fn(407, pick407); vt_fn(408, pick408); vt_fn(412, pick412); vt_fn(413, pick413); vt_fn(414, pick414);
    vt_fn(415, pick415); vt_fn(416, pick416); vt_fn(453, never); vt_fn(454, nothing);
    vt_fn(37, ms_on_hit);           /* +0x94: after our attack's damage on a monster (every class: bx lr) */
    vt_fn(356, ms_guarded);         /* +0x590: the guard reaction (build.py's guard patches let class 5 guard) */
    vt_fn(44, ms_invuln);           /* +0xb0: invulnerable now (GU's), + MHF's "evaded through an attack" */
    forge_tables_init();
    /* still GS's: 82 (resource setup + manager group 35, S), 443 (common actions 0x172-0x174 at GS frames) */
    logf("msport: class 5 vtable at %x (GS %x)", (uint32_t)(uintptr_t)ms_vt, MAIN(VT_GS));
}

/* 0x275bc8: the factory after any kind's constructor (r10 = the object, r8 = the hunter's equipment info, r7 = the
 * kind; build.py patched kind 0's jump-table entry 5 to the Great Sword case). Only kind 0 (quest) builds a class
 * object: the other kinds build GU's generic classes for every weapon (kind 1 = the village, 0x28bc94, 0x2740 B),
 * which keep their own vtable (the quest one reads fields past their end). Entered through ms_factory_c below. */
__asm__(".global ms_factory_c\n .hidden ms_factory_c\n .type ms_factory_c, %function\n"
        "ms_factory_c:\n mov r1, r8\n mov r2, r10\n mov r3, r7\n b ms_factory_cc\n");
int ms_factory_cc(uint32_t *regs, uint8_t *info, uint8_t *obj, uint32_t kind)
{
    (void)regs;
    if (!info || !obj || info[0x4d4] != MS_CLASS || kind != 0) return 0;
    *(uint32_t **)obj = ms_vt;
    ms_reset(ms_of(obj));
    logf("msport: class 5 object %x (Great Sword layout), vtable %x", (uint32_t)(uintptr_t)obj,
         (uint32_t)(uintptr_t)ms_vt);
    return 0;
}

/* ------------------------------------------------------------------------------------------------ HUD */

/* the HUD (static research gu_hud): class 5's gauge case is the Charge Blade's (build.py word 0x665b34: sharpness
 * + cUIOWeaponChargeAxe); its update body 0x6463fc reads the local hunter's vtable (phial count / max, colour,
 * state animations) into widget fields, then clamps and draws them. Hook 0x646560 (r4 = widget, r5 = the hunter or
 * 0), after those reads: for our class, 5 phial slots = the magnet gauge's bars (full bars lit), the colour = the
 * mode, element 0's animation (6-entry table) = this mode's Magnetise: ready 2, on 1, lockout 5 (S: CB's
 * steady / flashing pairs, to check in a test); the shield and second indicators off */
/* the gauge's look (test 1: "the HUD is the Charge Blade's"; tools/mshud.py): the widget's .gui (+0x24) draws CB's
 * vials and shield from HD_hud00. While our hunter drives it, the .gui's HD_hud00 texture entry points at
 * mh4uport\ms_hud00 (that atlas with MHF's gauge cells and horseshoe painted over them), back to HD_hud00 for anyone
 * else. The entry sits in the .gui resource's texture table: GU's lookup 0xb80fd0(rGUI, ID) gets the rGUI as a
 * sprite's +0x78 and reads its loaded file (+0x64): table +0xe8, count +0x70, 64-byte entries with the rTexture at
 * +0x28 (size +0xdc / +0xe0, GPU texture +0xd0), as the loader 0xb7f988 fills them. module/icons.c's hook on that
 * lookup hands us each rGUI (ms_gui_seen); the gauge's is the one named hud14_chargeAx. (Test 2 crash: walking the
 * .gui's objects read a non-sprite's +0x78 as a table.) The gauge's .gui releases its entries' textures with itself,
 * so ours gets one more reference per swap and HD_hud00 keeps the one the .gui held. */
#define RES_MGR      0x2126a64      /* sResource (module/icons.c) */
#define DTI_RTEXTURE 0x21255d0
typedef void *(*res_get_t)(void *mgr, void *dti, const char *path, uint32_t mode);
static uint8_t *s_hud_tex, *s_hud_orig, *s_hud_gui;
static uint8_t s_hud_tried;

static void *res_get(const char *path)
{
    void *mgr = *(void **)MAIN(RES_MGR);
    return mgr ? (*(res_get_t **)mgr)[0x30 / 4](mgr, (void *)MAIN(DTI_RTEXTURE), path, 1) : 0;
}

/* s in a resource's path (cResource keeps it near the top: bytes 4 .. 84 are searched, NULs included) */
static int path_has(const uint8_t *res, const char *s)
{
    for (int i = 4; i < 84; i++) {
        int k = 0;
        while (s[k] && res[i + k] == (uint8_t)s[k]) k++;
        if (!s[k]) return 1;
    }
    return 0;
}

/* icons.c tex_entry_c: an rGUI that GU looks a texture up in (valid: GU reads it right after) */
void ms_gui_seen(uint8_t *gui)
{
    static uint8_t *s_last;
    if (gui == s_last || gui == s_hud_gui) return;
    s_last = gui;
    if (!path_has(gui, "chargeAx")) return;
    s_hud_gui = gui;
    logf("msport: HUD gauge .gui %x", (uint32_t)(uintptr_t)gui);
}

static void hud_look(int ours)
{
    if (ours && !s_hud_tried) {
        s_hud_tried = 1;
        s_hud_tex = res_get("mh4uport\\ms_hud00");
        logf("msport: HUD atlas mh4uport\\ms_hud00 -> %x", (uint32_t)(uintptr_t)s_hud_tex);
    }
    uint8_t *g = s_hud_gui && path_has(s_hud_gui, "chargeAx") ? s_hud_gui : 0, *d = g ? FIELD(uint8_t *, g, 0x64) : 0;
    uint8_t *tab = d ? FIELD(uint8_t *, d, 0xe8) : 0;
    uint32_t n = d ? FIELD(uint32_t, d, 0x70) : 0;
    if (!s_hud_tex || !FIELD(void *, s_hud_tex, 0xd0) || !tab || n > 64) return;
    for (uint32_t i = 0; i < n; i++) {
        uint8_t *e = tab + 64 * i, *t = FIELD(uint8_t *, e, 0x28);
        if (!t) continue;
        if (ours && t != s_hud_tex && path_has(t, "HD_hud00") && FIELD(uint32_t, t, 0xdc) == FIELD(uint32_t, s_hud_tex,
            0xdc) && FIELD(uint32_t, t, 0xe0) == FIELD(uint32_t, s_hud_tex, 0xe0)) {
            s_hud_orig = t;
            res_get("mh4uport\\ms_hud00");
            FIELD(uint8_t *, e, 0x28) = s_hud_tex;
            logf("msport: HUD gauge entry %x: Magnet Spike atlas", (uint32_t)(uintptr_t)e);
        } else if (!ours && t == s_hud_tex && s_hud_orig) {
            FIELD(uint8_t *, e, 0x28) = s_hud_orig;
            logf("msport: HUD gauge entry %x: back to HD_hud00", (uint32_t)(uintptr_t)e);
        }
    }
}

int ms_hud_c(uint32_t *regs)
{
    uint8_t *w = (uint8_t *)regs[R4], *p = (uint8_t *)regs[R5];
    if (w) hud_look(p && *(uint32_t **)p == ms_vt);
    if (!w || !p || *(uint32_t **)p != ms_vt) return 0;
    struct ms_state *s = ms_of(p);
    uint32_t m = s->mode, st = s->mag[m];
    FIELD(uint32_t, w, 0x70) = 5;
    FIELD(uint32_t, w, 0x74) = (uint32_t)s->gauge / 2000;
    FIELD(uint32_t, w, 0x64) = m;
    FIELD(uint32_t, w, 0x60) = 0;
    FIELD(uint8_t, w, 0x6c) = 0;
    FIELD(uint32_t, w, 0x68) = st == 1 ? 1 : st == 2 ? 5 : s->mag_v[m] >= 1000 ? 2 : 0;
    return 0;
}

/* ------------------------------------------------------------------------------------------------ weapon attach */

/* 0x3078b8 (weapon, hunter, type), each frame from the weapon update 0x3077f0: GU picks an attach state from the body
 * motion's events (0x308834; 2 = on the back), the joint (0x3084c4, into weapon +0x13cc) and the offset record
 * (0x308334: f32 position, pad, f32 rotation in degrees; applied when it changes, +0x1408). The type is the weapon's
 * +0x13d0, its part type (0x16283a8; class 5's is patched to the Great Sword's 0), so GU attaches the Magnet Spike
 * as a Great Sword: GS's events, joint 8 with GS's grip (10, 0, 58) cm turned 180 deg about z (test 1 run 6: the
 * blade upside down). The Magnet Spike in hand = joint 8 (GU's +x hand = MHF bone 14, the frame msbuild keys the
 * weapon root in, bone-18 frames included) with no offset and scale 1, whenever a bank-5 motion plays or the hunter
 * is drawn and the events do not say "on the back". Anything else keeps GU's Great Sword path (its pwl carry joint,
 * offset and 0.8 scale; Phase 2 stand-in until MHF's carry). */
typedef uint32_t (*ms_wstate_t)(uint32_t zero, void *hunter, uint32_t type);
#define ATTACH_STATE FN(ms_wstate_t, 0x308834)
typedef void (*ms_rot_t)(void *obj, const float *euler);
#define SET_ROTATION FN(ms_rot_t, 0x8a7dc4)          /* radians, vec4 */
#define IS_PROWLER FN(ms_p_t, 0x27b918)
/* the hand record: no offset; the rotation undoes the model turn (msgrip.TURN = Ry(-90 deg), x -> z, so the smithy
 * viewer stands the weapon up): Ry(+90 deg), radians as SET_ROTATION's Rz Ry Rx */
static const float s_grip[8] = {0, 0, 0, 0, 0, 1.5707964f, 0, 0};

/* GU's own attach (on the back = state 2, the village's only state; other states mid draw / sheathe): it applies the
 * Great Sword's record 0x308334(weapon, hunter, type, state) when weapon +0x1408 is not that record (position +0x40,
 * rotation in degrees -> SET_ROTATION -> quaternion +0x50, x y z w), the state filtered as 0x3078b8 does for type 0
 * (mask 0xc40e4 kept, 15 -> 14 in the second mode, else 4). Applied here first with the model turn undone in the
 * weapon's frame (q = record's (x) hand grip's, Hamilton: the grip's turn acts first), so GU finds it applied (test
 * 2: the back turned 90 deg) */
typedef const float *(*ms_carry_t)(void *weapon, void *hunter, uint32_t type, uint32_t state);
#define CARRY_RECORD FN(ms_carry_t, 0x308334)

static void back_record(uint8_t *w, uint8_t *pl, uint32_t type, uint32_t st)
{
    if (st >= 0x14 || !(1u << st & 0xc40e4u)) st = st == 0xf && second_mode(pl) ? 0xe : 4;
    const float *rec = CARRY_RECORD(w, pl, type, st);
    if (!rec || FIELD(const float *, w, 0x1408) == rec) return;
    FIELD(const float *, w, 0x1408) = rec;
    for (int i = 0; i < 3; i++) FIELD(float, w, 0x40 + 4 * i) = rec[i];
    FIELD(float, w, 0x4c) = 0.0f;
    const float deg = 0.017453292f, e[4] = {rec[4] * deg, rec[5] * deg, rec[6] * deg, 0};
    float *q = &FIELD(float, w, 0x50), u[4], g[4];
    SET_ROTATION(w, s_grip + 4);
    for (int i = 0; i < 4; i++) u[i] = q[i];
    SET_ROTATION(w, e);
    for (int i = 0; i < 4; i++) g[i] = q[i];
    q[0] = g[3] * u[0] + g[0] * u[3] + g[1] * u[2] - g[2] * u[1];
    q[1] = g[3] * u[1] - g[0] * u[2] + g[1] * u[3] + g[2] * u[0];
    q[2] = g[3] * u[2] + g[0] * u[1] - g[1] * u[0] + g[2] * u[3];
    q[3] = g[3] * u[3] - g[0] * u[0] - g[1] * u[1] - g[2] * u[2];
    static int s_n;
    if (s_n++ < 8) logf("msport: carry record %x (state %u): (%d, %d, %d) cm, (%d, %d, %d) deg, turn undone",
                        (uint32_t)(uintptr_t)rec, st, (int)rec[0], (int)rec[1], (int)rec[2], (int)rec[4], (int)rec[5],
                        (int)rec[6]);
}

int ms_attach_c(uint32_t *regs)
{
    uint8_t *w = (uint8_t *)regs[R0], *pl = (uint8_t *)regs[R1];
    uint8_t *info = pl ? FIELD(uint8_t *, pl, 0x13c4) : 0;
    if (!info || info[0x4d4] != MS_CLASS || IS_PROWLER(pl)) return 0;
    uint32_t st = ATTACH_STATE(0, pl, regs[R2]);
    if (FIELD(uint32_t, pl, 0x13c8) != 0) {         /* not the quest class: on the back (0x308834 answers 2) */
        back_record(w, pl, regs[R2], st);
        return 0;
    }
    int hand = st != 2 && (CUR_MOTION(pl) / 1000 == 5 || state178(pl));
    static int s_n, s_last = -1;
    if (hand != s_last && s_n < 100) {
        s_n++;
        logf("msport: weapon %s (state %u, motion %u)", hand ? "in hand (joint 8)" : "on GS's carry", st,
             CUR_MOTION(pl));
    }
    s_last = hand;
    if (!hand) {
        back_record(w, pl, regs[R2], st);
        return 0;
    }
    FIELD(uint32_t, w, 0x13c8) = FIELD(uint32_t, w, 0x13cc);
    FIELD(uint32_t, w, 0x13d4) = 1;                 /* GU's state for joint 8 (the weapon sync reads it) */
    FIELD(uint32_t, w, 0x13cc) = 8;
    FIELD(float, w, 0x60) = FIELD(float, w, 0x64) = FIELD(float, w, 0x68) = 1.0f;
    FIELD(float, w, 0x6c) = 0.0f;
    ((void (*)(void *, void *, int))MS_VT(w, 0x48))(w, pl, 8);
    if (FIELD(const float *, w, 0x1408) != s_grip) {
        FIELD(const float *, w, 0x1408) = s_grip;
        for (int i = 0; i < 4; i++) FIELD(float, w, 0x40 + 4 * i) = 0.0f;
        SET_ROTATION(w, s_grip + 4);
    }
    return 1;
}

/* 0x53a164 (unit, motion, mode): every set-motion variant ends here. GU's common actions name their second-mode
 * motions only for SA / CB (the class byte gates slot 215, e.g. the drawn idle 0x2de664), so in Impact the Magnet
 * Spike's drawn idle / walk become the second-mode slots SA uses (5001 -> 5020, 5004 -> 5024), which hold MHF's
 * Impact motions (msbuild COMMON); the same for the idle variants 5-7 and the rolls 12 / 13 (MHF's Impact rolls
 * 1010 / 1011 in 32 / 33: test 1 rolled in the Cutting form). Only our class object (its vtable) is read. */
static const uint16_t s_impact_slot[][2] = {{5001, 5020}, {5004, 5024}, {5005, 5020}, {5006, 5020}, {5007, 5020},
                                            {5012, 5032}, {5013, 5033}};

int ms_setmotion_c(uint32_t *regs)
{
    uint8_t *u = (uint8_t *)regs[R0];
    if (!u || *(uint32_t **)u != ms_vt || ms_of(u)->mode != 1) return 0;
    for (uint32_t i = 0; i < sizeof s_impact_slot / sizeof s_impact_slot[0]; i++)
        if (regs[R1] == s_impact_slot[i][0]) { regs[R1] = s_impact_slot[i][1]; break; }
    return 0;
}

/* the weapon motion sync 0x308b3c, for a body motion outside bank 5 (jumps, GU's shared actions): GU plays the
 * weapon's motion 1 / 0x101, or for SA (class 8) by its mode, vt+0x35c = 1 -> 0x14 / 0x114. Class 5 takes SA's
 * branch: at both class reads (`ldrb r0, [r0, #0x4d4]`, 0x308ddc / 0x308e68, r0 = the equipment info) r0 is moved
 * so that the read gives 8. Our slot 215 answers Impact, so the weapon keeps the Impact form (weapon motion 20 = MHF
 * 1020's) where test 1 showed the Cutting form */
static const uint8_t s_sa_class = 8;

int ms_wsync_c(uint32_t *regs)
{
    const uint8_t *info = (const uint8_t *)regs[R0];
    if (info && info[0x4d4] == MS_CLASS) regs[R0] = (uint32_t)(uintptr_t)&s_sa_class - 0x4d4;
    return 0;
}
int ms_wsync2_c(uint32_t *regs) { return ms_wsync_c(regs); }

/* GU's weapon sound-request resolver 0x4ea0dc (?, class, equipment, k) -> file ID (C): class 5's jump-table case is
 * "no file", so every weapon sound of the motion sound sequence (op 0x66) was silent. Asked as class 0: GS's two001
 * + mSrqrNo (k 1) and two_bcom by mSndMaterial (k 0), read from our record (0x13f060 finds it through ms_base);
 * msbuild packs those files into w05.arc (msfx.py) */
int ms_snd_file_c(uint32_t *regs)
{
    static int s_n;
    if (regs[R1] == MS_CLASS && s_n++ < 12)     /* test 1: "no sound" (diagnostic: is the resolver reached?) */
        logf("msport: weapon sound request k %u (lr %x)", regs[R3], regs[LR] - MAIN_BASE);
    if (regs[R1] == MS_CLASS) regs[R1] = 0;
    return 0;
}

/* ------------------------------------------------------------------------------------------------ equipment */

/* The Magnet Spikes (GU has no type-12 tables): base / level records built from Great Sword 1's (vtable copy,
 * retyped, names from s_weapons), the smithy's create / process rows and its 15th forge category (notes/phase3.md
 * "Smithy"). Weapons 2-7 = MHF-Z rarity-12 Magnet Spikes (dump/mhf/ms_weapons.json; model n = arc/weapon/w05/
 * 00n.arc, msbuild MODELS), stats scaled into GU's G rank (S: raw x 0.55, element x 0.3, rarity 8; MHF's own: all
 * rarity 12, 3 slots, 0 % affinity, the user kept them, test 1), sharpness = MHF's bars (ms_kire_rows); weapon 1 =
 * the Phase 2 test weapon (not forged). Recipes: GU G-rank materials of the element's monsters (item ID = itemData
 * string / 2). Names / descriptions: English. */
struct ms_weapon {
    const char *name, *desc;
    uint8_t model, rare, element, kire;          /* rare 0-based; element 1 fire, 2 water, 3 thunder, 4 dragon, 5 ice;
                                                    kire = row of ms_kire_rows */
    uint16_t raw, elem;                          /* GU true raw, element / 10 */
    uint16_t item[4];
    uint8_t num[4];
};
static const struct ms_weapon s_weapons[] = {
    {"Magnet Spike", "", 1, 0, 0, 0, 100, 0, {0}, {0}},                        /* 0: the equip fallback's dummy */
    /* descriptions as GU's: up to 3 lines of <= 32 characters (test 1: one long line ran out of the box) */
    {"Proto Spike", "A test-built Magnet Spike\r\nfrom the Frontier.", 1, 3, 0, 0, 200, 0, {0}, {0}},
    {"Demon Flamespike \"Flash\"", "A Magnet Spike that burns\r\nwith a demon's flame. Its\r\nmagnetism scorches.",
     2, 7, 1, 0, 352, 24, {1576, 1570, 1585, 335}, {2, 4, 1, 5}},              /* MHF 17516: raw 640, fire 80 */
    {"Volnoborin IV", "A Magnet Spike that surges\r\nlike a riptide. Its poles\r\ndrip with seawater.",
     3, 7, 2, 3, 310, 45, {890, 888, 818, 332}, {2, 3, 4, 5}},                 /* MHF 17563: 564, water 150 */
    {"Torid Pillar \"Uzi\"", "A Magnet Spike charged with\r\nthunder. Its field crackles\r\nwith every swing.",
     4, 7, 3, 1, 309, 47, {1246, 1249, 1256, 330}, {2, 4, 1, 5}},              /* MHF 16964: 562, thunder 155 */
    {"Anoru Pillar \"Wandemu\"", "A Magnet Spike of frozen\r\niron. Its field freezes the\r\nair around it.",
     5, 7, 5, 2, 303, 50, {1145, 332, 331, 330}, {6, 6, 5, 5}},                /* MHF 16968: 551, ice 165 */
    {"Apophis Pillar \"Flash\"", "A Magnet Spike that draws\r\ndragon power into its core.",
     6, 7, 4, 0, 352, 24, {1695, 1693, 1457, 332}, {3, 4, 1, 5}},              /* MHF 16933: 640, dragon 80 */
    {"Apophis Pillar \"Clear\"", "A pure Magnet Spike: no\r\nelement, all force.",
     7, 7, 0, 0, 374, 0, {1488, 1490, 1523, 330}, {2, 3, 1, 5}},               /* MHF 16936: raw 680 */
};

/* the sharpness (C): MHF's bars, mhfdat header +0xac -> per weapon type, the Magnet Spike's (13) at 0x18ff500 = 8
 * cumulative thresholds of 400 (red .. purple + an 8th colour) by the record's +8 sharpness id; GU's kireajiData rows
 * = 7 cumulative thresholds of 450 (the last 50 = Handicraft's): GU's first six = MHF's, purple = MHF's purple + 8th
 * colour, on to 450. gear.c appends the rows; ms_kire_base = the first one's index (0 = refused: GU's 106) */
const uint16_t ms_kire_rows[][7] = {
    {170, 170, 170, 170, 170, 200, 450},    /* MHF id 2 (17516, 16933, 16936): red 170, white 30, purple 50 + 150 */
    {0, 0, 110, 110, 200, 270, 450},        /* id 13 (16964): yellow 110, blue 90, white 70, purple 50 + 80 */
    {0, 0, 0, 0, 300, 300, 450},            /* id 17 (16968): blue 300, purple 45 + 55 */
    {150, 150, 150, 150, 310, 310, 450},    /* id 21 (17563): red 150, blue 160, purple 50 + 40 */
};
const uint32_t ms_nkire = sizeof ms_kire_rows / sizeof ms_kire_rows[0];
uint32_t ms_kire_base;
#define MS_NWEAPONS (sizeof s_weapons / sizeof s_weapons[0])
#define MS_FIRST_FORGED 2
#define MS_NFORGED (MS_NWEAPONS - MS_FIRST_FORGED)
#define MS_PRICE 60000              /* S: GU's endgame forge prices */

#define BASE_SLOTS 90               /* rWeapon00BaseData record vtable; +0x18 = box type, +0x3c / +0x40 name /
                                       description, +0xbc / +0xc0 the same by level (0x126c48..: GMD by type) */
typedef uint8_t *(*getter_t)(void *equip, uint32_t type, uint32_t id);
#define GET_BASE FN(getter_t, 0x13c208)
#define GET_LEVEL FN(getter_t, 0x13ed08)
static uint32_t s_base_vt[2 + BASE_SLOTS];
static uint32_t s_base[MS_NWEAPONS][10];       /* 40-B records */
static uint32_t s_level[MS_NWEAPONS][5];       /* 20-B level rows, row k = weapon k's only level */
static int s_records;               /* 0 none, 1 built, -1 failed */
static uint32_t ms_box_type(void) { return MS_TYPE; }
static const struct ms_weapon *weapon_of(uint8_t *rec)
{
    uint32_t id = FIELD(uint32_t, rec, 4);
    return &s_weapons[id < MS_NWEAPONS ? id : 0];
}
static const char *w_name(uint8_t *rec) { return weapon_of(rec)->name; }
static const char *w_desc(uint8_t *rec) { return weapon_of(rec)->desc; }
static const char *w_name_lv(uint8_t *rec, uint32_t lv) { (void)lv; return weapon_of(rec)->name; }
static const char *w_desc_lv(uint8_t *rec, uint32_t lv) { (void)lv; return weapon_of(rec)->desc; }

static void build_records(void *equip)
{
    uint8_t *gs = GET_BASE(equip, 7, 1);
    uint8_t *row = gs ? GET_LEVEL(equip, 7, FIELD(uint16_t, gs, 0x26)) : 0;
    if (!gs || !row) { s_records = -1; logf("msport: Great Sword 1 records missing: no type-12 records"); return; }
    const uint32_t *vt = *(const uint32_t **)gs;
    for (int i = 0; i < 2 + BASE_SLOTS; i++) s_base_vt[i] = vt[i - 2];
    s_base_vt[2 + 0x18 / 4] = (uint32_t)(uintptr_t)ms_box_type;
    s_base_vt[2 + 0x3c / 4] = (uint32_t)(uintptr_t)w_name;
    s_base_vt[2 + 0x40 / 4] = (uint32_t)(uintptr_t)w_desc;
    s_base_vt[2 + 0xbc / 4] = (uint32_t)(uintptr_t)w_name_lv;
    s_base_vt[2 + 0xc0 / 4] = (uint32_t)(uintptr_t)w_desc_lv;
    for (uint32_t id = 0; id < MS_NWEAPONS; id++) {
        const struct ms_weapon *w = &s_weapons[id];
        uint8_t *r = (uint8_t *)s_base[id], *l = (uint8_t *)s_level[id];
        for (int i = 0; i < 40; i++) r[i] = gs[i];
        *(uint32_t **)r = s_base_vt + 2;
        FIELD(uint32_t, r, 4) = id;                       /* mIndex */
        FIELD(uint16_t, r, 8) = w->model;                 /* mModelID: weapon\w05\mbgNNN */
        FIELD(uint16_t, r, 10) = 1;                       /* mSrqrNo: weapon\w05\snd\001 (GS's, sounds phase) */
        FIELD(uint8_t, r, 13) = 1; FIELD(uint8_t, r, 14) = 0;    /* one level */
        FIELD(uint8_t, r, 15) = w->rare;
        FIELD(uint32_t, r, 16) = MS_PRICE;
        FIELD(uint8_t, r, 21) = w->element;
        FIELD(uint16_t, r, 24) = (uint16_t)id;            /* mSortID */
        for (int i = 28; i < 38; i++) r[i] = 0;           /* no upgrades */
        FIELD(uint16_t, r, 0x26) = (uint16_t)id;          /* its level row */
        for (int i = 0; i < 20; i++) l[i] = row[i];
        FIELD(uint32_t, l, 4) = id; FIELD(uint8_t, l, 8) = (uint8_t)id; FIELD(uint8_t, l, 9) = 1;
        FIELD(uint8_t, l, 10) = (uint8_t)(ms_kire_base ? ms_kire_base + w->kire : 106);   /* kireaji row (GU's
                                                                           endgame GS's if ours were refused) */
        FIELD(uint8_t, l, 11) = 10;                                      /* bar length step */
        FIELD(uint16_t, l, 12) = w->raw;
        FIELD(uint8_t, l, 14) = 0; FIELD(uint8_t, l, 15) = 0;            /* defense, affinity (MHF: 0) */
        FIELD(uint16_t, l, 16) = w->elem;
        FIELD(uint8_t, l, 18) = 3;                                       /* slots */
    }
    s_records = 1;
    logf("msport: %u type-12 weapons from Great Sword 1's records", (uint32_t)MS_NWEAPONS);
}

int ms_base_c(uint32_t *regs)                /* 0x13c208 (sEquip, type, id) -> base record */
{
    if (regs[R1] != MS_TYPE) return 0;
    if (!s_records) build_records((void *)regs[R0]);
    regs[R0] = s_records > 0 && regs[R2] < MS_NWEAPONS ? (uint32_t)(uintptr_t)s_base[regs[R2]] : 0;
    return 1;
}

int ms_level_c(uint32_t *regs)               /* 0x13ed08 (sEquip, type, row) -> level row */
{
    if (regs[R1] != MS_TYPE) return 0;
    if (!s_records) build_records((void *)regs[R0]);
    regs[R0] = s_records > 0 && regs[R2] < MS_NWEAPONS ? (uint32_t)(uintptr_t)s_level[regs[R2]] : 0;
    return 1;
}

/* the smithy (static research, phase3.md "Smithy"): its create / process getters 0x6f9658 / 0x70153c (this, type,
 * row) switch on the box type and answer 0 for 12. Our rows: rWeaponCreateData (44 B, vtable 0x1768234) per forged
 * weapon: level 1, no unlock condition, no key material (S: always listed; GU's own recipes key on material 1),
 * no provision, no scraps; rWeaponProcessData (36 B, vtable 0x17682e4): the all-zero level-1 row of a weapon with no
 * parent (as tools/weapons4u.py's created weapons) */
struct ms_create { uint32_t vt; uint16_t lv, no, disp, item[4]; uint8_t num[4], key[4]; uint16_t cat, rank,
                   piece[3], piece_num[3], pad; };
struct ms_process { uint32_t vt; uint16_t no, lv, item[4]; uint8_t num[4]; uint16_t cat, rank, piece[3],
                    piece_num[3]; };
static struct ms_create s_create[MS_NFORGED];
static struct ms_process s_process[MS_NFORGED];
static int s_rows;

static void build_rows(void)
{
    for (uint32_t k = 0; k < MS_NFORGED; k++) {
        const struct ms_weapon *w = &s_weapons[MS_FIRST_FORGED + k];
        struct ms_create *c = &s_create[k];
        struct ms_process *pr = &s_process[k];
        c->vt = MAIN(0x1768234); c->lv = 1; c->no = (uint16_t)(MS_FIRST_FORGED + k);
        for (int j = 0; j < 4; j++) { c->item[j] = w->item[j]; c->num[j] = w->num[j]; }
        pr->vt = MAIN(0x17682e4); pr->no = c->no; pr->lv = 1;
    }
    s_rows = 1;
}

int ms_forge_create_c(uint32_t *regs)       /* 0x6f9658 (smithy, type, row) -> create row */
{
    if (regs[R1] != MS_TYPE) return 0;
    if (!s_rows) build_rows();
    regs[R0] = regs[R2] < MS_NFORGED ? (uint32_t)(uintptr_t)&s_create[regs[R2]] : 0;
    return 1;
}

int ms_forge_process_c(uint32_t *regs)      /* 0x70153c (smithy, type, row) -> process row */
{
    if (regs[R1] != MS_TYPE) return 0;
    if (!s_rows) build_rows();
    regs[R0] = regs[R2] < MS_NFORGED ? (uint32_t)(uintptr_t)&s_process[regs[R2]] : 0;
    return 1;
}

/* the forge's category menu (build.py MS_LIT_PATCHES repoint its code here; the count byte 14 -> 15 is a word
 * patch): category index -> box type (GU's u8[14] at 0x1650022 + the Magnet Spike, page 3), labels (LbShop_
 * EqMakeMsg IDs, 7 read per page: 21 entries; 206 = our appended "Magnet Spike"), and the top panel's icon lists
 * by kind (GU's pointer table 0x176f3e4, kind 8 = the weapon categories: GU's 14 icons + MS_ICON_ID: ms_icon_rect) */
#define MS_ICON_ID 121
const uint8_t ms_forge_order[15] = {7, 14, 8, 18, 9, 19, 10, 16, 15, 21, 20, 13, 11, 17, MS_TYPE};
const uint16_t ms_forge_label[21] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 206, 206, 206, 206, 206, 206,
                                     206};
static const uint8_t s_weapon_icons[21] = {0x37, 0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x43, 0x45, 0x44, 0x3f,
                                           0x41, 0x42, MS_ICON_ID, 0x46, 0x47, 0x49, 0x48, 0x4a, 0};
uint32_t ms_shop_icons[10];
#define MS_LABEL_COUNT 206          /* LbShop_EqMakeMsg's strings: "Magnet Spike" appended as 206 */

/* hook 0x560920: GU's icon rectangle 0x560918(_, kind, icon, float out[4]) after its kind check. Kinds 0 / 1 (the
 * 16 / 24-unit equipment icons of HD_cmn_icon, in a 256 x 512 space) put icons < 95 on a 10-column grid and 95..106
 * at a position list (0x162e208 / 0x162e1a0); every grid cell is taken in GU's and HD UI's atlases, and icon 121 read
 * past the list (test 2: a piece of other icons). MS_ICON_ID = a spot empty in both atlases, where
 * tools/ms_icon_hdui.py paints MHF's icon; out = 2x units as GU writes them (its 512 x 1024 atlas) */
int ms_icon_rect_c(uint32_t *regs)
{
    static const uint16_t at[2][3] = {{184, 48, 16}, {208, 32, 24}};    /* ms_icon_hdui.py SPOTS */
    if (regs[R1] > 1 || regs[R2] != MS_ICON_ID) return 0;
    const uint16_t *a = at[regs[R1]];
    float *r = (float *)regs[R3];
    r[0] = 2.0f * a[0], r[1] = 2.0f * a[1], r[2] = 2.0f * (a[0] + a[2]), r[3] = 2.0f * (a[1] + a[2]);
    return 1;
}

static void forge_tables_init(void)
{
    const uint32_t *gu = (const uint32_t *)MAIN(0x176f3e4);
    for (int k = 0; k < 10; k++) ms_shop_icons[k] = gu[k];
    ms_shop_icons[8] = (uint32_t)(uintptr_t)s_weapon_icons;
}

/* texts (items.c, every rGUIMessage load): the forge label appended to LbShop_EqMakeMsg; CommonMsg's class-5 name
 * (string 90, "Med. Bowgun (Removed)") replaced. English in every language (S) */
static int name_is(const char *s, const char *base)     /* base, or base + "_<lang>" */
{
    while (*base) if (*s++ != *base++) return 0;
    return *s == 0 || *s == '_';
}
typedef void *(*res_alloc_t)(void *res, uint32_t size);
void ms_text_loaded(uint8_t *m, const char *name, uint32_t lang)
{
    (void)lang;
    uint32_t count = FIELD(uint32_t, m, 0x88);
    const char **old = FIELD(const char **, m, 0x98);
    if (!name || !old) return;
    if (name_is(name, "CommonMsg") && count > 90) {
        logf("msport: CommonMsg 90 \"%s\" -> Magnet Spike", old[90]);
        old[90] = "Magnet Spike";
        return;
    }
    if (!name_is(name, "LbShop_EqMakeMsg")) return;
    if (count != MS_LABEL_COUNT) { logf("msport: %s has %u strings, not %u: no forge label", name, count, MS_LABEL_COUNT); return; }
    const char **arr = ((res_alloc_t)(*(uint32_t **)m)[0x40 / 4])(m, (count + 1) * 4);   /* the load's allocator */
    if (!arr) return;
    for (uint32_t i = 0; i < count; i++) arr[i] = old[i];
    arr[count] = "Magnet Spike";
    FIELD(const char **, m, 0x98) = arr;
    FIELD(uint32_t, m, 0x88) = count + 1;
    logf("msport: forge label appended to %s (%u)", name, count);
}

/* pwl getters (sEquip, class, model[, k]): class 5 has no rPlayerWeaponList. mGmkMotNo = 0 (weapon\w05\g00); the
 * display / carry types and sub-parameters are Great Sword model 1's (Phase 2 stand-in) */
static int pwl(uint32_t *regs)
{
    if (regs[R1] != MS_CLASS) return 0;
    regs[R1] = 0; regs[R2] = 1;
    return 0;
}
int ms_pwl_gmk_c(uint32_t *regs)                           /* 0x13f554 */
{
    if (regs[R1] != MS_CLASS) return 0;
    regs[R0] = 0;
    return 1;
}
int ms_pwl_disp_c(uint32_t *regs) { return pwl(regs); }    /* 0x13f594 */
int ms_pwl_carry_c(uint32_t *regs) { return pwl(regs); }   /* 0x13f5d4 */
int ms_pwl_sub_c(uint32_t *regs) { return pwl(regs); }     /* 0x13f614 */

/* the item box (0x14b0b0 loads it raw: 2000 entries of 0x2c B from box + 0x1c; +4 u16 type (low 5 bits), +6 u16
 * weapon ID): a test build adds Magnet Spike ID 1 to the first empty entry when no type-12 entry exists */
static uint8_t *s_box;
int ms_box_ptr_c(uint32_t *regs) { s_box = (uint8_t *)regs[R0]; return 0; }   /* 0x14b0b0 entry */
int ms_box_loaded_c(uint32_t *regs)                                             /* 0x3e7804: after the load */
{
    (void)regs;
    if (!s_box) return 0;
    int empty = -1;
    for (int k = 0; k < 2000; k++) {
        uint8_t *e = s_box + 0x1c + 0x2c * k;
        uint32_t ty = FIELD(uint16_t, e, 4) & 0x1f;
        if (ty == MS_TYPE) { logf("msport: box entry %d holds Magnet Spike %u", k, FIELD(uint16_t, e, 6)); return 0; }
        if (!ty && empty < 0) empty = k;
    }
    if (empty < 0) { logf("msport: item box full: no Magnet Spike added"); return 0; }
    uint8_t *e = s_box + 0x1c + 0x2c * empty;
    FIELD(uint16_t, e, 4) = MS_TYPE; FIELD(uint16_t, e, 6) = 1;
    logf("msport: Magnet Spike 1 added to box entry %d (test build)", empty);
    return 0;
}

/* diagnostic: every bank motion a class-5 hunter asks for (0x281998 entry: p, motion), once per motion and action */
int ms_motion_c(uint32_t *regs)
{
    uint8_t *p = (uint8_t *)regs[R0];
    uint8_t *info = p ? FIELD(uint8_t *, p, 0x13c4) : 0;
    if (!info || info[0x4d4] != MS_CLASS) return 0;
    static uint32_t s_seen[64];
    static int s_n;
    uint32_t key = regs[R1] << 16 | FIELD(uint16_t, p, 0x250a);
    for (int i = 0; i < s_n; i++) if (s_seen[i] == key) return 0;
    if (s_n < 64) s_seen[s_n++] = key;
    logf("msport: motion %u in action %u/%u (lr %x)", regs[R1], FIELD(uint16_t, p, 0x2506), FIELD(uint16_t, p, 0x250a),
         regs[LR] - MAIN_BASE);
    return 0;
}
