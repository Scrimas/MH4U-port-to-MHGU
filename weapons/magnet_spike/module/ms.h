/* ms.h: the Magnet Spike as MHGU's class 5 (box type 12), Phase 2 vertical slice (weapons/magnet_spike/notes/
 * phase2.md, gu-weapon-class.md). Built only with MS_SLICE (module/build.py adds this folder, its hooks and patches).
 * The class object is a Great Sword object (same size, base ctor) whose vtable is ms_class.c's copy: every slot the
 * Great Sword overrides is replaced by a Magnet Spike function or the engine's common default (phase2.md checklist
 * "Great Sword code still used by class 5"). The actions are MHF's, run from gen/ms_data.inc (msbuild.py). */
#pragma once
#include <stdint.h>
#include "util.h"
#include "game.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define MS_CLASS 5u
#define MS_TYPE 12u                 /* box equipment type = class + 7 */
#define MS_PLAYERS 4

/* generated tables (gen/ms_data.inc) */
struct ms_step { uint16_t kind, mot, start, blend, frame, loops, table; };   /* MHF step; mot = bank-5 slot */
struct ms_event { uint8_t step, when; uint16_t frame, id, arg; };             /* when 0 step start, 1 frame, 2 never */
struct ms_action { uint16_t no; uint8_t mode, nsteps; uint16_t step0; uint8_t nevents; uint16_t ev0; };
enum { MS_EV_ATTACK = 1, MS_EV_GUARD, MS_EV_ARMOR, MS_EV_SPEED, MS_EV_TURN, MS_EV_TURN_TARGET, MS_EV_SHAKE,
       MS_EV_CHARGED };

/* per-hunter state (module side: the object keeps the Great Sword's layout) */
struct ms_state {
    uint8_t *p;                     /* the class object */
    uint8_t mode;                   /* 0 Cutting, 1 Impact (MHF: the mode of the last action started) */
    uint8_t charged;                /* MHF MS flag 0x20 (event 26): the Triple Strike charge is ready */
    uint8_t loops;                  /* loop wraps of the current step's motion */
    uint16_t held;                  /* last frame's virtual buttons (player +0x13f4) */
    uint16_t action;                /* the action ms_act last ran */
    float last_frame;
    uint32_t fired;                 /* events of the current action already run */
};
struct ms_state *ms_of(uint8_t *p);

/* GU calls (main offsets, C unless marked; gu-weapon-class.md) */
typedef void (*ms_setmot_t)(void *p, uint32_t motion, float blend, float start);
#define MS_SET_MOTION FN(ms_setmot_t, 0x281998)       /* motion = bank * 1000 + slot */
typedef int (*ms_p_t)(void *p);
#define MS_MOTION_END(p) ((FIELD(uint8_t, (p), 0x4b0 + 6) & 7) >> 2)   /* 0x950bcc(p + 0x4b0) */
#define MS_FRAME(p) FIELD(float, (p), 0x4fc)          /* the motion's frame (+0x4f4 = the blend countdown, +0x504
                                                         the end, +0x508 the loop start, +0x50c the speed) */
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

void ms_act(uint8_t *p);            /* ms_act.c: slot 201 */
void ms_input(uint8_t *p);          /* ms_act.c: slot 139 */
void ms_init(void);                 /* ms_class.c, from module_init */
