/* MHGU 1.4 main: addresses and calls used by the module. Offsets are main offsets (runtime = MAIN + off).
 * Sources: notes/enemy-class.md (CONFIRMED unless marked). */
#pragma once
#include <stdint.h>

/* main's runtime base: not a constant. Emulators place the game's modules differently (yuzu / Eden reserve an
 * argument area after rtld, Ryujinx does not), so crt0.S derives it from this module's own load address: the gap
 * between main and subsdk1 is the same everywhere (build.py MODULE_BASE - MAIN_BASE). Relocated by rtld before any
 * of our code runs. */
extern uint32_t g_main_base;
#define MAIN_BASE g_main_base
#define MAIN(off) (MAIN_BASE + (uint32_t)(off))
#define FN(type, off) ((type)MAIN(off))
#define FIELD(T, p, off) (*(T *)((uint8_t *)(p) + (off)))

/* MtDTI: 0x20 bytes. +0 vtable, +4 name, +0x10 parent, +0x18 size>>2 | flags | attr, +0x1C id */
typedef struct MtDTI { uint32_t w[8]; } MtDTI;

/* MtDTI ctor 0x7aedcc(dti, name, parent, size, id (0 = crc32 of name), attr, flags) */
typedef void (*MtDTI_ctor_t)(MtDTI *, const char *, MtDTI *, uint32_t, uint32_t, uint32_t, uint32_t);
#define MtDTI_ctor FN(MtDTI_ctor_t, 0x7aedcc)

/* allocator for a class: 0x7aa47c(dti); alloc = vt[0x20/4](a, size, align, dti->id), free = vt[0x34/4](a, p) */
typedef void *(*get_allocator_t)(MtDTI *);
#define get_allocator FN(get_allocator_t, 0x7aa47c)

/* uFestaEnemy: base class of every monster */
#define DTI_uFestaEnemy        ((MtDTI *)MAIN(0x18533f8))
#define VT_uFestaEnemy         MAIN(0x1734d44)        /* object vtable address point, 286 slots */
#define VT_uFestaEnemy_SLOTS   286
#define DTIVT_uEm001_00        MAIN(0x1732290)        /* a monster DTI vtable (3 slots, slot 2 = newInstance) */
#define SIZE_uFestaEnemy       0xcac0u
typedef void *(*ctor_t)(void *);
#define uFestaEnemy_ctor FN(ctor_t, 0xc9cf0)
#define uFestaEnemy_dtor FN(ctor_t, 0xc9d98)

/* enemy framework calls (notes/api-map.md; MH4U counterpart in brackets) */
typedef void (*setMotion_t)(void *self, uint32_t motion, float blend_frames, float start_frame);
#define setMotion FN(setMotion_t, 0xaff40)          /* [0x94e350] motion = bank << 8 | index */
typedef void (*setTargetMode_t)(void *self, uint32_t mode);
#define setTargetMode FN(setTargetMode_t, 0xbc8b0)  /* [0x9167ec] */
typedef int (*isMotionEnd_t)(void *self);
#define isMotionEnd FN(isMotionEnd_t, 0xb0a84)      /* [0xb05df4] */
typedef uint32_t (*curMotion_t)(void *self);
#define curMotion FN(curMotion_t, 0xb0a00)          /* [0x90f994] */
/* looping/idle variant of setMotion (Rathian idle: 0xaffac(this, 1, 10.0, x)) [0x94f440] */
#define setMotionLoop FN(setMotion_t, 0xaffac)
/* motionCheck(self, kind, out, s0, s1) -> bool [0x91ab1c]; identical thunk in both games
 * (mov r3,r2; mov r2,#0; b <impl>). kind 0: the motion reached frame s0 (one-shot trigger, the attack/event
 * pattern); kind 1/2/3/9: other frame queries (3 / 9 = window s0..s1). out (C): optional float* that receives the
 * step fraction inside the window (impl 0x727d0 stores 1.0 first); em089 scales its per-frame turns with it. */
