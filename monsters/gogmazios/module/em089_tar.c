/* em089 tar material animations: port of the animation side of 4U slot 39 [0x8b9e10..0x8ba09c] (spawn) and of
 * the per-frame switcher 0x8c8da0, on the GU material-animation API (em089_tar.h, tools/mrl_anim.py).
 * 4U keeps the animation indices of the type-1 material for all five (same entry order); here each material is
 * searched by name, so the order does not matter. Per-monster state lives in a small table keyed by `self`
 * (the object layout after the base belongs to em089_act.c). */
#include "game.h"
#include "util.h"
#include "em089_tar.h"

typedef int (*tar_find_t)(void *animset, const char *name);
typedef void (*tar_play_t)(void *mat, int slot, int index);
typedef int (*tar_cur_t)(void *mat, int slot);
#define tar_find FN(tar_find_t, TAR_GU_FIND_ANIM)
#define tar_play FN(tar_play_t, TAR_GU_PLAY_ANIM)
#define tar_cur  FN(tar_cur_t, TAR_GU_CUR_ANIM)

#define TAR_PARTS 5
#define TAR_SLOTS 4      /* simultaneous em089 instances tracked */
#define TAR_MATS  24     /* material indices tracked by the advance check (em089_00 has 15: 5 + 2 per tar part) */

/* names in one blob + byte offsets (pointer tables would need data relocations; clang turns switches into them):
 * [from * 3 + to] = transition (4U 0x8c8da0, T+0x68..), [from * 3 + from] = steady animation of `from` */
static const char s_names[] = "Solid\0Liquid\0Gas\0Sol_to_Liq\0Sol_to_Gas\0Liq_to_Sol\0Liq_to_Gas\0Gas_to_Sol\0"
                              "Gas_to_Liq";
static const uint8_t s_name_off[9] = {0, 17, 28, 39, 6, 50, 61, 72, 13};

static const char *tar_steady_name(uint32_t mode) { return s_names + s_name_off[(mode % 3) * 4]; }
static const char *tar_trans_name(uint32_t from, uint32_t to)
{
    return (from < 3 && to < 3 && from != to) ? s_names + s_name_off[from * 3 + to] : 0;
}

typedef struct {
    void *self;
    uint8_t cur[TAR_PARTS], target[TAR_PARTS];
    /* slot-0 frame seen last call, per material index (engine-advance detection). Per material, not per part:
     * every tar part has 2 materials (vertex-alpha classes, tools/mod4u2gu.py) playing in step, and a per-part
     * value written by the first one made the second look stalled -> advanced twice per frame. */
    float last_frame[TAR_MATS];
    uint32_t ticks, forced;           /* calls; calls where we advanced the materials ourselves */
    uint8_t wing_busy;                /* 4U T+0xa0: a wing transition is playing */
} tar_state_t;
static tar_state_t s_tar[TAR_SLOTS];

static tar_state_t *tar_get(void *self, int create)
{
    tar_state_t *free_slot = 0;
    for (int i = 0; i < TAR_SLOTS; i++) {
        if (s_tar[i].self == self) return &s_tar[i];
        if (!s_tar[i].self && !free_slot) free_slot = &s_tar[i];
    }
    if (!create) return 0;
    if (!free_slot) free_slot = &s_tar[0];       /* more than TAR_SLOTS em089 at once: reuse the first */
    free_slot->self = self;
    return free_slot;
}

/* tar part k (0..4) of a material object, or -1 (not a tar material / no animation set) */
static int tar_part(void *mat, void **set)
{
    if (!mat) return -1;
    uint32_t type = (FIELD(uint32_t, mat, TAR_MAT_TYPE_WORD) >> 22) & 0xff;
    *set = FIELD(void *, mat, TAR_MAT_ANIMSET);
    if (type < 1 || type > TAR_PARTS || !*set) return -1;
    return (int)type - 1;
}

static uint32_t tar_frames(void *set, int index)
{
    uint32_t *list = FIELD(uint32_t *, set, 0x10);
    if (!list || index < 0 || (uint32_t)index >= list[0]) return 0;
    uint32_t *entry = (uint32_t *)list[1 + index];
    return entry ? entry[0] : 0;
}

typedef void (*tar_mat_update_t)(void *mat, float dt);
#define tar_mat_update FN(tar_mat_update_t, TAR_GU_MAT_UPDATE)

/* The engine advances material animations only while this+0x168 != 0 (em089_tar.h). If a tar material's frame
 * did not move since the previous call although it should (looping, or not yet at its last frame), advance it
 * here with the monster's dt. Logs the state every ~10 s (first at call 30). */
