/* em007_01.h: Monoblos (GU Diablos variant 1, ID 0x107): the 4U -> GU map the ported 4U uEm101 handlers share
 * (em007_01_mv_*.c). [4U address or field] after each GU one; C = confirmed in code, S = strong, G = guess.
 * GU's Diablos class (uEm007_00) still carries many of his 4U helpers: "GU twin site" = GU's version of the same 4U
 * handler does the same call at the same place (GU 0xd430a8 = GU's horn charge, the counterpart of 4U 0x8db41c: same
 * steps, motions 0x20f / 0x210, attack params, timer 300.0, helper calls). */
#ifndef EM007_01_H
#define EM007_01_H

#include <stdint.h>
#include "game.h"
#include "util.h"

#define REC(self)   FIELD(uint8_t *, self, EN_RECORD)
#define WORK(self)  FIELD(uint8_t *, self, EN_WORK)
#define RF(p, off)  FIELD(float, p, off)
#define RU(p, off)  FIELD(uint32_t, p, off)

#define EN_VARIANT  (EN_ID + 5)  /* u8, set by setup 0x6fb14 from ID bits 8-11 */
#define EN_AREA     0x1054       /* u8 unit area [4U W+0x14c] (C: GU d433c4 where 4U 0x8e02c8 reads W+0x14c) */
#define REC_TIMER   0x1bc        /* float action timer [4U W+468] (C: GU d430a8 stores 300.0 as 4U 0x8db41c) */
#define REC_TGT_DIST 0x1f0       /* float distance to target slot 0 [4U W+568] (C: GU d435c4) */
#define REC_ATK0_STATE 0xa4d     /* u8 attack slot 0 state, bit 0 tested [4U W+0xc08+0x95] (C: GU d433dc) */
#define WK_CHARGE   0            /* u8 the charge's flag [4U work+1] (C: GU d430a8 / d431ec set / clear work+0 where
                                  * 4U sets / clears work+1) */

/* his 4U attack index i -> 1000 + i: GU's second attack table. attackEx's record lookup 0x70ffc takes indexes >= 1000
 * from this+0x75d8 (manifest field 27, attackdata) and the hitsize lookup 0x7105c from this+0x75e0 (field 29); 18 GU
 * monsters fill both, GU's Diablos neither (C). His 4U em101 records and hitsize groups sit there unchanged (tools/
 * build_em007_01_arc.py attack_files), GU's own in fields 26 / 28 for GU's Diablos handlers (his twin actions). */
#define MB_ATK_BASE 1000
#define MB_ATK(i)   (MB_ATK_BASE + (i))

/* ---- GU callees not in game.h */
typedef void (*attack_t)(void *self, uint32_t slot, uint32_t index);
#define attack      FN(attack_t, 0x7df94)           /* [0x914dfc] attackEx with param 0 (stygian em057_01.h) */
typedef int (*motionIs_t)(void *self, uint32_t motion);
#define motionPlaying FN(motionIs_t, 0x72788)       /* [0xb059a4] the current motion is `motion` (dalamadur dala.c) */
#define motionCheckB FN(motionCheck_t, 0xb0a60)    /* [0x93906c] motionCheck, the impl's r2 = 1 (dalamadur em090.h) */
#define setActionNow FN(setActionNext_t, 0x76a58)   /* [0x92b178] setAction(mode 1) + same-frame restart (em090.h) */
typedef float (*selfFloat_t)(void *self);
#define layerSpeed  FN(selfFloat_t, 0xafd30)        /* [0x941dd4] motion speed rec+908 * rec+916 * status (S: GU
                                                     * twin site d434dc) */
typedef void (*rootMove_t)(void *self, uint32_t motion, const void *angles, const void *offset);
#define rootMove    FN(rootMove_t, 0xb0cd4)         /* [0x941f9c(this, mot, angles)]: the motion's root move turned by
                                                     * the angle triple; GU adds the offset vector (GU twin site
                                                     * d432b4 passes *GOT 0x1839bdc) (S) */
#define ROOT_MOVE_OFFSET (*(const void **)MAIN(0x1839bdc))
typedef int (*selfMode_t)(void *self, uint32_t mode);
#define chargeTarget FN(selfMode_t, 0xd3c7bc)       /* [class 0x8defb0(this, mode)]: target / ground check of the
                                                     * charge, chains 3/7 itself; 1 = it acted (S: same calls,
                                                     * GU twin site d431c4) */
typedef int (*wallCheck_t)(void *self, uint32_t mask, uint32_t range);
#define wallCheck   FN(wallCheck_t, 0xd41050)       /* [class 0x8d750c(this, mask, range)]: horn hit on stage geometry
                                                     * (S: same structure, GU twin site d433b8) */
#define stuckScan   FN(selfMode_t, 0xd3b154)        /* [class 0x8e0d34(this)]: the stuck horn's hunter scan; GU adds
                                                     * a mode, 0 at GU's twin site d3ad60 (S) */
typedef uint32_t (*playerArea_t)(void);
#define playerArea  FN(playerArea_t, 0x4971c)       /* [*(*0xfb6b7c) + 0xc90] the local player's area (S: GU d433cc) */
typedef void (*rumble_t)(void *mgr, uint32_t id, uint32_t strength, uint32_t zero, uint32_t sp0);
#define rumble      FN(rumble_t, 0x19148)           /* GU's replacement of 4U 0xbfef9c(mgr, 7, pos) in the wall hit
                                                     * (GU d43408: (mgr, 7, 4096, 0, 0)) */
