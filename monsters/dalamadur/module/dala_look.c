/* The head's look system (goal E): the neck / head joints turn toward the target during the 7.x attacks.
 * C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4. 4U W = [this+0xe28].
 *
 * Per frame, both games, same order (C): the update clears mode / fixed flag and sets rate 0.015 (4U 0x90eb88 from
 * the base update 0x94d26c; GU 0xa5198 from the uEnemy update 0xadb3c at 0xadba4, unconditional), then the action
 * runs (GU 0xa59fc -> slot 125), then the look (4U 0x9104b8 at 0x94d5f4; GU 0xa79f8 at 0xae218, skipped only while
 * this+0x7648 != 0, G: meaning). So mode 3 and the set-up hold only on the frames a handler writes them; on the
 * other frames mode 0 relaxes every look joint toward 0 (apply(0) with the records' limits as shares).
 * Look 0x9104b8 = GU 0xa79f8 (C, compared instruction by instruction): mode 2 -> nothing; mode 0 -> apply(0);
 * else origin = the fixed origin when the flag is set, else the first look joint's position (0x93093c = GU jointPos
 * 0xc1708) or the body position, and then look point = target slot 0 (0x93e974 = GU 0xc2884) and yaw reference =
 * the body yaw (4U W+0x1ac, GU rec+0x54); angle = s16(atan2(point - origin) - yaw reference) -> apply.
 * Apply 4U 0x9342b8 = GU 0xa7bac (C): sum = the shares of the kind-1 records (mode 3: step table [angle >= 0 ? + :
 * -][index], else the record limit); angle clamped to +-sum; per record target = angle * share / sum, current
 * angle steps toward it by u32(share * rate * frame delta) (4U this+0x14, GU this+0x1c).
 * Fields, 4U W -> GU object (C, both functions and the 4U handlers): */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_look.h"

#define LK_ANGLE  0x7520   /* s16[6] current angle per table index        [W+0x79be] (C: 0xa7d4c / 0x9343e0) */
#define LK_POS    0x752c   /* u16[6] shares, angle >= 0                    [W+0x79fc] */
#define LK_NEG    0x7538   /* u16[6] shares, angle < 0                     [W+0x7a08] */
#define LK_RATE   0x7544   /* float step rate (update: 0.015)              [W+0x79cc] (C: 0xa7d34 / 0x93440c) */
#define LK_MODE   0x7548   /* u8 0 relax, 2 hold, 3 tables, else limits    [W+0x79d0] */
#define LK_FIXED  0x7549   /* u8 1 = origin / yaw reference fixed below    [W+0x79d1] */
#define LK_ORIGIN 0x7550   /* float[4] fixed origin                        [W+0x79e8] */
#define LK_POINT  0x7560   /* float[4] look point                          [W+0x79d8] */
#define LK_YAW    0x7570   /* u32 yaw reference (u16 angle)                [W+0x79f8] */
/* spawn 0xb8c54 zeroes +0x7520..+0x7548 (bzero 41 at 0xb99ec) and sets point / origin / yaw (C) */

/* GU 0xc2884(this, vec, slot) = 4U 0x93e974 (C, same structure): vec != NULL -> point = vec, else point = target
 * slot `slot` (kinds 0 / 3..7 / 9 / 10: rec+464 + 16 slot; 1 / 2: that hunter / monster's position) */
typedef void (*lookPoint_t)(void *self, const float *vec, uint32_t slot);
#define lookPoint  FN(lookPoint_t, 0xc2884)
/* GU 0xa7ff8(this): for every model joint (count this+0x490, 0xa0-byte joints at this+0x494, id byte +0x93) that a
 * kind-1 look record (or GU's two other joint lists 0xc1a20 / 0xc1af8) names, 0x94d770(joint, this+0xb740): joint
 * +4 = the joint callback, flag bits up the parent chain (idempotent, C). The callback 0xab1a0 rotates a joint by
 * LK_ANGLE[index] when a kind-1 record names it (index <= 5, angle != 0, C). Only the spawn setup runs it (0xb9910,
 * before slot 118 at 0xba2d4), while the list is still Kushala's empty one: run again after the install. */
