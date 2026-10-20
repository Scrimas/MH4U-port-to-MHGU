/* Battlequarters alias: Fortress gimmick logic adjusted to 4U (notes/stage.md section 12, arena-2 agent).
 *
 * Dragonator. 4U m19 (aMap19 setup 0x6594b4) places TWO uStageGimmick type-2 spears (m19d-gekiryusou) at
 * (+-495, 800, 4105) facing -z; the switch (SIS point kind 5) fires them; reuse after 600 s (4U 0x6b0ce0: elapsed >=
 * fps * 10 * 60, r9 = 10 for every quest but 351). GU runs the same spear motion in uShellSt003 (shell 0x194) and
 * spawns 4 of them for stage 26 at 0x502648 (count r11 = 4, positions = st003 FUP vec 3..6, ours = 4U's in vec 3/4).
 * The GU Dragonator controller is the stage-gimmick manager [0x18977a0] (state +0x36c, timer +0x370, flags +0x1a2):
 * 0x503c7c per frame; for stage 26 state 2 waits for the SIEGE PHASE 3 (0x3a5ec4(quest) = byte quest+0x1776, called
 * at 0x503d54) before the start timer (questPlus mGekiryuStartTime * 60) runs -> never in a quest without siege.
 * Ready = 0x503b88 (flags & 2 && state 5), fire = 0x503bb0 (flags |= 4, spear +0x15e5 = 1 on the non-null slots
 * +0x35c..+0x368, so fewer spears are fine: stage 25 has 2, 27 has 1).
 * Hooks (alias only):
 *   stage_spear_count @0x502694 (`add r4, r4, #1; cmp r11, r4` of the spear loop): after spear index 1 the loop ends
 *       (r4 = 3 -> 4 == r11) -> 2 spears, as 4U.
 *   stage_siege_phase @0x3a5ec4 (quest siege-phase getter): answers 3 for the call from the Dragonator state 2
 *       (lr 0x503d58) -> the stage-26 path continues with the questPlus timers (build_gog_quest.py --bq ships a
 *       questPlus with mIsGekiryu 1, start 0, reuse 600 = 4U's 10 min).
 *   stage_dragonator_fire @0x503bb0 (log only).
 *   stage_dragonator_camera (called by stage_cannon.c's 0x503a5c hook when the press was not a floor cannon): the
 *       Dragonator firing camera with 4U's m19 area-3 record instead of GU's Fortress one (see below).
 *
 * Dragonator camera (C, traced 2026-10-19). GU: the switch action (0x2d9504 / 0x120f7f8) calls the fire 0x503bb0, then
 * for the local hunter (0x27bcd0 == 1) tail-calls 0x503a5c(mgr): flags +0x1a2 bit 0x40 (camera on) -> release
 * 0x1b794(cam, 0, 1.0); stage 10 / 25 / 26 / 27 -> record 0 / 1 / 2 / 3 of the 64-B table 0x1897640 (.bss, filled from
 * code literals by the static initializer 0x505538; record 4 = 0x50491c's siege camera) -> 0x1b08c(cam, record, 1,
 * 1.0) with cam = [0x184d750]; result 1 -> bit 0x40 and countdown +0x374 = 240.0 (0x50396c subtracts the frame step
 * [[0x2126764]+0x68], releases at <= 0). 0x1b08c -> 0x162a8 pushes the record on the camera override stack: +0x00 fov,
 * +0x10 eye, +0x20 target, +0x30 up; 0x15460 blends them into uCamera +0x3c fov, +0x40 mCameraPos (property
 * registration 0x898790), +0x60 mTargetPos (0x898804), +0x50 up = WORLD coordinates. Stage 26 = Fortress record 2:
 * fov 50, eye (-1300, 2000, -2000), target (1000, 100, -5500) (Fortress spears at z -5500) = in the alias it looks
 * from mid-arena into Battlequarters' south ledge: terrain only.
 * 4U: the fire 0x6bc9dc, for the local hunter (0xd04fbc), picks the gimmick camera by stage + area (6/1 -> 0, 6/2 -> 1,
 * 10/1 -> 2, 12/1 -> 3, 14|21/1 -> 4, 19/3 -> 5) and calls 0xc01d64(cam, k): table 0xf2d440, 32-B records {eye,
 * target, fov, duration} (vectors written by the static initializer 0xd48f90, fov / duration in .data), duration =
 * 0xc06f00's limit (timer += step until > duration). m19 area 3 = record 5: eye (-2300, 2030, 1730), target (470, 890,
 * 2990) (in front of the +x spear's thrust, tip at z 4105 - 1600), fov 50, duration 300. GU record 1 = 4U record 2
 * value for value (Capcom's port), so the field order (eye, target, fov) is the same in both games.
 * The alias runs 0x503a5c's body here with 4U record 5 (up = GU's own up vector of record 2) and 4U's duration 300;
 * GU's table is not touched (Fortress quests keep record 2). */