static void tar_advance(void *self, tar_state_t *st, void **arr, int n)
{
    float dt = FIELD(float, self, TAR_EN_DT);
    int stalled = 0, moving = 0;
    st->ticks++;
    for (int i = 0; arr && i < n; i++) {
        void *set;
        int k = tar_part(arr[i], &set);
        if (k < 0 || i >= TAR_MATS) continue;
        int now = tar_cur(arr[i], 0);
        float f = FIELD(float, arr[i], TAR_MAT_FRAME0);
        if (now >= 0) {
            uint32_t frames = tar_frames(set, now);
            uint32_t *list = FIELD(uint32_t *, set, 0x10);
            uint32_t loop = (list && (uint32_t)now < list[0]) ? (((uint32_t *)list[1 + now])[1] & 1) : 0;
            if (f == st->last_frame[i] && dt > 0.0f && (loop || f < (float)frames) && frames > 1) {
                tar_mat_update(arr[i], dt);
                f = FIELD(float, arr[i], TAR_MAT_FRAME0);
                stalled++;
            } else if (f != st->last_frame[i]) moving++;
        }
        st->last_frame[i] = f;
        if (st->ticks % 300 == 30 && k == 0)
            logf("gogport: em089 tar anim: on %u flags1404 %x dt %x speed %x part0 anim %d frame %x",
                 FIELD(uint8_t, self, TAR_EN_MATANIM_ON), FIELD(uint32_t, self, 0x1404),
                 FIELD(uint32_t, self, TAR_EN_DT), FIELD(uint32_t, arr[i], TAR_MAT_SPEED), now,
                 FIELD(uint32_t, arr[i], TAR_MAT_FRAME0));
    }
    if (stalled) st->forced++;
    if (st->ticks % 300 == 30)
        logf("gogport: em089 tar anim: calls %u forced %u (this call: stalled %d moving %d)", st->ticks, st->forced,
             stalled, moving);
}

static void tar_play_name(void *mat, void *set, const char *name)
{
    int idx = tar_find(set, name);
    if (idx >= 0) tar_play(mat, 0, idx);
}

void em089_tar_spawn(void *self)
{
    tar_state_t *st = tar_get(self, 1);
    for (int k = 0; k < TAR_PARTS; k++) st->cur[k] = st->target[k] = (k < 2) ? TAR_LIQUID : TAR_SOLID;
    int n = FIELD(int32_t, self, TAR_MAT_COUNT), found = 0;
    void **arr = FIELD(void **, self, TAR_MAT_ARRAY);
    for (int i = 0; arr && i < n; i++) {
        void *set;
        int k = tar_part(arr[i], &set);
        if (k < 0) continue;
        found++;
        tar_play_name(arr[i], set, k < 2 ? "Liquid" : "Liq_to_Sol");
        logf("gogport: em089 tar mat %d part %d set %x Solid %d Liquid %d -> slot0 %d", i, k, (uint32_t)set,
             tar_find(set, "Solid"), tar_find(set, "Liquid"), tar_cur(arr[i], 0));
    }
    logf("gogport: em089 tar spawn: %d materials, %d tar", n, found);
}

uint32_t em089_tar_update(void *self)
{
    uint32_t entered = 0;                        /* 4U slot 50: steady Solid started (head / tail bits) */
    tar_state_t *st = tar_get(self, 0);
    if (!st) {                                   /* spawn hook not run (or before the model): default modes */
        st = tar_get(self, 1);
        for (int k = 0; k < TAR_PARTS; k++) st->cur[k] = st->target[k] = (k < 2) ? TAR_LIQUID : TAR_SOLID;
    }
    int n = FIELD(int32_t, self, TAR_MAT_COUNT);
    void **arr = FIELD(void **, self, TAR_MAT_ARRAY);
    for (int i = 0; arr && i < n; i++) {
        void *set;
        int k = tar_part(arr[i], &set);
        if (k < 0) continue;
        uint32_t cur = st->cur[k], tgt = st->target[k];
        if (cur != tgt) {                                /* mode changed: transition */
            const char *name = tar_trans_name(cur, tgt);
            if (name) tar_play_name(arr[i], set, name);
            continue;
        }
        int steady = tar_find(set, tar_steady_name(cur));
        int now = tar_cur(arr[i], 0);
        if (steady < 0 || now == steady) continue;
        uint32_t frames = now >= 0 ? tar_frames(set, now) : 0;
        float last = frames > 1 ? (float)(frames - 1) : 0.0f;
        if (now < 0 || FIELD(float, arr[i], TAR_MAT_FRAME0) >= last) {
            tar_play(arr[i], 0, steady);
            if (cur == TAR_SOLID) entered |= 1u << k;
        }
    }
    for (int k = 0; k < TAR_PARTS; k++) st->cur[k] = st->target[k];
    tar_advance(self, st, arr, n);
    return entered;
}

void em089_tar_set_mode(void *self, uint32_t k, uint32_t mode)
{
    if (k >= TAR_PARTS || mode > TAR_GAS) return;
    tar_state_t *st = tar_get(self, 1);
    st->target[k] = (uint8_t)mode;
}