typedef int (*motionCheck_t)(void *self, uint32_t kind, float *out, float s0, float s1);
#define motionCheck FN(motionCheck_t, 0xb0a24)
/* timerDown(self, &timer, scale) -> 1 once timer <= 0 (timer -= speed * scale, clamped to 0) [0xb0709c] */
typedef int (*timerDown_t)(void *self, float *timer, float scale);
#define timerDown FN(timerDown_t, 0x72128)
/* attack collision: attackEx(self, slot, attack index, param) [0x933144]: slot 0/1 selects a 152-byte attack
 * slot in the record (4U: W + table + slot * 0x98), index = entry of the monster's attackdata (field 26), param =
 * 3rd value from the 4U handler (hit group / duration, not decoded). attack(self, slot, index) = param 0 [0x914dfc].
 * 4U em089 7/7: slot0 = 13, slot1 = 14 at entry, slot1 = 48 at frame 240, slot1 = 49 at frame 254. */
typedef void (*attackEx_t)(void *self, uint32_t slot, uint32_t index, uint32_t param);
#define attackEx FN(attackEx_t, 0x7dc2c)
/* setMotionEx(self, motion, flags, blend, start) [0x9190c4]; 4U turns use flags 2 */
typedef void (*setMotionEx_t)(void *self, uint32_t motion, uint32_t flags, float blend_frames, float start_frame);
#define setMotionEx FN(setMotionEx_t, 0xafda4)
/* attackReset(self, slot) [0x90f934] (C, same per-slot shape: 4U 152-byte slots at W+0xc08, GU 184-byte slots,
 * clears the hit state / sets id 255): em089 calls it before re-arming a slot with attackEx */
typedef void (*attackFlag_t)(void *self, uint32_t slot);
#define attackFlag FN(attackFlag_t, 0x7e048)
/* setAttackId(self, id): byte this+0x7583, 255 = none; 4U handlers call it with 0/1 on entry [0x9162f8] */
typedef void (*setAttackId_t)(void *self, uint32_t id);
#define setAttackId FN(setAttackId_t, 0xb1a14)
/* stopMove(self): clears the move velocity (4U attacks call it on entry) [0x91b3f4] (S, no args in Rathian) */
typedef void (*stopMove_t)(void *self);
#define stopMove FN(stopMove_t, 0x7bdd4)
/* setAction(self, category, number, mode, [sp] 0): writes this+0x73e0/1, clears the step bytes, runs slot 127
 * (remap) when mode == 1 [0x90efac]. Monsters chain actions with the wrapper setActionNext [0x94ef9c]. */
typedef void (*setAction_t)(void *self, uint32_t cat, uint32_t num, uint32_t mode, uint32_t zero);
#define setAction FN(setAction_t, 0x76154)
typedef void (*setActionNext_t)(void *self, uint32_t cat, uint32_t num);
#define setActionNext FN(setActionNext_t, 0x76984)
/* setActionW(self, cat, num) [0x935ac8] (C, same body: returns when category == 11, else setAction(cat, num,
 * mode 2)). em089 ends some actions with setTargetMode(0) + setActionW(1, 20) + thinkRequest(0). */
#define setActionW FN(setActionNext_t, 0x752ec)
/* thinkRequest(self, 0) [0x927730] (C: 0x82510 sets this+0x72f0 = 1 when r1 == 0) */
typedef void (*thinkRequest_t)(void *self, uint32_t zero);
#define thinkRequest FN(thinkRequest_t, 0x82510)

/* ---- movement / targeting services used by the em089 handlers (2026-10-17 port; 4U address in brackets) ---- */
/* move sequence (engine turn-in-place / turn-and-go): start(self, table, mode, flags, angle_offset) and
 * poll(self, table) -> 1 when finished. "2" = table is a pair of record pointers {near, far}: the far record is
 * used when |angle to the target slot| > near->angle_lo (identical selection code in both games); "1" = a single
 * record. Record (64 bytes, same in both games): float turn_start, turn_end, straight_end; u16 angle_max
 * (rate = angle / (end - start)), u16 straight_angle; then 3 entries {u32 motion, blend, start, u32 flags}:
 * straight (|angle| <= straight_angle), positive angle, negative angle. Only difference: 4U stores blend/start as
 * s32 (0x911da8 converts), GU as float (0x77370); motion flags are the same field (4U Rathian 0xe0bc10 = GU
 * 0x16a2a64 with ints). The target is the slot rec+464 (+16 if rec+0x336 bit 7). [4U 0x91db5c/0x91db7c ->
 * 0x92f420/0x92f728 = GU 0x7a340/0x7a364 -> 0x795ac/0x79abc (C); single: 4U 0x911c44/0x92f720 = GU 0x7a314/
 * 0x7a338 (C)] */