#define lookJoints FN(void (*)(void *), 0xa7ff8)
#define EN_JOINT_N    0x490
#define EN_JOINTS     0x494
#define JOINT_SIZE    0xa0
#define JOINT_CB      0x4
#define JOINT_ID      0x93
#define EN_JOINT_CB   0xb740   /* the callback object the joints point to */

/* the dtbparts object (enemy+0x75f0, shared by the four arcs: dala_break.c): look records +0x68 (16 bytes {s32
 * joint, u8 kind, pad, s32 index +8, s32 limit +0xc}), u8 count +0x8d (loader 0x5575c: new[16 n] at 0x55a78, C);
 * the resource's clear 0x56180 frees +0x68 with delete[] (0x561ac, C) */
#define EN_DTBPARTS   0x75f0
#define DTP_LOOK      0x68
#define DTP_LOOK_N    0x8d
#define gu_new    FN(void *(*)(uint32_t), 0x7af3a0)
#define gu_delete FN(void (*)(void *), 0x7af3e4)

/* 4U list: 0x94c590 = species row (0x688854) +0x84 = em_data emd file word 35 (+0x8c; the row is the file + 8,
 * as the part table row +0x78 = word 32 in dala_break.c), 0x18-byte records {s32 joint, u8 kind, pad, s32 index,
 * s32 limit, u8 0xff, pad} closed by joint -1 (0x910524 / 0x934474, C). GU record = the 4U record's first 16 bytes,
 * count = records before the closer (C: 34 of the 40 monsters in both games, every one with a non-empty GU list
 * among em001 / 002 / 005 / 006 / 021 / 022 / 023 / 027 / 088 / 099 / 105 byte-equal; the 6 others are GU-authored
 * lists of remodelled monsters). em024 = em110 (C, identical): */
#define N_LOOK 6
static const uint32_t k_look[N_LOOK][4] = {
    {103, 1, 0, 364}, {104, 1, 1, 364}, {105, 1, 2, 364}, {106, 1, 3, 364}, {107, 1, 4, 364}, {5, 1, 5, 728},
};

static void *s_dtp;   /* the object the records went into */

static int install_list(uint8_t *obj)
{
    uint32_t *old = FIELD(uint32_t *, obj, DTP_LOOK);
    uint32_t n = obj[DTP_LOOK_N], same = (n == N_LOOK && old);
    for (uint32_t i = 0; same && i < 4 * N_LOOK; i++) {
        uint32_t v = old[i];
        if (i % 4 == 1) v &= 0xff;   /* the kind is a byte, +5..+7 are not loaded */
        same = v == k_look[i / 4][i % 4];
    }
    if (same) return 1;
    uint32_t *mem = gu_new(16 * N_LOOK);
    if (!mem) { logf("dalaport: look list: alloc failed"); return 0; }
    for (uint32_t i = 0; i < 4 * N_LOOK; i++) mem[i] = k_look[i / 4][i % 4];
    FIELD(uint32_t *, obj, DTP_LOOK) = mem;
    obj[DTP_LOOK_N] = N_LOOK;
    logf("dalaport: look list: dtbparts %x had %u (first joint %d kind %u), now %u", (uint32_t)obj, n,
         n && old ? (int32_t)old[0] : 0, n && old ? old[1] & 0xff : 0, N_LOOK);
    if (old) gu_delete(old);
    return 1;
}

/* the model joints named by a look record that do not point to this instance's joint callback yet (*found = how
 * many of the 6 the model has) */
static uint32_t joints_missing(void *self, uint32_t *found)
{
    uint32_t n = FIELD(uint32_t, self, EN_JOINT_N), miss = 0;
    uint8_t *j = FIELD(uint8_t *, self, EN_JOINTS);
    *found = 0;
    if (!j) return 0;   /* no model yet */
    uint32_t cb = (uint32_t)self + EN_JOINT_CB;
    for (uint32_t i = 0; i < n; i++, j += JOINT_SIZE) {
        uint32_t id = j[JOINT_ID];
        for (uint32_t k = 0; k < N_LOOK; k++) {
            if (k_look[k][0] != id) continue;
            ++*found;
            if (FIELD(uint32_t, j, JOINT_CB) != cb) miss++;
        }
    }
    return miss;
}

