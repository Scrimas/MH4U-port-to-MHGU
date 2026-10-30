/* ms.h: the Magnet Spike as MHGU's class 5 (box type 12): Phase 3 full moveset (weapons/magnet_spike/notes/
 * phase3.md, mechanics.md, gu-weapon-class.md). Built only with MS_SLICE (module/build.py adds this folder, its hooks
 * and patches). The class object is a Great Sword object (same size, base ctor) whose vtable is ms_class.c's copy:
 * every slot the Great Sword overrides is replaced by a Magnet Spike function or the engine's common default. The
 * actions are MHF's, run from gen/ms_data.inc (msbuild.py); the mechanics are MHF's MS code (mechanics.md). */
#pragma once
#include <stdint.h>
#include "util.h"
#include "game.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define MS_CLASS 5u
#define MS_TYPE 12u                 /* box equipment type = class + 7 */
#define MS_PLAYERS 4

/* generated tables (gen/ms_data.inc) */
struct ms_pair { uint8_t inp, cond; };                                        /* class id k = MHF input + condition */
struct ms_step { uint16_t kind, mot, start, blend, frame, loops, table; };   /* MHF step; mot = bank-5 slot */
struct ms_event { uint8_t step, when; uint16_t frame, loop; uint8_t lvl, id; uint16_t prm, hit; };
                                    /* when 0 step start, 1 frame, 2 never, 3 charge level >= lvl; id = MHF event */
struct ms_action { uint16_t no; uint8_t mode, nsteps; uint16_t step0; uint8_t nevents; uint16_t ev0; };

/* per-hunter state: MHF's MS block (ext + 0x1c0, mechanics.md 3) and the player fields its code uses. Times in MHF
 * ticks (1/30 s) */
struct ms_state {
    uint8_t *p;                     /* the class object */
    uint8_t mode;                   /* MS+0x64: 0 Cutting, 1 Impact (the mode of the last action started) */
    uint8_t loops;                  /* loop wraps of the current step's motion */
    uint8_t slot;                   /* the GU attack slot armed last (0 / 1) */
    uint8_t gc_hits;                /* MS+0x66: guarded hits of the current guard */
    uint16_t held;                  /* last update's virtual buttons (player +0x13f4) */
    uint32_t held32;                /* the whole word (+0x13fc): its unknown bits are logged (Minus, test 3) */
    uint16_t action;                /* the action ms_act last ran */
    float last_frame;
    uint32_t fired;                 /* events of the current action already run */
    uint32_t code_fired;            /* code-spawned hits of the current action already armed */
    uint32_t flags;                 /* MS+0x5c (mechanics.md 3) */
    int32_t gauge;                  /* MS+0x7a: 0..10000, 5 bars of 2000 */
    float regen;                    /* MS+0x7c */
    uint8_t mag[2];                 /* MS+0x88 per mode: 0 charging, 1 magnetised, 2 lockout */
    float mag_v[2];                 /* MS+0x8a: charge 0..1000 / timer */
    uint8_t air, end_on_land, keep_if, charge_lvl;   /* P+0x418 bit 0, P+0x410 == 2, ext+0x284, P+0xb28 */
    float fwd, vert;                /* ev27 / ev28 drives (units / tick) */
    uint8_t curve;                  /* MS+0x6d: drive curves, low nibble forward, high vertical (ev29 / ev30) */
    float fwd_n, vert_n, fwd_k, vert_k;   /* MS+0x6e / +0x70: ticks since the drive started; 0.97^n */
    float grav, grav_t;             /* ev25: y -= grav * 0.1 * t per tick */
    float fall_g, vy;               /* ev31 custom gravity and the speed it built */
    float hold_v;                   /* ev33: ticks of zero velocity */
    float charge;                   /* P+0xb24: Triple Strike charge ticks */
    float step_t;                   /* ticks in the current step */
    uint8_t *mk_mon;                /* the monster the marker sticks to (0 none) */
    float mk_t;                     /* marker lifetime */
    uint8_t att;                    /* attraction phase: 0 off, 1 lift, 2 fly, 3 fall */
    float att_t, att_h, dir[3];
    uint8_t *pin_mon, *pin_pending; /* the pinned monster; the one the pin attack hit (started next update) */
    float pin_hold, pin_cd, qte, pin_off[3];
    uint16_t pin_yaw_m, pin_yaw_p;
    uint16_t armed[2];              /* hit-data entry armed in each attack slot */
    uint8_t shock_on, shock_k;      /* Magnetic Shock 5 x 3 task running, spots spawned */
    float shock_t;                  /* its ticks */
    float mk_blink, aura_t;         /* ticks to the marker's and Magnetise's next flash */
};
struct ms_state *ms_of(uint8_t *p);
void ms_reset(struct ms_state *s);