#include <stdint.h>
#include "util.h"
#include "game.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

int stage_alias_active(void);   /* stage.c */

#define STAGE_GIMMICK_MGR  0x18977a0u   /* data word -> stage gimmick manager (0x2ed438, 0x503c7c's this) */
#define DRAGONATOR_STATE   0x36cu
#define DRAGONATOR_TIMER   0x370u
#define GIMMICK_FLAGS      0x1a2u
#define SPEAR_SLOTS        0x35cu       /* 4 x uShellSt003* */
#define SPEARS_4U          2u
#define LR_DRAGONATOR_PHASE 0x503d58u  /* return address of `bl 0x3a5ec4` in 0x503c7c (state 2) */

/* 0x502694 inside the spawner 0x50249c: r4 = index of the spear just spawned, r11 = count (4 for stage 26) */
int stage_spear_count_c(uint32_t *regs)
{
    static uint32_t s_n;
    if (!stage_alias_active() || regs[R4] != SPEARS_4U - 1) return 0;
    regs[R4] = 3;                          /* the displaced add makes it 4 = r11: loop done after 2 spears */
    if (++s_n <= 4) logf("gogport: stage dragonator: 2 spears spawned (4U count), Fortress spears 3/4 skipped");
    return 0;
}

/* 0x3a5ec4(quest) -> u8 siege phase: 3 for the Dragonator controller's stage-26 check while the alias runs */
int stage_siege_phase_c(uint32_t *regs)
{
    static uint32_t s_n;
    if (regs[LR] - MAIN_BASE != LR_DRAGONATOR_PHASE || !stage_alias_active()) return 0;
    if (++s_n <= 2) logf("gogport: stage dragonator: siege phase check answered 3 (alias, no siege)");
    regs[R0] = 3;
    return 1;
}

int stage_cannon_fire(uint32_t *regs);   /* stage_cannon.c (arena-4): 1 = the switch press was a floor cannon */

/* 0x503bb0(mgr): Dragonator fired by the switch (log: state, spear slots) */
int stage_dragonator_fire_c(uint32_t *regs)
{
    static uint32_t s_n;
    uint8_t *m = (uint8_t *)(uintptr_t)regs[R0];
    if (stage_cannon_fire(regs)) return 1;  /* 4U floor cannon fired instead (kind-11 records at the cannons) */
    if (!stage_alias_active() || ++s_n > 20) return 0;
    logf("gogport: stage dragonator: fire (state %u, flags %x, spears %x %x %x %x)", FIELD(uint32_t, m, DRAGONATOR_STATE),
         FIELD(uint16_t, m, GIMMICK_FLAGS), FIELD(uint32_t, m, SPEAR_SLOTS), FIELD(uint32_t, m, SPEAR_SLOTS + 4),
         FIELD(uint32_t, m, SPEAR_SLOTS + 8), FIELD(uint32_t, m, SPEAR_SLOTS + 12));
    return 0;
}

