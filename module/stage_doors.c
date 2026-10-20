/* Battlequarters alias: 4U side doors a02 / a03 + sinking wall a04 (arena-4 agent, notes/stage.md section 14).
 *
 * 4U: the m19 per-frame stage logic 0x6b70cc plays action 0 of the KowareObj (area 3, mId 3 = scheduler m19a03d-a01)
 * via 0x6c3400 -> command 0 (0x1d23a0), once, when the kobj is idle and not done, the first large monster's HP
 * (0x6ae768 = HP * 100 / max) is <= 40.0 and the ELAPSED quest time (limit min * fps * 60 - remaining countdown) is
 * more than fps * 600 (10 min); then HUD message 0x5aa0f0(21) = "All clear to use the Demolisher!" once (stage+0x1c bit 2).
 * (Quests 1002 / 62211 use 50 % / 90 % + 1 min; ours is neither.) The action plays scheduler frames 0..200: doors swing
 * to +-pi/2, the wall sinks 360, SE 309..312 (SoundControl), CreateKowareEft 16 (m19a03_008) at frame 2, and at the
 * action start the KowareObj code swaps the collision parts 5 (wall slab, off) / 6 (on) (0x1cd494).
 *
 * GU (Capcom's port of the same KowareObj): tools/stage4u2gu.py ships the converted a01 as m26a02d-k03 (created by
 * 0x4fe9c0, registered in mgr [0x18977a0]+0x21c), so GU plays the action, the SE and the collision swap (0x513e2c,
 * 0x4ffdc4) itself. This file adds what 4U's stage class did:
 *   stage_frame @0x503c7c (gimmick manager per frame, r0 = mgr): the 4U trigger -> command 0 via 0x514f9c, HUD
 *       message, the frame-2 effect (em089_efx_stage_kowareeft: the Effect controller class is absent in GU);
 *   stage_kobj_bcast @0x500d18 (inside 0x500cb4, r0 = kobj): GU sends command 0 to EVERY kobj at quest start
 *       (non-siege quests: Fortress barricades open); for every area-2 kobj of the alias (doors mId 3 and the
 *       converted 4U breakables k01 / k02, mId 1 / 2) it becomes command 1 (a no-op case of 0x514f9c). 4U's m19
 *       stage start (0x6c222c) plays nothing on them (0x1d0c64 pre-breaks k01..k03 only for quest 1002), so without
 *       this the doors would open at once and the breakables would show their action-0 frames from the start.
 * Deviations: HUD text = GU QuestDialog 93 "The Demolisher is ready for use." (GU has no "All clear..." line; the
 * kind-1 ids match 4U up to 12 only); boss = first large monster of sEnemy with HP > 0 (4U also checks a record
 * flag W+0x1b4 bit 0 whose GU field was not traced); single player (4U's net message for the kobj not sent: GU's
 * 0x515328 sends its own when online).
 * Define STAGE_DOORS_OFF: no trigger, no broadcast block (GU then opens the doors at quest start). */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "em089_efx.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

int stage_alias_active(void);        /* stage.c */
uint32_t stage_setup_serial(void);   /* stage.c */
void stage_cannon_tick(void *mgr);   /* stage_cannon.c */

#define STAGE_GIMMICK_MGR 0x18977a0u
#define MGR_KOBJ          0x21cu      /* uKowareObj *[24] (0x500d40 registers) */
#define MGR_KOBJ_N        24u
#define KOBJ_AREA         0x182u      /* u8 mAreaNo */
#define KOBJ_STATUS       0x184u      /* u8: 6 = action playing (0x513e24) */
#define KOBJ_ACT          0x185u      /* u8 current action id, 255 = none (0x513378) */
#define KOBJ_ID           0x188u      /* u8 mId */
#define KOBJ_SCHED        0x158u      /* its scheduler; +0x34 f32 frame */
#define SCHED_FRAME       0x34u
#define DOORS_AREA        2u          /* 4U arena area 3 */
#define DOORS_ID          3u
typedef void (*kobj_cmd_t)(void *kobj, uint32_t cmd, uint32_t a, uint32_t b);
#define kobj_cmd FN(kobj_cmd_t, 0x514f9c)
typedef int (*hud_msg_t)(uint32_t kind, uint32_t id, uint32_t arg);
#define hud_msg FN(hud_msg_t, 0x65dd68)   /* GU Dragonator: 0x65dd68(1, 12, 0) */
#define HUD_DEMOLISHER    93u         /* GU QuestDialog 93 (4U QDialog 21, see header) */

#define GAME_PTR          0x2126764u  /* +56 f32 fps (0x61d000), +0x60 running (0x503c90) */
#define SQUEST_PTR        0x188ad90u  /* +0x1c remaining frames (countdown), +0xcc time limit (min) (0x61cff4) */
#define SENEMY_PTR        0x1851fe0u
typedef void *(*enemy_get_t)(void *sEnemy, uint32_t i);
#define enemy_get FN(enemy_get_t, 0x5ceb4)   /* slots 0..9 */
#define EN_REC            0x1428u
#define EN_SMALL          0xb5f7u
#define REC_HP_           0x370u

static const float k_eft_pos[3] = {0.0f, 0.0f, 0.0f};   /* a01 Effect controller: KowareEftPos (world) */

static struct {
    uint32_t serial;
    uint8_t fired, msg, eft;
    uint32_t logs;
} s_d;

static void *doors_kobj(void *mgr)
{
    for (uint32_t i = 0; i < MGR_KOBJ_N; i++) {
        uint8_t *k = FIELD(uint8_t *, mgr, MGR_KOBJ + 4 * i);
        if (k && k[KOBJ_AREA] == DOORS_AREA && k[KOBJ_ID] == DOORS_ID) return k;
    }
    return 0;
}

