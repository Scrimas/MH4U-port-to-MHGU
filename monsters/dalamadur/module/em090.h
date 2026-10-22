/* Dalamadur: the head half uEm090_00 (4U uEm024) and the tail half uEm091_00 (4U uEm083), each running its normal
 * and Shah variant (GU variant 1 = 4U em110 / em111). notes: monsters/dalamadur/notes/class-study.md, plan.md. */
#pragma once
#include "game.h"
#include "alloc.h"          /* allocations.toml (tools/alloc.py) */

#define EM090_ID     DALAMADUR_EM_ID        /* 0x5a; Shah = 0x15a (variant 1) */
#define EM091_ID     DALAMADUR_TAIL_EM_ID   /* 0x5b; Shah = 0x15b */

/* our fields after the base object (0xcac0 = work pointer, set by the ctor) */
#define DALA_SIZE    (SIZE_uFestaEnemy + 0x150)
#define F_CTL        0xcac4   /* u8 controlled flag last logged (0xff = never) */
#define F_OWNER      0xcac5   /* u8 owner index last logged */
#define F_BUSY       0xcac6   /* u16 action serial + 1 of the running handler (AI think blocked) */
#define F_FRAMES     0xcac8   /* u32 frames run (slot 125) */
#define F_ARROWS     0xcacc   /* u8 arrows shown + 1 (0 = not yet), dala_efx_arrows_frame */
#define F_LASTACT    0xcad0   /* u16 last logged action (cat << 8 | num) | 0x8000 */
#define F_POOL       0xcad4   /* s32 head: the shared HP both halves had after the last sync (0 = not set) */
#define F_WORK       0xcae0   /* 0x100 bytes: the 4U class work struct [this+0x8d88] + offset (DALA_WORK; the head
                                 uses up to +0x68: +0x14..+0x3c the meteor machine, dala_meteor.c; +0x50 the on-body
                                 point, dala_gather.c; Shah's effect slots +120..+0xf0) */
#define F_WALK_H     0xcbe0   /* s32[5] sCollision handles of the walk pieces (-1 = none), dala_walk.c */
#define F_WALK_R     0xcbf4   /* void *[5] their rCollision resources */
#define F_WALK_SET   0xcc08   /* u8 active 4U walk set (0xff = not applied yet) */
#define F_STATE7     0xcc0c   /* u32 the cond-7 state word of the visibility rows [4U W+0x7a14] (dala_parts.c) */
#define F_END        0xcc10   /* = DALA_SIZE */

/* the controller (net owner) fields, GU (class-study.md "Who controls each half online", C) */
#define EN_OWNER     0x7424   /* u8 owner = the controlling member's index */

#define EN_VARIANT   (EN_ID + 5)   /* u8: 0 = Dalamadur, 1 = Shah */

/* u8 "no enemy push": sHitPush's enemy-vs-enemy pass 0x17cbf0 skips an enemy while it is set; the update clears it
 * each frame (0xa5198 -> 0xa532c), so it is rewritten every frame after that (GU's Ahtal-Ka / Ahtal-Neset in slot
 * 119: 0x10b6b7c / 0x10a8748). 4U: uEm024 / uEm083 slot 44 tails write W+0x55b = 1 every frame (0x77311c /
 * 0x8a1fc4). Without it the two halves' push spheres (emd word 21, radius 100 at the origin) moved them 200 apart. */
#define REC_NO_ENEMY_PUSH 0x529
/* u8 "no ground": GU's ground probe 0xbdf1c (rec+0x5b0 / +0x5b4 / +0x5b8) and the ground adjust 0xbe010 skip the
 * enemy while it is set (C); Ahtal-Ka / Ahtal-Neset write it every frame in slot 119 next to the push flag
 * (0x10b6b6c / 0x10a8738, C). Without it GU lifted both halves from 4U's spawn point y 0 to y 301 (test 2026-10-21:
 * front legs above the ground). */
#define REC_NO_GROUND     0x5cd5

/* ---- the action framework shared by both halves (dala.c; notes/port.md for the GU side) ---- */
#define REC(self)    FIELD(uint8_t *, self, EN_RECORD)
#define STEP(self)   FIELD(uint8_t, REC(self), REC_STEP0)   /* 4U W+0x144 */
#define STEP1(self)  FIELD(uint8_t, REC(self), REC_STEP1)   /* 4U W+0x145 */
#define MODE(self)   FIELD(uint8_t, REC(self), REC_MODE)    /* 4U W+0x1c9: body placement 0 / 1 / 2 */
/* per-action timer 4U W+468 = GU rec+0x1bc: reaction-sequence op 3 writes it in both players (4U 0x931b7c, GU
 * 0x9f568, C); Rathian's idle counts it down */
#define REC_TIMER    0x1bc
#define REC_HP_FLOOR 0x380    /* float: setHP 0x9a764 keeps HP >= max * this (-1 = none) [4U W+0x3f8] */
#define TIMER(self)  FIELD(float, REC(self), REC_TIMER)
#define DALA_WORK(T, self, off) FIELD(T, self, F_WORK + (off))   /* 4U [this+0x8d88] + off */

/* 4U frame checks, identical thunks into GU 0x727d0 (C): kind 0 = the motion reached frame s0 */
typedef int (*atFrame_t)(void *self, float frame);
#define atFrame  FN(atFrame_t, 0xb0a30)    /* [0x941dbc] */
#define atFrameB FN(atFrame_t, 0xb0a6c)    /* [0x94a50c]: same with the impl's r2 = 1 */
#define motionCheckB FN(motionCheck_t, 0xb0a60)   /* [0x93906c]: motionCheck with the impl's r2 = 1 */
/* setAction(cat, num, mode 1) + same-frame restart this+0x73ea = 1, unconditional [0x92b178: W+0x1d8 = 1] (C) */
#define setActionNow FN(setActionNext_t, 0x76a58)