#define CAMERA_MGR         0x184d750u   /* data word -> camera manager (0x503a84 / 0x503b48) */
#define GU_CAM_RECORDS     0x1897640u   /* 64-B camera records (static initializer 0x505538) */
#define GU_CAM_FORTRESS    2u           /* stage 26 */
#define CAM_ON             0x40u        /* flags +0x1a2 */
#define CAM_TIMER          0x374u       /* f32 countdown (0x50396c) */
#define CAM4U_DURATION     300.0f       /* 4U table 0xf2d440 record 5 +0x1c (GU uses 240 for every stage) */
typedef int (*cam_push_t)(void *cam, const void *rec, uint32_t mode, float speed);
#define cam_push FN(cam_push_t, 0x1b08c)
typedef void (*cam_pop_t)(void *cam, uint32_t all, float speed);
#define cam_pop FN(cam_pop_t, 0x1b794)

/* GU record layout (0x162a8): fov, pad x3, eye xyz 0, target xyz 0, up xyz 0. Values = 4U 0xf2d440 record 5 (m19 a03) */
static float s_cam4u[16] __attribute__((aligned(16))) = {
    50.0f, 0.0f, 0.0f, 0.0f,
    -2300.0f, 2030.0f, 1730.0f, 0.0f,
    470.0f, 890.0f, 2990.0f, 0.0f,
    0.0f, 1.0f, 0.0f, 0.0f,
};

/* 0x503a5c(mgr) body for the alias: 1 = done (GU's Fortress record not used) */
int stage_dragonator_camera(uint32_t *regs)
{
    static uint32_t s_n;
    uint8_t *m = (uint8_t *)(uintptr_t)regs[R0];
    void *cam = *(void **)MAIN(CAMERA_MGR);
    if (!stage_alias_active() || !m || !cam) return 0;
    const float *gu = (const float *)MAIN(GU_CAM_RECORDS + 64u * GU_CAM_FORTRESS);
    if (gu[12] != 0.0f || gu[13] != 0.0f || gu[14] != 0.0f)
        for (int i = 12; i < 15; i++) s_cam4u[i] = gu[i];   /* GU's up vector ([0x191e890], copied by 0x505538) */
    if (FIELD(uint16_t, m, GIMMICK_FLAGS) & CAM_ON) {      /* 0x503a6c: previous Dragonator camera still on */
        cam_pop(cam, 0, 1.0f);
        FIELD(uint16_t, m, GIMMICK_FLAGS) &= (uint16_t)~CAM_ON;
        FIELD(float, m, CAM_TIMER) = 0.0f;
    }
    int r = cam_push(cam, s_cam4u, 1, 1.0f);
    if (r == 1) {
        FIELD(uint16_t, m, GIMMICK_FLAGS) |= CAM_ON;
        FIELD(float, m, CAM_TIMER) = CAM4U_DURATION;
    }
    if (++s_n <= 10)
        logf("gogport: stage dragonator: camera 4U m19a03 eye (%d, %d, %d) target (%d, %d, %d) fov %d up (%d, %d, %d)/1000"
             " for %d frames -> push %d (GU Fortress record: eye (%d, %d, %d) target (%d, %d, %d))",
             (int32_t)s_cam4u[4], (int32_t)s_cam4u[5], (int32_t)s_cam4u[6], (int32_t)s_cam4u[8], (int32_t)s_cam4u[9],
             (int32_t)s_cam4u[10], (int32_t)s_cam4u[0], (int32_t)(s_cam4u[12] * 1000.0f), (int32_t)(s_cam4u[13] * 1000.0f),
             (int32_t)(s_cam4u[14] * 1000.0f), (int32_t)CAM4U_DURATION, r, (int32_t)gu[4], (int32_t)gu[5], (int32_t)gu[6],
             (int32_t)gu[8], (int32_t)gu[9], (int32_t)gu[10]);
    return 1;
}
