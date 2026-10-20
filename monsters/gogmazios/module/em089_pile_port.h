/* em089_pile_port.h - faithful C port of the MH4U v1.1 Gogmazios (em089) falling
 * Dragonator spear ("portable pile bunker"): cut object k1 (type 3, mode 1)
 * update 0xc2d364 / launch 0xc2e478 / ballistic 0xc2f95c, spear controller
 * 0xc2e96c, and the uStageGimmick type 2 sub 3 timeline 0x33c7c8.
 * GU side (the pj_* externs, the object, the prompt and the hit): em089_pile.c.
 *
 * Conventions
 *  - Time unit: 4U frames. dt = 4U obj+0x14 (1.0 per 30 fps frame).
 *  - Matrices: float[16], row vectors (v' = v * M), translation in m[12..14].
 *  - Angles: 4U u16 binary angles (65536 = 360 deg) kept in u32 like 4U.
 *  - Local-authority path only (4U obj+0xe2f == 0). See em089_pile_port.c header
 *    for the remote-copy (e2f == 1) differences.
 *  - Float contraction is off in em089_pile_port.c: 4U VFP vmla/vmls are not fused.
 */
#ifndef PILE_PORT_H
#define PILE_PORT_H

#include <stdint.h>
#include "util.h"

typedef struct pile_s pile_t;

/* pj_efx attach_joint values */
#define PILE_ATTACH_WORLD (-1)  /* world effect: pos/rot_deg are world */
#define PILE_ATTACH_ROOT  255   /* 4U joint 255 + owner obj: attached to the spear
                                   object root, off = object-space offset, rot 0 */
                                /* 0..n: attached to that spear joint, off in joint space */

struct pile_s {
    /* ---- inputs (4U enemy W fields) ---- */
    float    scale;        /* W+0x1b8 * W+0x1bc (4U 0x911cb4); also the cut obj model scale (obj+0x60, 0xc2d33c) */
    uint32_t w_yaw;        /* W+0x1ac monster yaw (u16); 4U reads it live at launch AND at landing */
    float    w_pos[3];     /* W+0x198 monster position at sever (0x94e50c -> landing target e58) */

    /* ---- cut object k1 (4U obj = W+0xd48+1*0xec8) ---- */
    uint8_t  inited;       /* port only: pile_init done */
    uint8_t  e2a;          /* obj+0xe2a state: 2 fall, 3 landed, 4 resting */
    uint8_t  e2f;          /* obj+0xe2f 0 = local authority (only path ported) */
    uint8_t  ec0;          /* obj+0xec0 controller sub-state 0..6 (6 = hidden) */
    uint8_t  gf_enable;    /* 4U: e44 != 255 && 0x6c5e88(stage,e43,e44): static ground follow on */
    int16_t  e40;          /* obj+0xe40 fall time T (emd rec +2 = 160) */
    float    e34;          /* obj+0xe34 timer (fall t; then 1000.., 1500.., 2000..) */
    float    ec4;          /* obj+0xec4 spark SE timer */
    float    pos[3];       /* obj+0xea0 position (copied to obj+0xd00 for the model) */
    float    prev[3];      /* obj+0xe70 position at frame start */
    float    vel[3];       /* obj+0xe80 velocity */
    float    acc[3];       /* obj+0xe90 acceleration (0, g, 0) */
    float    tgt[3];       /* obj+0xe58 landing target (y = ground + 20*scale) */
    uint32_t ang[3];       /* obj+0xeb0/eb4/eb8 angles X, Y, Z (u16 in u32) */
    uint32_t model_flags;  /* obj+0x108 uModel parts-display bit array word 0 (bits 1..4 used here) */
    uint8_t  rec_live;     /* obj+0xe68 != -1 (kind-36 interaction record alive) */
    float    rec_pos[3];   /* record +0x34: = obj pos every frame (0xc2e3d4) */
    int      se_follow;    /* port: SE id moved with the spear (4U 0x301074), 210 while falling, else 0 */

    /* ---- uStageGimmick type 2 / sub 3 / area 3 (the "pile", 0x6c3a8c(stage,2,3,2)) ---- */
    uint8_t  g_state;      /* g+0xc78 0/7/1/2/3/5/6 */
    uint8_t  g_cd0;        /* g+0xcd0 SE 218 already played */
    float    g_timer;      /* g+0xca0 */
    float    g_thrust;     /* g+0xcc0 thrust along the gimmick Z axis */
    float    g_base[3];    /* g+0xc80 base position (0,0,0 for this gimmick) */
    float    g_rot[3];     /* g+0xc90/c94/c98 rot x, y, z in radians (z = spin) */
    float    g_tip[3];     /* g+0xcb0 pile point (hit shell + SE 218/219 position) */
    float    g_mtx[16];    /* g world matrix (vtbl+0x54(g,-1) = g+0xb0), copied into spear joint 2 */
    void    *g_efx;        /* g+0xcc4 stored effect handle (mask 2, then mask 4) */
    uint8_t  dd28;         /* [0xfbeffc]+0xdd28 stage gimmicks on (set 1 by pile_init) */
    uint8_t  dd29;         /* [0xfbeffc]+0xdd29 bit 1 = pile used (0x6a1f18) */
};