typedef struct { uint32_t motion; float blend, start; uint32_t flags; } seq_entry;
typedef struct { float turn_start, turn_end, straight_end; uint32_t angle; seq_entry e[3]; } seq_rec;
typedef void (*seqStart_t)(void *self, const void *table, uint32_t mode, uint32_t flags, int32_t angle_offset);
typedef int (*seqPoll_t)(void *self, const void *table);
#define seqStart2 FN(seqStart_t, 0x7a340)
#define seqPoll2  FN(seqPoll_t, 0x7a364)
#define seqStart1 FN(seqStart_t, 0x7a314)
#define seqPoll1  FN(seqPoll_t, 0x7a338)
/* setStopDist(self, flags, 0, dist): arm "move to target slot" with stop distance dist * size scale; the target
 * slot is rec+464 (+16 when flags & 0x100) [0x92dc88 (C: same body, GU has the extra byte r2 at rec+0x5e9c, 388
 * of 437 GU callers pass 0)] */
typedef void (*setStopDist_t)(void *self, uint32_t flags, uint32_t zero, float dist);
#define setStopDist FN(setStopDist_t, 0x78b88)
/* inRange(self, a, b) -> 1 when the armed target is reached; its tail 0x78f7c also turns the yaw rec+0x54 toward
 * the target slot (0xc0e78), i.e. calling it every frame is the 4U run steering [0x92dd04] (C) */
typedef int (*inRange_t)(void *self, uint32_t a, uint32_t b);
#define inRange FN(inRange_t, 0x78c34)
/* findTarget(self, a, angle_range, b) -> angle or -1 [0x9128e4] (C: identical wrapper into 0xa6d28 = 4U 0x943a18:
 * [sp] -1, [sp+4] b, r3 = a ? 0x2000 : 0xffff); findTargetEx(self, a, b, c, [sp] d) [0x9276b4] (C) */
typedef int32_t (*findTarget_t)(void *self, uint32_t a, uint32_t range, uint32_t b);
#define findTarget FN(findTarget_t, 0xa6cd8)
typedef int32_t (*findTargetEx_t)(void *self, uint32_t a, int32_t b, uint32_t c, uint32_t d);
#define findTargetEx FN(findTargetEx_t, 0xa6d04)
/* setTarget(self, kind, sub, param, slot): define what target slot rec+464 + 16 * slot tracks [0x916bcc] (S: same
 * slot arrays rec+464/+560/+564/+568/+576 vs 4U W+536/+632/+636/+640/+648) */
typedef void (*setTarget_t)(void *self, uint32_t kind, uint32_t sub, uint32_t param, uint32_t slot);
#define setTarget FN(setTarget_t, 0xc6e14)
/* turnToTarget(self, max_step, angle_offset) -> 1 when facing the target slot rec+464 [0x91db84] (C, identical
 * body: atan2 + turn step 0xc0e78 on yaw rec+0x54). turnToward 0x76c28 below is its explicit-position twin. */
typedef int (*turnToTarget_t)(void *self, uint32_t max_step, uint32_t angle_offset);
#define turnToTarget FN(turnToTarget_t, 0x76cc4)
/* turnStep(self, target, cur, max) -> new u16 angle: cur stepped toward target by max * this+28 [0x91ab28: same
 * arguments, max * this+20] (C: GU 0x76c28 calls it with (target, yaw, max)) */
typedef uint32_t (*turnStep_t)(void *self, uint32_t target, uint32_t cur, uint32_t max);
#define turnStep FN(turnStep_t, 0xc0e78)
/* rotateVel(self, angles, flags): rotate the velocity rec+0x10 by the u16 angle triple (x, y, z) at angles (the
 * monster's own: rec+0x50); flags bit 0 / state class rec+0x1ba in {1,2,4,5,6} select the variant [0x91150c] (C:
 * same state mask 0x76) */