/* GU calls (main offsets, C unless marked; gu-weapon-class.md, mechanics.md "GU side") */
typedef void (*ms_setmot_t)(void *p, uint32_t motion, float blend, float start);
#define MS_SET_MOTION FN(ms_setmot_t, 0x281998)       /* motion = bank * 1000 + slot */
typedef int (*ms_p_t)(void *p);
#define MS_MOTION_END(p) ((FIELD(uint8_t, (p), 0x4b0 + 6) & 7) >> 2)   /* 0x950bcc(p + 0x4b0) */
#define MS_FRAME(p) FIELD(float, (p), 0x4fc)          /* the motion's frame (+0x4f4 = the blend countdown, +0x504
                                                         the end, +0x508 the loop start, +0x50c the speed) */
#define MS_MOT_SPEED(p) FIELD(float, (p), 0x50c)
typedef int (*ms_reached_t)(void *p, float frame);
#define MS_REACHED FN(ms_reached_t, 0x280e4c)         /* the frame after this tick's advance (+0x14d0 + +0x14d4,
                                                         wrapped on a loop) >= frame; 0 while blending: the classes'
                                                         own step and event check */
typedef uint32_t (*ms_curmot_t)(void *u);
#define CUR_MOTION FN(ms_curmot_t, 0x53a058)          /* the unit's motion as bank * 1000 + slot */
typedef void (*ms_settbl_t)(void *p, uint32_t table, int frame);
#define MS_SET_TABLE FN(ms_settbl_t, 0x2e9b7c)        /* clears the buffered commands */
typedef void (*ms_settbl2_t)(void *p, uint32_t table, int frame, int keep);
#define MS_SET_TABLE_KEEP FN(ms_settbl2_t, 0x2e9c50)
typedef void (*ms_flags_t)(void *p, uint32_t flags, uint32_t a, uint32_t b);
#define MS_ACTION_FLAGS FN(ms_flags_t, 0x282fd8)
typedef void (*ms_setact_t)(void *p, uint32_t st, uint32_t no, uint32_t x);
#define MS_SET_ACTION FN(ms_setact_t, 0x2831e0)
typedef void (*ms_end_t)(void *p, uint32_t sheathed, uint32_t blend, uint32_t x, uint32_t flags, uint32_t a5,
                         uint32_t a6);
#define MS_TO_NEUTRAL FN(ms_end_t, 0x2b6e94)          /* vt+0x68c (0x2b6f68, 3 stack args): back to the neutral
                                                         action; flags = the set-action flags (slot 190), GS: 0 */
typedef void (*ms_arm_t)(void *p, uint32_t slot, uint32_t hit, uint32_t type);
#define MS_ARM FN(ms_arm_t, 0x2b7240)                 /* attack slot from pl_we05_hitdata[hit] */
typedef void (*ms_setid_t)(void *p, uint32_t id);
#define MS_SET_CLASS_ID FN(ms_setid_t, 0x285e54)      /* player +0x1424 bit */
typedef void (*ms_flagb_t)(void *p, uint32_t on);
#define MS_DRAW_FLAG FN(ms_flagb_t, 0x2a264c)         /* +0x2749 bit 3, set by the draw attacks */
#define MS_VT(p, off) (*(uint32_t **)(p))[(off) / 4]
typedef void (*ms_iframes_t)(void *p, float frames, int force);
#define MS_IFRAMES FN(ms_iframes_t, 0x2a6760)         /* i-frame timer +0x2b40 (1/60-s frames): max(t, n), = n
                                                         if force */