static void look_log(void *self)
{
    static uint8_t s_mode = 0xff;
    static uint32_t s_n, s_tick;
    uint8_t mode = FIELD(uint8_t, self, LK_MODE);
    int changed = mode != s_mode;
    s_mode = mode;
    if (!changed && (mode != 3 || ++s_tick % 30)) return;
    if (++s_n > 80) return;
    const int16_t *a = (const int16_t *)((uint8_t *)self + LK_ANGLE);
    const float *p = (const float *)((uint8_t *)self + LK_POINT);
    logf("dalaport: look mode %u fixed %u action %u/%u point %d %d yaw %x angles %d %d %d %d %d %d",
         mode, FIELD(uint8_t, self, LK_FIXED), FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_CAT + 1),
         (int32_t)p[0], (int32_t)p[2], FIELD(uint32_t, self, LK_YAW) & 0xffff, a[0], a[1], a[2], a[3], a[4], a[5]);
}

void dala_look_install(void *self)
{
    if ((FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff)) return;   /* tail: 4U em083 has no look joint */
    uint8_t *obj = FIELD(uint8_t *, self, EN_DTBPARTS);
    if (!obj) return;
    if (obj != s_dtp) {
        if (!install_list(obj)) return;
        s_dtp = obj;
    }
    uint32_t found, miss = joints_missing(self, &found);
    if (miss) {
        static uint32_t s_n;
        lookJoints(self);
        miss = joints_missing(self, &found);
        if (++s_n <= 8)
            logf("dalaport: look joints registered on %x: %u of 6 on the model (of %u joints), %u still missing",
                 (uint32_t)self, found, FIELD(uint32_t, self, EN_JOINT_N), miss);
    }
    look_log(self);
}

/* 4U 0x76ec80 (7.0 / 7.2 / 7.3 / 7.4 / 7.86) and 0x76fce8 (7.41 / 7.43 / 7.45 / 7.46 / 7.88), the writes before
 * the step switch, every frame, no em test (C): fixed origin flag 1; set 0 also rate 0.005 (0x3ba3d70a), set 1
 * keeps the update's 0.015. Origin / yaw are 4U arena coordinates (the arena keeps 4U's: S). */
void dala_look_setup(void *self, uint32_t set)
{
    static const float k_org[2][4] = {
        {-6500.0f, 0.0f, 1657.0f, 0.0f},             /* 0xc5cb2000, 0, 0x44cf2000 */
        {2283.15991f, 0.0f, 3886.46997f, 0.0f},      /* 0x450eb28f, 0, 0x4572e785 */
    };
    static const uint32_t k_yaw[2] = {0x43ce, 0x8555};
    static const uint16_t k_tab[2][12] = {
        {182, 364, 546, 728, 910, 1092, 8192, 182, 182, 182, 182, 182},
        {3641, 91, 91, 91, 2185, 5461, 0, 0, 0, 0, 0, 0},
    };
    set = set ? 1 : 0;
    FIELD(uint8_t, self, LK_FIXED) = 1;
    if (set == 0) FIELD(float, self, LK_RATE) = 0.005f;
    for (uint32_t i = 0; i < 4; i++) FIELD(float, self, LK_ORIGIN + 4 * i) = k_org[set][i];
    FIELD(uint32_t, self, LK_YAW) = k_yaw[set];
    for (uint32_t i = 0; i < 12; i++) FIELD(uint16_t, self, LK_POS + 2 * i) = k_tab[set][i];   /* +0x752c..+0x7542 */
}

void dala_look_point(void *self)
{
    lookPoint(self, 0, 0);
}

void dala_look_mode(void *self, uint32_t mode)
{
    FIELD(uint8_t, self, LK_MODE) = (uint8_t)mode;
}