typedef void (*rotateVel_t)(void *self, const void *angles, uint32_t flags);
#define rotateVel FN(rotateVel_t, 0x7cab8)
/* accelVel(self, angles, flags): velocity rec+0x10 += acceleration rec+0x20 * time scale, rotated by the angles
 * [0x9165cc: W+352 += W+368 * this+20] (C: same fields, dt this+28 read as this+0x1428 - 0x140c) */
#define accelVel FN(rotateVel_t, 0x7a8dc)
#define REC_ACCEL   0x20    /* float acceleration x, y, z [4U W+368] */
/* flag setters used by em089's sleep (3/2): rec+0x36b = 1 [0x922cd8: W+0x3e3 = 1], rec+0x3a2 = 2 [0x93c6c8:
 * W+0x41a = 2] (C, single store each); 4U W+0xb00 -> rec+0x990 (S, api-map) */
#define sleepFlagA FN(stopMove_t, 0x7fcbc)
#define sleepFlagB FN(stopMove_t, 0xc0410)
/* speedFactor(self) = rec+428 * rec+432 [0x911cb4] (C) */
typedef float (*speedFactor_t)(void *self);
#define speedFactor FN(speedFactor_t, 0xbe5d4)
/* resetVel(self): velocity rec+0x10..0x18 = 0 [0x916260] (C); stopMove also clears rec+0x20..0x28 */
#define resetVel FN(stopMove_t, 0x7b5d4)
/* vertAccel(self, a): rec+0x5c += a * this+28 (time scale), rec+0x1b9 = 1 [0x915d7c: W+384 += a * this+20,
 * W+0x1c7 = 1] (C) */
typedef void (*vertAccel_t)(void *self, float a);
#define vertAccel FN(vertAccel_t, 0xbf7d8)
/* rest(self): the pair 0xbf590 (float per-species value) + 0xbca40(self, value) (adds value * speed to rec+0x19c
 * by state, setTargetMode(1)) used by GU slot 248 [4U 0x93d8a8 + 0x92e9d4, same pair before em089's landing /
 * fall motions] (S) */
typedef float (*restValue_t)(void *self);
typedef void (*restApply_t)(void *self, float v);
#define restValue FN(restValue_t, 0xbf590)
#define restApply FN(restApply_t, 0xbca40)
/* netEvent2(self, param) [0x93e590] (S, aligned 99/99: host check then 0x49d94(self, 2, param)) */
typedef void (*netEvent2_t)(void *self, uint32_t param);
#define netEvent2 FN(netEvent2_t, 0xaa704)
/* selectDataSet(self, idx): copy row idx of the monster data list (+0x74, 36-byte rows) into the record and note
 * it at this+0x75c0/0x75c2 [0x947438: same rows from 0x93863c +0x74] (S, aligned 99/99). em089 slot 40 picks
 * 0 ground / 1 flying (W+0x1c9) / 2 special state (W+0x1c8 in 1, 3). */
typedef void (*selectDataSet_t)(void *self, uint32_t idx);
#define selectDataSet FN(selectDataSet_t, 0xc833c)
/* wanderPoint(self, a, b): random point (+-60 degrees, random distance) into this+0xba60, the AI's move destination
 * copied to rec+464 at think time [0x92d0d4] (S, aligned 99/99) */
typedef void (*wanderPoint_t)(void *self, uint32_t a, uint32_t b);
#define wanderPoint FN(wanderPoint_t, 0xc46c8)
#define REC_HP      0x370   /* s32 HP, +4 max [4U W+0x3e8/0x3ec: same clamp code as GU 0x9a774] (C) */
#define REC_TGT_KIND 0x230  /* u8 target slot 0 kind, +2 sub, +4 param; +1/+3/+5 saved copies [4U W+0x278..0x27d] (S) */
#define REC_VEL     0x10    /* float velocity x, y, z [4U W+352] */
#define REC_ANGLES  0x50    /* u32 x, yaw (0x54), z angle triple [4U W+424] */
#define REC_VSPEED  0x5c    /* float vertical speed [4U W+384] */
#define REC_STATE   0x1ba   /* u8 state class [4U W+0x1c8] (C: 0x7cab8 vs 0x91150c) */
#define REC_MODE    0x1bb   /* u8 mode flag, bit 0 tested by the engine, net-synced [4U W+0x1c9] (S) */
#define EN_DT       28      /* float time scale (frames per tick), used by 0xc0e78 / 0xbf7d8 [4U this+20] (C) */

