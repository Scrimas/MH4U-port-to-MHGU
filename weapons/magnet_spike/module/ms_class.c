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

struct ms_state *ms_of(uint8_t *p)
{
    struct ms_state *free_ = 0;
    for (int i = 0; i < MS_PLAYERS; i++) {
        if (s_state[i].p == p) return &s_state[i];
        if (!s_state[i].p && !free_) free_ = &s_state[i];
    }
    if (!free_) free_ = &s_state[0];
    for (uint32_t i = 0; i < sizeof *free_; i++) ((uint8_t *)free_)[i] = 0;
    free_->p = p;
    return free_;
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
static void reset_state(uint8_t *p, int k) { (void)k; struct ms_state *s = ms_of(p); s->charged = 0; s->fired = 0; }
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
    struct ms_state *s = ms_of(obj);
    s->mode = 0;
    logf("msport: class 5 object %x (Great Sword layout), vtable %x", (uint32_t)(uintptr_t)obj,
         (uint32_t)(uintptr_t)ms_vt);
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
static const float s_grip[8];                       /* the hand record: no offset, no rotation */

int ms_attach_c(uint32_t *regs)
{
    uint8_t *w = (uint8_t *)regs[R0], *pl = (uint8_t *)regs[R1];
    uint8_t *info = pl ? FIELD(uint8_t *, pl, 0x13c4) : 0;
    if (!info || info[0x4d4] != MS_CLASS || IS_PROWLER(pl)) return 0;
    if (FIELD(uint32_t, pl, 0x13c8) != 0) return 0; /* not the quest class: on the back (0x308834 answers 2) */
    uint32_t st = ATTACH_STATE(0, pl, regs[R2]);
    int hand = st != 2 && (CUR_MOTION(pl) / 1000 == 5 || state178(pl));
    static int s_n, s_last = -1;
    if (hand != s_last && s_n < 100) {
        s_n++;
        logf("msport: weapon %s (state %u, motion %u)", hand ? "in hand (joint 8)" : "on GS's carry", st,
             CUR_MOTION(pl));
    }
    s_last = hand;
    if (!hand) return 0;
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
 * Impact motions (msbuild COMMON). Only our class object (its vtable) is read. */
int ms_setmotion_c(uint32_t *regs)
{
    uint8_t *u = (uint8_t *)regs[R0];
    if (!u || *(uint32_t **)u != ms_vt || ms_of(u)->mode != 1) return 0;
    if (regs[R1] == 5001) regs[R1] = 5020;
    else if (regs[R1] == 5004) regs[R1] = 5024;
    return 0;
}

/* ------------------------------------------------------------------------------------------------ equipment */

#define VT_BASE_GS 0x173791cu       /* rWeapon00BaseData record vtable, 90 slots; +0x18 = box type */
#define BASE_SLOTS 90
typedef uint8_t *(*getter_t)(void *equip, uint32_t type, uint32_t id);
#define GET_BASE FN(getter_t, 0x13c208)
#define GET_LEVEL FN(getter_t, 0x13ed08)
static uint32_t s_base_vt[2 + BASE_SLOTS];
static uint32_t s_base[2][16];      /* 40-B records: IDs 0 (the equip fallback's dummy) and 1 */
static uint32_t s_level[8];         /* one 20-B level row, shared */
static int s_records;               /* 0 none, 1 built, -1 failed */
static uint32_t ms_box_type(void) { return MS_TYPE; }

static void build_records(void *equip)
{
    uint8_t *gs = GET_BASE(equip, 7, 1);
    uint8_t *row = gs ? GET_LEVEL(equip, 7, FIELD(uint16_t, gs, 0x26)) : 0;
    if (!gs || !row) { s_records = -1; logf("msport: Great Sword 1 records missing: no type-12 records"); return; }
    const uint32_t *vt = *(const uint32_t **)gs;
    for (int i = 0; i < 2 + BASE_SLOTS; i++) s_base_vt[i] = vt[i - 2];
    s_base_vt[2 + 0x18 / 4] = (uint32_t)(uintptr_t)ms_box_type;
    for (int id = 0; id < 2; id++) {
        uint8_t *r = (uint8_t *)s_base[id];
        for (int i = 0; i < 40; i++) r[i] = gs[i];
        *(uint32_t **)r = s_base_vt + 2;
        FIELD(uint32_t, r, 4) = id;                       /* mIndex */
        FIELD(uint16_t, r, 8) = 1; FIELD(uint16_t, r, 10) = 1;   /* mModelID / mSrqrNo: weapon\w05\001 */
        FIELD(uint8_t, r, 13) = 1; FIELD(uint8_t, r, 14) = 0;    /* one level */
        for (int i = 28; i < 38; i++) r[i] = 0;           /* no upgrades */
        FIELD(uint16_t, r, 0x26) = 0;                     /* first level row */
    }
    uint8_t *l = (uint8_t *)s_level;
    for (int i = 0; i < 20; i++) l[i] = row[i];
    FIELD(uint32_t, l, 4) = 0; FIELD(uint8_t, l, 8) = 1; FIELD(uint8_t, l, 9) = 1;
    FIELD(uint16_t, l, 12) = 200;   /* Phase 2 test raw (MHF Proto Spike : a has 450 on MHF's scale; Phase 5) */
    s_records = 1;
    logf("msport: type-12 records from Great Sword 1 (row %u, sharpness type %u)", FIELD(uint16_t, gs, 0x26), l[10]);
}

int ms_base_c(uint32_t *regs)                /* 0x13c208 (sEquip, type, id) -> base record */
{
    if (regs[R1] != MS_TYPE) return 0;
    if (!s_records) build_records((void *)regs[R0]);
    regs[R0] = s_records > 0 && regs[R2] < 2 ? (uint32_t)(uintptr_t)s_base[regs[R2]] : 0;
    return 1;
}

int ms_level_c(uint32_t *regs)               /* 0x13ed08 (sEquip, type, row) -> level row */
{
    if (regs[R1] != MS_TYPE) return 0;
    if (!s_records) build_records((void *)regs[R0]);
    regs[R0] = s_records > 0 ? (uint32_t)(uintptr_t)s_level : 0;
    return 1;
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
