/* em089 head aim: the 4U second motion layer (layer 1) poses that turn Gogmazios' head toward the hunter during
 * the tar breaths, on the GU layer-1 API (game.h "motion layer 1"). Status / evidence: notes/port-checklist.md
 * "Head aim (aim agent)". No per-monster state of its own: the weights live in the model (layer-1 weight) and in
 * the enemy record (rec+0x308 = 4U W+916), exactly where 4U keeps them. */
#pragma once
#include <stdint.h>

enum {
    EM089_AIM_PITCH_UP   = 0,   /* 7/105 [0x8bdd2c]: motion 0x26b, joint 3 -> target, up to 30 deg, target above */
    EM089_AIM_PITCH_DOWN = 1,   /* 7/135 [0x8c02b0]: motion 0x27f, joint 3 -> target + 100 up, up to 45 deg, below */
    EM089_AIM_YAW        = 2,   /* 7/110 [0x8be434 r1 = 1]: pair 0x255 / 0x256, relative yaw / 20 deg, smoothed */
    EM089_AIM_YAW_HOLD   = 3,   /* 7/110 step 3: re-apply the pair with the held weight (no smoothing) */
};

/* entry of the action, right after its setMotion (that call already cleared layer 1 and the aim weight).
 * PITCH_*: pose the layer-1 motion with the weight from the head-to-target pitch (4U 0x9200a4).
 * YAW / YAW_HOLD: aim reset (4U 0x918f28; redundant after setMotion, kept explicit). */
void em089_aim_start(void *self, uint32_t kind);

/* PITCH_*: the one-shot re-evaluation 4U does at frame 158 (7/105) / 238 (7/135), only if the weight is not 0.
 * YAW: every frame of 7/110 step 2 (smoothing 0.3 / frame + pair at the main motion frame).
 * YAW_HOLD: every frame of 7/110 step 3. */
void em089_aim_update(void *self, uint32_t kind);

/* drop the aim now (layer-1 weight 0, rec+0x308 = 0). Not needed at action ends: the next setMotion does it. */
void em089_aim_stop(void *self);

/* current layer-1 weight (4U 0xb052d8). 4U 7/105 picks its breath effect by it at frame 160 (0 -> effect 53 level,
 * else effect 36 tilted 0x1556 up). */
float em089_aim_weight(void *self);

/* 1/33, 1/34 [0x8bb0f4 r1 = 2 / 3]: extra layer-1 motion 80 / 81 (flags 2, blend 16, start 0) at weight 1 over the
 * turn motion 65 / 66 (4U 0xb07ba4 + 0xb054e0). */
void em089_aim_layer(void *self, uint32_t motion, uint32_t flags, float blend, float start, float weight);