void em089_tar_set_part(void *self, uint32_t mode, uint32_t part)
{
    /* 4U parts 0, 7, 2, 3, 6 -> k 0..4 */
    int k = part == 0 ? 0 : part == 7 ? 1 : part == 2 ? 2 : part == 3 ? 3 : part == 6 ? 4 : -1;
    if (k >= 0) em089_tar_set_mode(self, (uint32_t)k, mode);
}

int em089_tar_mode(void *self, uint32_t k)
{
    tar_state_t *st = tar_get(self, 0);
    return (st && k < TAR_PARTS) ? st->cur[k] : -1;
}

/* ---- wing size / lights (em089_tar.h) */
#define TAR_MAT_TYPE_WING   50
#define TAR_MAT_TYPE_LIGHTS 6

static void *tar_mat_of_type(void *self, uint32_t type, void **set)
{
    int n = FIELD(int32_t, self, TAR_MAT_COUNT);
    void **arr = FIELD(void **, self, TAR_MAT_ARRAY);
    for (int i = 0; arr && i < n; i++) {
        if (!arr[i] || ((FIELD(uint32_t, arr[i], TAR_MAT_TYPE_WORD) >> 22) & 0xff) != type) continue;
        *set = FIELD(void *, arr[i], TAR_MAT_ANIMSET);
        if (*set) return arr[i];
    }
    return 0;
}

static const char s_wing[] = "Small\0SmalltoLarge\0LargetoSmall\0Large";   /* 4U table 0xff6fa4 order */
static const uint8_t s_wing_off[4] = {0, 6, 19, 32};
#define WING_SMALL 0
#define WING_S2L   1
#define WING_L2S   2
#define WING_LARGE 3

/* 4U 0x94d7a8 (same test as em089_act.c tar_dead): action category 11 or 14, or 12/255 */
static int wing_dead(void *self)
{
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT);
    return cat == 11 || cat == 14 || (cat == 12 && FIELD(uint8_t, self, EN_ACT_NUM) == 255);
}

int em089_wing_update(void *self)
{
    void *set, *mat = tar_mat_of_type(self, TAR_MAT_TYPE_WING, &set);
    tar_state_t *st = tar_get(self, 1);
    if (!mat) return 0;
    int idx[4];
    for (int k = 0; k < 4; k++) idx[k] = tar_find(set, s_wing + s_wing_off[k]);
    int ret = 0, start = -1;
    uint32_t m = curMotion(self) & 0xffff;
    if (m == 0x108) {
        if (motionCheck(self, 0, 0, 148.0f, 0.0f)) { start = WING_S2L; ret = EM089_WING_SET; }
    } else if (m == 0x10b) {
        if (motionCheck(self, 0, 0, 128.0f, 0.0f)) { start = WING_L2S; ret = EM089_WING_CLEAR; }
    } else if (m == 0x30b || m == 0x30c) {
        if (motionCheck(self, 0, 0, 30.0f, 0.0f)) { start = WING_L2S; ret = EM089_WING_CLEAR; }
    } else if (FIELD(uint8_t, FIELD(uint8_t *, self, EN_RECORD), REC_STATE) == 0 && !wing_dead(self) &&
               tar_cur(mat, 0) == idx[WING_LARGE] && idx[WING_LARGE] >= 0) {
        start = WING_L2S; ret = EM089_WING_CLEAR;
    }
    if (start >= 0 && idx[start] >= 0) {
        tar_play(mat, 0, idx[start]);                    /* frame 0 (4U also stores 0.0 to the frame) */
        st->wing_busy = 1;
    }
    if (st->wing_busy) {                                 /* transition finished -> steady state */
        int now = tar_cur(mat, 0);
        float f = FIELD(float, mat, TAR_MAT_FRAME0);
        int next = (now >= 0 && now == idx[WING_S2L]) ? WING_LARGE : (now >= 0 && now == idx[WING_L2S]) ? WING_SMALL : -1;
        if (next >= 0 && f >= (float)tar_frames(set, now) && idx[next] >= 0) {
            tar_play(mat, 0, idx[next]);
            st->wing_busy = 0;
        }
    }
    return ret;
}

static const char s_light[] = "Light_Gas_Bress\0Light_Gas_Bress_End\0Light_Wing_Attack_back\0Light_Wing_Attack\0"
                              "Light_Wing_Attack_gekiryusou\0Light_Wing_Attack_houdai\0Light_Tail_Attack01\0"
                              "Light_Tail_Attack02";
static const uint8_t s_light_off[8] = {0, 16, 36, 59, 77, 106, 131, 151};

void em089_light_play(void *self, int k)
{
    void *set, *mat = tar_mat_of_type(self, TAR_MAT_TYPE_LIGHTS, &set);
    if (!mat) return;
    tar_play(mat, 0, (k >= 0 && k < 8) ? tar_find(set, s_light + s_light_off[k]) : -1);
}
