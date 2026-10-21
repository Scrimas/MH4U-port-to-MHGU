/* Dalamadur: the head half uEm090_00 (4U uEm024) and the tail half uEm091_00 (4U uEm083), each running its normal
 * and Shah variant (GU variant 1 = 4U em110 / em111). notes: monsters/dalamadur/notes/class-study.md, plan.md. */
#pragma once
#include "game.h"
#include "alloc.h"          /* allocations.toml (tools/alloc.py) */

#define EM090_ID     DALAMADUR_EM_ID        /* 0x5a; Shah = 0x15a (variant 1) */
#define EM091_ID     DALAMADUR_TAIL_EM_ID   /* 0x5b; Shah = 0x15b */

/* our fields after the base object (0xcac0 = work pointer, set by the ctor) */
#define DALA_SIZE    (SIZE_uFestaEnemy + 0x40)
#define F_CTL        0xcac4   /* u8 controlled flag last logged (0xff = never) */
#define F_OWNER      0xcac5   /* u8 owner index last logged */
#define F_FRAMES     0xcac8   /* u32 frames run (slot 125) */

/* the controller (net owner) fields, GU (class-study.md "Who controls each half online", C) */
#define EN_OWNER     0x7424   /* u8 owner = the controlling member's index */

#define EN_VARIANT   (EN_ID + 5)   /* u8: 0 = Dalamadur, 1 = Shah */

/* u8 "no enemy push": sHitPush's enemy-vs-enemy pass 0x17cbf0 skips an enemy while it is set; the update clears it
 * each frame (0xa5198 -> 0xa532c), so it is rewritten every frame after that (GU's Ahtal-Ka / Ahtal-Neset in slot
 * 119: 0x10b6b7c / 0x10a8748). 4U: uEm024 / uEm083 slot 44 tails write W+0x55b = 1 every frame (0x77311c /
 * 0x8a1fc4). Without it the two halves' push spheres (emd word 21, radius 100 at the origin) moved them 200 apart. */
#define REC_NO_ENEMY_PUSH 0x529

void em090_register_class(void);
void em091_register_class(void);
/* dala.c: shared by both halves */
void dala_fields_init(void *self);
void dala_state_frame(void *self);                  /* GU slot 119 (per frame), both halves */
void dala_ctl_log(void *self, const char *half);    /* log the controller whenever it changes (MP tests) */
void dala_idle(void *self, uint32_t motion);        /* goal D1: hold the idle motion, nothing else */