void em090_register_class(void);
void em091_register_class(void);
/* dala.c: shared by both halves */
void dala_fields_init(void *self);
void dala_state_frame(void *self);                  /* GU slot 119 (per frame), both halves */
void dala_ctl_log(void *self, const char *half);    /* log the controller whenever it changes (MP tests) */
void dala_begin(void *self);                        /* 4U "strb 1, [W, #0x144]" + AI think blocked */
void dala_busy(void *self);
void dala_chain(void *self, uint32_t cat, uint32_t num);   /* 4U setActionNext 0x94ef9c */
void dala_end(void *self);                          /* 4U vcall vt+0x164 = our GU slot 247 (dala_end_slot) */
void dala_end_slot(void *self);                     /* GU slot 247 = 4U slot 89 (0x76c700 / 0x89fab8) */
int dala_think_blocked(void *self);                 /* GU slot 253 */
int dala_timer(void *self);                         /* 4U timerDown(&W+468) 0xb0709c */
int dala_at(void *self, float frame);               /* 4U motionCheck(0, 0, frame, 0) 0x91ab1c */
void dala_motion_keep(void *self, uint32_t motion, uint32_t flags, float blend, float start);   /* 4U 0x920058 */
void dala_attack(void *self, uint32_t slot, uint32_t index, uint32_t param);   /* 4U 0x933144 / 0x914dfc */
void dala_stub(void *self, const char *what, uint32_t a, uint32_t b);   /* logged 4U call without a GU mapping */
void dala_log_action(void *self, const char *half, const char *how);
void *dala_partner(void *self);                     /* 4U 0x68fd44(mgr, partner em) */
void *dala_head(void);                              /* this machine's head half (0 = none spawned) */
void dala_head25_frame(void *self);                 /* dala_head25.c: 4U head slot 25 parts (heat zone, 10/114) */
void dala_mat_spawn(void *self);                    /* dala_mat.c: head material animations (spawn, per frame) */
void dala_mat_frame(void *self);
void dala_register_half(void *self, uint32_t tail);  /* spawn: remember this half for dala_partner */
void dala_forget_half(void *self);                  /* delete */
void dala_place_log(void *self);                    /* D1 test: positions every 300 frames, 6 times */
void dala_hp_sync(void *head);                      /* shared HP, controller only (head's slot 119) */
void dala_death_sync(void *head);                   /* one half dead -> the other dies too (head's slot 119) */
void dala_walk_spawn(void *self);                   /* dala_walk.c: register the walk pieces (slot 118) */
void dala_walk_release(void *self);                 /* delete */
void dala_walk_frame(void *self);                   /* GU slot 168: 4U set rule + move with the joints */
void dala_join_frame(void *self);                   /* dala_join.c: tail bone 0 = head bone 0 (slot 168, both) */
#define SLOT_WALK 168
int dala_parts_frame(void *self);                   /* dala_parts.c: GU slot 130 = 4U slot 48 (hitzones, flags) */
#define SLOT_MOTION_FRAME 130
void dala_paint(void *self);                        /* GU slot 240: paint both halves (4U 0x910650) */
#define SLOT_PAINT 240
void dala_carve_install(void *self);                /* dala_carve.c: 4U carve records into the shared dtbparts */
void dala_carve_point(void *self);                  /* GU slot 264: the carcass carve point of this half */
#define SLOT_CARVE 264                              /* vt+0x420, base 0xac6c4 (death sequence end 0xa19ec) */
void dala_carcass_log(void *self);                  /* test log while dead (slot 119, both halves) */
/* dala_psl.c: GU slot 75 = the PSL (motion effect) post 0x70028, logged; dala_psl_watch: slot 119, both halves */
void *dala_psl_post(void *self, uint32_t list, const uint8_t *data, uint32_t slot, void *req);
#define SLOT_PSL_POST 75
void dala_psl_watch(void *self);
/* dala_react.c: one attack damages one half only (GU slots 38 hit landed / 209 hit candidate, 4U 0xbf4d28) */
void dala_hit_landed(void *self, uint8_t *hit, void *attacker, uint32_t kind);
#define SLOT_HIT_LANDED 38
int dala_hit_ok(void *self, const uint8_t *hit);
#define SLOT_HIT_OK 209
int dala_break_flinch(void *self, uint32_t part);   /* dala_react.c: GU slot 143 = 4U slot 60 (both halves) */
#define SLOT_BREAK_FLINCH 143
int dala_part_ok(void *self, uint32_t part);         /* dala_react.c: GU slot 140 = 4U slot 57 (both halves) */
#define SLOT_PART_OK 140
int dala_death_kind_ok(void *self);                 /* dala_react.c: GU slot 175 = 4U slot 82 (both halves) */
#define SLOT_DEATH_KIND 175
int dala_broken(void *self);                        /* dala_stage.c: 4U 0x7731a4, highest broken arena piece */
void dala_warp(void *self, float x, float y, float z, uint32_t yaw);   /* em090_act7.c: 4U W+0x150 / W+0x198 / yaw */
void dala_arena_frame(void *self);                  /* dala_stage.c: 4U slot 40's stage-8 hold (0x91b268) */
void em091_state_frame(void *self);                 /* em091_act.c: GU slot 119 = 4U slot 40 */
/* setBattleState(this, 1) [4U 0x91b158 = GU 0xbcb9c(this, state), callee map S]: both halves at spawn */
#define setBattleState FN(void (*)(void *, uint32_t), 0xbcb9c)
/* em091_act.c / em090_act.c: the halves' action dispatchers (GU slot 125 = 4U slot 44) */
void em091_act_run(void *self);
void em090_act_run(void *self);