/* end of an action: virtual slot 247 (base 0x75224): setTargetMode(0), setAction(0, 0|1|2 by state, mode 2),
 * then 0x82510(self, 0) = this+0x72f0 = 1 (think requested) -> next frame the AI (0x82ddc) picks the next action.
 * Slot 248 (0x75338) = same with (0, 3). The 4U equivalent is the vcall vt+0x164 used by every em089 handler. */
#define SLOT_ACTION_END   247
#define SLOT_ACTION_END_3 248
/* slot 249 (0x75394): setTargetMode(3), setAction(0, 6, mode 2) unless category 11, think requested = 4U
 * 0x9559a8 (C: same sequence; em089 ends its landing / flight-end actions with it) */
#define SLOT_ACTION_END_6 249
#define VCALL0(self, slot) (((void (*)(void *))((*(uint32_t **)(self))[slot]))(self))
/* turnToward(self, max_step, angle_offset, pos) -> 1 when facing pos: yaw rec+0x54 (u16 angle) is rotated toward
 * atan2(pos.x - rec+64, pos.z - rec+72) + offset by at most max_step * this+28 per frame (via 0xc0e78, the
 * counterpart of the 4U turn step 0x91ab28). The AI's target positions are rec+464 + 16 * slot (read by the
 * selector's angle conditions, 0x86d80). */
typedef int (*turnToward_t)(void *self, uint32_t max_step, uint32_t angle_offset, const float *pos);
#define turnToward FN(turnToward_t, 0x76c28)
#define REC_POS_X   64      /* float position x, y, z */
#define REC_POS_Z   72
#define REC_YAW     0x54    /* u16 yaw angle (stored as u32) */
/* libm atan2f through the main PLT (0x76c28 calls it with dx, dz) */
typedef float (*atan2f_t)(float, float);
#define atan2f_gu FN(atan2f_t, 0x13efd70)
/* libm sinf / cosf (radians) through the PLT [4U table sin 0x568bf0 / cos 0x568bb8 on u16 angles] (C: table
 * entries are (sin, cos, dsin, dcos); GU 0x795ac feeds the yaw * 2pi/65536 to both) */
typedef float (*sinf_t)(float);
#define sinf_gu FN(sinf_t, 0x13efde8)
#define cosf_gu FN(sinf_t, 0x13efdf4)
/* setMotionSpeed(self, s): motion speed multiplier rec+0x398 [0x922c78: W+0x410] (C: both setMotionEx reset it
 * to 1.0) */
typedef void (*setMotionSpeed_t)(void *self, float s);
#define setMotionSpeed FN(setMotionSpeed_t, 0xb0870)
/* this machine controls the monster (net owner): u8 this+0x7420 = rec+0x5fe0, also tested by the think check
 * 0x82538 [4U W+0x1d9, set where the owner index W+0x1da equals the local player index] (C) */
#define EN_CONTROLLED 0x7420
#define REC_TARGET  464     /* float[4] move destination, slot rec+0x335 & 1 (range test 0x78c34); not the hunter */
/* jointPos(model, joint id, float out[4]): world position of a joint (id -> index table +0x498, joints +0x494,
 * 160 bytes each, position at +64; unknown id -> joint 0) */
typedef void (*jointPos_t)(void *model, uint32_t joint, float *out);
#define jointPos FN(jointPos_t, 0xc1708)
/* local player object = [[main+0x2126F48]+0x58] (cheats project, Pixel's chain) */
#define PLAYER_ROOT MAIN(0x2126F48)