/* ---- externs implemented by the caller (GU side, em089_pile.c) ---- */
extern void  pj_joint_get_local(void *obj, int joint, float m[16]);       /* = 4U 0xb052ec */
extern void  pj_joint_set_local(void *obj, int joint, const float m[16]); /* = 4U 0xb05754 */
extern void  pj_joint_world_pos(void *obj, int joint, float out[3]);      /* world position of a spear joint
                                                                             (4U 0xb054ac / vtbl+0x54: last computed, i.e. previous frame) */
extern void  pj_obj_set_world(void *obj, const float m[16]);              /* object world rotation + position (no scale) */
extern float pj_ground_y(const float from[3], float max_drop, int *hit);  /* ground ray straight down from `from`
                                                                             (= 4U 0x2bb2a8; from already includes 4U's +100 rise;
                                                                             max_drop < 0 = unlimited, 4U passes -1.0 in the ray w) */
extern void  pj_se(int id, const float pos[3]);                           /* em089 sound request id at a position */
extern void *pj_efx(uint32_t mask, uint32_t flags, const float pos[3], const float rot_deg[3],
                    int attach_joint, const float off[3]);                /* em089_024 element mask; see PILE_ATTACH_* */
extern int   pj_efx_alive(void *h);
extern void  pj_efx_kill(void *h);
extern void  pj_record_create(const float pos[3], float radius, float height); /* the kind-36 interaction record */
extern void  pj_record_disable(void);
#define pj_log(...) logf("gogport: em089 " __VA_ARGS__)               /* literal formats only (logf: %d %u %x %s %c) */
extern float pj_sin(float rad);   /* = 4U 0xd145ac (sinf) */
extern float pj_cos(float rad);   /* = 4U 0xd13278 (cosf) */
extern float pj_sqrt(float x);    /* unused by the ported code (no 4U sqrt on these paths); kept for the interface */

/* ---- entry points ---- */
void pile_init(pile_t *p, const float launch_pos[3], uint16_t monster_yaw, float scale);
     /* = sever: launch from joint 200's world position. Uses launch_pos as the monster
        position too (4U uses W+0x198 for the landing target): prefer pile_init_ex. */
void pile_activate(pile_t *p);            /* = 0x6a1f18 effect on the gimmick: start the timeline (dd29 bit 1) */
void pile_frame(pile_t *p, void *obj, float dt); /* gimmick timeline, then the spear update */
int  pile_ready(const pile_t *p);         /* landed, record live, not activated (4U ready check 0xb0f498) */
int  pile_hidden(const pile_t *p);        /* ec0 == 6: draw off for good */
void pile_tip(const pile_t *p, float out[3]); /* g+0xcb0 (the hit / SE point) */
int  pile_gimmick_state(const pile_t *p); /* +0xc78, for the hit shell gate */

/* ---- extra entry points (facts the fixed interface cannot carry) ---- */
void pile_init_ex(pile_t *p, const float launch_pos[3], const float monster_pos[3],
                  uint16_t monster_yaw, float scale);
     /* 4U sever 0x94e39c(enemy,1,0,NULL): landing target = ground under the MONSTER
        position W+0x198 (+20*scale), not under joint 200. */
void pile_set_monster_yaw(pile_t *p, uint16_t yaw);
     /* 4U reads W+0x1ac live at landing (rest offset, final yaw, dust rotation). Call each
        frame before pile_frame if the monster turns during the 160-frame fall. */
void pile_obj_world(const pile_t *p, float m[16], int with_scale);
     /* the object world matrix exactly as pile_frame sends it; with_scale != 0 also scales
        rows 0..2 by `scale` as 4U 0x6d3fd0 does with obj+0x60. Use it once after
        pile_init (4U renders the launch frame at the start position). */
int  pile_se_follow(const pile_t *p, float out[3]);
     /* SE to move with the spear this frame (4U 0x301074(mgr,210,...) each falling frame):
        returns 210 and the position, or 0. */

#endif /* PILE_PORT_H */
