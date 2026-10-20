/* em089 tar material animations (Solid / Liquid / Gas and transitions) on the GU material-animation API.
 * Assets: tools/build_em089_arc.py converts the 4U animation blocks of the 5 tar materials (types 1..5 = the
 * names' m01 head, m02 chest, m03 l_arm, m04 r_arm, m05 tail) into GU MRL blocks; 'Solid' autoplays, so without
 * this code every tar part shows Solid. Format and runtime: tools/mrl_anim.py docstring.
 * Since 2026-10-18 (tar-look agent) each tar part has TWO materials of the same type (4U per-vertex alpha classes
 * 0.5 / 0.75, tools/mod4u2gu.py VALPHA_CLASSES), driven identically; the 4U diffuse w (material alpha) is
 * animated too: alpha-tested drips that scroll down (as in 4U: head Solid w 0.025 = hidden, chest / arms Solid
 * w 0.9 / 1.0 = matte tar, Liquid / Gas w 0.7..1 = sparser drip streaks in the 0.5 class, solid in the 0.75). */
#pragma once
#include <stdint.h>

/* GU (MHGU 1.4 main offsets, read from the code, see tools/mrl_anim.py) */
#define TAR_GU_FIND_ANIM   0xb0bb0cu  /* int  (void *animset, const char *name): index or -1 */
#define TAR_GU_PLAY_ANIM   0xb0cab0u  /* void (void *mat, int slot 0..3, int index): +0x50+8*slot = index, frame 0 */
#define TAR_GU_CUR_ANIM    0xb0ffb8u  /* int  (void *mat, int slot): (s16) +0x50+8*slot, -1 = none */
/* per-frame advance (material vtable slot 8): void (void *mat, float dt) -> 0xb0ea4c: for the 4 slots
 * frame += mat+0x20 (speed, ctor 1.0) * dt, wrap if entry flags bit 0 (loop) else clamp, then apply the tracks
 * (vt slot 22 = set constant). The engine calls it from the unit virtual 0x88f45c (uFestaEnemy slot 24) for
 * every material with an animation set, but only while byte this+0x168 != 0; the enemy per-frame code 0x71fd4
 * writes this+0x168 = !(this+0x1404 bit 13) every frame (parent's flag if this+0x30). dt = this+0x1c. */
#define TAR_GU_MAT_UPDATE  0xb0ffc4u
#define TAR_MAT_SPEED      0x20
#define TAR_EN_MATANIM_ON  0x168      /* monster: byte, material animation update enabled */
#define TAR_EN_DT          0x1c       /* monster: frame delta (f32) */
#define TAR_MAT_ARRAY      0xf8       /* monster: material objects (0x890adc(this, i) = this+0xf8[i]) */
#define TAR_MAT_COUNT      0xfc       /*          their count */
#define TAR_MAT_TYPE_WORD  0x18       /* material: type = (word >> 22) & 0xff (MRL entry w6 bits 21-28) */
#define TAR_MAT_ANIMSET    0x74       /* material: animation set, +0x10 -> {count, entry *[count]}, entry +0 frames */
#define TAR_MAT_FRAME0     0x54       /* material: slot 0 frame (f32) */

/* tar modes = 4U: 0 Solid, 1 Liquid, 2 Gas */
#define TAR_SOLID  0
#define TAR_LIQUID 1
#define TAR_GAS    2

/* spawn: 4U slot 39 [0x8b9e10..0x8ba09c]: head and chest Liquid, arms and tail Liq_to_Sol (-> Solid). Call from
 * object slot 118 (em089_spawn_setup), after the model is loaded. Logs the tar materials found once. */
void em089_tar_spawn(void *self);

/* per frame: 4U 0x8c8da0. Plays the transition when a part's mode changed, then the steady animation once the
 * transition reached its last frame. Call once per frame (object slot 132, base = bx lr, the per-material loop
 * em049 uses for the same purpose, or any existing per-frame hook). Cheap when nothing changes. */
uint32_t em089_tar_update(void *self);   /* returns bit k for each part k that entered steady Solid this frame */

/* tar state machine (em089_act.c, needs the object fields): 4U slot 39 spawn part [0x8b9bc8..0x8b9e0c: amounts,
 * modes, hitzones, state word W+0x7814] and the 4U slot 50 visibility bits (0x8000 head / 0x10000 tail while in
 * steady Solid), fed with em089_tar_update's result. Both re-evaluate the mesh-group visibility of the word. */
void em089_tar_machine_spawn(void *self);
void em089_tar_steady(void *self, uint32_t entered);

/* set the tar mode of part k (0 head, 1 chest, 2 l_arm, 3 r_arm, 4 tail) = 4U work struct T = *(this+0x8d88):
 * u16 T+0x54+2k (current target mode; T+0x5e+2k = previous). Call wherever the 4U code stores T+0x54+2k. */
void em089_tar_set_mode(void *self, uint32_t k, uint32_t mode);

/* same, addressed by the 4U part number of 0x8c69b8(this, mode, part): parts 0, 7, 2, 3, 6 -> k 0..4
 * (0x8c69b8 itself only sets the visibility bits of W+0x7814; this is the animation side). */
void em089_tar_set_part(void *self, uint32_t mode, uint32_t part);

/* current mode of part k (0..4), or -1 */
int em089_tar_mode(void *self, uint32_t k);

/* ---- wing size (material type 50 'm50_wing', 4U animations Small / SmalltoLarge / LargetoSmall / Large; the 4U
 * w is the material alpha, alpha-tested at ref 40: Small 0.165 = only the opaque membrane core, Large 1.0 = the
 * whole torn membrane). 'Small' autoplays (4U slot 39 plays it at spawn [0x8ba04c]), so without this hook the
 * wing stays Small. Port of 4U 0x8c64b8, called once per frame from 4U slot 77 [0x8c9aa0] (em089_act.c
 * em089_slot77 = its port): motion 0x108 at frame 148 -> SmalltoLarge; motion 0x10b at 128, 0x30b / 0x30c at 30
 * -> LargetoSmall; other motions: steady Large reverts (LargetoSmall) when state class rec+0x1ba == 0 and not dead
 * (0x94d7a8); a finished SmalltoLarge / LargetoSmall continues with Large / Small.
 * Returns the 4U state-word change: EM089_WING_SET = W+0x7814 |= 0x20000, EM089_WING_CLEAR = &= ~0x20000 (bit 17
 * = emd row "group 102 shown while set"; the caller owns the word and re-evaluates the group visibility), 0 = none. */
#define EM089_WING_WORD_BIT 0x20000u
#define EM089_WING_SET   1
#define EM089_WING_CLEAR 2
int em089_wing_update(void *self);

/* ---- lights (material type 6 'm06_add'): 4U 0x8c62c0(this, k) plays Light animation k of the 4U name table
 * 0xff6fb4 (0 Light_Gas_Bress, 1 Light_Gas_Bress_End, 2 Light_Wing_Attack_back, 3 Light_Wing_Attack,
 * 4 Light_Wing_Attack_gekiryusou, 5 Light_Wing_Attack_houdai, 6 Light_Tail_Attack01, 7 Light_Tail_Attack02),
 * frame 0; k < 0 stops (slot 39 at spawn). Call where ported 4U code calls 0x8c62c0 (slot 47 lights etc.). The
 * lights' meshes (groups 2, 5, 17, 18, 19) are only drawn while their state-word bits 18-22 are set. */
void em089_light_play(void *self, int k);