/* mesh-group visibility: bit g of this+0x110.. (u32[16], 1 = drawn; GU 0x89079c tests it). The spawn setup 0xb8c54
 * sets all 512 bits (memset 0xff @0xba258), then calls slot 118. The field-3 XFS (rMonsterPartsManager, stored at
 * this+0x1420 by the loader callback 0x70854) lists states of (group, visible); applyPartsState(self, state)
 * [0x72d34] writes one state's bits (state < 0 or >= count: nothing). The engine itself never picks a state
 * (0xb610/14/18 = -1 unless the monster calls 0x71454): every monster applies its own (Rathian @0xcf5a18: 0, then
 * one of each break pair). The 4U counterpart is the cond-7 rows of the emd parts table on the state word W+0x7814
 * (em089 tar states, 0x8c69b8). */
typedef void (*applyPartsState_t)(void *self, int32_t state);
#define applyPartsState FN(applyPartsState_t, 0x72d34)
#define EN_PARTS_MGR 0x1420   /* rMonsterPartsManager*: +0x68 state count, +0x74 state array */
#define EN_GROUP_VIS 0x110    /* u32[16] mesh-group visibility bits (bit g, LSB first, 1 = drawn) */

/* per-part hitzone row pointers rec+0x418 + 4 * row (4U W+0x460) into the meat tables of the data block
 * *(this+0x75ec) + 100 (+0xc base table, +0x10 alternate table; rows of 10 bytes in both games).
 * partMeatBase(self, row) [0xbab88 = 4U 0x936ea8, C: same body]: row -> base table row `row`;
 * partMeatAlt(self, row, alt) [0xbabb8 = 4U 0x93415c, C]: row -> alternate table row `alt` (nothing if no table) */
typedef void (*partMeatBase_t)(void *self, uint32_t row);
#define partMeatBase FN(partMeatBase_t, 0xbab88)
typedef void (*partMeatAlt_t)(void *self, uint32_t row, uint32_t alt);
#define partMeatAlt FN(partMeatAlt_t, 0xbabb8)
#define EN_MEAT_DATA  0x75ec  /* data block pointer; meat tables at +100 (0x71078) */
#define REC_PART_MEAT 0x418

/* category 17 is handled by the base (Rathian's dispatcher tail-calls 0xaf598) */
typedef void (*act_base_t)(void *self);
#define action_base17 FN(act_base_t, 0xaf598)

/* uFestaEnemy virtual slots we override */
#define SLOT_DTOR_DELETE 1
#define SLOT_GET_DTI     5
#define SLOT_ACTION      125   /* per frame from 0xa5c40: run the current action (category this+0x73e0) */
#define SLOT_STATE_FRAME 119   /* bx lr, per frame from 0xadb3c (uEnemy update): monster state hook [4U slot 40] */
#define SLOT_ACTION_START 129  /* bx lr, setAction bookkeeping 0x755b4 -> vt+0x204 (this, cat, num) [4U slot 47] (C:
                                  same arguments; em089's 47 counts actions by (cat, num)) */
#define SLOT_PARTS_FRAME 132   /* bx lr, per frame from 0xae42c: per-part / material loop [4U slot 50] */
#define SLOT_AI_COND     133   /* return 0; AI opcode 0x6f -> 0x81ff8 -> vt+0x214 (this, id): monster condition
                                  value [4U slot 51] (C: em089 ids 0..28 = the 29 cases of 4U 0x8c9084) */
#define SLOT_SPAWN_SETUP 118   /* (self, flag) from the spawn setup 0xb8c54 after all groups were set visible;
                                  base bx lr, Kushala 0xdf2180 (work fields + 0x71454(self, 1, 6, -1)) */