#define RUMBLE_MGR  (**(void ***)MAIN(0x1838d90))
typedef int (*enemyDrop_t)(void *self, const float *pos, uint32_t chance, uint32_t zero);
#define enemyDrop   FN(enemyDrop_t, 0xac0ec)        /* [0x911f58] item drop at pos, chance % (em089_break.c) */

#define REC_TURN    0x204        /* u32 turn angle of the scrape [4U W+0x24c] (C: GU's scrape 0xd3c128 stores the
                                  * clamped angle there and feeds it to spinWindow, as 4U 0x8da77c) */
typedef void (*spinWindow_t)(void *self, uint32_t ang, float a, float b);
#define spinWindow  FN(spinWindow_t, 0x76e8c)       /* [0x9175a8] yaw += (s32)ang over frames a..b (em057_01.h) */
#define spinWindow11 FN(spinWindow_t, 0x770a0)      /* [0x937298] the same with motion window kind 11 and the step
                                                     * fraction preset to 1.0 (C: same body) */
typedef void (*camShakeJoint_t)(void *self, int32_t joint, uint32_t id, uint32_t zero);
#define camShakeJoint FN(camShakeJoint_t, 0xc24d8)  /* [0x910c6c(this, joint, id)] (stygian em057_01.h) */
#define EN_MOVECLASS 0xb5f8      /* u8 move class [4U this+0xca8 bits: bit k -> k] (stygian em057_01.h) */
#define REC_FLAGS   0x3b4        /* u16 part flags, bit 0 = tail severed [4U W+0x42c] (dalamadur dala_parts.c) */
typedef int (*atFrame_t)(void *self, float f);
#define atFrame     FN(atFrame_t, 0xb0a30)          /* [0x941dbc] motionCheck(0, f, 0) */
typedef void (*camEvent_t)(void *self, uint32_t kind, uint32_t r2, uint32_t type14, float s0);
#define camEvent    FN(camEvent_t, 0xaa418)         /* [0x93457c(this, kind, 255), s0 = 0]: camera event of the
                                                     * monster's camera list (gogmazios em089_act.c, C) */

/* 4U 0x568c8c(dx, dz) -> u16 angle; GU's counterpart atan2f(dx, dz) * 65536 / 2pi + 0.5 (stygian em057_01.h) */
static inline uint32_t atan_u16(float y, float x)
{
    return (uint32_t)(int32_t)(atan2f_gu(y, x) * 10430.378f + 0.5f) & 0xffff;
}

/* em007_01_mv_b.c: 4U target position of his dig / scrape handlers (kind of target slot 0) */
void mb_target_pos(void *self, float *out);

/* em007_01_moves.c: chain to his 4U action (cat, n): GU's number for a twin, ours (PORT_BASE + n) otherwise */
void mb_chain(void *self, uint32_t cat, uint32_t n);        /* setActionNext [0x94ef9c] */
void mb_chain_now(void *self, uint32_t cat, uint32_t n);    /* setActionNow [0x92b178] */
static inline void end_action(void *self) { VCALL0(self, SLOT_ACTION_END); }       /* vt+0x164 */

/* 4U-only state with no GU field (module side, per monster instance; a new quest starts it afresh: the old handles
 * died with that quest's effects, as black_gravios em005_01_laser_reset) */
struct mb_state {
    void *self;
    uint32_t quest;     /* port_quest_id() it belongs to */
    float w488;         /* [4U W+488]: 1.0 from the charge before 2/13 (read by 4U 0x8d8cc0), the stalk's turn rate */
    float shake_t;      /* [4U class work+0x10]: the burrowed travel's camera-shake timer (GU's tail owns work+16) */
    float snd_t;        /* [4U class work+0x58]: the burrowed rest's sound timer */
    uint32_t trail;     /* 1 = a burrow travel of his started GU's trail (this+0xb7c4, em007_01_mv_h.c) */
    void *mound;        /* [4U class work+0x84]: the burrowed rest's effect (em007_01_mv_h.c), with the vtable */
    uint32_t mound_vt;  /* it had at the post, whether it was seen alive and its transform pointers then */
    uint32_t mound_seen, mound_xf[2];
    uint16_t w60;       /* [4U class work+0x60..0x80]: the spin turn's (2/13 2/15) angle, angle triple, push vector */
    uint32_t ang64[3];  /* and turn (GU's version keeps them at GU work+0x20..0x48) */
    float v70[4];
    int32_t a80;
    uint8_t angry;      /* [4U class work+8] and [4U class work+80]: his rage veins' state and timer (em007_01_mat.c) */
    float angry_t;
    uint8_t parts;      /* 1 + the parts bits last logged (em007_01_mat.c), 0 = none yet */
};
struct mb_state *mb_state(void *self);
/* em007_01_mat.c: every frame (GU slot 125): his rage veins */
void mb_angry_frame(void *self);
/* em007_01_mv_h.c: every frame (GU slot 125): the end rules of his ground effects; lying = the action is his 6/8, 6/9
 * or 6/10, travel = his 6/4, 6/12, 6/15, 6/16 or 6/20 */
void mb_mound_frame(void *self, int lying, int travel);

#endif