typedef int (*ms_evlvl_t)(void *p, uint32_t skill);
#define MS_EVASION FN(ms_evlvl_t, 0x2a69dc)           /* Evasion level 0 / 1 / 2 (GU's roll asks with 0x1f) */
#define MS_HAS_SKILL FN(ms_evlvl_t, 0x2864c4)         /* the hunter has skill effect id (GU's guard code: 14, 15) */
typedef void (*ms_stam_t)(void *p, float amount, int flag);
#define MS_STAMINA FN(ms_stam_t, 0x2a5ebc)            /* action cost (< 0) with Constitution; 150 = a roll */
#define MS_STAMINA_NOW(p) FIELD(float, (p), 0x13e0)   /* 6 x the displayed value (S) */
typedef void (*ms_bits_t)(void *p, uint32_t a, uint32_t lo, uint32_t hi);
#define MS_BITS_SET FN(ms_bits_t, 0x283238)           /* action flags +0x2510 / +0x2514 (cleared per action) */
#define MS_BITS_CLEAR FN(ms_bits_t, 0x28321c)
#define MS_GUARDING 0x10                              /* +0x2510 bit: "guarding now" (the can-guard check) */
typedef void (*ms_p0_t)(void *p);
#define MS_GUARD_STAMINA FN(ms_p0_t, 0x2a609c)        /* -150 / -200 / -360 by the attack's guard power */
typedef void (*ms_shake_t)(void *p, uint32_t preset, uint32_t flags);
#define MS_SHAKE FN(ms_shake_t, 0x2a063c)             /* camera shake (local hunter); 0xf = GS's landing */
typedef int (*ms_land_t)(void *p, float eps, float *ground);
#define MS_LANDED FN(ms_land_t, 0x2a84d8)             /* 1 when y <= ground + eps: move state 0, y = ground */
#define MS_GROUND_Y(p) FIELD(float, (p), 0x10f0)      /* the ground probe's height under the hunter */
typedef void (*ms_mstate_t)(void *p, uint32_t state);
#define MS_MOVE_STATE(p, st) ((ms_mstate_t)MS_VT(p, 0x300))(p, st)   /* +0x2505: 0 ground, 2 air */
typedef uint8_t *(*ms_em_t)(void *mgr, int i);
#define MS_EM_GET FN(ms_em_t, 0x5ceb4)                /* monster slot 0..9 of the manager *(MAIN 0x1851fe0) */
#define MS_EM_MGR (*(void **)MAIN(0x1851fe0))
#define MS_CAM_MGR (*(uint8_t **)MAIN(0x2126504))     /* +0x54 = the camera: eye +0x40, look-at +0x60 */
#define MS_U16_RAD 9.58738e-5f                        /* u16 angle -> radians */
typedef void *(*ms_efx_t)(void *p, uint32_t id, void *req, uint32_t one);
#define MS_EFFECT(p, id) ((ms_efx_t)MS_VT(p, 0x39c))(p, id, (uint8_t *)(p) + 0x2550, 1)   /* 0x282624: post the
                                     class PEL's list-1 record id (GS's w00_000 copy as w05_000) on the hunter's
                                     request (GU's classes: arg 1 in 112 of 115 calls) */
typedef void (*ms_req_t)(void *req);
#define MS_REQ_CTOR FN(ms_req_t, 0x40b10)             /* a proof-effect request (~0xd8 B, em089_efx.c): +0x1c flags (bit
                                                         0 = at the world position +0xc0), +0xd0 attach model */
#define MS_REQ_DTOR FN(ms_req_t, 0x40b50)
enum { MS_EFX_CHARGED = 7, MS_EFX_GUARD = 9, MS_EFX_MAGNETISE = 11 };   /* GS's charge flashes (list-1 6-11 / 30 /
                                     31, its PTS ties GS's flash sound 150; 0-5 / 20 / 21 are its slash arcs, 1000+
                                     ours, msfx.py): S, stand-ins for MHF's effects */

static inline int ms_drawn(uint8_t *p) { return ((int (*)(void *))MS_VT(p, 0x178))(p) == 1; }

void ms_act(uint8_t *p);            /* ms_act.c: slot 201 */
void ms_input(uint8_t *p);          /* ms_act.c: slot 139 */
void ms_on_hit(uint8_t *p, uint8_t *atk, uint8_t *mon, uint32_t kind);      /* ms_act.c: slot 37 */
void ms_guarded(uint8_t *p, uint32_t level, uint8_t *info, int32_t *dmg);   /* ms_act.c: slot 356 */
int ms_invuln(uint8_t *p);          /* ms_act.c: slot 44 */
void ms_init(void);                 /* ms_class.c, from module_init */
void ms_text_loaded(uint8_t *m, const char *name, uint32_t lang);           /* ms_class.c, from items.c */