/* enemy object fields */
#define EN_ACT_CAT  0x73e0   /* current action category / number, previous pair at +2/+3 (setAction 0x76154) */
#define EN_ACT_NUM  0x73e1
#define EN_ACT_SERIAL 0x73e8 /* u16 action serial, incremented by setAction */
/* base slot 253 (0x7ff90): 1 = AI think blocked (categories 11 / 14, death 12/255) */
#define SLOT_THINK_BLOCKED 253
typedef int (*think_blocked_t)(void *self);
#define think_blocked_base FN(think_blocked_t, 0x7ff90)
#define REC_STEP0   0x1a1    /* action step bytes rec+0x1a1..0x1a3 (cleared by setAction) [4U W+0x144..0x146] */
#define REC_STEP1   0x1a2
#define REC_STEP2   0x1a3
#define EN_THINK_REQ 0x72f0  /* u8: 1 = AI think requested (set by the action-end slots via 0x82510) */
#define EN_CMDTBL   0x75f4   /* rEnemyCmd (manifest field 37) set through callback 0x70a5c; AI groups = +0x68 */
#define EN_RECORD   0x1428   /* enemy record pointer (HP at rec+0x370) */
#define EN_WORK     0xcac0   /* monster work pointer = record + 96 (set by each monster ctor) */
#define EN_ID       0xb5f0   /* set by setup 0x6fb14: id, +4 em number, +5 variant, +6 table index, +7 small */

/* ---- motion layer 1 (head aim, module/em089_aim.c; notes/port-checklist.md "Head aim") ----
 * Model layer k = this+0x4b0 + k * 0x140 [4U this+576 + k * 304]; layer count this+0x4a4 = 2 for every enemy (uEnemy
 * ctor 0xacc8c -> setLayerNum 0x957480(this, 2)). setMotion / setMotionEx clear layer 1 (motion 0xffff via 0x53a164)
 * and reset the aim weight (0xafda4 tail = aimReset), so a layer-1 pose lasts until the next main motion. The GU
 * wrappers compute the layer speed themselves (rec+908 * rec+916 * status factor = 4U 0x941dd4). All C. */
/* layer1MotionW(self, mot, start_frame, s1): layer-1 motion at start_frame, no blend, weight 1 - s1 [0x9200a4] */
typedef void (*layer1MotionW_t)(void *self, uint32_t motion, float start_frame, float one_minus_weight);
#define layer1MotionW FN(layer1MotionW_t, 0xb03e8)
/* layer1Motion(self, mot, flags, blend, start): layer-1 motion, weight untouched [0xb07ba4] */
typedef void (*layer1Motion_t)(void *self, uint32_t motion, uint32_t flags, float blend_frames, float start_frame);
#define layer1Motion FN(layer1Motion_t, 0xb000c)
/* layer1Pair(self, motA, motB, frame, w): w >= 0 -> motA else motB at `frame`, weight |rec+0x308| [0x935ff0] */
typedef void (*layer1Pair_t)(void *self, uint32_t mot_a, uint32_t mot_b, float frame, float w);
#define layer1Pair FN(layer1Pair_t, 0xb0694)
/* layer-1 weight this+0x638: setter [0xb054e0] / getter [0xb052d8] */
typedef void (*layer1SetWeight_t)(void *self, float w);
#define layer1SetWeight FN(layer1SetWeight_t, 0x726dc)
typedef float (*layer1Weight_t)(void *self);
#define layer1Weight FN(layer1Weight_t, 0x726f8)
/* aimSmooth(self, target, rate): rec+0x308 steps toward target by rate * this+28, clamped to [-1, 1] [0x918e80] */
typedef void (*aimSmooth_t)(void *self, float target, float rate);
#define aimSmooth FN(aimSmooth_t, 0xb07d0)
/* aimReset(self): layer-1 weight 0, rec+0x308 / +0x30c / +0x310 = 0 [0x918f28] */
typedef void (*aimReset_t)(void *self);
#define aimReset FN(aimReset_t, 0xafeec)
/* current layer-0 motion frame this+0x500 [4U this+656] */
typedef float (*motionFrame_t)(void *self);
#define motionFrame FN(motionFrame_t, 0xb09e4)
/* layer-0 fields, same offsets inside the layer in both games (C): blend frames left this+0x4f4 [4U this+644]
 * (getter 0xb0a8c: > 0), motion speed this+0x50c [4U this+668] (getter 0xb09bc) */
#define MOT_BLEND   0x4f4
#define MOT_SPEED   0x50c
#define REC_AIM_W   0x308   /* float signed aim weight [-1, 1] (aimSmooth / layer1Pair) [4U W+916] */