/* 4U 0x6ae768: HP * 100 / max of the first large monster, 100 if none */
static float boss_hp_percent(void)
{
    void *se = *(void **)MAIN(SENEMY_PTR);
    if (!se) return 100.0f;
    for (uint32_t i = 0; i < 10; i++) {
        uint8_t *e = enemy_get(se, i);
        if (!e || e[EN_SMALL]) continue;
        uint8_t *rec = FIELD(uint8_t *, e, EN_REC);
        if (!rec) continue;
        int32_t hp = FIELD(int32_t, rec, REC_HP_), mx = FIELD(int32_t, rec, REC_HP_ + 4);
        if (mx <= 0 || hp <= 0) continue;
        return (float)hp * 100.0f / (float)mx;
    }
    return 100.0f;
}

static int game_fps(void)
{
    uint8_t *g = *(uint8_t **)MAIN(GAME_PTR);
    return g ? (int)FIELD(float, g, 56) : 0;
}

/* ELAPSED quest frames = limit * fps * 60 - [sQuest+0x1c], the formula of GU 0x61cff4 / 4U 0x6b7474: +0x1c (4U
 * +0x803c) is the REMAINING-time countdown (GU 0x3a0160 decrements it once per frame while >= 1; 4U's gimmick re-arm
 * 0x6b0f18 only works with a countdown), so the 4U door test is "more than 10 minutes elapsed" (arena-3's note said
 * "remaining", corrected) */
#ifndef TEST_DOORS_SEC
#define TEST_DOORS_SEC 600       /* 4U: 10 minutes elapsed; test builds may lower it (-DTEST_DOORS_SEC=60) */
#endif

static int32_t quest_elapsed(int fps)
{
    uint8_t *q = *(uint8_t **)MAIN(SQUEST_PTR);
    if (!q) return 0;
    return (int32_t)(FIELD(uint32_t, q, 0xcc) * (uint32_t)fps * 60u) - (int32_t)FIELD(uint32_t, q, 0x1c);
}

static void doors_tick(void *mgr)
{
    if (s_d.serial != stage_setup_serial()) {
        s_d.serial = stage_setup_serial(); s_d.fired = s_d.msg = s_d.eft = 0;
    }
    uint8_t *k = doors_kobj(mgr);
    if (!k) {
        if (++s_d.logs == 1) logf("gogport: stage doors: no KowareObj (area 2, mId 3) in the manager");
        return;
    }
    if (!s_d.fired) {
        if (k[KOBJ_ACT] == 0) { s_d.fired = s_d.msg = s_d.eft = 1; return; }   /* already played (restored state) */
        int fps = game_fps();
        float hp = boss_hp_percent();
        int32_t el = quest_elapsed(fps);
        if (!(hp <= 40.0f) || el <= fps * TEST_DOORS_SEC || k[KOBJ_STATUS] == 6) return;
        kobj_cmd(k, 0, 0, 0);
        s_d.fired = 1;
        logf("gogport: stage doors: boss HP %u %% <= 40, %u s elapsed > %u -> KowareObj %x action 0 (status %u act %u)",
             (uint32_t)hp, fps ? (uint32_t)(el / fps) : 0u, (uint32_t)TEST_DOORS_SEC, (uint32_t)k, k[KOBJ_STATUS],
             k[KOBJ_ACT]);
    }
    if (!s_d.msg) {
        s_d.msg = 1;
        int r = hud_msg(1, HUD_DEMOLISHER, 0);
        logf("gogport: stage doors: HUD message %u (4U 21) -> %d", HUD_DEMOLISHER, r);
    }
    if (!s_d.eft) {
        uint8_t *sch = FIELD(uint8_t *, k, KOBJ_SCHED);
        if (sch && k[KOBJ_ACT] == 0 && FIELD(float, sch, SCHED_FRAME) >= 2.0f) {
            s_d.eft = 1;
            void *h = em089_efx_stage_kowareeft(16, 0, k_eft_pos, DOORS_AREA);
            logf("gogport: stage doors: frame 2 effect m19a03_008 (KowareEft 16) %s", h ? "posted" : "not posted");
        }
    }
}

/* 0x503c7c(mgr): stage gimmick manager per frame (Dragonator controller) */
int stage_frame_c(uint32_t *regs)
{
    void *mgr = (void *)(uintptr_t)regs[R0];
    uint8_t *g = *(uint8_t **)MAIN(GAME_PTR);
    /* GU 0x503c7c skips only when +0x60 == 0 AND +0x64 (paused) is set; 0 at +0x60 is the normal state */
    if (!mgr || !stage_alias_active() || !g || (!FIELD(uint32_t, g, 0x60) && FIELD(uint8_t, g, 0x64))) return 0;
#ifndef STAGE_DOORS_OFF
    doors_tick(mgr);
#endif
    stage_cannon_tick(mgr);
    return 0;
}

/* inside 0x500cb4 at 0x500d18 (r0 = kobj, about to get command 0 at quest start) */
int stage_kobj_bcast_c(uint32_t *regs)
{
#ifdef STAGE_DOORS_OFF
    (void)regs;
    return 0;
#else
    static uint32_t s_n;
    uint8_t *k = (uint8_t *)(uintptr_t)regs[R0];
    if (!k || !stage_alias_active() || k[KOBJ_AREA] != DOORS_AREA) return 0;
    regs[R1] = 1;                     /* command 1: no case in 0x514f9c (returns) */
    if (++s_n <= 8) logf("gogport: stage doors: quest-start command 0 blocked for area-2 KowareObj %x (mId %u)",
                         (uint32_t)k, k[KOBJ_ID]);
    return 0;
#endif
}
