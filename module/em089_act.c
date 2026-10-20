/* uEm089_00 action framework: slot 125 runs the current action (category this+0x73e0, number +0x73e1).
 *
 * GU conventions (notes/port.md, notes/api-map.md):
 *  - an action is a step machine on rec+0x1a1 (cleared by setAction, = 4U W+0x144; +0x1a2/+0x1a3 = W+0x145/146).
 *  - an action ends with virtual slot 247 (4U vt+0x164): setAction(0, 0|1|2, mode 2) + "think requested"; slot 249
 *    = 4U 0x9559a8. The AI (0x82ddc) then picks the next action from the command table (manifest field 37).
 *  - death (12/255) is run by the framework (0xa5c40 -> 0xa6bb8) and never reaches slot 125.
 *  - category 17 goes to the base 0xaf598 (as in Rathian).
 * Each handler is a step-by-step translation of the MH4U em089 handler named in its comment (4U address, r1 variant
 * from the dispatchers: cat 0 0x8b6f2c, 1 0x8bac40, 2 0x8bd4b0, 4 0x8c2640, 7 0x8c0f94, 3/11/13 inline in slot 44
 * 0x8c3ac0). Frame / timer values are 4U's, used with the engine's speed-scaled helpers (motionCheck, timerDown,
 * the time scale this+28). Skipped everywhere: the frame-event helper 0x8b8e28 (sounds / effects / footsteps).
 *
 * Targets: the engine helpers (move sequences, setStopDist / inRange steering, turnToTarget) aim at the target
 * slot rec+464. In our tests that slot was not the hunter, so sync_target() copies the targeted hunter's position
 * into it before each such call (em089_target_hunter: the hunter of slot 0, the same one on every machine).
 *
 * Attack collisions (attackEx) use em089's own attackdata indexes (converted data). They are on by default since
 * 2026-10-17; -DEM089_NO_ATTACK_HIT turns them back into log lines. attackEx is crash-safe on a bad index (0x70ffc
 * checks the attackdata count and attackEx returns). */
#ifndef EM089_NO_ATTACK_HIT
#define EM089_ATTACK_HIT
#endif
#include "game.h"
#include "util.h"
#include "em089.h"
#include "em089_tar.h"
#include "em089_shell.h"
#include "em089_aim.h"
#include "em089_snd.h"   /* code-played sounds (sound agent) */
#include "em089_shell016.h"   /* breath / beam / explosion attack shells (4U uShell016, shell agent) */
#include "em089_efx.h"        /* effect posts (effects agent) */
#include "em089_shell005.h"   /* 2/35 tremor shell (shell agent) */
#include "em089_react.h"      /* category 10 reactions: 4U 0x8c2784 -> GU sequence player 0xa134c (react agent) */

/* our fields after the base object (EM089_SIZE in em089.c reserves 0x50 bytes) */
#define F_LAST_ACTION (SIZE_uFestaEnemy + 4)     /* u16: last logged action | 0x8000 */
#define F_BUSY        (SIZE_uFestaEnemy + 6)     /* u16: action serial + 1 of the running handler (think blocked) */
#define F_TIMER       (SIZE_uFestaEnemy + 8)     /* float: per-action timer [4U W+468] */
#define F_MISC        (SIZE_uFestaEnemy + 0xc)   /* u32: per-action scratch */
#define F_AIM         (SIZE_uFestaEnemy + 0x10)  /* float[4]: em089 aim point [4U W+392] */
#define F_TURN        (SIZE_uFestaEnemy + 0x20)  /* u32: em089 aim turn rate [4U work+0xdc] */
#define F_RANGE       (SIZE_uFestaEnemy + 0x24)  /* u8: "target reached" latch [4U work+0xc9] */
#define F_SHAKE       (SIZE_uFestaEnemy + 0x25)  /* u8: roar camera shake done [4U work+0xca] */
#define F_HEADING     (SIZE_uFestaEnemy + 0x26)  /* u8: arena wall type for the 1/22 turns [4U work+0xda] */
#define F_NOSYNC      (SIZE_uFestaEnemy + 0x27)  /* u8: keep the engine target slot: 1 one turn, 2 EMC arena point */
#define F_TAR         (SIZE_uFestaEnemy + 0x28)  /* float[8]: em089 tar amounts per part [4U work+0..0x1c] */
#define F_SAFETY      (SIZE_uFestaEnemy + 0x48)  /* float: port-only safety timer for open-ended loops */
#define F_HITS        (SIZE_uFestaEnemy + 0x4c)  /* u8: hit counter of slot 47 [4U work+0xcb] */
#define F_RAGE        (SIZE_uFestaEnemy + 0x4d)  /* u8: rage roll of slot 40 [4U work+0xcc] */
#define F_LATCH_D8    (SIZE_uFestaEnemy + 0x4e)  /* u8: one-shot latch of condition 22 [4U work+0xd8] */
#define F_LATCH_D9    (SIZE_uFestaEnemy + 0x4f)  /* u8: one-shot latch of condition 27 / 7/146 [4U work+0xd9] */
#define F_COOL        (SIZE_uFestaEnemy + 0x50)  /* float: cooldown read by condition 10 [4U work+0xd0] */
#define F_DATASET     (SIZE_uFestaEnemy + 0x54)  /* u8: data set last selected by slot 40 (0xff = none) */
#define F_TAR_TIMER   (SIZE_uFestaEnemy + 0x58)  /* float[8]: tar decay timers per part [4U work+0x20..0x3c] */
#define F_TAR_MODE    (SIZE_uFestaEnemy + 0x78)  /* u8[5]: tar mode of part k, 0 Solid 1 Liquid 2 Gas [work+0x54+2k] */
#define F_TAR_WORD    (SIZE_uFestaEnemy + 0x80)  /* u32: tar state word [4U W+0x7814] */
#define F_TAR_VIS     (SIZE_uFestaEnemy + 0x84)  /* u32: word last applied to the group bits */
#define F_TAR_VISOK   (SIZE_uFestaEnemy + 0x88)  /* u8: F_TAR_VIS valid */
#define F_TAR_D4      (SIZE_uFestaEnemy + 0x8c)  /* float: chest-Liquid event timer [4U work+0xd4] */
#define F_FLAG_E4     (SIZE_uFestaEnemy + 0x90)  /* u8: em089 flag set by the per-motion table 0x8c5768 [work+0xe4] */
#define F_TGT         (SIZE_uFestaEnemy + 0x91)  /* u8: 1 + index of the targeted hunter, 0 = none yet (net-synced) */
#define F_SHELL_N     (SIZE_uFestaEnemy + 0x94)  /* u8: tar blobs posted in this action (rand index) [work+0xcd] */
#define F_SHELL_RARE  (SIZE_uFestaEnemy + 0x95)  /* u8: rare drips (kind 6 / 7) posted [work+0xec] */
#define F_SHELL_ED    (SIZE_uFestaEnemy + 0x96)  /* u8: shiny-drop table set, 1 after a rare drip [work+0xed] */
#define F_LIGHT       (SIZE_uFestaEnemy + 0x97)  /* u8: light state 0..3 of 0x8c6300 [work+0xc8] */
#define F_END         (SIZE_uFestaEnemy + 0x98)  /* = EM089_SIZE (em089.c) */

/* record fields mapped for the behaviour port (C = same code shape in both games):
 * REC_SPAWN_B3: spawn-record byte 3 (4U W+0x797e, copied by 4U 0x91e360 [0x91e3ec]; GU 0x6fb14 copies the same
 *   byte to rec+0x5cb6 [0x6fc28], next to bytes 0/2/4/5 -> 4U W+0x79ba/0x797f/0x7982/0x7988 = GU rec+0x5ce4/0x5cb7/
 *   0x5cba/0x5cbf; GU's EMC evaluator kind 4 tests rec+0x5cb6 == 100 like 4U's readers of W+0x797e). 4U quests:
 *   m11014 0, m11035 1 (quest00/01.arc boss records +8: ff 03 00 00 / ff 03 00 01). In GU that byte is the Hyper
 *   flag (questData boss +3 = 1 on GU's Hyper quests, e.g. "Commission: Hyper Kecha Wacha"), so our quests keep it 0
 *   and spawn_b3() gives 4U's value from the quest instead.
 * REC_SPEED2: second motion-speed factor (4U W+0x40c = W+1036; 4U 0x941dd4 = W+1028 * W+1036 * status, GU 0xb000c
 *   reads rec+908 * rec+916 with the same status / category 10-11-13 test: C); GU spawn setup 0xb8f20 resets it. */
#define REC_SPAWN_B3 0x5cb6
#define REC_SPEED2   0x394
/* GU rage: addAnger 0xbcc04(this, dmg) adds to the anger counter rec+0x510 (s16; threshold from data block +0x28
 * by HP decile, default 600); at the threshold, when not enraged (rage timer rec+0x514 <= 0) it posts think event
 * rec+0x362 |= 4 (0x7fc40), which the think-event dispatcher 0x7f0cc turns into list 6 = EMC group 6
 * ([this+0x72f4]+0x18, 0x7f960). */
#define REC_ANGER      0x510
#define REC_RAGE_TIMER 0x514

#define REC(self)   FIELD(uint8_t *, self, EN_RECORD)
#define STEP(self)  FIELD(uint8_t, REC(self), REC_STEP0)
#define STEP1(self) FIELD(uint8_t, REC(self), REC_STEP1)
#define STEP2(self) FIELD(uint8_t, REC(self), REC_STEP2)

int gog_quest_index(void);   /* stage.c: 1 = quest 11491 (4U m11014), 2 = quest 11492 (4U m11035), 0 = other */
/* 4U spawn byte 3 (W+0x797e, REC_SPAWN_B3): 1 in quest 11492 like 4U m11035, else GU's byte (0 in quest 11491) */
static uint32_t spawn_b3(void *self)
{
    return gog_quest_index() == 2 ? 1 : FIELD(uint8_t, REC(self), REC_SPAWN_B3);
}
#define TIMER(self) FIELD(float, self, F_TIMER)
#define DT(self)    FIELD(float, self, EN_DT)

/* MH4U em089 motions (bank << 8 | index into em089_0..3.lmt) */
enum {
    MOT_IDLE = 0x002, MOT_ROAR = 0x004 /* roar (1/0: shockwave hit + camera shake) */, MOT_RUN = 0x005,
    MOT_008 = 0x008, MOT_WALK_ATK = 0x019, MOT_01C = 0x01c, MOT_01D = 0x01d, MOT_IDLE2 = 0x03c,
    MOT_03E = 0x03e, MOT_TURN_L = 0x041, MOT_TURN_R = 0x042, MOT_STOMP = 0x049, MOT_RUN_STOP = 0x04b,
    MOT_REACT_SMALL = 0x107, MOT_108 = 0x108, MOT_REACT = 0x109, MOT_10C = 0x10c, MOT_REACT2 = 0x10f,
    MOT_ATK_524 = 0x20c, MOT_ATK_526 = 0x20e, MOT_ATK_574 = 0x23e,
};

static void act_end(void *self) { VCALL0(self, SLOT_ACTION_END); }
static void act_end6(void *self) { VCALL0(self, SLOT_ACTION_END_6); }   /* 4U 0x9559a8 */
static int mc(void *self, uint32_t kind, float a, float b) { return motionCheck(self, kind, 0, a, b); }
static int at_frame(void *self, float frame) { return motionCheck(self, 0, 0, frame, 0.0f); }
static void set_mode(void *self, uint32_t m) { FIELD(uint8_t, REC(self), REC_MODE) = (uint8_t)m; }   /* W+0x1c9 */

static void hit(void *self, uint32_t slot, uint32_t index, uint32_t param)
{
#ifdef EM089_ATTACK_HIT
    attackEx(self, slot, index, param);
    {   /* damage check: GU slot = rec + 0x998 + 184 * slot (0x7dde8), power = record +4 -> slot +0x38 (0x168c68),
         * rate rec+0x384 = nando row [+4] (0xc0528); damage before the hunter's defense = power * rate (0x169548) */
        static uint32_t s_n;
        if (slot <= 1 && ++s_n <= 120) {
            uint8_t *s = REC(self) + 0x998 + 184 * slot;
            float rate = FIELD(float, REC(self), 0x384);
            uint32_t pw = FIELD(uint16_t, s, 0x38);
            logf("gogport: em089 attack slot %u index %u active %u power %u rate %d/100 -> %d", slot, index, s[5], pw,
                 (int32_t)(rate * 100.0f), (int32_t)((float)pw * rate));
        }
    }
#else
    static uint32_t s_n;
    if (++s_n <= 40) logf("gogport: em089 attack slot %u index %u param %u (not enabled)", slot, index, param);
    (void)self;
#endif
}

/* 4U attackReset + attackEx (0x90f934 then 0x933144): re-arm a slot inside a running action */
static void rehit(void *self, uint32_t slot, uint32_t index, uint32_t param)
{
#ifdef EM089_ATTACK_HIT
    attackFlag(self, slot);
#endif
    hit(self, slot, index, param);
}

/* logged stub for a 4U callee without a confident GU mapping */
static void stub(const char *what, uint32_t a, uint32_t b)
{
    static uint32_t s_n;
    if (++s_n <= 60) logf("gogport: em089 stub %s (%u, %u)", what, a, b);
}

/* steering toward the hunter. rec+464 is only the engine's target slot (it jumped thousands of units between
 * actions in the second test), so the port follows the targeted hunter's root joint. Which hunter: target slot 0
 * kind 1 (engine resolver 0xc4ba8 case 1 [0xc4c70 / 0xc53e4]: param = index 0..3, with sub 10 a bit mask whose
 * lowest bit wins, 255 = none) in the hunter list *(main+0x1885b58) + 0x1c + 4 * i (0x274ce4, GOT 0x1838d80;
 * entries checked with the resolver's kind test against DTI 0x1898670 [0xc540c..0xc544c]). The host's action
 * message carries slot 0 (pack slot 267 0xcb330 reads rec+0x230..0x238), so every machine picks the same hunter.
 * F_TGT keeps it through actions that target something else (and travels in em089_net_get); before the first
 * kind-1 target the host takes its own hunter. Falls back to the local hunter, then to the slot. */
#define HUNTER_LIST MAIN(0x1885b58)
#define DTI_HUNTER  MAIN(0x1898670)
static void *hunter_ok(void *pl)
{
    return (pl && *(void **)((uint8_t *)pl + 0x498) && *(void **)((uint8_t *)pl + 0x494)) ? pl : 0;
}

static void *local_hunter(void)
{
    void *root = *(void **)PLAYER_ROOT;
    return hunter_ok(root ? *(void **)((uint8_t *)root + 0x58) : 0);
}

/* hunter i of the list when it is of the resolver's class (getDTI vt+0x14, parents at +0x10, id word +4) */
static void *hunter_at(uint32_t i)
{
    uint8_t *list = *(uint8_t **)HUNTER_LIST;
    void *pl = (list && i < 4) ? *(void **)(list + 0x1c + 4 * i) : 0;
    if (!pl) return 0;
    const uint8_t *d = ((const uint8_t *(*)(void *))(*(uint32_t **)pl)[5])(pl);
    for (; d; d = *(const uint8_t **)(d + 0x10))
        if (*(const uint32_t *)(d + 4) == *(const uint32_t *)(DTI_HUNTER + 4)) return hunter_ok(pl);
    return 0;
}

static int32_t local_index(void)
{
    void *me = local_hunter();
    for (uint32_t i = 0; i < 4 && me; i++) if (hunter_at(i) == me) return (int32_t)i;
    return -1;
}

/* slot 0's hunter index, -1 when slot 0 is not a hunter */
static int32_t slot_hunter(void *self)
{
    const uint8_t *k = REC(self) + REC_TGT_KIND;
    uint32_t sub = k[2], p = k[4];
    if (k[0] != 1 || p == 255) return -1;
    if (sub != 10) return p <= 3 ? (int32_t)p : -1;
    for (int32_t i = 0; i < 4; i++) if (p & (1u << i)) return i;
    return -1;
}

void *em089_target_hunter(void *self)
{
    uint8_t *tgt = &FIELD(uint8_t, self, F_TGT);
    int32_t i = slot_hunter(self);
    if (i >= 0 && hunter_at((uint32_t)i)) *tgt = (uint8_t)(i + 1);
    if (!*tgt && FIELD(uint8_t, self, EN_CONTROLLED)) *tgt = (uint8_t)(local_index() + 1);
    void *pl = *tgt ? hunter_at(*tgt - 1u) : 0;
    return pl ? pl : local_hunter();
}

static int target_pos(void *self, float *out)
{
    void *pl = em089_target_hunter(self);
    if (pl) { jointPos(pl, 0, out); return 1; }
    const float *t = (const float *)(REC(self) + REC_TARGET);
    for (int i = 0; i < 4; i++) out[i] = t[i];
    return 0;
}

/* copy the hunter into target slot 0 before an engine helper reads it (see the header) */
static void sync_target(void *self)
{
    float t[4];
    if (FIELD(uint8_t, self, F_NOSYNC) || !target_pos(self, t)) return;
    float *slot = (float *)(REC(self) + REC_TARGET);
    slot[0] = t[0]; slot[1] = t[1]; slot[2] = t[2]; slot[3] = 0.0f;
}

/* ---- tar blobs (em089_shell.c, 4U uShell050) ----
 * 4U rand 0x2b02c0(mgr, s): x = s * 176 (s = 0 -> 1), x mod 65363 (as u16). The shell helpers seed it with the action
 * serial (W+0x1d2 = this+0x73e8) and iterate it work+0xcd + 1 times, so every blob of an action gets its own value. */
static uint32_t shell_rand(void *self)
{
    uint32_t r = FIELD(uint16_t, self, EN_ACT_SERIAL);
    for (uint32_t i = 0; i <= FIELD(uint8_t, self, F_SHELL_N); i++) {
        uint32_t x = (r ? r : 1) * 176u;
        uint64_t p = (uint64_t)x * 0x2015aea7u + 0x2015aea7u;
        r = (x + ((uint32_t)(p >> 32) >> 13) * 173u) & 0xffff;
    }
    return r;
}

/* 4U 0x8c9dd4(this, joint, frame, spread): at motion frame 2 * frame, a tar shot (kind 4, 5 after the first roar)
 * lobbed from the joint to a random point of the disk of radius spread * (r & 0xff) / 255, angle r & 0xff00, around
 * target slot 0 (0x934f7c / 0xaad008; here the hunter, as the port's steering) */
static void tar_shot(void *self, uint32_t joint, float frame, float spread)
{
    if (!at_frame(self, frame * 2.0f)) return;
    uint32_t r = shell_rand(self);
    float c[4], t[3];
    target_pos(self, c);
    float d = spread * (float)(r & 0xff) * 0.003921569f, a = (float)(r & 0xff00) * (6.28318531f / 65536.0f);
    t[0] = c[0] + sinf_gu(a) * d; t[1] = c[1]; t[2] = c[2] + cosf_gu(a) * d;
    em089_shell_post(self, FIELD(uint8_t, self, F_SHAKE) ? 5 : 4, joint, t);
    FIELD(uint8_t, self, F_SHELL_N)++;
}

/* 4U work+0xed: the item drop 0x911f58 takes its table from set 0x930bdc(this), which for em 89 is 1 when work+0xed
 * == 1, else 0 (tools/hagi_em089.py): set 0 = One-shot Binder 100 %, set 1 = the shiny table. GU asks enemy vtable
 * slot 149 (0xac0ec -> [vt+0x254]; uFestaEnemy's answers 0) and reads hagi header byte 14 + set. */
uint32_t em089_drop_set(void *self)
{
    return FIELD(uint8_t, self, F_SHELL_ED) == 1;
}

void em089_set_drop_flag(void *self, uint32_t v)
{
    FIELD(uint8_t, self, F_SHELL_ED) = (uint8_t)v;
}

/* 4U 0x8b8e28(this, joint, k, mask, frame): tar drip from the joint at motion frame 2 * frame when tar part k
 * (0 head, 1 chest, 2 / 3 arms, 4 tail) is in a mode of mask (bit 0 Solid, 1 Liquid, 2 Gas). Kind 0 (1 after the
 * first roar); while fewer than 4 rare drips: r % 500 == 0 -> kind 6 (7). Kind 8 [0x8b8f7c..0x8b8fd4]: spawn byte 3
 * (W+0x797e = rec+0x5cb6) 1 or 2, after the phase-2 roar (work+0xca), unless kind 7 (4U also re-runs the rand loop
 * there; its value is unused). */
static void tar_drip(void *self, uint32_t joint, uint32_t k, uint32_t mask, float frame)
{
    if (k >= 5 || !(mask & (1u << FIELD(uint8_t, self, F_TAR_MODE + k)))) return;
    if (!at_frame(self, frame * 2.0f)) return;
    uint32_t odd = FIELD(uint8_t, self, F_SHAKE) != 0, kind = odd;
    if (FIELD(uint8_t, self, F_SHELL_RARE) <= 3 && shell_rand(self) % 500 == 0) {
        FIELD(uint8_t, self, F_SHELL_RARE)++;
        FIELD(uint8_t, self, F_SHELL_ED) = 1;
        kind = 6 + odd;
    }
    {
        uint32_t b3 = spawn_b3(self);
        if ((b3 == 1 || b3 == 2) && odd && kind != 7) kind = 8;
    }
    em089_shell_post(self, kind, joint, 0);
    FIELD(uint8_t, self, F_SHELL_N)++;
}

/* a handler's drip list {joint, k, mask, frame} (4U: consecutive 0x8b8e28 calls) */
typedef struct { uint8_t joint, k, mask; float frame; } drip_t;
static void tar_drips(void *self, const drip_t *d, uint32_t n)
{
    for (uint32_t i = 0; i < n; i++) tar_drip(self, d[i].joint, d[i].k, d[i].mask, d[i].frame);
}

/* 4U turnToTarget 0x91db84(this, max_step, offset): turn the yaw toward the target slot (GU 0x76cc4); here toward
 * the hunter through its explicit-position twin 0x76c28 */
static int face(void *self, uint32_t max_step, uint32_t offset)
{
    float t[4];
    if (!target_pos(self, t) && t[0] == 0.0f && t[2] == 0.0f) return turnToTarget(self, max_step, offset);
    return turnToward(self, max_step, offset, t);
}

/* yaw += K degrees per frame inside a motionCheck window, scaled by the window fraction and the time scale
 * (4U: yaw W+0x1ac += (this+0xd58 * K * frac * 65536) / 360, uxtah) */
static void yaw_add(void *self, float deg, float frac)
{
    uint32_t *yaw = &FIELD(uint32_t, REC(self), REC_YAW);
    int32_t d = (int32_t)(DT(self) * deg * (frac * 65536.0f) * (1.0f / 360.0f));
    *yaw += (uint16_t)d;
}

/* forward / vertical velocity in the monster's frame, then rotate by its angles (4U W+352.. + 0x91150c) */
static void lunge(void *self, float speed)
{
    FIELD(float, REC(self), REC_VEL + 8) = speed;
    rotateVel(self, REC(self) + REC_ANGLES, 1);
}

static void rise(void *self, float speed)
{
    FIELD(float, REC(self), REC_VEL + 4) = speed;
    rotateVel(self, REC(self) + REC_ANGLES, 0);
}

/* 4U 0x8b69f4(this, amount, part, mode): em089 tar accumulation per part (parts 0, 2, 3, 6, 7), clamped to 255
 * (mode 1) or 159 (mode 0). Read by the tar state machine (tar_machine, 4U 0x8c352c).
 * The handlers' motion-window calls pass the frame delta, which 4U truncates to an integer (u16 of this+20: 1 per
 * frame at its fixed 30 fps). Here the float delta: the same 1 per frame at 30 fps, and the same amount per second
 * with a 60 / 120 FPS patch, where the truncated delta (0.5 / 0.25) was 0 and no tar ever built up (and machines
 * with different patches disagreed on the tar state, i.e. on hitzones, online). */
static void tar_add(void *self, float amount, uint32_t part, uint32_t mode)
{
    if (!(amount > 0.0f) || !(part == 0 || part == 7 || part == 2 || part == 3 || part == 6)) return;
    float *t = &FIELD(float, self, F_TAR) + part;
    float v = *t + amount * 2.0f, cap = mode ? 255.0f : 159.0f;
    *t = v > cap ? cap : v < 0.0f ? 0.0f : v;
}

/* 4U 0x8c34a0(this, slot < 2): attack slot W+0xc08 + slot * 152 with u16 +52 != 0xffff gets s16 +72 = 30 and
 * u32 +0x3c |= 4. GU slot = rec+0x998 + slot * 184 (attackEx 0x7dc2c -> arm 0x168be8 / 0x168e98). Field map from the
 * arm functions, which copy the same attack record in the same order (4U arm 0xb700f8): serial (0xbe9a0c / GU
 * 0x16b920) 4U +52 = GU +52, record +0xc flags 4U +0x3c = GU +0x40, record byte +0x18 4U +72 = GU +80 (C for the
 * layout; the GU slot update reading timer / flag 4 the same way is S). */
#define ATK_SLOT0   0x998
#define ATK_SLOT_SZ 184
static void atk_shorten(void *self, uint32_t slot)
{
    static uint32_t s_n;
    if (slot >= 2) return;
    uint8_t *s = REC(self) + ATK_SLOT0 + slot * ATK_SLOT_SZ;
    if (FIELD(uint16_t, s, 52) == 0xffff) return;
    FIELD(int16_t, s, 80) = 30;
    FIELD(uint32_t, s, 0x40) |= 4;
    if (++s_n <= 20) logf("gogport: em089 attack slot %u shortened (serial %x, action %u/%u)", slot,
                          FIELD(uint16_t, s, 52), FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM));
}

/* 4U slot 40 tail [0x8ba384..0x8ba3cc]: every frame, slots 0 / 1 with serial != 0xffff get timer +72 = 0 and flag 4
 * cleared, i.e. the 0x8c34a0 shortening lasts only for the frames whose handler calls it. Run at the start of our
 * slot 125 (before the handler) rather than in slot 119, so the order "reset, then the handler may shorten" holds
 * whatever the GU engine's order of slots 119 / 125 is. */
static void atk_unshorten(void *self)
{
    for (uint32_t slot = 0; slot < 2; slot++) {
        uint8_t *s = REC(self) + ATK_SLOT0 + slot * ATK_SLOT_SZ;
        if (FIELD(uint16_t, s, 52) == 0xffff) continue;
        FIELD(int16_t, s, 80) = 0;
        FIELD(uint32_t, s, 0x40) &= ~4u;
    }
}

/* block the AI while this action runs: the GU AI re-picks an action about every 5 s even mid-action. Keyed by the
 * action serial (this+0x73e8, bumped by every setAction), so our own end or an engine reaction lifts it. */
static void busy(void *self)
{
    FIELD(uint16_t, self, F_BUSY) = (uint16_t)(FIELD(uint16_t, self, EN_ACT_SERIAL) + 1);
}

/* object slot 253 (base 0x7ff90: 1 for categories 11 / 14 and death). FIX 2026-10-19 (test 2: HP never dropped,
 * anger 0, melee never hurt): slot 253 is NOT only the think gate. ~130 engine sites call it, among them the
 * per-frame damage update 0x97ddc (0x97ea4: 1 -> skip all damage: no HP loss, no flinch / break, no addAnger),
 * the death check 0x9e3dc and the attack code 0x7e104 / 0x7e13c / 0x7e194 (1 -> attack slots inactive). Our busy
 * flag made it 1 during every action. The busy block now answers only the AI think check 0x82538 (its call returns
 * to 0x82554); every other caller gets the base answer. */
int em089_think_blocked(void *self)
{
    if (__builtin_return_address(0) == (void *)MAIN(0x82554) &&
        FIELD(uint16_t, self, F_BUSY) == (uint16_t)(FIELD(uint16_t, self, EN_ACT_SERIAL) + 1)) return 1;
    return think_blocked_base(self);
}

/* chain to the next action (4U setActionNext 0x94ef9c) and block the AI at once (the same-frame think of the
 * enemy update 0xa59fc step 3 would otherwise replace it before its handler first runs) */
static void chain(void *self, uint32_t cat, uint32_t num)
{
    setActionNext(self, cat, num);
    busy(self);
}

/* 4U ending "setTargetMode(0); setActionW(1, 20); thinkRequest(0)" (2/61, 2/62): start 1/20 and let the AI pick */
static void end_1_20(void *self)
{
    setTargetMode(self, 0);
    setActionW(self, 1, 20);
    thinkRequest(self, 0);
}

/* step 0 of every 4U handler: "strb 1, [W, #0x144]" */
static void begin(void *self)
{
    busy(self);
    STEP(self) = 1;
}

/* the old entry helper (cat 0/1 ports): target mode, attack id 0, motion */
static void enter(void *self, uint32_t target_mode, uint32_t motion, float blend, float start)
{
    begin(self);
    setTargetMode(self, target_mode);
    setAttackId(self, 0);
    setMotion(self, motion, blend, start);
}

/* frame cap for the old ports that end on their motion end (some motions loop) */
#define MAX_ACTION_FRAMES 240.0f

/* ---- move-sequence tables (4U 0xe0de0c.., converted: s32 blend/start -> float, flags unchanged) ---- */
#define SEQ_E(m, b) {m, b, 0.0f, 0x8000}
static const seq_rec k_seq_de0c = {28, 68, 64, 0x1c724000, {SEQ_E(0x00d, 6), SEQ_E(0x00b, 6), SEQ_E(0x00c, 6)}};
static const seq_rec k_seq_de4c = {28, 76, 64, 0x00008000, {SEQ_E(0x00d, 6), SEQ_E(0x015, 6), SEQ_E(0x016, 6)}};
static const seq_rec k_seq_dee4 = {28, 68, 64, 0x0e394000, {SEQ_E(0x00d, 6), SEQ_E(0x00b, 6), SEQ_E(0x00c, 6)}};
static const seq_rec k_seq_df24 = {28, 76, 64, 0x00008000, {SEQ_E(0x00d, 6), SEQ_E(0x015, 6), SEQ_E(0x016, 6)}};
static const seq_rec k_seq_df64 = {78, 160, 44, 0x00005550, {SEQ_E(0x03c, 4), SEQ_E(0x03f, 4), SEQ_E(0x040, 4)}};
static const seq_rec k_seq_dfa4 = {34, 314, 0, 0x00008000, {SEQ_E(0x03c, 4), SEQ_E(0x043, 4), SEQ_E(0x044, 4)}};
static const seq_rec k_seq_dea4 = {0, 132, 44, 0x0e398000, {SEQ_E(0x107, 4), SEQ_E(0x107, 4), SEQ_E(0x107, 4)}};
static const seq_rec *const k_seq_2_1[2] = {&k_seq_de0c, &k_seq_de4c};    /* 4U 0xe0de8c */
static const seq_rec *const k_seq_2_2[2] = {&k_seq_dee4, &k_seq_df24};    /* 4U 0xe0de94 */
static const seq_rec *const k_seq_2_62[2] = {&k_seq_df64, &k_seq_dfa4};   /* 4U 0xe0de9c */

/* ---- category 0: neutral (faithful) ---- */

/* 0/0, 0/1 [4U 0x8b9aa8, 0x8b999c (identical)]: timer W+468 = 60; in mode 1 (flying, W+0x1c9 = GU rec+0x1bb)
 * setTargetMode(1) + loop motion 60 (6, 0), mode 1, attack id 1; else setTargetMode(0) + loop motion 2, mode 0,
 * id 0; ends when the timer runs out. 0/2 is not handled by 4U em089; GU's end slot 247 can request it, so it
 * shares this handler (port-only). */
static void act_idle(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        TIMER(self) = 60.0f;
        if (FIELD(uint8_t, REC(self), REC_MODE) == 1) {
            setTargetMode(self, 1);
            setMotionLoop(self, MOT_IDLE2, 6.0f, 0.0f);
            set_mode(self, 1);
            setAttackId(self, 1);
        } else {
            setTargetMode(self, 0);
            setMotionLoop(self, MOT_IDLE, 6.0f, 0.0f);
            set_mode(self, 0);
            setAttackId(self, 0);
        }
    } else if (timerDown(self, &TIMER(self), 1.0f)) {
        act_end(self);
    }
}

/* vertical speed decay toward 0 by 2.5 per tick (4U 0x915d7c pattern of 0/6, 2/67) */
static void vspeed_decay(void *self)
{
    float *vs = &FIELD(float, REC(self), REC_VSPEED);
    if (*vs < 0.0f) { vertAccel(self, 2.5f); if (!(*vs < 0.0f)) *vs = 0.0f; }
    else { vertAccel(self, -2.5f); if (*vs < 0.0f) *vs = 0.0f; }
}

/* 0/3 [inline in 0x8b6f2c]: rest pair with value 720 (0x92e9d4(720) = restApply), loop motion 263 (6, 0); slot 249
 * at the motion end. 0/6 [4U 0x8b9844]: vertical speed decay every frame, setTargetMode(3), loop motion 263 (4, 0),
 * slot 249 at the motion end. var 0 = 0/3, 1 = 0/6. */
static void act_0_3(void *self, uint32_t var)
{
    static const drip_t k_d03[] = {{60, 2, 7, 20}, {71, 3, 7, 20}, {2, 1, 7, 40}};
    static const drip_t k_d06[] = {{63, 2, 7, 7}, {73, 3, 7, 7}, {2, 1, 7, 59}};
    if (var) vspeed_decay(self);
    if (STEP(self) == 0) {
        begin(self);
        if (var) { setTargetMode(self, 3); setMotionLoop(self, MOT_REACT_SMALL, 4.0f, 0.0f); }
        else { restApply(self, 720.0f); setMotionLoop(self, MOT_REACT_SMALL, 6.0f, 0.0f); }
        return;
    }
    tar_drips(self, var ? k_d06 : k_d03, 3);
    if (isMotionEnd(self)) act_end6(self);
}

/* 0/9 [inline in 0x8b6f2c]: setTargetMode(5), 0x920058(2, flags 1, 8, 0) (= setMotionEx unless the motion layer
 * is busy; the guard 0xb059a4 is not mapped: plain setMotionEx here); at the motion end 4U 0x94e654 =
 * setTargetMode(5) + setAction(0, 9, mode 2) + think requested (composed from setActionW + thinkRequest). */
static void act_0_9(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 5);
        setMotionEx(self, MOT_IDLE, 1, 8.0f, 0.0f);
        return;
    }
    if (!isMotionEnd(self)) return;
    setTargetMode(self, 5);
    setActionW(self, 0, 9);
    thinkRequest(self, 0);
}

/* play one motion to its end, then end the action (fallback) */
static void act_play(void *self, uint32_t motion, uint32_t target_mode)
{
    if (STEP(self) == 0) { enter(self, target_mode, motion, 6.0f, 0.0f); TIMER(self) = MAX_ACTION_FRAMES; }
    else if (isMotionEnd(self) || timerDown(self, &TIMER(self), 1.0f)) act_end(self);
}


/* ---- category 1: roars, idles, turns (faithful) ---- */

/* 4U 0x93457c(this, kind, 255) [s0 = 0 at every em089 site] is NOT a net event: when the monster's target is the
 * local player (0x940bbc / GU 0xc7ecc vs the local index) it stores that index (W+0x78e6 / this+0x7582) and posts
 * camera event type 4, id = kind, with the monster's camera list, to the camera manager (4U 0xc037bc on *0x105729c,
 * the jointFx manager; GU 0xaa418 -> 0x49dcc -> 0x19240 on *0x184d650 whose +0x54 is the uFestaCamera; GU r3 = 0
 * selects type 4, 1 type 0x14). C. The list is this+0x75f8 (setter 0x7091c) = the monster's camera list file:
 * the camera code 0x1d4a0 reads its data (+0x64) as LCM (u16 +6 = 256 ids, u32 +8 + 4 * id = record, 0 = skip;
 * an absent id does nothing). em089's 4U LCM is converted into the arc since 2026-10-18 (tools/lcm4u2gu.py, field
 * 11; ids 0-3, 6, 7, 10-12, 15-17, 19-26, 28-31 = 4U ids, so 2, 3, 7, 25, 29, 30, 31 exist): ON by default,
 * -DEM089_NO_CAM_EVENTS turns it back into a logged stub. Kinds per action: 1/8 25, 1/30 31, 1/17 7, 1/28 30,
 * 1/16 3, 1/27 29, 2/15 netEvent2 (separate). */
typedef void (*cam_event_t)(void *self, uint32_t kind, uint32_t r2, uint32_t type14, float s0);
static void *s_cam_self;
static void net_event(uint32_t kind)
{
    static uint32_t s_n;
#ifndef EM089_NO_CAM_EVENTS
    if (s_cam_self) {
        FN(cam_event_t, 0xaa418)(s_cam_self, kind, 255, 0, 0.0f);
        if (++s_n <= 30) logf("gogport: em089 camera event %u (0x93457c -> GU 0xaa418)", kind);
        return;
    }
#endif
    (void)s_cam_self; (void)s_n;
    stub("camera event 0x93457c (disabled)", kind, 255);
}

/* roar family. 1/0 [4U 0x8ba3e4]: motion 4 (6, 0), mode 0, attack id 0; frame 208: slot 1 = 3 (5) (the roar
 * shockwave) and 0xc0819c at joint 3 (stub); ends at the motion end.
 * FOR THE EFFECTS AGENT: 4U 0xc0819c(*0x10572f8, area W+0x14c, &pos of joint 3 (0x93093c)) = new uMhRadialBlurFilter
 * (200 B, vtable 0xe6313c) at that position when the monster is in the player's area (unit line 20 via 0x64608c):
 * the roar's radial blur; GU has uRadialBlurFilter (DTI 0x21209b4, newInstance 0x8b8a9c, 240 B), no spawn helper
 * found yet. 4U 0xc0bd38(*0x10572a4, 57, area, ...) = effect manager 0xc0765c type 2 = new uEffect002 (336 B, packet
 * id 57 at the monster, area-gated); GU has no uEffectNNN classes (effect system replaced).
 * 1/3, 1/8, 1/25, 1/26 [4U 0x8ba4f8, r1 = 0..3]: same; 1/8 posts camera event 25 at entry; at frame 208 1/25 posts
 * uEffect002 57 once (latch work+0xca = phase 2) and 1/26 sets the tar of parts 0, 2, 3, 6, 7 to 159.
 * 1/29..1/32 [4U 0x8bb3a8, r1 = 0..3]: the flying version: motion 73, mode 1, attack id 1, frame 140, event 31.
 * var: bits 0..1 = r1, bit 2 = 1/0 (no extras), bit 3 = flying. */
static void act_roar(void *self, uint32_t var)
{
    uint32_t v = var & 3, plain = var & 4, fly = var & 8;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, fly ? MOT_STOMP : MOT_ROAR, 6.0f, 0.0f);
        set_mode(self, fly ? 1 : 0);
        setAttackId(self, fly ? 1 : 0);
        if (!plain && v == 1) net_event(fly ? 31 : 25);
        return;
    }
    if (at_frame(self, fly ? 140.0f : 208.0f)) {
        hit(self, 1, 3, 5);
        em089_efx_roar_blur(self);   /* 4U 0xc0819c(area, joint 3 position): radial blur, player's area only */
        if (!plain && v == 2 && !FIELD(uint8_t, self, F_SHAKE)) {
            FIELD(uint8_t, self, F_SHAKE) = 1;
            logf("gogport: em089 phase 2: roar %s sets work+0xca", fly ? "1/31" : "1/25");
            em089_efx_aura(self, &FIELD(uint8_t, self, F_SHAKE), &FIELD(uint8_t, self, F_FLAG_E4));   /* uEffect002 57 */
        }
        if (!plain && v == 3) {
            float *t = &FIELD(float, self, F_TAR);
            t[0] = t[2] = t[3] = t[6] = t[7] = 159.0f;
        }
    }
    if (isMotionEnd(self)) act_end(self);
}

/* 1/1 [inline in 0x8bac40]: motion 2 (6, 0), end at the motion end. 1/18: motion 0x30b (6, 0) likewise. 1/4: motion
 * 0x30b with motion speed 0.7, speed 0.5 from frame 80. 1/21: motion 61 (8, 0). 1/24: motion 71 (8, 0), mode 1,
 * attack id 1. (Frame events skipped.) var = motion | 0x1000 (1/4 speeds) | 0x2000 (blend 8) | 0x4000 (1/24). */
static void log_maphit_1_24(void *self);   /* after maphit_frame */
static void act_1_inline(void *self, uint32_t var)
{
    uint32_t mot = var & 0xfff;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, mot, (var & 0x2000) ? 8.0f : 6.0f, 0.0f);
        if (var & 0x1000) setMotionSpeed(self, 0.7f);
        if (var & 0x4000) { set_mode(self, 1); setAttackId(self, 1); log_maphit_1_24(self); }
        return;
    }
    if ((var & 0x1000) && at_frame(self, 80.0f)) setMotionSpeed(self, 0.5f);
    static const drip_t k_d21[] = {{61, 2, 7, 32}, {3, 0, 7, 1}, {2, 1, 7, 80}};     /* 1/21 (0x8baec0) */
    static const drip_t k_d24[] = {{1, 1, 7, 65}, {4, 0, 7, 100}, {2, 1, 6, 120}};   /* 1/24 (0x8baf84) */
    if (mot == 0x03d) tar_drips(self, k_d21, 3);
    else if (mot == 0x047) tar_drips(self, k_d24, 3);
    if (isMotionEnd(self)) act_end(self);
}

/* 1/5, 1/17 [4U 0x8ba6fc, r1 = 0/1]: idle loop motion 2 (6, 0); 1/17 posts net event 7 and ends at the kind-1
 * check of 180, 1/5 at the motion end. 1/20, 1/28 [4U 0x8baaac, r1 = 0/1]: hover idle, mode 1, attack id 1, motion
 * 60 (1/20 looped; 1/28 once + net event 30), same endings. var bit 1 = hover. */
static void act_1_5(void *self, uint32_t var)
{
    uint32_t v = var & 1, hover = var & 2;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        if (hover) { set_mode(self, 1); setAttackId(self, 1); }
        if (hover && v) setMotion(self, MOT_IDLE2, 6.0f, 0.0f);
        else setMotionLoop(self, hover ? MOT_IDLE2 : MOT_IDLE, 6.0f, 0.0f);
        if (v) net_event(hover ? 30 : 7);
        return;
    }
    static const drip_t k_d[] = {{62, 2, 7, 25}, {72, 3, 7, 100}, {142, 4, 6, 65}, {4, 0, 6, 50}};
    static const drip_t k_dh[] = {{71, 3, 7, 100}, {2, 1, 7, 200}, {61, 2, 7, 300}, {4, 0, 7, 400},
                                  {142, 4, 6, 500}};
    if (hover) tar_drips(self, k_dh, 5);
    else tar_drips(self, k_d, 4);
    if (v ? mc(self, 1, 180.0f, 0.0f) : isMotionEnd(self)) act_end(self);
}

/* 1/16, 1/27 [4U 0x8ba84c, r1 = 0/1]: arena gimmick motions 0x31e / 0x32b (4, 0), slot 0 = 1, net event 3 / 29;
 * the yaw turns -1.26761 degrees per tick in 88..372 (1/27: -2.25 in 20..60, -1.6875 in 160..320); ends at the
 * motion end */
static void act_1_16(void *self, uint32_t var)
{
    float f;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, var ? 0x32b : 0x31e, 4.0f, 0.0f);
        hit(self, 0, 1, 0);
        net_event(var ? 29 : 3);
        return;
    }
    if (var) {
        f = 1.0f;
        if (motionCheck(self, 9, &f, 20.0f, 60.0f)) yaw_add(self, 2.25f, -f);
        f = 1.0f;
        if (motionCheck(self, 9, &f, 160.0f, 320.0f)) yaw_add(self, 1.6875f, -f);
    } else {
        f = 1.0f;
        if (motionCheck(self, 9, &f, 88.0f, 372.0f)) yaw_add(self, 1.26761f, -f);
    }
    if (isMotionEnd(self)) act_end(self);
}

/* 1/22, 1/23, 1/33, 1/34 [4U 0x8bb0f4, r1 = 0..3]: flying turn, motion 65 / 66 / 65 / 66 with flags 2 (16, 0),
 * mode 1, attack id 1, slot 0 = 58 (8), slot 1 = 59 (16), stopMove. Step 1: in window 60..100 the yaw steps (0x111
 * per tick, turnStep 0x91ab28 = GU 0xc0e78) toward the arena heading chosen by work+0xda (wall type 2 -> 0xd000,
 * 3 -> 0x4000, 4 -> 0x8000, else 0); at the motion end the action ends and work+0xda = 0.
 * 1/33 / 1/34 add motion layers 80 / 81 (0xb07ba4 + 0xb054e0, em089_aim_layer). Entry, after stopMove: forward
 * speed W+360 = speedFactor * 150 * this+668 / 16; step 1: velocity rotated by the angles (0x91150c, flags 0) while
 * this+644 > 0. 4U this+576 + k = GU this+0x4b0 + k (layer 0, same layout, C): this+644 = blend frames left (GU
 * this+0x4f4, getter 0xb0a8c), this+668 = motion speed (GU this+0x50c, getter 0xb09bc; 4U 0x8cba00 / GU 0xd3d108
 * divide the same timer by it). work+0xda is only set by the unported 7/47 wall branch, so the heading is 0 here as
 * in 4U without a wall hit. */
static void act_1_22(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotionEx(self, (var & 1) ? MOT_TURN_R : MOT_TURN_L, 2, 16.0f, 0.0f);
        if (var >= 2) em089_aim_layer(self, var == 2 ? 80 : 81, 2, 16.0f, 0.0f, 1.0f);
        set_mode(self, 1);
        setAttackId(self, 1);
        hit(self, 0, 58, 8);
        hit(self, 1, 59, 16);
        stopMove(self);
        FIELD(float, REC(self), REC_VEL + 8) = speedFactor(self) * 150.0f * FIELD(float, self, MOT_SPEED) * 0.0625f;
        return;
    }
    if (FIELD(float, self, MOT_BLEND) > 0.0f) rotateVel(self, REC(self) + REC_ANGLES, 0);
    tar_drip(self, 141, 4, 7, 62.0f);
    uint32_t w = FIELD(uint8_t, self, F_HEADING), h = w == 2 ? 0xd000 : w == 3 ? 0x4000 : w == 4 ? 0x8000 : 0;
    if (mc(self, 9, 60.0f, 100.0f)) {
        uint32_t *yaw = &FIELD(uint32_t, REC(self), REC_YAW);
        *yaw = turnStep(self, h, *yaw & 0xffff, 0x111);
    }
    if (isMotionEnd(self)) { act_end(self); FIELD(uint8_t, self, F_HEADING) = 0; }
}

/* ---- category 2: locomotion (faithful) ---- */

/* footstep tremor hits of the run motions: frame -> attack slot / index */
typedef struct { float frame; uint8_t slot, index; } step_hit;
static void step_hits(void *self, const step_hit *h, uint32_t n)
{
    for (uint32_t i = 0; i < n; i++)
        if (at_frame(self, h[i].frame)) hit(self, h[i].slot, h[i].index, 0);
}

/* 2/0, 2/65, 2/66 [4U 0x8b70dc, r1 = 0/1/2]: run, motion 5 (start-up 0..424, then a two-stride loop to 1300).
 * Entry: setStopDist(0, -200) on the target slot, mode 0, attack id 0, latch cleared, timer W+468 = 360 (0 for
 * 2/66). Step 1 every frame: 18 footstep hits; timerDown; the latch is set once inRange(0, 15) (only at the kind-1
 * check of frame 72) or inRange(0, 0) reports the target reached (the inRange call also steers: engine 0x78f7c).
 * When latched and the timer expired (2/65 also: as soon as findTargetEx(0, -1, 0x2000, 4) finds someone), the
 * stop waits for a foot plant: windows 255..424 / 645..866 / 1089..1300 -> step 2 (2/68 at frame 424 or 866),
 * windows 0..254 / 425..644 / 867..1088 -> step 3 (2/69 at frame 254, 644 or 1088), else the action ends.
 * Port-only: a safety timer (3000) forces the stop if the hunter is never reached. */
static const step_hit k_run_hits[] = {
    {285, 0, 21}, {700, 1, 21}, {1125, 1, 21}, {62, 0, 22}, {390, 0, 22}, {816, 0, 22}, {1238, 0, 22},
    {284, 1, 23}, {665, 0, 23}, {1110, 0, 23}, {26, 1, 24}, {471, 0, 24}, {916, 0, 24}, {195, 1, 25},
    {600, 1, 25}, {1040, 1, 25}, {460, 1, 26}, {895, 1, 26},
};
static void act_2_0(void *self, uint32_t var)
{
    static const drip_t k_d[] = {{71, 3, 7, 27}, {14, 4, 7, 51}, {18, 4, 7, 132}, {62, 2, 7, 180}, {2, 1, 7, 211},
                                 {72, 3, 7, 255}, {61, 2, 7, 313}, {62, 2, 7, 358}, {1, 1, 7, 439}, {72, 3, 7, 475},
                                 {4, 0, 7, 542}, {61, 2, 7, 595}};
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, MOT_RUN, 6.0f, 0.0f);
        sync_target(self);
        setStopDist(self, 0, 0, -200.0f);
        set_mode(self, 0);
        setAttackId(self, 0);
        FIELD(uint8_t, self, F_RANGE) = 0;
        TIMER(self) = var == 2 ? 0.0f : 360.0f;
        FIELD(float, self, F_SAFETY) = 3000.0f;
        return;
    case 1: {
        step_hits(self, k_run_hits, sizeof k_run_hits / sizeof k_run_hits[0]);
        tar_drips(self, k_d, sizeof k_d / sizeof k_d[0]);
        int expired = timerDown(self, &TIMER(self), 1.0f);
        sync_target(self);
        int in = mc(self, 1, 72.0f, 0.0f) ? inRange(self, 0, 15) : inRange(self, 0, 0);
        if (in) FIELD(uint8_t, self, F_RANGE) = 1;
        int forced = timerDown(self, &FIELD(float, self, F_SAFETY), 1.0f);
        if (forced) logf("gogport: em089 run %u/%u safety stop", 2u, FIELD(uint8_t, self, EN_ACT_NUM));
        if (!((FIELD(uint8_t, self, F_RANGE) && expired) || forced)) {
            if (var != 1 || findTargetEx(self, 0, -1, 0x2000, 4) == -1) return;
        }
        if (mc(self, 3, 255, 424) || mc(self, 3, 645, 866) || mc(self, 3, 1089, 1300)) STEP(self) = 2;
        else if (mc(self, 3, 0, 254) || mc(self, 3, 425, 644) || mc(self, 3, 867, 1088)) STEP(self) = 3;
        else act_end(self);
        return;
    }
    case 2:
        if (at_frame(self, 424.0f)) chain(self, 2, 68);
        if (at_frame(self, 866.0f)) chain(self, 2, 68);
        return;
    case 3:
        if (at_frame(self, 254.0f)) chain(self, 2, 69);
        if (at_frame(self, 644.0f)) chain(self, 2, 69);
        if (at_frame(self, 1088.0f)) chain(self, 2, 69);
        return;
    }
}

/* 2/1, 2/2 [4U inline in the cat-2 dispatcher 0x8bd4b0]: turn toward the target with the engine move sequence:
 * step 0 setTargetMode(0), seqStart2(table, 0, flags 65, 0); step 1 ends when seqPoll2 reports done. Tables 4U
 * 0xe0de8c (2/1: straight 13 under 40 degrees, 11 / 12 up to 90, 13 / 21 / 22 beyond) and 0xe0de94 (2/2: straight
 * under 20 degrees), converted to GU records. */
static void act_2_1(void *self, uint32_t var)
{
    const void *tbl = var ? (const void *)k_seq_2_2 : (const void *)k_seq_2_1;
    sync_target(self);
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        seqStart2(self, tbl, 0, 65, 0);
        return;
    }
    static const drip_t k_d[] = {{4, 0, 7, 44}, {1, 1, 7, 45}, {62, 2, 6, 63}, {72, 3, 6, 63}};
    tar_drips(self, k_d, 4);
    if (seqPoll2(self, tbl)) act_end(self);
}

/* 2/62 [4U inline in 0x8bd4b0]: same with table 0xe0de9c (motions 60 / 63 / 64 / 67 / 68), mode 1, attack id 1;
 * at the end setTargetMode(0) + setActionW(1, 20) + thinkRequest(0) */
static void act_2_62(void *self, uint32_t var)
{
    (void)var;
    sync_target(self);
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        seqStart2(self, k_seq_2_62, 0, 65, 0);
        set_mode(self, 1);
        setAttackId(self, 1);
        return;
    }
    static const drip_t k_d[] = {{62, 2, 7, 55}, {140, 4, 6, 10}, {72, 3, 7, 123}};
    tar_drips(self, k_d, 3);
    if (seqPoll2(self, k_seq_2_62)) end_1_20(self);
}

/* 2/6, 2/19..2/22, 2/28, 2/60 [4U 0x8b7b38, r1 = 0, 1, 2, 3, 4, 5, 7]: walk cycle, motion 25 (6, 0).
 * Entry: r1 0 (and 6): attack slot 0 = 2; r1 1..4: slot 0 = 18 + setStopDist(0, 0); r1 5: slot 0 = 18 and step 2;
 * r1 7: nothing. Step 1 (W+0x145 = count byte, 0 = keep walking): r1 1/2: findTarget(0, 0x10000, 4) -> found:
 * r1 2 keeps its angle (W+0x146 = (a + 0x8000) >> 8) and W+0x145 = 2, r1 1 W+0x145 = 1; else inRange(0, 0) ->
 * W+0x145 = 1. r1 3/4: same with findTarget(0, 0x400, 4) (r1 4 keeps the angle). Others: W+0x145 = 1 at once.
 * At the motion end: W+0x145 == 0 -> walk again; r1 2/4 with W+0x145 == 2 -> setTarget(5, 11, W+0x146, 0) and
 * chain 2/1 (turn toward the found target); else end. Step 2 (2/28): chain 7/52 at the kind-1 check of 148. */
static void act_2_6(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, MOT_WALK_ATK, 6.0f, 0.0f);
        if (var == 0 || var == 6) hit(self, 0, 2, 0);
        else if (var <= 4) { hit(self, 0, 18, 0); sync_target(self); setStopDist(self, 0, 0, 0.0f); }
        else if (var == 5) { STEP(self) = 2; hit(self, 0, 18, 0); }
        return;
    }
    if (STEP(self) == 2) {
        if (mc(self, 1, 148.0f, 0.0f)) chain(self, 7, 52);
        return;
    }
    if (STEP(self) != 1) return;
    if (STEP1(self) == 0) {
        if (var >= 1 && var <= 4) {
            int32_t a = findTarget(self, 0, var <= 2 ? 0x10000 : 0x400, 4);
            if (a != -1) {
                if (var == 2 || var == 4) { STEP2(self) = (uint8_t)((uint32_t)(a + 0x8000) >> 8); STEP1(self) = 2; }
                else STEP1(self) = 1;
            } else {
                sync_target(self);
                if (inRange(self, 0, 0)) STEP1(self) = 1;
            }
        } else {
            STEP1(self) = 1;
        }
    }
    static const drip_t k_d[] = {{61, 2, 7, 45}, {71, 3, 7, 75}, {1, 4, 6, 60}};
    tar_drips(self, k_d, 3);
    if (!isMotionEnd(self)) return;
    if (STEP1(self) == 0) { setMotion(self, MOT_WALK_ATK, 6.0f, 0.0f); return; }
    if ((var == 2 || var == 4) && STEP1(self) == 2) {
        setTarget(self, 5, 11, STEP2(self), 0);
        FIELD(uint8_t, self, F_NOSYNC) = 1;   /* the following 2/1 turns toward this target, not the hunter */
        chain(self, 2, 1);
        return;
    }
    act_end(self);
}

/* 4U 0x9399c0(this) = 0x945e60(this, 1), the AI's post-action think-list choice (timer W+0x78b8 > 0 and group 13
 * -> list 13, else groups 8 / 9 / 14 / 16 / 19 / 20 / 21 / 15 by state) = GU 0x8282c(this, 1) (C: same shape, r1 == 2
 * early path, timer this+0x758c > 0 -> list 13 from [this+0x72f4]+0x34, then the group 8 / 9 / 14 reads at
 * 0x828d0 / 0x82a44 / 0x8290c). */
typedef void (*think_list_after_t)(void *self, uint32_t mode);
#define thinkListAfter FN(think_list_after_t, 0x8282c)

/* 2/15, 2/27 [4U 0x8b7ea0, r1 = 1/0]: motion 8 (6, 0), attack slot 0 = 20; 2/15 also posts net event 2 (0) at
 * entry and calls 0x9399c0 (thinkListAfter(1)) at the end, before the action end; ends at the motion end */
static void act_2_27(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, MOT_008, 6.0f, 0.0f);
        hit(self, 0, 20, 0);
        if (var == 1) netEvent2(self, 0);
        return;
    }
    static const drip_t k_d[] = {{61, 2, 7, 26}, {71, 3, 7, 26}, {4, 0, 6, 65}};
    tar_drips(self, k_d, 3);
    if (!isMotionEnd(self)) return;
    if (var == 1) {
        static uint32_t s_n;
        thinkListAfter(self, 1);
        if (++s_n <= 10) logf("gogport: em089 2/15 end: thinkListAfter -> list %u", FIELD(uint8_t, self, 0x72fc));
    }
    act_end(self);
}

/* 2/35 [4U 0x8b7fb8]: TAKEOFF into the hover (not a landing): motion 264 (no root motion, the hips rise at its end),
 * motions 268 / 263 carry a constant root track y 720 (x 2.5 model scale = the 1800 seen in the log), and 0/6 after
 * it loops 263 (hover idle). The +1800 itself comes from the rest pair (restApply 720 * size), before motion 268,
 * so 0x954e5c's height test (900) skips in 4U too. Motion 264 (6, 0); at its end rest pair (0x93d8a8 + 0x92e9d4), motion 268
 * (0, 0) and 0x954e5c(1, 1, {0, 0, 800}, 0.8, 900); then motion 263
 * FOR THE EFFECTS AGENT: 4U 0x954e5c(this, r1 kind 1, r2, r3 &offset {0, 0, 800}, s0 scale 0.8, s1 900) is the uEnemy
 * ground-impact effect, not a quake: skipped when the monster is higher than ground (W+0x624) + s1; position = W+408
 * + offset * 0x923fc8 (model scale) rotated by the yaw W+0x1ac; then by r1 (kind 1..7) a shell-manager post
 * 0x661d18(*0xef3cf0, &pos, type 1 / 2 / 11 / 12 / 26 / 27 / 28, 0xffff, .., scale s0 (x0.8 / x0.6 by kind)) =
 * dust/splash; then a ground-material check via 0xc094e8(*0x10572a4, W+0x5f8). GU counterpart not identified.
 * (4, 0); at its end slot 249 (4U 0x9559a8) */
static void act_2_35(void *self, uint32_t var)
{
    (void)var;
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, MOT_108, 6.0f, 0.0f);
        return;
    case 1: {
        static const drip_t k_d[] = {{72, 3, 7, 24}, {62, 2, 7, 30}, {141, 4, 7, 50}};
        tar_drips(self, k_d, 3);
        if (!isMotionEnd(self)) return;
        STEP(self) = 2;
        restApply(self, restValue(self));
        setMotion(self, MOT_10C, 0.0f, 0.0f);
        {
            static const float k_off[3] = {0.0f, 0.0f, 800.0f};
            em089_shell005_ground_impact(self, 1, k_off, 0.8f, 900.0f);   /* 4U posts the tremor shell first */
            em089_efx_ground_impact(self, 1, k_off, 0.8f, 900.0f);   /* 4U 0x954e5c(1, 1, {0, 0, 800}, 0.8, 900) */
        }
        return;
    }
    case 2:
        if (!isMotionEnd(self)) return;
        STEP(self) = 3;
        setMotion(self, MOT_REACT_SMALL, 4.0f, 0.0f);
        return;
    default:
        if (isMotionEnd(self)) act_end6(self);
        return;
    }
}

/* 2/33, 2/34, 2/45, 2/46 [4U 0x8b818c, r1 = motion 28 / 29, r2 = 0 / 1]: motion (6, 0), attack slot 0 = 19;
 * turnToTarget 91 per frame in the kind-3 window 60..120 (r2 = 1: 182 in 28..120); ends at the motion end */
static void act_2_33(void *self, uint32_t var)
{
    uint32_t alt = var & 1, fast = var >> 1;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, alt ? MOT_01D : MOT_01C, 6.0f, 0.0f);
        hit(self, 0, 19, 0);
        return;
    }
    static const drip_t k_d[2][3] = {{{2, 1, 7, 21}, {72, 3, 7, 60}, {18, 4, 6, 62}},
                                     {{2, 1, 7, 21}, {62, 2, 7, 60}, {14, 4, 6, 62}}};
    tar_drips(self, k_d[alt], 3);
    if (fast ? mc(self, 3, 28.0f, 120.0f) : mc(self, 3, 60.0f, 120.0f)) face(self, fast ? 182 : 91, 0);
    if (isMotionEnd(self)) act_end(self);
}

/* 2/61, 2/63, 2/64 [4U 0x8b836c, r1 = 0/1/2]: flying run, motion 62 (6, 0); same structure as 2/0: entry
 * setStopDist(0, -200), mode 1, attack id 1, latch cleared, timer 360 (0 for 2/64); step 1: 14 footstep hits,
 * timerDown, latch on inRange(0, 128); latched and expired (2/63: or findTargetEx(0, -1, 0x2000, 4) found) ->
 * windows 260..499 / 740..820 (2/63: 260..509 / 750..820) -> step 2, 0..259 / 500..739 (2/63: 0..259 / 510..749)
 * -> step 3, else setTargetMode(0) + setActionW(1, 20) + thinkRequest(0). Step 2: chain 2/70 at frame 500;
 * step 3: chain 2/71 at frame 260 or 740. Port-only safety timer as in 2/0. */
static const step_hit k_fly_hits[] = {
    {300, 0, 21}, {514, 0, 21}, {112, 0, 22}, {330, 0, 22}, {674, 0, 22}, {198, 0, 23}, {424, 0, 23},
    {170, 1, 24}, {406, 1, 24}, {624, 1, 24}, {230, 1, 25}, {446, 1, 25}, {314, 1, 26}, {536, 1, 26},
};
static void act_2_61(void *self, uint32_t var)
{
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, MOT_03E, 6.0f, 0.0f);
        sync_target(self);
        setStopDist(self, 0, 0, -200.0f);
        set_mode(self, 1);
        setAttackId(self, 1);
        FIELD(uint8_t, self, F_RANGE) = 0;
        TIMER(self) = var == 2 ? 0.0f : 360.0f;
        FIELD(float, self, F_SAFETY) = 3000.0f;
        return;
    case 1: {
        static const drip_t k_d[] = {{4, 0, 6, 69}, {62, 2, 7, 99}, {142, 4, 6, 179}, {72, 3, 7, 185},
                                     {62, 2, 7, 295}, {2, 1, 6, 310}, {72, 3, 7, 400}};
        step_hits(self, k_fly_hits, sizeof k_fly_hits / sizeof k_fly_hits[0]);
        tar_drips(self, k_d, sizeof k_d / sizeof k_d[0]);
        int expired = timerDown(self, &TIMER(self), 1.0f);
        sync_target(self);
        if (inRange(self, 0, 128)) FIELD(uint8_t, self, F_RANGE) = 1;
        int forced = timerDown(self, &FIELD(float, self, F_SAFETY), 1.0f);
        int a;
        if ((FIELD(uint8_t, self, F_RANGE) && expired) || forced) a = 1;
        else if (var == 1 && findTargetEx(self, 0, -1, 0x2000, 4) != -1) a = 2;
        else return;
        if (a == 1 ? (mc(self, 3, 260, 499) || mc(self, 3, 740, 820)) : (mc(self, 3, 260, 509) || mc(self, 3, 750, 820)))
            STEP(self) = 2;
        else if (a == 1 ? (mc(self, 3, 0, 259) || mc(self, 3, 500, 739)) : (mc(self, 3, 0, 259) || mc(self, 3, 510, 749)))
            STEP(self) = 3;
        else
            end_1_20(self);
        return;
    }
    case 2:
        if (at_frame(self, 500.0f)) chain(self, 2, 70);
        return;
    case 3:
        if (at_frame(self, 260.0f)) chain(self, 2, 71);
        if (at_frame(self, 740.0f)) chain(self, 2, 71);
        return;
    }
}

/* 2/67 [4U 0x8b8b28]: hover turn. Every frame the vertical speed W+384 (GU rec+0x5c) decays toward 0 by 2.5 per
 * tick (0x915d7c = GU 0xbf7d8). Entry: setTargetMode(3), loop motion 263 (4, 0), single-record sequence 4U
 * 0xe0dea4 (seqStart1, flags 65); slot 249 when seqPoll1 reports done. */
static void act_2_67(void *self, uint32_t var)
{
    (void)var;
    vspeed_decay(self);
    sync_target(self);
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 3);
        setMotionLoop(self, MOT_REACT_SMALL, 4.0f, 0.0f);
        seqStart1(self, &k_seq_dea4, 0, 65, 0);
        return;
    }
    static const drip_t k_d[] = {{3, 0, 7, 3}, {2, 1, 7, 30}, {142, 4, 7, 60}};
    tar_drips(self, k_d, 3);
    if (seqPoll1(self, &k_seq_dea4)) act_end6(self);
}

/* 2/68..2/71 [4U 0x8b8ca4, r1 = 0..3]: run / flight stops, motion 75 + r1 with flags 2 (20, 0); r1 >= 2: mode 1
 * and attack id 1 (else mode 0, id 0); ends at the motion end */
static void act_run_stop(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotionEx(self, MOT_RUN_STOP + var, 2, 20.0f, 0.0f);
        set_mode(self, var >= 2);
        setAttackId(self, var >= 2);
        return;
    }
    static const drip_t k_d[] = {{62, 2, 7, 55}, {1, 1, 7, 5}, {140, 4, 7, 10}};
    tar_drips(self, k_d, 3);
    if (isMotionEnd(self)) act_end(self);
}

/* ---- categories 3, 4, 13: rest / knock-back / special (faithful) ---- */

/* 3/0, 3/1 [4U 0x8b6654, r1 = 0/1]: settle down / take off: 3/0 rest pair, 3/1 setTargetMode(1); motion 263
 * (4, 0), stopMove; in window 0..120 vertical speed = speedFactor * 2.5 (3/1: -2.5) rotated by the angles
 * (flags 0); slot 249 at the motion end. */
static void act_3_0(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        begin(self);
        if (var) setTargetMode(self, 1);
        else restApply(self, restValue(self));
        setMotion(self, MOT_REACT_SMALL, 4.0f, 0.0f);
        stopMove(self);
        return;
    }
    if (mc(self, 9, 0.0f, 120.0f)) rise(self, speedFactor(self) * (var ? -2.5f : 2.5f));
    if (isMotionEnd(self)) act_end6(self);
}

/* 3/2 [4U 0x8b67e4] and 4/4 [4U 0x8b938c]: sleep / down. 3/2 every frame: sleep flags (0x922cd8, 0x93c6c8) and
 * W+0xb00 = 1 (GU rec+0x990, S); entry 3/2: restApply(720), 4/4: setTargetMode(3); motion 263 (4, 0); at its end
 * motion 266 (6, 0); at its end setTargetMode(0), motion 267 (0, 0), slot 0 = 42; at its end the action ends.
 * var 0 = 3/2, 1 = 4/4. */
static void act_sleep(void *self, uint32_t var)
{
    static const drip_t k_d2[] = {{72, 3, 7, 24}, {62, 2, 7, 30}, {140, 4, 7, 50}};   /* motion 266 */
    static const drip_t k_d3[] = {{72, 3, 7, 48}, {62, 2, 7, 60}, {1, 1, 7, 85}};     /* motion 267 */
    if (!var) { sleepFlagA(self); sleepFlagB(self); FIELD(uint8_t, REC(self), 0x990) = 1; }
    switch (STEP(self)) {
    case 0:
        begin(self);
        if (var) setTargetMode(self, 3);
        else restApply(self, 720.0f);
        setMotion(self, MOT_REACT_SMALL, 4.0f, 0.0f);
        return;
    case 1:
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        setMotion(self, 0x10a, 6.0f, 0.0f);
        return;
    case 2:
        tar_drips(self, k_d2, 3);
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        setTargetMode(self, 0);
        setMotion(self, 0x10b, 0.0f, 0.0f);
        hit(self, 0, 42, 0);
        return;
    default:
        tar_drips(self, k_d3, 3);
        if (isMotionEnd(self)) act_end(self);
        return;
    }
}

/* knock-back push shared by cat 4: r1 1/2 = stopMove, velocity x = 36 and acceleration x = -1.2 (negated for 2);
 * then in window 0..100 accelVel (flags 1) until the velocity changes sign */
static void push_start(void *self, uint32_t v)
{
    if (v != 1 && v != 2) return;
    stopMove(self);
    float s = v == 2 ? -1.0f : 1.0f;
    FIELD(float, REC(self), REC_VEL) = 36.0f * s;
    FIELD(float, REC(self), REC_ACCEL) = -1.2f * s;
}

/* drips of the 4/0 and 4/5 push motions (4U 0x8b92b8.., 0x8b975c..) */
static const drip_t k_drips_push[] = {{72, 3, 7, 10}, {62, 2, 7, 12}, {71, 3, 7, 50}, {60, 2, 7, 55}};

static void push_step(void *self, uint32_t v)
{
    if (!v || !mc(self, 3, 0.0f, 100.0f)) return;
    float *vx = &FIELD(float, REC(self), REC_VEL), old = *vx;
    accelVel(self, REC(self) + REC_ANGLES, 1);
    if (!(*vx * old > 0.0f)) { *vx = 0.0f; FIELD(float, REC(self), REC_ACCEL) = 0.0f; }
}

/* 4/0, 4/2, 4/3 [4U 0x8b905c, r1 = 0/1/2]: setTargetMode(3), motion 263 (4, 0); frame 90: motion 265 (4, 0) and
 * the push (4/2, 4/3); step 2: turnToTarget 182, push, at the motion end motion 263 (4, 10); slot 249 at its end.
 * Not ported: window 34..112 writes 2200 / distance + 1 (near) into 4U this+0xd38 (0x8b929c: this + 3072 + 312,
 * the body-bend input of 7/26; earlier notes said 0xc78), GU twin not found. */
static void act_4_0(void *self, uint32_t var)
{
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 3);
        setMotion(self, MOT_REACT_SMALL, 4.0f, 0.0f);
        return;
    case 1:
        if (!at_frame(self, 90.0f)) return;
        STEP(self)++;
        setMotion(self, MOT_REACT, 4.0f, 0.0f);
        push_start(self, var);
        return;
    case 2:
        face(self, 182, 0);
        push_step(self, var);
        tar_drips(self, k_drips_push, 4);
        if (!isMotionEnd(self)) return;
        STEP(self)++;
        setMotion(self, MOT_REACT_SMALL, 4.0f, 10.0f);
        return;
    default:
        if (isMotionEnd(self)) act_end6(self);
        return;
    }
}

/* 4/5, 4/7, 4/8, 4/9, 4/10, 4/11 [4U 0x8b9584, r1 = 0/1/2, r2 = 0/1]: setTargetMode(3), motion 263 (4, 0); frame
 * 116: motion 271 (18, 0) and the push (r1 1/2); step 2: turnToTarget 182, push, at frame 114 (r2 1: 230) motion
 * 263 (18, 0); slot 249 at its end. var = r1 | r2 << 2. */
static void act_4_5(void *self, uint32_t var)
{
    uint32_t v = var & 3, w = var >> 2;
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 3);
        setMotion(self, MOT_REACT_SMALL, 4.0f, 0.0f);
        return;
    case 1:
        if (!at_frame(self, 116.0f)) return;
        STEP(self)++;
        setMotion(self, MOT_REACT2, 18.0f, 0.0f);
        push_start(self, v);
        return;
    case 2:
        face(self, 182, 0);
        push_step(self, v);
        tar_drips(self, k_drips_push, 4);
        if (!at_frame(self, w ? 230.0f : 114.0f)) return;
        STEP(self)++;
        setMotion(self, MOT_REACT_SMALL, 18.0f, 0.0f);
        return;
    default:
        if (isMotionEnd(self)) act_end6(self);
        return;
    }
}

/* 4/6 [inline in 0x8c2640]: rest pair, motion 274 (0, 0); slot 249 at the motion end */
static void act_4_6(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        restApply(self, restValue(self));
        setMotion(self, 0x112, 0.0f, 0.0f);
        return;
    }
    if (isMotionEnd(self)) act_end6(self);
}

/* 4U 0xb05934 = GU 0x53a984 (apimap 99/99; both end with model vcalls +0x4c then +0x50): apply the pose / matrices
 * at once after a setMotion (4U copies the root offset this+0xd00 + this+0xd10 into the position first). GU monsters
 * call it right after setMotion 0xaff40 (e.g. 0xd22988, 0xd30d88, 0xd530e0): C. */
typedef void (*model_refresh_t)(void *self);
#define modelRefresh FN(model_refresh_t, 0x53a984)

/* 13/11 [inline in slot 44 0x8c3ac0]: mode 1, attack id 1, setTargetMode(0), motion 73 from frame 240 (0, 240),
 * then 0xb05934 (modelRefresh); ends at the motion end */
static void act_13_11(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        set_mode(self, 1);
        setAttackId(self, 1);
        setTargetMode(self, 0);
        setMotion(self, MOT_STOMP, 0.0f, 240.0f);
        modelRefresh(self);
        return;
    }
    if (isMotionEnd(self)) act_end(self);
}

/* ---- category 7: attacks (faithful step machines; aim layers / effects stubbed where noted) ---- */

/* u16 angle from the monster to a point (4U atan2 0x568c8c on (x - W+408, z - W+416)) */
static uint32_t angle_to(void *self, const float *p)
{
    float a = atan2f_gu(p[0] - FIELD(float, REC(self), REC_POS_X), p[2] - FIELD(float, REC(self), REC_POS_Z));
    return (uint32_t)(int32_t)(a * 10430.378f + 0.5f) & 0xffff;   /* 65536 / 2pi, constant 0x76cc0 */
}

/* 4U 0x8bdc9c(this, cur, target, max, mode): step the angle cur toward target by at most max * time scale;
 * mode 0 = shortest way, 1 = always positive, 2 = always negative. Returns the new u16 angle. */
static uint32_t angle_step(void *self, uint32_t cur, uint32_t tgt, uint32_t max, uint32_t mode)
{
    uint32_t step = (uint32_t)(DT(self) * (float)max), d = (tgt - cur) & 0xffff;
    if (mode == 0) {
        if (d < 0x8000) return d < step ? tgt : (cur + step) & 0xffff;
        return 0x10000 - d < step ? tgt : (cur - step) & 0xffff;
    }
    if (d >= 0x8000) d = 0x10000 - d;
    if (mode == 1) return d >= step ? (cur + step) & 0xffff : tgt;
    return step <= d ? (cur - step) & 0xffff : tgt;
}

/* hunter yaw from its root joint rotation (joint +96 quaternion x, y, z, w; forward = row 2 of the matrix that
 * 0x53ab88 builds) (W: not checked in game, logged once) */
static int hunter_yaw(void *self, uint32_t *yaw)
{
    uint8_t *pl = em089_target_hunter(self);
    if (!pl) return 0;
    uint8_t idx = (*(uint8_t **)(pl + 0x498))[0];
    if (idx == 255) return 0;
    const float *q = (const float *)(*(uint8_t **)(pl + 0x494) + idx * 160 + 96);
    float fx = 2.0f * (q[0] * q[2] + q[1] * q[3]), fz = 1.0f - 2.0f * (q[0] * q[0] + q[1] * q[1]);
    *yaw = (uint32_t)(int32_t)(atan2f_gu(fx, fz) * 10430.378f + 0.5f) & 0xffff;
    return 1;
}

/* 4U 0x93156c(this, out, {0, 0, z}): aim point = target position + offset rotated by the target player's
 * orientation (4U rotates by the player's three angles; the yaw alone here). No player: the target position. */
static void lead_point(void *self, float z, float *out)
{
    uint32_t yaw;
    target_pos(self, out);
    if (!hunter_yaw(self, &yaw)) return;
    float r = (float)yaw * (6.2831853f / 65536.0f);
    out[0] += z * sinf_gu(r);
    out[2] += z * cosf_gu(r);
    out[3] = 0.0f;
    static uint32_t s_n;
    if (++s_n <= 5) logf("gogport: em089 lead point z %d hunter yaw %x -> %d,%d", (int32_t)z, yaw, (int32_t)out[0], (int32_t)out[2]);
}

static float target_dist(void *self)
{
    float t[4];
    target_pos(self, t);
    float dx = t[0] - FIELD(float, REC(self), REC_POS_X), dz = t[2] - FIELD(float, REC(self), REC_POS_Z);
    float d2 = dx * dx + dz * dz, d;
    __asm__("vsqrt.f32 %0, %1" : "=t"(d) : "t"(d2));   /* -fno-builtin: no libm sqrtf in the module */
    return d;
}

/* em089 aim at entry (7/7 pattern): aim point W+392 = lead point(z); turn rate work+0xdc = |angle to the aim point
 * - yaw| * inv_window rounded up (ceilf 0xd131e8), or cap when the difference is >= max_diff */
static void aim_rate(void *self, uint32_t max_diff, float inv_window, uint32_t cap);
static void aim_setup(void *self, float z, uint32_t max_diff, float inv_window, uint32_t cap)
{
    lead_point(self, z, &FIELD(float, self, F_AIM));
    aim_rate(self, max_diff, inv_window, cap);
}

/* same rate rule toward the aim point already stored in F_AIM */
static void aim_rate(void *self, uint32_t max_diff, float inv_window, uint32_t cap)
{
    float *aim = &FIELD(float, self, F_AIM);
    uint32_t d = (angle_to(self, aim) - FIELD(uint32_t, REC(self), REC_YAW)) & 0xffff;
    if (d >= 0x8000) d = 0x10000 - d;
    if (d >= max_diff) { FIELD(uint32_t, self, F_TURN) = cap; return; }
    float r = (float)(int32_t)d * inv_window;
    uint32_t n = (uint32_t)r;
    FIELD(uint32_t, self, F_TURN) = (n + ((float)n < r)) & 0xffff;
}

/* em089 aim turn in a kind-9 window: yaw = angle_step(yaw, target angle, rate * window fraction, mode); the
 * target angle is the live angle to W+392, or a fixed angle (work+0xe0) when fixed >= 0 */
static void aim_turn_to(void *self, float a, float b, uint32_t mode, int32_t fixed)
{
    float frac = 1.0f;
    if (!motionCheck(self, 9, &frac, a, b)) return;
    uint32_t *yaw = &FIELD(uint32_t, REC(self), REC_YAW);
    uint32_t max = (uint32_t)((float)FIELD(uint32_t, self, F_TURN) * frac);
    uint32_t tgt = fixed >= 0 ? (uint32_t)fixed : angle_to(self, &FIELD(float, self, F_AIM));
    *yaw = angle_step(self, *yaw, tgt, max, mode);
}

static void aim_turn(void *self, float a, float b, uint32_t mode) { aim_turn_to(self, a, b, mode, -1); }

/* aim at the target itself (4U W+536) instead of a lead point */
static void aim_target(void *self) { target_pos(self, &FIELD(float, self, F_AIM)); }

/* 7/7, 7/52, 7/55 [4U 0x8bb5b0, r1 = 0/1/2]: tar jump, motion 526 ((6, 0); 7/52 and 7/55: (10, 20)), mode 0,
 * attack id 0, slot 0 = 13 (8), slot 1 = 14 (24), stopMove; aim point = lead point at distance / 2.5 + 175 ahead of
 * the hunter, turn rate = angle / 122 (cap 104 at 70 degrees). Step 1: aim turn in window 0..122; frame 240:
 * re-arm slot 1 = 48 (24); frame 254: slot 1 = 49 (16); ends at the motion end. */
static void act_7_7(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        set_mode(self, 0);
        setAttackId(self, 0);
        if (var == 1 || var == 2) setMotion(self, MOT_ATK_526, 10.0f, 20.0f);
        else setMotion(self, MOT_ATK_526, 6.0f, 0.0f);
        hit(self, 0, 13, 8);
        hit(self, 1, 14, 24);
        stopMove(self);
        aim_setup(self, target_dist(self) / 2.5f + 175.0f, 0x31c7, 1.0f / 122.0f, 104);
        return;
    }
    aim_turn(self, 0.0f, 122.0f, 0);
    if (at_frame(self, 240.0f)) rehit(self, 1, 48, 24);
    if (at_frame(self, 254.0f)) rehit(self, 1, 49, 16);
    static const drip_t k_d[] = {{4, 0, 7, 12}, {2, 1, 7, 40}, {1, 1, 6, 5}};
    tar_drips(self, k_d, 3);
    if (isMotionEnd(self)) act_end(self);
}

/* 7/17 [4U 0x8bb958]: motion 574 (6, 0), mode 0, attack id 0, slot 0 = 5 (8), slot 1 = 11 (24); turnToTarget 38
 * per frame from the kind-2 check of 72; frame 140: slot 1 = 12 (16); ends at the motion end */
static void act_7_17(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        set_mode(self, 0);
        setAttackId(self, 0);
        setMotion(self, MOT_ATK_574, 6.0f, 0.0f);
        hit(self, 0, 5, 8);
        hit(self, 1, 11, 24);
        return;
    }
    if (mc(self, 2, 72.0f, 0.0f)) face(self, 38, 0);
    if (at_frame(self, 140.0f)) hit(self, 1, 12, 16);
    static const drip_t k_d[] = {{4, 0, 7, 2}, {2, 1, 7, 78}, {142, 4, 6, 80}};
    tar_drips(self, k_d, 3);
    if (isMotionEnd(self)) act_end(self);
}

/* 7/19, 7/20 [4U 0x8bbaf8, r1 = 0/1]: tail sweep, motion 572 / 573 (6, 0), mode 0, attack id 0, slot 0 = 6 / 7,
 * slot 1 = 16. Step 1: the yaw turns 180 degrees in window 132..260 (1.40625 per tick) and 60 in 304..360 (15/14
 * per tick), negative for 7/20; window 300..386: tar on part 6 and 0x8c34a0(1); ends at the motion end.
 * Not ported: the per-frame model flag this+0xca8 |= 4 or 2 (by W+0x42c & 1, render side). */
static void act_7_19(void *self, uint32_t var)
{
    float f;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        set_mode(self, 0);
        setAttackId(self, 0);
        setMotion(self, var ? 0x23d : 0x23c, 6.0f, 0.0f);
        hit(self, 0, var ? 7 : 6, 0);
        hit(self, 1, 16, 0);
        return;
    }
    f = 1.0f;
    if (motionCheck(self, 9, &f, 132.0f, 260.0f)) yaw_add(self, 1.40625f, var == 1 ? -f : f);
    f = 1.0f;
    if (motionCheck(self, 9, &f, 304.0f, 360.0f)) yaw_add(self, 15.0f / 14.0f, var == 1 ? -f : f);
    if (mc(self, 3, 300.0f, 386.0f)) { tar_add(self, DT(self),6, 0); atk_shorten(self, 1); }
    tar_drip(self, 1, 1, 7, 20.0f);
    tar_drip(self, 4, 0, 7, 110.0f);
    if (var) tar_drip(self, 72, 3, 6, 70.0f);
    else tar_drip(self, 62, 2, 6, 70.0f);
    if (isMotionEnd(self)) act_end(self);
}

/* 7/25, 7/53 [4U 0x8bbe04, r1 = 0/1]: motion 521 (6, 0), mode 0, attack id 0, slot 0 = 8 (8), slot 1 = 47 (16);
 * turnToTarget 227 per frame from the kind-2 check of 80; at the kind-1 check of 172 chain 7/30 (7/53: 7/54) */
static void act_7_25(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, 0x209, 6.0f, 0.0f);
        set_mode(self, 0);
        setAttackId(self, 0);
        hit(self, 0, 8, 8);
        hit(self, 1, 47, 16);
        return;
    }
    if (mc(self, 2, 80.0f, 0.0f)) face(self, 227, 0);
    if (mc(self, 1, 172.0f, 0.0f)) chain(self, 7, var ? 54 : 30);
    static const drip_t k_d[] = {{62, 2, 7, 70}, {2, 1, 7, 70}, {18, 4, 6, 15}};   /* the last one a tail call */
    tar_drips(self, k_d, 3);
}

/* 7/26, 7/30, 7/54 [4U 0x8bc288, r1 = 1/0/2]: mode 0, attack id 0. 7/26: motion 522 (6, 0) then (step 1:
 * turnToTarget 132 from the kind-2 check of 124) at its end motion 523 from frame 116 (0, 116) with slot 0 = 9
 * (8), slot 1 = 46 (16), step 3; 7/30, 7/54: motion 523 (6, 0) with the same slots, step 2. Steps 2/3:
 * turnToTarget 91 from the kind-2 check of 40; 7/54 chains 7/55 at the kind-1 check of 192, the others end at
 * the motion end. Step 2 skips the turn (and its window check) while the motion blend runs (4U this+644 > 0 =
 * MOT_BLEND). Not ported: 7/26 writes 0.6 to 4U this+0xd38 (this + 3072 + 312; earlier notes said 0xc78) every
 * frame: a body-bend input read by the model code 0x956bfc (vtable entry 0xe5c7f4, trig on it), GU twin not found. */
static void act_7_26(void *self, uint32_t var)
{
    switch (STEP(self)) {
    case 0:
        busy(self);
        setTargetMode(self, 0);
        set_mode(self, 0);
        setAttackId(self, 0);
        if (var == 1) { STEP(self) = 1; setMotion(self, 0x20a, 6.0f, 0.0f); return; }
        STEP(self) = 2;
        setMotion(self, 0x20b, 6.0f, 0.0f);
        hit(self, 0, 9, 8);
        hit(self, 1, 46, 16);
        return;
    case 1:
        if (mc(self, 2, 124.0f, 0.0f)) face(self, 132, 0);
        tar_drip(self, 14, 4, 6, 15.0f);
        if (!isMotionEnd(self)) return;
        STEP(self) = 3;
        setMotion(self, 0x20b, 0.0f, 116.0f);
        hit(self, 0, 9, 8);
        hit(self, 1, 46, 16);
        return;
    case 2:
        if (FIELD(float, self, MOT_BLEND) <= 0.0f && mc(self, 2, 40.0f, 0.0f)) face(self, 91, 0);
        tar_drip(self, 72, 3, 7, 93.0f);
        tar_drip(self, 1, 1, 7, 168.0f);
        if (var == 2) { if (mc(self, 1, 192.0f, 0.0f)) chain(self, 7, 55); return; }
        if (isMotionEnd(self)) act_end(self);
        return;
    default:
        if (mc(self, 2, 40.0f, 0.0f)) face(self, 91, 0);
        tar_drip(self, 72, 3, 7, 93.0f);
        tar_drip(self, 1, 1, 7, 168.0f);
        if (isMotionEnd(self)) act_end(self);
        return;
    }
}

/* 7/27 [4U 0x8bbf9c]: tail slam, motion 524 (6, 0), mode 0, attack id 0, slot 0 = 10, stopMove. Step 1:
 * turnToTarget 45 at offset 0xc000 from the kind-2 check of 60; window 16..50: forward speed 4.41176 (75/17)
 * rotated by the monster's angles (0x91150c, flags 1); the yaw turns 90 degrees in 136..170 (2.64706 per tick)
 * and 90 in 240..266 (3.46154 per tick); window 228..290: tar on part 2 and 0x8c34a0(0); ends at the motion end. */
static void act_7_27(void *self, uint32_t var)
{
    float f;
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        set_mode(self, 0);
        setAttackId(self, 0);
        setMotion(self, MOT_ATK_524, 6.0f, 0.0f);
        hit(self, 0, 10, 0);
        stopMove(self);
        return;
    }
    if (mc(self, 2, 60.0f, 0.0f)) face(self, 45, 0xc000);
    if (mc(self, 9, 16.0f, 50.0f)) lunge(self, 75.0f / 17.0f);
    f = 1.0f;
    if (motionCheck(self, 9, &f, 136.0f, 170.0f)) yaw_add(self, 90.0f / 34.0f, f);
    f = 1.0f;
    if (motionCheck(self, 9, &f, 240.0f, 266.0f)) yaw_add(self, 90.0f / 26.0f, f);
    if (mc(self, 3, 228.0f, 290.0f)) { tar_add(self, DT(self),2, 0); atk_shorten(self, 0); }
    static const drip_t k_d[] = {{142, 4, 7, 5}, {18, 4, 7, 30}, {72, 3, 6, 189}};
    tar_drips(self, k_d, 3);
    if (isMotionEnd(self)) act_end(self);
}

/* 7/32, 7/93 [4U 0x8bc5cc, r1 = 0/1]: take-off, rest pair (0x93d8a8 + 0x92e9d4), motion 607 (14, 0), 7/93: slot
 * 0 = 37; stopMove. Step 1, 7/93: vertical speed = speedFactor * K * window fraction rotated by the angles (flags
 * 0) in 260..296 (K -3.05556), 296..316 (-13), 316..344 (15/14), 344..390 (7.17391); slot 249 at the motion end.
 * 7/32 [0x8bc8b8..0x8bc97c]: findTargetEx(0, -1, 0x2000, 4) != -1, a map contact of wall type 4 or 5 this frame
 * (map_contact_45), owner W+0x1d9 and the kind-1 check of 310 not yet passed: inside 0..308 (kind 3) -> step 2
 * (chain 4/6 at the kind-1 check of 308, stopMove), else chain 4/6 + stopMove at once. */

/* the monster's map-contact list: 4U W+0x810 count (< 10) of 48-B records W+0x630 + 48 i, filled by 0x9185d8 from
 * the collision dispatcher 0x2ba7fc (after the polygon-info filler 0x2b95a4) = GU count rec+0x7a0, records
 * rec+0x5c0 + 48 i, filled by 0xa75f4 from the dispatcher 0x18285c (target type +0x1052 == 1 = enemy; after the
 * filler 0x1815a4): C. Record +5 = polygon attribute >> 24 (wall type) in both. */
#define REC_CONTACT_N   0x7a0
#define REC_CONTACT0    0x5c0
static int map_contact_45(void *self)
{
    uint8_t *rec = REC(self);
    uint32_t n = FIELD(uint8_t, rec, REC_CONTACT_N);
    for (uint32_t i = 0; i < n && i < 10; i++) {
        uint32_t t = rec[REC_CONTACT0 + 48 * i + 5];
        if (t == 4 || t == 5) return 1;
    }
    return 0;
}

static void act_7_32(void *self, uint32_t var)
{
    static const struct { float a, b, k; } win[] = {
        {260, 296, -3.05556f}, {296, 316, -13.0f}, {316, 344, 15.0f / 14.0f}, {344, 390, 7.17391f}};
    switch (STEP(self)) {
    case 0:
        begin(self);
        restApply(self, restValue(self));
        setMotion(self, 0x25f, 14.0f, 0.0f);
        if (var == 1) hit(self, 0, 37, 0);
        stopMove(self);
        return;
    case 1:
        /* drips 0x8bc6c4..0x8bc8a8 (4U order, var 0 = 7/32, 1 = 7/93) */
        if (var) { tar_drip(self, 72, 3, 7, 120.0f); tar_drip(self, 62, 2, 7, 120.0f); }
        tar_drip(self, 72, 3, 7, 135.0f); tar_drip(self, 62, 2, 7, 135.0f);
        if (!var) { tar_drip(self, 2, 1, 7, 115.0f); tar_drip(self, 2, 1, 7, 130.0f); }
        tar_drip(self, 72, 3, 7, 152.0f); tar_drip(self, 62, 2, 7, 152.0f);
        tar_drip(self, 72, 3, 7, 167.0f); tar_drip(self, 62, 2, 7, 167.0f);
        tar_drip(self, 72, 3, 7, 182.0f); tar_drip(self, 62, 2, 7, 182.0f);
        if (var) { tar_drip(self, 72, 3, 7, 207.0f); tar_drip(self, 62, 2, 7, 207.0f); }
        else {
            tar_drip(self, 2, 1, 7, 147.0f); tar_drip(self, 2, 1, 7, 162.0f);
            tar_drip(self, 2, 1, 7, 177.0f); tar_drip(self, 2, 1, 7, 192.0f);
        }
        if (var == 1)
            for (uint32_t i = 0; i < sizeof win / sizeof win[0]; i++) {
                float f = 1.0f;
                if (motionCheck(self, 9, &f, win[i].a, win[i].b)) rise(self, speedFactor(self) * win[i].k * f);
            }
        if (var == 0 && findTargetEx(self, 0, 0xffffffffu, 0x2000, 4) != -1 && map_contact_45(self) &&
            FIELD(uint8_t, self, EN_CONTROLLED) && !mc(self, 1, 310.0f, 0.0f)) {
            static uint32_t s_n;
            int early = mc(self, 3, 0.0f, 308.0f);
            if (++s_n <= 20) logf("gogport: em089 7/32 interrupted by a type-4/5 map contact (%s)", early ? "step 2" : "4/6 now");
            if (early) { STEP(self)++; return; }          /* [0x8bcb58]: inside 0..308 -> step 2 (4/6 at 308) */
            chain(self, 4, 6); stopMove(self);             /* [0x8bc634] */
            return;
        }
        if (isMotionEnd(self)) act_end6(self);
        return;
    default:
        if (mc(self, 1, 308.0f, 0.0f)) { chain(self, 4, 6); stopMove(self); }
        return;
    }
}

/* 7/45, 7/60, 7/62, 7/64, 7/66 [4U 0x8bcbb8, r1 = 0..4]: dash start, motion 535 (6, 0), mode 0, attack id 0.
 * Step 1: turnToTarget 182 from the kind-2 check of 116; when this machine controls the monster (W+0x1d9 = GU
 * this+0x7420) chain the dash 7/47, 7/61, 7/63, 7/65, 7/67 at the kind-1 check of 186; otherwise step 2 at the
 * motion end, where it waits for control. */
static void act_7_45(void *self, uint32_t var)
{
    static const uint8_t next[5] = {47, 61, 63, 65, 67};
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, 0x217, 6.0f, 0.0f);
        set_mode(self, 0);
        setAttackId(self, 0);
        return;
    }
    int owner = FIELD(uint8_t, self, EN_CONTROLLED) != 0;
    if (STEP(self) == 2) { if (owner) chain(self, 7, next[var]); return; }
    if (mc(self, 2, 116.0f, 0.0f)) face(self, 182, 0);
    tar_drip(self, 71, 3, 7, 32.0f);
    tar_drip(self, 61, 2, 7, 54.0f);
    if (owner) { if (mc(self, 1, 186.0f, 0.0f)) chain(self, 7, next[var]); return; }
    if (isMotionEnd(self)) STEP(self)++;
}

/* 7/47, 7/61, 7/63, 7/65, 7/67 [4U 0x8bcdd4, r1 = 0..4]: tar dash, motion 536 (14, 0), W+0x145 = 0,
 * setStopDist(0, 0), slot 0 = 15 (3), mode 0, attack id 0, timer W+468 = 9999. Step 1: turnToTarget
 * (u16)(91 * fraction) / 2 in window 80..504; the dash ends when inRange(0, 0) (also steering), the motion end or
 * the timer; then step 2 with the stop motion 537 (blend 20 in dash frames 0..121 / 170..217, else 6);
 * step 2: re-arm reset of slot 0 at frame 80, end at the motion end. The entry [0x8bceb4..0x8bcf20] sets no target:
 * the dash runs at whatever slot 0 holds (the hunter, or the EMC arena point of g1 s101..s104).
 * Wall probe (below): ahead of the monster; on a facing wall of the variant's type it zeroes the timer, stores the
 * wall type in work+0xda (F_HEADING) and, for types 2 / 3, W+0x145 = 1; when the dash then ends with the timer
 * already out (and the monster is controlled here) it chains a turn 1/22, 1/23, 1/33 or 1/34 by the dash frame. */

/* 4U 0x2b9cd4(col *0x10574fc, owner, from, to, s0 y offset, area, pos out, normal out, info out, mask) = GU
 * 0x1835b8(col *0x21270e0, owner, from, to, s0, area, pos out, normal out, info out, mask) (S/C: same prologue
 * (normalise with epsilon, extend, add s0 to both y), same core: 4U 0x2b9904 = GU 0x182f70 (pos / normal / info
 * out pointers [r11+8 / +0xc / +0x10], area as 1 << area), info filler 4U 0x2b95a4 = GU 0x1815a4: info +0..+5 =
 * polygon attribute bit fields, +5 = attribute >> 24 (wall type) in both; the face normal (0x183240 / 0xcd3684) at
 * info +0x18 (4U) / +0x20 (GU), z at +0x20 / +0x28). C for the GU layout (read from 0x1815a4). */
typedef uint32_t (*map_sweep_t)(void *col, void *owner, const float *from, const float *to, float yoff, uint32_t area,
                                float *pos_out, float *normal_out, uint8_t *info_out, uint32_t mask);
#define mapSweep   FN(map_sweep_t, 0x1835b8)
#define COL_MGR_GU (*(void **)MAIN(0x21270e0))
#define EN_AREA_BYTE 0x1054

/* 4U 7/47 step 1 probe [0x8bcfac..0x8bd26c]: to = pos + yaw-rotated (0, 0, speedFactor * 1567), s0 10, area,
 * mask 0x3fff0000; on a hit: normal angle n = atan2(nx, nz); accept when |n + 0x8000 - yaw| < (u16)(0.5 + deg *
 * 65536 / 360) with deg 50 (variant 0) or 60; wall type t = info +5 by variant: 0: 2..5, 1: 5 / 2, 2: 3, 3: 4,
 * 4: 2 / 5; then timer = 0, work+0xda = t for 2 / 3 (and W+0x145 = 1), 4 for 4, else 5, and r6 = 1 [0x8bd214]
 * (returned: the same frame then takes the turn chain). Wall type = attribute index 0 = SBC group word 1 >> 24
 * (4U 0xcd4064 / GU 0xc1c2fc read [col+0x48][poly] + 48 + 4; m19a03d-a-w00: the high platform face z 3400..3403
 * is type 5, the skin in front of it at z 3301..3307 and the plain walls type 0). */
static int wall_probe(void *self, uint32_t var)
{
    static uint32_t s_n, s_acc;
    void *col = COL_MGR_GU;
    if (!col) return 0;
    uint8_t *rec = REC(self);
    const float *p = &FIELD(float, rec, REC_POS_X);
    uint32_t yaw = FIELD(uint32_t, rec, REC_YAW) & 0xffff;
    float a = (float)yaw * (6.28318531f / 65536.0f), d = speedFactor(self) * 1567.0f;
    float from[4] = {p[0], p[1], p[2], 0.0f};
    float to[4] = {p[0] + sinf_gu(a) * d, p[1], p[2] + cosf_gu(a) * d, 0.0f};
    float pos[4] = {0}, nrm[4] = {0};
    uint8_t info[0x60] = {0};
    if (!mapSweep(col, self, from, to, 10.0f, FIELD(uint8_t, self, EN_AREA_BYTE), pos, nrm, info, 0x3fff0000u)) return 0;
    float nx = FIELD(float, info, 0x20), nz = FIELD(float, info, 0x28);
    uint32_t n = (uint32_t)(int32_t)(atan2f_gu(nx, nz) * 10430.378f + 0.5f) & 0xffff;
    uint32_t diff = (n + 0x8000u - yaw) & 0xffff;
    uint32_t thr = (uint32_t)(0.5f + (var == 0 ? 50.0f : 60.0f) * 65536.0f * (1.0f / 360.0f)) & 0xffff;
    uint32_t t = info[5];
    if (!(thr > diff || diff > ((0x10000u - thr) & 0xffff))) return 0;
    int ok = var == 0 ? (t >= 2 && t <= 5) : var == 1 ? (t == 5 || t == 2) : var == 2 ? t == 3 : var == 3 ? t == 4
           : (t == 2 || t == 5);
    /* separate caps: test 5's 30 lines were all spent on var-0 type-0 hits before the high-ground loop */
    if (ok ? ++s_acc <= 30 : ++s_n <= 30)
        logf("gogport: em089 7/47 wall probe: type %u diff %x (var %u) %s at %d %d", t, diff, var, ok ? "-> stop" : "ignored",
             (int32_t)pos[0], (int32_t)pos[2]);
    if (!ok) return 0;
    TIMER(self) = 0.0f;
    if (t == 2 || t == 3) { STEP1(self) = 1; FIELD(uint8_t, self, F_HEADING) = (uint8_t)t; }
    else FIELD(uint8_t, self, F_HEADING) = t == 4 ? 4 : 5;
    return 1;
}

static void act_7_47(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        STEP1(self) = 0;
        setTargetMode(self, 0);
        setMotion(self, 0x218, 14.0f, 0.0f);
        sync_target(self);
        setStopDist(self, 0, 0, 0.0f);
        hit(self, 0, 15, 3);
        set_mode(self, 0);
        setAttackId(self, 0);
        TIMER(self) = 9999.0f;
        return;
    }
    if (STEP(self) == 2) {
        if (at_frame(self, 80.0f)) {
#ifdef EM089_ATTACK_HIT
            attackFlag(self, 0);
#endif
        }
        tar_drip(self, 71, 3, 7, 15.0f);
        tar_drip(self, 61, 2, 7, 30.0f);
        if (isMotionEnd(self)) act_end(self);
        return;
    }
    float f = 1.0f;
    if (motionCheck(self, 9, &f, 80.0f, 504.0f)) face(self, (uint32_t)((float)((uint32_t)(91.0f * f) & 0xffff) * 0.5f) & 0xffff, 0);
    /* 4U r6: timer already out [0x8bcf94] or the probe accepted a wall this frame [0x8bd214] (the port read only
     * the first, so a wall hit took the stop motion instead of the turn) */
    int expired = TIMER(self) <= 0.0f;
    if (!expired && wall_probe(self, var)) expired = 1;
    tar_drip(self, 71, 3, 7, 20.0f);
    tar_drip(self, 61, 2, 7, 40.0f);
    sync_target(self);   /* no-op while slot 0 holds an EMC arena point (F_NOSYNC 2): 4U 7/47 sets no target */
    int in = inRange(self, 0, 0), end = !in && isMotionEnd(self);
    if (!in && !end && !timerDown(self, &TIMER(self), 1.0f)) return;
    float fr = motionFrame(self);   /* 4U this+656 */
    {
        static uint32_t s_n;
        const float *d = (const float *)(REC(self) + REC_TARGET);
        if (++s_n <= 40)
            logf("gogport: em089 7/%u dash end: %s at %d %d frame %d, dest %d %d (%s)", FIELD(uint8_t, self, EN_ACT_NUM),
                 in ? "in range" : end ? "motion end" : expired ? "wall" : "timer", (int32_t)FIELD(float, REC(self), REC_POS_X),
                 (int32_t)FIELD(float, REC(self), REC_POS_Z), (int32_t)fr, (int32_t)d[0], (int32_t)d[2],
                 FIELD(uint8_t, self, F_NOSYNC) == 2 ? "arena point" : "hunter");
    }
    if (expired && FIELD(uint8_t, self, EN_CONTROLLED)) {
        /* [0x8bd2f0..0x8bd428] turn chain by the dash frame (float-bit range tests): 152..178 / 230..252 / other
         * -> 1/22 (1/33 with W+0x145), [0, 152) / (178, 230) -> 1/23 (1/34) */
        int side = (fr >= 0.0f && fr < 152.0f) || (fr > 178.0f && fr < 230.0f);
        uint32_t n = STEP1(self) ? (side ? 34 : 33) : (side ? 23 : 22);
        static uint32_t s_n;
        if (++s_n <= 20) logf("gogport: em089 7/47 wall turn -> 1/%u (frame %d, W+0x145 %u)", n, (int32_t)fr, STEP1(self));
        chain(self, 1, n);
        return;
    }
    STEP(self)++;
    /* [0x8bd42c..0x8bd48c] stop motion blend 20 in frames 0..121 and 170..217, else 6 */
    setMotion(self, 0x219, ((fr >= 0.0f && fr <= 121.0f) || (fr >= 170.0f && fr <= 217.0f)) ? 20.0f : 6.0f, 0.0f);
}

/* 7/105 [4U 0x8bdd2c]: tar breath down, motion 577 (6, 0), mode 0, attack id 0. Step 1: turnToTarget 0x111 in
 * window 40..100; step 2 from frame 160; step 2: tar on part 0 in window 160..280, end at the motion end.
 * Not ported: the pitch aim layer (joint 3 -> target pitch, clamped 30 degrees, 0x9200a4(0x26b, ..) at entry,
 * 0xb052d8 / 0xb054e0 at frame 158). At frame 160 the breath attack shell 0x6620c4 = em089_shell016_post: 53 when
 * the aim-layer weight (0xb052d8) is 0, else 36. */
static void act_7_105(void *self, uint32_t var)
{
    (void)var;
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, 0x241, 6.0f, 0.0f);
        set_mode(self, 0);
        setAttackId(self, 0);
        em089_aim_start(self, EM089_AIM_PITCH_UP);
        return;
    case 1:
        if (mc(self, 3, 40.0f, 100.0f)) face(self, 0x111, 0);
        if (at_frame(self, 158.0f)) em089_aim_update(self, EM089_AIM_PITCH_UP);
        if (at_frame(self, 160.0f)) {   /* [0x8be078..0x8be138]: step 2, attack shell by the aim-layer weight */
            STEP(self)++;
            em089_shell016_post(self, em089_aim_weight(self) == 0.0f ? 53 : 36, 0);
        }
        tar_drip(self, 72, 3, 7, 35.0f);
        tar_drip(self, 62, 2, 7, 50.0f);
        tar_drip(self, 4, 0, 6, 59.0f);
        return;
    default:
        if (mc(self, 3, 160.0f, 280.0f)) tar_add(self, DT(self),0, 0);
        if (isMotionEnd(self)) act_end(self);
        return;
    }
}

/* 7/106 [4U 0x8be1a8]: tar breath sweep, motion 578 (6, 0), motion speed 0.8, mode 0, attack id 0. Step 1: speed
 * 1.0 at frame 320; turnToTarget 65 in window 80..206; step 2 at frame 350 (effect post 37 skipped); step 2: tar
 * on part 0 in window 352..470, end at the motion end. */
static void act_7_106(void *self, uint32_t var)
{
    (void)var;
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, 0x242, 6.0f, 0.0f);
        setMotionSpeed(self, 0.8f);
        set_mode(self, 0);
        setAttackId(self, 0);
        return;
    case 1:
        if (at_frame(self, 320.0f)) setMotionSpeed(self, 1.0f);
        if (mc(self, 9, 80.0f, 206.0f)) face(self, 65, 0);
        if (at_frame(self, 350.0f)) { STEP(self)++; em089_shell016_post(self, 37, 0); }   /* [0x8be354..0x8be3c8] */
        tar_drip(self, 4, 0, 6, 20.0f);
        return;
    default:
        if (mc(self, 3, 352.0f, 470.0f)) tar_add(self, DT(self),0, 0);
        tar_drip(self, 14, 4, 7, 185.0f);
        tar_drip(self, 18, 2, 7, 280.0f);
        if (isMotionEnd(self)) act_end(self);
        return;
    }
}

/* 7/107, 7/110, 7/120, 7/129 [4U 0x8be434, r1 = 0..3]: tar breath. 7/107: motion 575 (6, 0), mode 0, attack id 0,
 * then at its end motion 583 from frame 220 (0, 220); the others start motion 583 directly ((6, 0) / (0, 204) /
 * (0, 220)) with mode 1, attack id 1, step 2. Step 2: step 3 at frame 240 or the motion end (effect post 41
 * skipped); step 3: tar on part 0 in window 240..390, end at the motion end.
 * Not ported: 7/110's aim layers (0x92d0d4 at the kind-2 check of 250, 0x918e80 yaw-to-target / 20, 0x935ff0
 * motions 597 / 598 with this+656 and W+916): the sweep does not follow the hunter. */
static void act_7_107(void *self, uint32_t var)
{
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 0);
        if (var == 0) { setMotion(self, 0x23f, 6.0f, 0.0f); set_mode(self, 0); setAttackId(self, 0); return; }
        setMotion(self, 0x247, var == 1 ? 6.0f : 0.0f, var == 1 ? 0.0f : var == 2 ? 204.0f : 220.0f);
        set_mode(self, 1);
        setAttackId(self, 1);
        STEP(self) = 2;
        if (var == 1) em089_aim_start(self, EM089_AIM_YAW);
        return;
    case 1:
        if (var != 0) { STEP(self) = 2; return; }
        if (isMotionEnd(self)) {
            setMotion(self, 0x247, 0.0f, 220.0f);
            STEP(self)++;
        }
        tar_drip(self, 71, 3, 7, 29.0f);
        tar_drip(self, 7, 2, 7, 100.0f);
        tar_drip(self, 4, 0, 6, 20.0f);
        return;
    case 2:
        if (var == 1) em089_aim_update(self, EM089_AIM_YAW);
        if (at_frame(self, 240.0f) || isMotionEnd(self)) {   /* [0x8be750..0x8be84c], every variant */
            STEP(self)++;
            em089_shell016_post(self, 41, 0);
        }
        return;
    default:
        if (mc(self, 3, 240.0f, 390.0f)) tar_add(self, DT(self),0, 0);
        if (var == 1) em089_aim_update(self, EM089_AIM_YAW_HOLD);
        if (isMotionEnd(self)) act_end(self);
        if (var == 1) {
            tar_drip(self, 61, 2, 7, 150.0f);
            tar_drip(self, 71, 3, 7, 150.0f);
            tar_drip(self, 4, 0, 6, 125.0f);
        }
        return;
    }
}

/* 7/126 [4U 0x8bfe80]: flying breath, mode 1, attack id 1, motion 592 (6, 0). Step 1: step 2 at frame 240
 * (effect post 41 skipped); step 2: tar on part 0 in window 240..390, at the motion end motion 583 from frame
 * 430, step 3; step 3: end at the motion end. */
static void act_7_126(void *self, uint32_t var)
{
    (void)var;
    switch (STEP(self)) {
    case 0:
        busy(self);
        set_mode(self, 1);
        setAttackId(self, 1);
        STEP(self)++;
        setTargetMode(self, 0);
        setMotion(self, 0x250, 6.0f, 0.0f);
        return;
    case 1:
        if (at_frame(self, 240.0f)) { STEP(self)++; em089_shell016_post(self, 41, 0); }   /* [0x8bff50..0x8bffcc] */
        return;
    case 2:
        if (mc(self, 3, 240.0f, 390.0f)) tar_add(self, DT(self),0, 0);
        if (!isMotionEnd(self)) return;
        setMotion(self, 0x247, 0.0f, 430.0f);
        STEP(self)++;
        return;
    default:
        if (isMotionEnd(self)) act_end(self);
        return;
    }
}

/* 7/133 [4U 0x8c0090]: motion 618 (6, 0), mode 1, attack id 1, slot 0 = 38, slot 1 = 39; frame 300: slot 0 = 40,
 * slot 1 = 41; the yaw turns -2.25 degrees per tick in window 360..400; at the motion end setTargetMode(0) +
 * setActionW(1, 20) + thinkRequest(0). Not ported: the render flag this+0xca8 (as 7/19). */
static void act_7_133(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, 0x26a, 6.0f, 0.0f);
        set_mode(self, 1);
        setAttackId(self, 1);
        hit(self, 0, 38, 0);
        hit(self, 1, 39, 0);
        return;
    }
    tar_drip(self, 142, 4, 7, 20.0f);
    tar_drip(self, 62, 2, 7, 150.0f);
    tar_drip(self, 2, 1, 6, 283.0f);
    if (at_frame(self, 300.0f)) { hit(self, 0, 40, 0); hit(self, 1, 41, 0); }
    float f = 1.0f;
    if (motionCheck(self, 9, &f, 360.0f, 400.0f)) yaw_add(self, 2.25f, -f);
    if (isMotionEnd(self)) end_1_20(self);
}

/* 7/135 [4U 0x8c02b0]: flying breath down, mode 1, attack id 1, motion 638 (4, 0). Step 1: step 2 at frame 240
 * (effect post 41 skipped); step 2: tar on part 0 in window 240..390, end at the motion end.
 * Not ported: the pitch aim layer (joint 3 -> target + 100 up, clamped 45 degrees: 0x9200a4(0x27f, ..) at entry,
 * 0xb052d8 / 0xb054e0 at frame 238). */
static void act_7_135(void *self, uint32_t var)
{
    (void)var;
    switch (STEP(self)) {
    case 0:
        busy(self);
        set_mode(self, 1);
        setAttackId(self, 1);
        STEP(self)++;
        setTargetMode(self, 0);
        setMotion(self, 0x27e, 4.0f, 0.0f);
        em089_aim_start(self, EM089_AIM_PITCH_DOWN);
        return;
    case 1:
        if (at_frame(self, 238.0f)) em089_aim_update(self, EM089_AIM_PITCH_DOWN);
        if (at_frame(self, 240.0f)) { STEP(self)++; em089_shell016_post(self, 41, 0); }   /* [0x8c05a4..0x8c0620] */
        return;
    default:
        if (mc(self, 3, 240.0f, 390.0f)) tar_add(self, DT(self),0, 0);
        tar_drip(self, 72, 3, 7, 230.0f);
        tar_drip(self, 62, 2, 7, 310.0f);
        tar_drip(self, 4, 0, 6, 121.0f);
        if (isMotionEnd(self)) act_end(self);
        return;
    }
}

/* 7/136, 7/137 [4U 0x8be910, r1 = 4/5 (only variants used)]: sweeping breath, motion 613 / 614 (6, 0), mode 1,
 * attack id 1. Step 1: tar on part 0 in window 238..498 (effect post 51 at frame 238 skipped); the yaw turns
 * +0.75 degrees per tick in window 0..80 and -15/19 in 680..756 (signs swapped for 7/137); end at the motion end. */
static void act_7_136(void *self, uint32_t var)
{
    float f, sign = var == 5 ? -1.0f : 1.0f;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, var == 5 ? 0x266 : 0x265, 6.0f, 0.0f);
        set_mode(self, 1);
        setAttackId(self, 1);
        return;
    }
    if ((var == 4 || var == 5) && at_frame(self, 238.0f)) em089_shell016_post(self, 51, 0);   /* [0x8bea5c..0x8beac8] */
    if (mc(self, 3, 238.0f, 498.0f)) tar_add(self, DT(self),0, 0);
    f = 1.0f;
    if (motionCheck(self, 9, &f, 0.0f, 80.0f)) yaw_add(self, 0.75f, sign * f);
    f = 1.0f;
    if (motionCheck(self, 9, &f, 680.0f, 756.0f)) yaw_add(self, 15.0f / 19.0f, -sign * f);
    if (isMotionEnd(self)) act_end(self);
    if (var == 5) tar_drip(self, 72, 3, 7, 44.0f);
    else if (var == 4) tar_drip(self, 62, 2, 7, 44.0f);
    if (var == 4 || var == 5) tar_drip(self, 2, 1, 7, 132.0f);
}

/* 7/138 [4U 0x8c0680]: tar bombardment, mode 1, attack id 1, motion 632 (0, 0); ends at the motion end.
 * Step 1: 7 tar shots 0x8c9dd4(joint, frame, spread) (tar_shot, frames x2 inside), then the motion end. */
static void act_7_138(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        busy(self);
        set_mode(self, 1);
        setAttackId(self, 1);
        STEP(self)++;
        setTargetMode(self, 0);
        setMotion(self, 0x278, 0.0f, 0.0f);
        return;
    }
    tar_shot(self, 4, 107.0f, 2000.0f);
    tar_shot(self, 2, 118.0f, 0.0f);
    tar_shot(self, 60, 132.0f, 2000.0f);
    tar_shot(self, 60, 159.0f, 0.0f);
    tar_shot(self, 71, 163.0f, 2000.0f);
    tar_shot(self, 4, 175.0f, 2000.0f);
    tar_shot(self, 4, 178.0f, 2000.0f);
    if (isMotionEnd(self)) act_end(self);
}

/* 7/139 [4U 0x8c07d8]: tail slam (mirror of 7/27), motion 636 (6, 0), mode 0, attack id 0, slot 0 = 45. Step 1:
 * turnToTarget 45 at offset 0xc000 from the kind-2 check of 60; the yaw turns -90 degrees in 136..170 and -90 in
 * 240..266; window 228..290: tar on part 3 and 0x8c34a0(0); ends at the motion end. */
static void act_7_139(void *self, uint32_t var)
{
    float f;
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        set_mode(self, 0);
        setAttackId(self, 0);
        setMotion(self, 0x27c, 6.0f, 0.0f);
        hit(self, 0, 45, 0);
        return;
    }
    if (mc(self, 2, 60.0f, 0.0f)) face(self, 45, 0xc000);
    f = 1.0f;
    if (motionCheck(self, 9, &f, 136.0f, 170.0f)) yaw_add(self, 90.0f / 34.0f, -f);
    f = 1.0f;
    if (motionCheck(self, 9, &f, 240.0f, 266.0f)) yaw_add(self, 90.0f / 26.0f, -f);
    if (mc(self, 3, 228.0f, 290.0f)) { tar_add(self, DT(self),3, 0); atk_shorten(self, 0); }
    tar_drip(self, 142, 4, 7, 10.0f);
    tar_drip(self, 14, 4, 7, 25.0f);
    tar_drip(self, 62, 2, 6, 194.0f);
    if (isMotionEnd(self)) act_end(self);
}

/* 7/140, 7/141 [4U 0x8c0a64, r1 = 0/1]: flying tail slam, mode 1, attack id 1, motion 616 / 617 (6, 0), slot 0 =
 * 44 / 43. Step 1: window 250..350: tar on part 3 (7/141: part 2) and 0x8c34a0(0); end at the motion end. */
static void act_7_140(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        busy(self);
        set_mode(self, 1);
        setAttackId(self, 1);
        STEP(self)++;
        setTargetMode(self, 0);
        setMotion(self, var ? 0x269 : 0x268, 6.0f, 0.0f);
        hit(self, 0, var ? 43 : 44, 0);
        return;
    }
    if (mc(self, 3, 250.0f, 350.0f)) { tar_add(self, DT(self),var ? 2 : 3, 0); atk_shorten(self, 0); }
    tar_drip(self, var ? 62 : 72, var ? 2 : 3, 7, 106.0f);
    tar_drip(self, 4, 0, 6, 111.0f);
    if (isMotionEnd(self)) act_end(self);
}

/* 7/142 [4U 0x8c0c70]: tar rain (flying), setTargetMode(3), motion 620 (14, 0), stopMove; slot 249 at the motion
 * end. Step 1: 13 tar shots and 12 drips (any tar mode), in the 4U call order (it drives the shell rand index). */
static void act_7_142(void *self, uint32_t var)
{
    static const drip_t k_d0[] = {{74, 3, 7, 66}, {75, 3, 7, 66}};
    static const drip_t k_d1[] = {{64, 2, 7, 124}, {65, 2, 7, 124}, {74, 3, 7, 163}, {75, 3, 7, 163}};
    static const drip_t k_d2[] = {{64, 2, 7, 216}, {65, 2, 7, 216}, {2, 1, 7, 70}, {2, 1, 7, 115}, {2, 1, 7, 165},
                                  {2, 1, 7, 210}};
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 3);
        setMotion(self, 0x26c, 14.0f, 0.0f);
        stopMove(self);
        return;
    }
    tar_shot(self, 4, 41.0f, 2000.0f);
    tar_shot(self, 4, 70.0f, 2000.0f);
    tar_shot(self, 3, 115.0f, 2000.0f);
    tar_shot(self, 3, 165.0f, 0.0f);
    tar_shot(self, 3, 210.0f, 2000.0f);
    tar_drips(self, k_d0, 2);
    tar_shot(self, 64, 71.0f, 2000.0f);
    tar_shot(self, 65, 71.0f, 2000.0f);
    tar_shot(self, 74, 118.0f, 2000.0f);
    tar_shot(self, 75, 118.0f, 2000.0f);
    tar_drips(self, k_d1, 4);
    tar_shot(self, 64, 169.0f, 2000.0f);
    tar_shot(self, 65, 169.0f, 0.0f);
    tar_shot(self, 74, 208.0f, 2000.0f);
    tar_shot(self, 75, 208.0f, 2000.0f);
    tar_drips(self, k_d2, 6);
    if (isMotionEnd(self)) act_end6(self);
}

/* 7/143, 7/147, 7/148 [4U 0x8c1300, r1 = 0/1/2]: hover attack, setTargetMode 3 (7/148: 1; 7/147: rest pair, which
 * sets mode 1), motion 621 (14, 0), stopMove. Step 1 (7/147, 7/148): vertical speed = speedFactor * 150/59 in
 * window 0..118 and * -30/7 in 410..480, rotated by the angles (flags 0); effect post 54 at frame 218 skipped;
 * slot 249 at the motion end. */
static void act_7_143(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        begin(self);
        if (var == 0) setTargetMode(self, 3);
        else if (var == 2) setTargetMode(self, 1);
        else restApply(self, restValue(self));
        setMotion(self, 0x26d, 14.0f, 0.0f);
        stopMove(self);
        return;
    }
    if (var != 0 && mc(self, 9, 0.0f, 118.0f)) rise(self, speedFactor(self) * (150.0f / 59.0f));
    if (at_frame(self, 218.0f)) em089_shell016_post(self, 54, 0);   /* [0x8c1474..0x8c14e0], every variant */
    if (var != 0 && mc(self, 9, 410.0f, 480.0f)) rise(self, speedFactor(self) * (-30.0f / 7.0f));
    static const drip_t k_d[] = {{74, 3, 7, 69}, {64, 2, 7, 69}, {74, 3, 7, 117}, {64, 2, 7, 117}, {74, 3, 7, 187},
                                 {64, 2, 7, 187}, {2, 1, 7, 57}, {2, 1, 7, 107}};
    tar_drips(self, k_d, 8);
    if (isMotionEnd(self)) act_end6(self);
}

/* 7/144, 7/145 [4U 0x8c1630, r1 = 0/1]: as 7/140 with motions 605 / 606 (6, 0), slot 0 = 44 / 43, tar window
 * 318..380 on part 3 (7/145: part 2) */
static void act_7_144(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        busy(self);
        set_mode(self, 1);
        setAttackId(self, 1);
        STEP(self)++;
        setTargetMode(self, 0);
        setMotion(self, var ? 0x25e : 0x25d, 6.0f, 0.0f);
        hit(self, 0, var ? 43 : 44, 0);
        return;
    }
    if (mc(self, 3, 318.0f, 380.0f)) { tar_add(self, DT(self),var ? 2 : 3, 0); atk_shorten(self, 0); }
    if (isMotionEnd(self)) act_end(self);
}

/* 7/146 [4U 0x8c17bc]: long flying charge, setTargetMode(3), motion 623 (14, 0), resetVel. Step 1: six movement
 * windows (resetVel, then forward z / side x = speedFactor * k * window fraction, rotated by the angles, flags 1)
 * and nine yaw windows (degrees per tick); motion speed 0.95 inside 600..1300, else 1.0; at the motion end the
 * em089 latch work+0xd9 = 1 (read by AI condition 27) and slot 249. Effect posts 52/55/56 at frame 572 skipped. */
static void act_7_146(void *self, uint32_t var)
{
    static const struct { float a, b, kz, kx; } mv[] = {
        {20, 100, -5.375f, 0}, {120, 210, 8.55556f, -6.77778f}, {240, 300, 17.8333f, 0.6f},
        {320, 370, 15.0f, -2.0f}, {380, 420, 18.25f, -0.5f}, {440, 480, 8.45f, 4.875f}};
    static const struct { float a, b, deg; } yw[] = {
        {210, 240, 2.66667f}, {300, 320, 4.5f}, {370, 380, 8.0f}, {420, 440, 4.0f}, {480, 500, 1.5f},
        {890, 950, -3.0f}, {1000, 1050, 3.6f}, {1070, 1130, 3.0f}, {1150, 1250, -1.8f}};
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 3);
        setMotion(self, 0x26f, 14.0f, 0.0f);
        resetVel(self);
        return;
    }
    for (uint32_t i = 0; i < sizeof mv / sizeof mv[0]; i++) {
        float f = 1.0f;
        if (!motionCheck(self, 9, &f, mv[i].a, mv[i].b)) continue;
        resetVel(self);
        float s = speedFactor(self) * f;
        FIELD(float, REC(self), REC_VEL + 8) = s * mv[i].kz;
        if (mv[i].kx != 0.0f) FIELD(float, REC(self), REC_VEL) = s * mv[i].kx;
        rotateVel(self, REC(self) + REC_ANGLES, 1);
    }
    for (uint32_t i = 0; i < sizeof yw / sizeof yw[0]; i++) {
        float f = 1.0f;
        if (motionCheck(self, 9, &f, yw[i].a, yw[i].b)) yaw_add(self, yw[i].deg, f);
    }
    static const drip_t k_d[] = {   /* 4U 0x8c1ef0..0x8c22fc */
        {74, 3, 7, 69}, {64, 2, 7, 69}, {74, 3, 7, 117}, {64, 2, 7, 117}, {74, 3, 7, 167}, {64, 2, 7, 167},
        {74, 3, 7, 194}, {64, 2, 7, 194}, {74, 3, 7, 230}, {64, 2, 7, 230}, {2, 1, 7, 57}, {2, 1, 7, 107},
        {2, 1, 7, 150}, {2, 1, 7, 190}, {74, 3, 7, 290}, {64, 2, 7, 290}, {74, 3, 7, 350}, {64, 2, 7, 350},
        {74, 3, 7, 417}, {64, 2, 7, 417}, {74, 3, 7, 483}, {64, 2, 7, 483}, {74, 3, 7, 523}, {64, 2, 7, 523},
        {74, 3, 7, 562}, {64, 2, 7, 562}, {74, 3, 7, 602}, {64, 2, 7, 602}, {74, 3, 7, 640}, {64, 2, 7, 640},
        {74, 3, 7, 706}, {64, 2, 7, 706}, {74, 3, 7, 751}, {64, 2, 7, 751}, {74, 3, 7, 798}, {64, 2, 7, 798},
        {141, 4, 7, 469}, {141, 4, 7, 568}};
    tar_drips(self, k_d, sizeof k_d / sizeof k_d[0]);
    if (at_frame(self, 572.0f)) {   /* [0x8c2300..0x8c248c]: the finale shell by action serial (W+0x1d2) % 3 */
        uint32_t r = FIELD(uint16_t, self, EN_ACT_SERIAL) % 3;
        em089_shell016_post(self, r == 1 ? 55 : r == 2 ? 56 : 52, 0);
    }
    setMotionSpeed(self, mc(self, 3, 600.0f, 1300.0f) ? 0.95f : 1.0f);
    if (isMotionEnd(self)) { FIELD(uint8_t, self, F_LATCH_D9) = 1; act_end6(self); }
}

/* 7/109 [4U 0x8bed30]: tar jump (flying), motion 582 (8, 0), mode 1, attack id 1, slot 0 = 27 (8), slot 1 = 28
 * (16); aim point = lead point (distance / 2.5 + 175), rate = angle / 54 (cap 118 at 35 degrees). Step 1 -> 2 at
 * once; step 2: aim turn in window 10..64; frame 295: slot 0 = 50 (16), slot 1 = 51 (16); ends at the motion end. */
static void act_7_109(void *self, uint32_t var)
{
    (void)var;
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, 0x246, 8.0f, 0.0f);
        set_mode(self, 1);
        setAttackId(self, 1);
        hit(self, 0, 27, 8);
        hit(self, 1, 28, 16);
        aim_setup(self, target_dist(self) / 2.5f + 175.0f, 0x18e4, 1.0f / 54.0f, 118);
        return;
    case 1:
        STEP(self) = 2;
        return;
    default:
        aim_turn(self, 10.0f, 64.0f, 0);
        if (at_frame(self, 295.0f)) { hit(self, 0, 50, 16); hit(self, 1, 51, 16); }
        tar_drip(self, 1, 1, 7, 5.0f);
        tar_drip(self, 140, 4, 7, 33.0f);
        tar_drip(self, 2, 1, 7, 60.0f);
        if (isMotionEnd(self)) act_end(self);
        return;
    }
}

/* 7/112 [4U 0x8bf060]: motion 579 (6, 0), mode 0, attack id 0, slot 0 = 29; window 166..228: tar on part 2 and
 * 0x8c34a0(0); ends at the motion end */
static void act_7_112(void *self, uint32_t var)
{
    (void)var;
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, 0x243, 6.0f, 0.0f);
        set_mode(self, 0);
        setAttackId(self, 0);
        hit(self, 0, 29, 0);
        return;
    }
    if (mc(self, 3, 166.0f, 228.0f)) { tar_add(self, DT(self),2, 0); atk_shorten(self, 0); }
    tar_drip(self, 61, 2, 7, 10.0f);
    tar_drip(self, 71, 3, 7, 40.0f);
    if (isMotionEnd(self)) act_end(self);
}

/* 7/114, 7/115 [4U 0x8bf19c, r1 = 0/1]: flying tar breath, motion 601 / 602 (4, 0), mode 1, attack id 1; turn rate
 * toward the target = angle / 82 (200 from 90 degrees). Step 1: inside window 78..160 the yaw steps toward the
 * target when it is on the positive side (7/114) / negative side (7/115); at the motion end motion 583 from frame
 * 230, step 2; step 2: step 3 at frame 240 (effect post 41 skipped); step 3: tar on part 0 in window 240..400, end
 * at the motion end. (4U's 7/115 window bounds are register-carried, taken as 78..160 too.) */
static void act_7_114(void *self, uint32_t var)
{
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, var ? 0x25a : 0x259, 4.0f, 0.0f);
        set_mode(self, 1);
        setAttackId(self, 1);
        aim_target(self);
        aim_rate(self, 0x4000, 1.0f / 82.0f, 200);
        return;
    case 1: {
        aim_target(self);
        uint32_t ang = angle_to(self, &FIELD(float, self, F_AIM));
        uint32_t d = (ang - FIELD(uint32_t, REC(self), REC_YAW)) & 0xffff;
        if ((d < 0x8000) == (var == 0)) aim_turn_to(self, 78.0f, 160.0f, 0, (int32_t)ang);
        tar_drip(self, 1, 1, 7, 92.0f);
        if (!isMotionEnd(self)) return;
        setMotion(self, 0x247, 0.0f, 230.0f);
        STEP(self)++;
        return;
    }
    case 2:
        if (at_frame(self, 240.0f)) { STEP(self)++; em089_shell016_post(self, 41, 0); }   /* [0x8bf4ec..0x8bf560] */
        tar_drip(self, 71, 3, 7, 10.0f);
        tar_drip(self, 61, 2, 7, 15.0f);
        return;
    default:
        if (mc(self, 3, 240.0f, 400.0f)) tar_add(self, DT(self),0, 0);
        if (isMotionEnd(self)) act_end(self);
        return;
    }
}

/* 7/118, 7/127 [4U 0x8bf5bc, r1 = 0/1]: breath wind-up, motion 580 (mode 0, attack id 0) / 585 (mode 1, id 1),
 * blend 0, stopMove. Step 1: turnToTarget 234 in window 40..110 (7/127: 205 in 60..120); at the motion end chain
 * 7/120 (7/127: 7/129). */
static void act_7_118(void *self, uint32_t var)
{
    if (STEP(self) == 0) {
        begin(self);
        setTargetMode(self, 0);
        setMotion(self, var ? 0x249 : 0x244, 0.0f, 0.0f);
        set_mode(self, var);
        setAttackId(self, var);
        stopMove(self);
        return;
    }
    if (var ? mc(self, 3, 60.0f, 120.0f) : mc(self, 3, 40.0f, 110.0f)) face(self, var ? 205 : 234, 0);
    tar_drip(self, 71, 3, 7, var ? 80.0f : 75.0f);
    tar_drip(self, 7, 2, 7, 100.0f);
    tar_drip(self, 4, 0, 6, var ? 60.0f : 50.0f);
    if (isMotionEnd(self)) chain(self, 7, var ? 129 : 120);
}

/* 7/122..7/125 [4U 0x8bf7e0, r1 = side 0/1, r2 = big 0/1]: flying tail / wing sweep, mode 1, attack id 1, motion
 * 587 / 589 (big) or 588 / 590 by side, blend 4; big: slot 0 = 35 (8), slot 1 = 36 (16), else slot 0 = 33 (8).
 * Aim point = lead point (distance / 2.5 + 175), its angle kept (work+0xe0); rate: big = angle / 180 (182 at 180
 * degrees), small = angle / 74 (332 from 135 degrees). Step 1: big: window 100..280 toward the kept angle, always
 * positive (side 0) / negative (side 1); small: window 94..168 toward the live angle, shortest way; at the motion
 * end motion 582 from frame 298 (big; slot 0 = 56, slot 1 = 57) or 260 (small; slot 0 = 33, slot 1 = 34), step 2;
 * step 2: frame 307 (big; slot 0 = 54, slot 1 = 55) or 295 (small; slot 0 = 52, slot 1 = 53), end at the
 * motion end. */
static void act_7_122(void *self, uint32_t var)
{
    uint32_t side = var & 1, big = var >> 1;
    switch (STEP(self)) {
    case 0:
        begin(self);
        setTargetMode(self, 0);
        set_mode(self, 1);
        setAttackId(self, 1);
        setMotion(self, big ? (side ? 0x24e : 0x24d) : (side ? 0x24c : 0x24b), 4.0f, 0.0f);
        if (big) { hit(self, 0, 35, 8); hit(self, 1, 36, 16); }
        else hit(self, 0, 33, 8);
        aim_setup(self, target_dist(self) / 2.5f + 175.0f, big ? 0x8000 : 0x6000, big ? 1.0f / 180.0f : 1.0f / 74.0f,
                  big ? 182 : 332);
        FIELD(uint32_t, self, F_MISC) = angle_to(self, &FIELD(float, self, F_AIM));
        return;
    case 1:
        if (big) aim_turn_to(self, 100.0f, 280.0f, side ? 2 : 1, (int32_t)FIELD(uint32_t, self, F_MISC));
        else aim_turn(self, 94.0f, 168.0f, 0);
        tar_drip(self, 1, 1, 7, 33.0f);
        tar_drip(self, 3, 0, 7, 50.0f);
        tar_drip(self, 142, 4, 7, 70.0f);
        if (!isMotionEnd(self)) return;
        setMotion(self, 0x246, 0.0f, big ? 298.0f : 260.0f);
        if (big) { hit(self, 0, 56, 16); hit(self, 1, 57, 16); }
        else { hit(self, 0, 33, 16); hit(self, 1, 34, 16); }
        STEP(self)++;
        return;
    default:
        if (big) { if (at_frame(self, 307.0f)) { hit(self, 0, 54, 16); hit(self, 1, 55, 16); } }
        else if (at_frame(self, 295.0f)) { hit(self, 0, 52, 16); hit(self, 1, 53, 16); }
        if (isMotionEnd(self)) act_end(self);
        return;
    }
}

/* ---- reactions (GU numbering, requested by the engine) ---- */

/* category 10/11: until the reaction-sequence tables exist (Rathian: 0xa134c(this, table, flag)), play one
 * Gogmazios reaction motion and end. */
static void act_react(void *self, uint32_t var)
{
    act_play(self, var ? MOT_REACT2 : MOT_REACT, 0);
}

typedef void (*act_fn)(void *self, uint32_t var);
static const struct { uint8_t cat, num; uint16_t var; act_fn fn; } s_ported[] = {
    {0, 0, 0, act_idle}, {0, 1, 0, act_idle}, {0, 2, 0, act_idle}, {0, 3, 0, act_0_3}, {0, 6, 1, act_0_3},
    {0, 9, 0, act_0_9},
    /* category 1: every em089 number (dispatcher 0x8bac40); act_1_inline var = motion | flags */
    {1, 0, 4, act_roar}, {1, 3, 0, act_roar}, {1, 8, 1, act_roar}, {1, 25, 2, act_roar}, {1, 26, 3, act_roar},
    {1, 29, 8, act_roar}, {1, 30, 9, act_roar}, {1, 31, 10, act_roar}, {1, 32, 11, act_roar},
    {1, 1, 0x002, act_1_inline}, {1, 4, 0x30b | 0x1000, act_1_inline}, {1, 18, 0x30b, act_1_inline},
    {1, 21, 0x03d | 0x2000, act_1_inline}, {1, 24, 0x047 | 0x2000 | 0x4000, act_1_inline},
    {1, 5, 0, act_1_5}, {1, 17, 1, act_1_5}, {1, 20, 2, act_1_5}, {1, 28, 3, act_1_5},
    {1, 16, 0, act_1_16}, {1, 27, 1, act_1_16},
    {1, 22, 0, act_1_22}, {1, 23, 1, act_1_22}, {1, 33, 2, act_1_22}, {1, 34, 3, act_1_22},
    /* category 2: every em089 number (dispatcher 0x8bd4b0) */
    {2, 0, 0, act_2_0}, {2, 65, 1, act_2_0}, {2, 66, 2, act_2_0},
    {2, 1, 0, act_2_1}, {2, 2, 1, act_2_1}, {2, 62, 0, act_2_62},
    {2, 6, 0, act_2_6}, {2, 19, 1, act_2_6}, {2, 20, 2, act_2_6}, {2, 21, 3, act_2_6}, {2, 22, 4, act_2_6},
    {2, 28, 5, act_2_6}, {2, 60, 7, act_2_6},
    {2, 15, 1, act_2_27}, {2, 27, 0, act_2_27}, {2, 35, 0, act_2_35},
    {2, 33, 0, act_2_33}, {2, 34, 1, act_2_33}, {2, 45, 2, act_2_33}, {2, 46, 3, act_2_33},
    {2, 61, 0, act_2_61}, {2, 63, 1, act_2_61}, {2, 64, 2, act_2_61}, {2, 67, 0, act_2_67},
    {2, 68, 0, act_run_stop}, {2, 69, 1, act_run_stop}, {2, 70, 2, act_run_stop}, {2, 71, 3, act_run_stop},
    /* categories 3, 4 (dispatcher 0x8c2640), 13 */
    {3, 0, 0, act_3_0}, {3, 1, 1, act_3_0}, {3, 2, 0, act_sleep}, {4, 4, 1, act_sleep},
    {4, 0, 0, act_4_0}, {4, 2, 1, act_4_0}, {4, 3, 2, act_4_0}, {4, 6, 0, act_4_6},
    {4, 5, 0, act_4_5}, {4, 7, 1, act_4_5}, {4, 8, 2, act_4_5}, {4, 9, 4, act_4_5}, {4, 10, 5, act_4_5},
    {4, 11, 6, act_4_5}, {13, 11, 0, act_13_11},
    /* category 7 (dispatcher 0x8c0f94) */
    {7, 7, 0, act_7_7}, {7, 52, 1, act_7_7}, {7, 55, 2, act_7_7}, {7, 17, 0, act_7_17},
    {7, 19, 0, act_7_19}, {7, 20, 1, act_7_19}, {7, 25, 0, act_7_25}, {7, 53, 1, act_7_25},
    {7, 26, 1, act_7_26}, {7, 30, 0, act_7_26}, {7, 54, 2, act_7_26}, {7, 27, 0, act_7_27},
    {7, 32, 0, act_7_32}, {7, 93, 1, act_7_32},
    {7, 45, 0, act_7_45}, {7, 60, 1, act_7_45}, {7, 62, 2, act_7_45}, {7, 64, 3, act_7_45}, {7, 66, 4, act_7_45},
    {7, 47, 0, act_7_47}, {7, 61, 1, act_7_47}, {7, 63, 2, act_7_47}, {7, 65, 3, act_7_47}, {7, 67, 4, act_7_47},
    {7, 105, 0, act_7_105}, {7, 106, 0, act_7_106},
    {7, 107, 0, act_7_107}, {7, 110, 1, act_7_107}, {7, 120, 2, act_7_107}, {7, 129, 3, act_7_107},
    {7, 109, 0, act_7_109}, {7, 112, 0, act_7_112}, {7, 114, 0, act_7_114}, {7, 115, 1, act_7_114},
    {7, 118, 0, act_7_118}, {7, 127, 1, act_7_118},
    {7, 122, 0, act_7_122}, {7, 123, 1, act_7_122}, {7, 124, 2, act_7_122}, {7, 125, 3, act_7_122},
    {7, 126, 0, act_7_126}, {7, 133, 0, act_7_133}, {7, 135, 0, act_7_135},
    {7, 136, 4, act_7_136}, {7, 137, 5, act_7_136}, {7, 138, 0, act_7_138}, {7, 139, 0, act_7_139},
    {7, 140, 0, act_7_140}, {7, 141, 1, act_7_140}, {7, 142, 0, act_7_142},
    {7, 143, 0, act_7_143}, {7, 147, 1, act_7_143}, {7, 148, 2, act_7_143},
    {7, 144, 0, act_7_144}, {7, 145, 1, act_7_144}, {7, 146, 0, act_7_146},
};

/* ==== vtable overrides (4U em089 slots -> GU uFestaEnemy slots, notes/port-checklist.md "Vtable overrides") ==== */

/* our fields: zeroed at construction (4U slot 39's first-frame init also zeroes work+0xcb..0xd9, 0xd0) */
void em089_fields_init(void *self)
{
    for (uint32_t o = SIZE_uFestaEnemy + 4; o < F_END; o++) FIELD(uint8_t, self, o) = 0;
    FIELD(uint8_t, self, F_DATASET) = 0xff;
}

/* GU slot 133 (base 0x6bf2c = return 0) = 4U slot 51 [0x8c9084]: the monster condition the AI opcode 0x6f evaluates
 * (GU selector 0x844e8 -> 0x81ff8 -> vt+0x214 (this, id); 4U em089 EMC uses ids 0..28 = the 29 cases, 111 times).
 * Target = the hunter (4U: target slot W+536). Arena cases 4..7 / 14..21: see arena_dist. Case 28 = spawn byte 3
 * == 2 (REC_SPAWN_B3; both 4U Gogmazios quests have 0 / 1, so it is 0 there too). */

/* 4U arena points 0x936894 -> 0x689f7c(mgr, record, (area << 8) | n, out): stage 13 (global +0xc8c) reads the
 * fixed table 0x1004b78, every other stage the record's point table at +0x40: 8-byte {u8 stage, list} entries ->
 * 16-byte {u8 area, u8 count, .., points} entries -> 12-byte (x, y, z) points, out w = 0; no match -> (0, 0, 0).
 * The record is 0x688854 = species table 0xf3a024[89][0], filled at 0x68959c with rEnemyData (DTI 0x10a00d0)
 * +0x64 data + 8, so +0x40 = emd file word 18 (C by format: em009's word 18 parses as this layout, words 16 / 17
 * do not). em089 (em_data.arc) word 18 = 0xd40: one stage, 19 (Battlequarters), one area, 3 (m19a03), 19 points.
 * (The earlier "+0x40 = 0 -> all (0, 0, 0)" read file word 16.) Area: 0x69dbf0 passes rec+0x14c through except on
 * stage 13; the table has area 3 only, which is the arena (m19a03d), so the port uses it unconditionally. */
static const float k_arena_pts[19][3] = {
    {-128, 0, 2935}, {-128, 0, 1750}, {2493, 0, 1422}, {1225, 0, 1422}, {-215, 0, -4131}, {-215, 0, -2594},
    {-1733, 0, 896}, {-893, 0, -32}, {-777, 0, 1200}, {1350, 0, 1200}, {-128, 0, 6500}, {6000, 0, 1422},
    {-215, 0, -7500}, {-4000, 0, 2250}, {-128, 0, 3625}, {2992, 0, 1422}, {-215, 0, -4724}, {-2331, 0, 1215},
    {0, 0, 1200},
};

static void arena_point(uint32_t n, float *out)
{
    out[0] = out[1] = out[2] = out[3] = 0.0f;   /* port-only bound: the EMC asks 0..13, the conditions 0..17 */
    if (n < sizeof k_arena_pts / sizeof k_arena_pts[0])
        for (int i = 0; i < 3; i++) out[i] = k_arena_pts[n][i];
}

/* The cases measure the MONSTER: [this+0xc28] is the work record (same W+0x7814 flags as [this+0xe28], 0x8b9bf4 /
 * 0x8b9c24), W+408 = rec+64. Distance in 3D (0x8c91d0.., 0x8c6284..). */
static float arena_dist(void *self, uint32_t n)
{
    const float *p = &FIELD(float, REC(self), REC_POS_X);
    float a[4], d;
    arena_point(n, a);
    float x = p[0] - a[0], y = p[1] - a[1], z = p[2] - a[2], d2 = x * x + y * y + z * z;
    __asm__("vsqrt.f32 %0, %1" : "=t"(d) : "t"(d2));
    return d;
}

int em089_cond(void *self, uint32_t id)
{
    static uint32_t s_logged;
    if ((id >= 4 && id <= 7) || (id >= 14 && id <= 21)) {
        /* [0x8c9188 / 0x8c926c / 0x8c9354 / 0x8c9440]: point 2k within 450 -> 80 + 10k, else point 2k+1 within
         * 750 (k even) / 800 (k odd) -> 2k, else 2k + 1; [0x8c9784..0x8c9848] 0x8c6230: point 14..17 within 1500
         * (cases 18..21 repeat points 14..17) */
        uint32_t r;
        if (id >= 14) r = arena_dist(self, 14 + ((id - 14) & 3)) <= 1500.0f;
        else {
            uint32_t k = id - 4;
            r = arena_dist(self, 2 * k) <= 450.0f ? 80 + 10 * k
              : arena_dist(self, 2 * k + 1) <= ((k & 1) ? 800.0f : 750.0f) ? 2 * k : 2 * k + 1;
        }
        static uint8_t s_last[22];
        static uint32_t s_n;
        if (s_last[id] != r + 1 && ++s_n <= 60)
            logf("gogport: em089 cond %u (arena) -> %u at %d %d %d", id, r, (int32_t)FIELD(float, REC(self), REC_POS_X),
                 (int32_t)FIELD(float, REC(self), REC_POS_X + 4), (int32_t)FIELD(float, REC(self), REC_POS_Z));
        s_last[id] = (uint8_t)(r + 1);
        return r;
    }
    float t[4];
    uint32_t d = 0;
    if (id == 8 || (id >= 11 && id <= 13) || id == 23 || id == 24) {
        target_pos(self, t);
        d = (angle_to(self, t) - FIELD(uint32_t, REC(self), REC_YAW)) & 0xffff;
    }
    switch (id) {
    case 0: return FIELD(uint8_t, REC(self), REC_MODE) == 1;
    case 1: return findTargetEx(self, 0, 1024, 9472, 4) != -1;
    case 2: return FIELD(uint8_t, self, F_SHAKE) != 0;
    case 3: { uint32_t h = FIELD(uint8_t, self, F_HITS); return h >= 3 ? 2 : h == 2 ? 1 : 0; }
    case 8: {   /* [0x8c953c] target slot height: ground 4, ledge 1 / 3 by x, top 0 / 2 by z */
        uint32_t r = t[1] <= 300.0f ? 4 : t[1] <= 1200.0f ? (t[0] >= 0.0f ? 1 : 3) : (t[2] >= 0.0f ? 0 : 2);
        static uint32_t s_last = 99, s_n;
        if (r != s_last && ++s_n <= 60)
            logf("gogport: em089 cond 8 (hunter height) %u -> %u at %d %d %d", s_last, r, (int32_t)t[0], (int32_t)t[1],
                 (int32_t)t[2]);
        s_last = r;
        return r;
    }
    case 9: return FIELD(uint8_t, self, F_RAGE) != 0;
    case 10: return FIELD(float, self, F_COOL) <= 0.0f;
    case 11: return (uint32_t)(d - 0x5556) < 0x5555 ? 0 : 1;
    case 12: return d < 0x8000;
    case 13: return (uint32_t)(d - 0x6aac) < 0x2aa9 ? 0 : 1;
    case 22:
        if (FIELD(uint8_t, self, F_LATCH_D8)) return 1;
        FIELD(uint8_t, self, F_LATCH_D8) = 1;
        return 0;
    case 23: case 24: return (uint32_t)(d - 0x4000) > 0x8000;
    case 25: {   /* save target slot 0 (kind, sub, param) into the +1 copies */
        uint8_t *k = REC(self) + REC_TGT_KIND;
        k[1] = k[0]; k[3] = k[2]; k[5] = k[4];
        return 0;
    }
    case 26: {   /* restore it, re-arm the target and pick a wander point */
        uint8_t *k = REC(self) + REC_TGT_KIND;
        k[0] = k[1]; k[2] = k[3]; k[4] = k[5];
        setTarget(self, k[0], k[2], k[4], 0);
        wanderPoint(self, 0, 0);
        return 0;
    }
    case 27:
        if (FIELD(uint8_t, self, F_LATCH_D9)) return 1;
        FIELD(uint8_t, self, F_LATCH_D9) = 1;
        return 0;
    case 28:   /* [0x8c996c] W+0x797e == 2 = spawn byte 3 (rec+0x5cb6): EMC g0 s3 / s10 pick the s25..s32 script set */
        return spawn_b3(self) == 2;
    default:
        if (++s_logged <= 40) logf("gogport: em089 cond %u (arena / unmapped) -> 0", id);
        return 0;
    }
}

static void lights_action_start(void *self, uint32_t cat, uint32_t num);   /* below, with the tar state word */

/* GU slot 129 (base bx lr; called by setAction's on-start bookkeeping 0x755b4 with (cat, num), 0x7580c) = 4U
 * slot 47 [0x8c8778, (this, cat, num)]: counts the flying attacks 7/32, 7/93, 7/142, 7/143, 7/146..7/148 in
 * work+0xcb (AI condition 3) and resets the count on any other action except categories 0 / 3, 2/67 and 4/x
 * (x != 4). Not ported: W+0x28d = 1 (unmapped record byte) and the category-10 branch for 10/108, 10/109, 10/114,
 * 10/202, 10/203 (flying knock-down: net object 0xc088d8, reactions), logged. */
void em089_action_start(void *self, uint32_t cat, uint32_t num)
{
    uint8_t *hits = &FIELD(uint8_t, self, F_HITS);
    if (cat == 7) {
        if (num == 32 || num == 93 || num == 142 || num == 143 || num == 146 || num == 147 || num == 148) (*hits)++;
        else *hits = 0;
    } else if (cat == 0 || cat == 3 || (cat == 2 && num == 67) || (cat == 4 && num != 4)) {
        /* kept */
    } else {
        *hits = 0;
    }
    if (cat == 10 && (num == 108 || num == 109 || num == 114 || num == 202 || num == 203))
        stub("slot 47 cat-10 branch", num, 0);
    lights_action_start(self, cat, num);   /* 0x8c8a40..0x8c8be4 */
    FIELD(uint8_t, self, F_SHELL_N) = 0;   /* 0x8c8bec: work+0xcd = 0 (tar blob rand index) */
}

/* GU slot 127 (base bx lr) = 4U slot 46 [0x8c677c]: the action-request remap both setActions run in a loop until
 * the pair is stable (4U 0x90efac -> vt+0xb8 at 0x90f1c8, GU 0x76154 -> vt+0x1fc at 0x764b0, then GU slot 128),
 * under the same condition in both (mode 1, or monster owned here (4U W+0x1d9 / GU this+0x7420) and mode != 3: C).
 * em089: a request 0/0 or 0/1 (also the end-of-action idle of slot 247, mode 2) becomes 1/5 (idle motion 2) or,
 * in mode 1 (W+0x1c9, flying), 1/20 (hover idle). */
void em089_action_remap(void *self, uint8_t *cat, uint8_t *num)
{
    static uint32_t s_n;
    if (*cat != 0 || (*num != 0 && *num != 1)) return;
    uint8_t from = *num;
    *cat = 1;
    *num = FIELD(uint8_t, REC(self), REC_MODE) == 1 ? 20 : 5;
    if (++s_n <= 20) logf("gogport: em089 remap 0/%u -> 1/%u (slot 46)", from, *num);
}

/* GU slot 130 (base return 0; per frame from the enemy update 0xae830 / 0xaf19c, result unused, after a this+0x7426
 * check) = 4U slot 48 [0x8c6e58] (per frame from 0x919f60 after a W+0x1dd check, result unused): per-motion camera
 * shakes. 4U jointFx 0x910c6c(this, joint, id) = GU 0xc24d8(this, joint, id, 0): both return unless the monster is
 * in the player's area, joint -1 = no position, else the joint position, then the camera manager (GU 0x19148 ->
 * the uFestaCamera at mgr+0x54); 621 of 625 GU calls pass r3 = 0, shake ids 0..9 in both games. Table read out of
 * 0x8c6e58 by emulation (scratchpad emu4u.py, every motion, each motionCheck(0, frame) taken alone, tail intact /
 * severed): {motion, frame, joint, shake id, tail: 0 any, 1 intact only, 2 severed only (4U 0x91a884 W+0x42c & 1 =
 * GU rec+0x3b4 & 1)}. */
typedef void (*cam_shake_joint_t)(void *self, int32_t joint, uint32_t id, uint32_t zero);
#define camShakeJoint FN(cam_shake_joint_t, 0xc24d8)
#define REC_DETACHED 0x3b4   /* u16 detached-part bits (4U W+0x42c), em089_break.h BRK_REC_DETACHED */
static const struct { uint16_t mot, frame; int16_t joint; uint8_t id, tail; } k_shake[] = {
    {0x008, 121, 1, 1, 0}, {0x00b, 96, -1, 8, 0}, {0x00c, 96, -1, 8, 0}, {0x015, 128, -1, 8, 0},
    {0x016, 128, -1, 8, 0}, {0x019, 105, 1, 1, 0}, {0x01c, 104, -1, 7, 0}, {0x01d, 104, -1, 7, 0},
    {0x10b, 10, 1, 1, 0}, {0x112, 12, 63, 5, 0}, {0x112, 30, 73, 5, 0}, {0x209, 128, 63, 5, 0},
    {0x20b, 140, 73, 5, 0}, {0x20c, 175, 63, 5, 0}, {0x20c, 235, 63, 7, 0}, {0x20c, 250, 63, 7, 0},
    {0x20c, 265, 63, 7, 0}, {0x20c, 280, 63, 7, 0}, {0x20e, 222, 2, 1, 0}, {0x20e, 242, 4, 5, 0},
    {0x218, 96, -1, 7, 0}, {0x218, 132, -1, 7, 0}, {0x219, 137, 73, 5, 0}, {0x23c, 286, 142, 1, 2},
    {0x23c, 286, 143, 1, 1}, {0x23c, 352, 143, 7, 1}, {0x23c, 367, 143, 7, 1}, {0x23d, 286, 142, 1, 2},
    {0x23d, 286, 143, 1, 1}, {0x23d, 352, 143, 7, 1}, {0x23d, 367, 143, 7, 1}, {0x241, 162, 4, 1, 0},
    {0x241, 172, 4, 7, 0}, {0x241, 182, 4, 7, 0}, {0x241, 192, 4, 7, 0}, {0x241, 202, 4, 7, 0},
    {0x241, 212, 4, 7, 0}, {0x241, 222, 4, 7, 0}, {0x241, 232, 4, 7, 0}, {0x241, 242, 4, 7, 0},
    {0x241, 252, 4, 7, 0}, {0x241, 262, 4, 7, 0}, {0x241, 272, 4, 7, 0}, {0x241, 282, 4, 7, 0},
    {0x241, 292, 4, 7, 0}, {0x241, 302, 4, 7, 0}, {0x242, 353, 4, 1, 0}, {0x242, 363, 4, 7, 0},
    {0x242, 373, 4, 7, 0}, {0x242, 383, 4, 7, 0}, {0x242, 393, 4, 7, 0}, {0x242, 403, 4, 7, 0},
    {0x242, 413, 4, 7, 0}, {0x242, 423, 4, 7, 0}, {0x242, 433, 4, 7, 0}, {0x242, 443, 4, 7, 0},
    {0x242, 453, 4, 7, 0}, {0x242, 463, 4, 7, 0}, {0x242, 473, 4, 7, 0}, {0x243, 120, 63, 5, 0},
    {0x243, 180, 63, 7, 0}, {0x243, 193, 63, 7, 0}, {0x243, 206, 63, 7, 0}, {0x243, 219, 63, 7, 0},
    {0x246, 266, 1, 9, 0}, {0x246, 309, 63, 9, 0}, {0x246, 325, 73, 9, 0}, {0x24d, 366, 1, 1, 0},
    {0x24e, 366, 1, 1, 0}, {0x25d, 198, 73, 5, 0}, {0x25d, 335, 73, 7, 0}, {0x25d, 350, 73, 7, 0},
    {0x25d, 365, 73, 7, 0}, {0x25d, 380, 73, 7, 0}, {0x25e, 198, 63, 5, 0}, {0x25e, 335, 63, 7, 0},
    {0x25e, 350, 63, 7, 0}, {0x25e, 365, 63, 7, 0}, {0x25e, 380, 63, 7, 0}, {0x268, 198, 73, 5, 0},
    {0x268, 335, 73, 7, 0}, {0x268, 350, 73, 7, 0}, {0x268, 365, 73, 7, 0}, {0x268, 380, 73, 7, 0},
    {0x269, 198, 63, 5, 0}, {0x269, 335, 63, 7, 0}, {0x269, 350, 63, 7, 0}, {0x269, 365, 63, 7, 0},
    {0x269, 380, 63, 7, 0}, {0x26a, 200, 142, 7, 2}, {0x26a, 200, 143, 1, 1}, {0x26a, 350, 143, 7, 1},
    {0x26a, 365, 143, 7, 1}, {0x26a, 380, 143, 7, 1}, {0x26a, 395, 143, 7, 1}, {0x26a, 410, 143, 7, 1},
    {0x26a, 425, 143, 7, 1}, {0x26a, 534, 142, 8, 2}, {0x26a, 534, 143, 7, 1}, {0x27c, 175, 73, 5, 0},
    {0x27c, 235, 73, 7, 0}, {0x27c, 250, 73, 7, 0}, {0x27c, 265, 73, 7, 0}, {0x27c, 280, 73, 7, 0},
    {0x316, 2, -1, 9, 0}, {0x316, 30, -1, 1, 0}, {0x317, 2, -1, 9, 0}, {0x317, 30, -1, 1, 0},
    {0x318, 99, -1, 1, 0}, {0x31e, 184, -1, 1, 0}, {0x31e, 424, -1, 1, 0}, {0x328, 283, -1, 1, 0},
    {0x329, 283, -1, 1, 0}, {0x337, 480, -1, 7, 0}, {0x337, 528, -1, 1, 0},
};

int em089_motion_frame(void *self)
{
    static uint32_t s_n;
    uint32_t m = curMotion(self) & 0xffff;
    uint32_t severed = FIELD(uint16_t, REC(self), REC_DETACHED) & 1;
    for (uint32_t i = 0; i < sizeof k_shake / sizeof k_shake[0]; i++) {
        if (k_shake[i].mot != m) continue;
        if ((k_shake[i].tail == 1 && severed) || (k_shake[i].tail == 2 && !severed)) continue;
        if (!at_frame(self, (float)k_shake[i].frame)) continue;
        camShakeJoint(self, k_shake[i].joint, k_shake[i].id, 0);
        if (++s_n <= 40) logf("gogport: em089 camera shake id %u joint %d (motion %x frame %u)", k_shake[i].id,
                              k_shake[i].joint, m, k_shake[i].frame);
    }
    return 0;
}

/* ==== tar state machine (4U slot 39 spawn part, 0x8c2518, 0x8c352c, 0x8c69b8, slot 50 head / tail bits) ====
 * Per tar part (4U part numbers 0 head, 7 chest, 2 l_arm, 3 r_arm, 6 tail = k 0..4): amount work+4*part (F_TAR),
 * mode work+0x54+2k (F_TAR_MODE): amount <= 100 Solid, <= 160 Liquid, else Gas. A mode change sets the part's
 * hitzone row (rec+0x418, 4U W+0x460), the one-hot bits of the state word W+0x7814 and the material animation
 * (em089_tar.c, 4U slot 50). The word drives the 4U emd cond-7 mesh-group rows (tar_vis). */

/* 4U part -> k (-1 = not a tar part) and hitzone row (jump tables at 0x8c35d8: head 0, chest 5, arms 2 / 3, tail 4) */
static int tar_k(uint32_t part) { return part == 0 ? 0 : part == 7 ? 1 : part == 2 ? 2 : part == 3 ? 3 : part == 6 ? 4 : -1; }
static uint32_t tar_row(uint32_t part) { return part == 7 ? 5 : part == 6 ? 4 : part; }

/* Gas hitzone rows: 4U em089 rodata 0xff6fd4 (6 rows x 10 bytes, row = tar_row) */
static const uint8_t k_tar_gas_meat[6][10] = {
    {50, 55, 60, 30, 5, 5, 10, 60, 0, 100}, {0, 0, 0, 0, 0, 0, 0, 0, 0, 100},
    {45, 40, 55, 25, 0, 0, 10, 40, 0, 100}, {45, 40, 55, 25, 0, 0, 10, 40, 0, 100},
    {55, 50, 55, 40, 5, 5, 15, 60, 0, 100}, {55, 45, 60, 35, 5, 5, 15, 65, 0, 100},
};

/* 4U emd cond-7 visibility rows (emdata4u.part_rows): {group, hide while (0: bit set, 1: bit clear), bit}. Each
 * group has exactly one cond-7 row. Their other rows (g34 break 0, g13 / g14 / g19 tail sever, g15 cond 11) are
 * taken as intact, like the spawn XFS states (breaks / sever not ported). Bit 17 (g102) = wing size (0x8c64b8,
 * em089_slot77), bits 18..22 (g17, g18, g19, g5, g2) = lights (slot 47 0x8c8a40.., 0x8c6300: lights_action_start /
 * lights_frame). (0x8c9db4 / 0x8ca09c write the MODEL flags this+0x108, not this word.) */
static const uint8_t k_tar_vis[14][3] = {
    {2, 1, 22}, {3, 0, 15}, {4, 1, 1}, {5, 1, 21}, {7, 1, 11}, {13, 1, 4}, {14, 0, 16},
    {15, 1, 10}, {17, 1, 18}, {18, 1, 19}, {19, 1, 20}, {22, 0, 1}, {34, 0, 0}, {102, 1, 17},
};

static void tar_vis(void *self)
{
    static uint32_t s_logs;
    uint32_t w = FIELD(uint32_t, self, F_TAR_WORD);
    if (FIELD(uint8_t, self, F_TAR_VISOK) && FIELD(uint32_t, self, F_TAR_VIS) == w) return;
    FIELD(uint8_t, self, F_TAR_VISOK) = 1;
    FIELD(uint32_t, self, F_TAR_VIS) = w;
    for (uint32_t i = 0; i < 14; i++) {
        uint32_t g = k_tar_vis[i][0], set = (w >> k_tar_vis[i][2]) & 1;
        uint32_t *bits = &FIELD(uint32_t, self, EN_GROUP_VIS + 4 * (g >> 5));
        if (k_tar_vis[i][1] ? set : !set) *bits |= 1u << (g & 31);
        else *bits &= ~(1u << (g & 31));
    }
    if (++s_logs <= 60)
        logf("gogport: em089 tar word %x -> groups %x %x %x %x", w, FIELD(uint32_t, self, EN_GROUP_VIS),
             FIELD(uint32_t, self, EN_GROUP_VIS + 4), FIELD(uint32_t, self, EN_GROUP_VIS + 8),
             FIELD(uint32_t, self, EN_GROUP_VIS + 12));
}

/* hitzone of a part for a mode: 0x936ea8 (Solid: base row), 0x93415c (Liquid: alternate row), Gas: own table */
static void tar_meat(void *self, uint32_t row, uint32_t mode)
{
#ifdef TAR_NO_MEAT
    (void)self; (void)row; (void)mode;
    return;   /* control build: keep the engine's default rows (0xbabf4: part i -> base row i) */
#endif
    uint8_t *data = FIELD(uint8_t *, self, EN_MEAT_DATA);
    if (mode == TAR_GAS) FIELD(const uint8_t *, REC(self), REC_PART_MEAT + 4 * row) = k_tar_gas_meat[row];
    else if (!data) return;                                  /* no data block: GU would crash in 0x71078 users */
    else if (mode == TAR_LIQUID) partMeatAlt(self, row, row);
    else if (FIELD(void *, data + 100, 0xc)) partMeatBase(self, row);
}

/* 4U 0x8c69b8(this, mode, part): part k one-hot to bit k (Solid), 5 + k (Liquid) or 10 + k (Gas) of W+0x7814 */
static void tar_word(void *self, uint32_t mode, uint32_t part)
{
    int k = tar_k(part);
    if (k < 0 || mode > TAR_GAS) return;
    uint32_t *w = &FIELD(uint32_t, self, F_TAR_WORD);
    *w = (*w & ~(0x421u << k)) | (1u << (5 * mode + (uint32_t)k));
}

/* a mode change of 0x8c352c: hitzone, word, T+0x54+2k (-> material animation) */
static void tar_set(void *self, uint32_t part, uint32_t mode)
{
    static uint32_t s_logs;
    int k = tar_k(part);
    tar_meat(self, tar_row(part), mode);
    tar_word(self, mode, part);
    FIELD(uint8_t, self, F_TAR_MODE + k) = (uint8_t)mode;
    em089_tar_set_mode(self, (uint32_t)k, mode);
    if (++s_logs <= 100)
        logf("gogport: em089 tar part %u -> mode %u (amount %d)", part, mode, (int32_t)(&FIELD(float, self, F_TAR))[part]);
}

/* 4U slot 39 [0x8b9bc8..0x8b9e0c], tar part: W+0x7814 = 0, amounts and timers 0, then head and chest 130,
 * modes head / chest Liquid, arms / tail Solid, hitzones 0x936ea8(2, 3, 4), 0x93415c(0, 0), (5, 5), then
 * 0x8c69b8 (1, 0), (1, 7), (0, 2), (0, 3), (0, 6) -> word 0x7c. Animations: em089_tar_spawn. */
void em089_tar_machine_spawn(void *self)
{
    float *amt = &FIELD(float, self, F_TAR), *tim = &FIELD(float, self, F_TAR_TIMER);
    uint8_t *mode = &FIELD(uint8_t, self, F_TAR_MODE);
    FIELD(uint32_t, self, F_TAR_WORD) = 0;
    for (int i = 0; i < 8; i++) amt[i] = tim[i] = 0.0f;
    amt[0] = amt[7] = 130.0f;
    FIELD(float, self, F_TAR_D4) = 0.0f;
    mode[0] = mode[1] = TAR_LIQUID;
    mode[2] = mode[3] = mode[4] = TAR_SOLID;
    tar_meat(self, 2, TAR_SOLID); tar_meat(self, 3, TAR_SOLID); tar_meat(self, 4, TAR_SOLID);
    tar_meat(self, 0, TAR_LIQUID); tar_meat(self, 5, TAR_LIQUID);
    tar_word(self, 1, 0); tar_word(self, 1, 7); tar_word(self, 0, 2); tar_word(self, 0, 3); tar_word(self, 0, 6);
    {   /* diagnostic: the 8 hitzone rows the GU damage code reads (0xbab60: rec+0x418[part], part < 8) */
        uint8_t *data = FIELD(uint8_t *, self, EN_MEAT_DATA);
        logf("gogport: em089 meat data %x base %x alt %x", (uint32_t)data,
             data ? FIELD(uint32_t, data + 100, 0xc) : 0, data ? FIELD(uint32_t, data + 100, 0x10) : 0);
        for (uint32_t i = 0; i < 8; i++) {
            const uint8_t *r = FIELD(const uint8_t *, REC(self), REC_PART_MEAT + 4 * i);
            if (r) logf("gogport: em089 meat row %u %x: cut %u imp %u shot %u fire %u ko %u", i, (uint32_t)r,
                        r[0], r[1], r[2], r[3], r[8]);
            else logf("gogport: em089 meat row %u null", i);
        }
    }
    FIELD(uint8_t, self, F_TAR_VISOK) = 0;
    tar_vis(self);
    FIELD(uint8_t, self, F_LIGHT) = 0;   /* slot 39 [0x8ba104]: work+0xc8 = 0 */
    em089_light_play(self, -1);          /* slot 39 [0x8ba074..0x8ba090]: light controller slot 0 = -1 (none) */
}

/* 4U 0x94d7a8: action category 11 or 14, or 12/255 (death / capture) */
static int tar_dead(void *self)
{
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT);
    return cat == 11 || cat == 14 || (cat == 12 && FIELD(uint8_t, self, EN_ACT_NUM) == 255);
}

/* 4U 0x8c2518: while work+0xca (set by the 1/25 / 1/31 phase-2 roar, never cleared) every tar part is refilled to
 * 255 each frame (-> Gas for the rest of the fight) and the motion speed factor W+0x40c (GU rec+916) is set to 1.155
 * when spawn byte 3 (W+0x797e) is 1 or 2, else 1.1 (literals 0x8c2630 / 0x8c2634). The 4U call 0x954e48 before the
 * loop only picks between two identical copies of it. */
static void tar_refill(void *self)
{
    static void *s_logged;
    if (!FIELD(uint8_t, self, F_SHAKE)) return;
    float *amt = &FIELD(float, self, F_TAR);
    amt[0] = amt[2] = amt[3] = amt[6] = amt[7] = 255.0f;
    uint32_t b3 = spawn_b3(self);
    FIELD(float, REC(self), REC_SPEED2) = (b3 == 1 || b3 == 2) ? 1.155f : 1.1f;
    if (s_logged != self) {
        s_logged = self;
        logf("gogport: em089 phase 2 refill: tar 255, speed2 x1000 %d (spawn byte3 %u)",
             (int32_t)(FIELD(float, REC(self), REC_SPEED2) * 1000.0f), b3);
    }
}

/* 4U 0x8c352c: per part (loop order 0, 2, 3, 6, 7): dead -> amounts 0; amount > 0: timer -= dt, at <= 0 the amount
 * loses 2 (clamped at 0) and the timer restarts at 180; then the mode from the amount (<= 100 Solid, <= 160
 * Liquid, else Gas; amount 0 = Solid) and tar_set when it differs. Then, alive with the chest Liquid: work+0xd4 +=
 * dt; past 210: 0x2fcc50(*0xfccd6c, 203, this, 2, W+0x14c, -2) = sSoundControl sound 203 at joint 2
 * (em089_snd_tar_chest, sound agent: GU 0x4efd74) and reset. */
static void tar_machine(void *self)
{
    float *amt = &FIELD(float, self, F_TAR), *tim = &FIELD(float, self, F_TAR_TIMER);
    uint8_t *mode = &FIELD(uint8_t, self, F_TAR_MODE);
    int dead = tar_dead(self);
    for (uint32_t p = 0; p < 8; p++) {
        int k = tar_k(p);
        if (k < 0) continue;
        if (dead) amt[p] = 0.0f;
        uint32_t want = TAR_SOLID;
        if (amt[p] > 0.0f) {
            tim[p] -= DT(self);
            if (tim[p] <= 0.0f) {
                amt[p] -= 2.0f;
                if (amt[p] <= 0.0f) amt[p] = 0.0f;
                tim[p] = 180.0f;
            }
            want = amt[p] <= 100.0f ? TAR_SOLID : amt[p] <= 160.0f ? TAR_LIQUID : TAR_GAS;
        }
        if (mode[k] != want) tar_set(self, p, want);
    }
    if (!dead && mode[1] == TAR_LIQUID) {
        float *t = &FIELD(float, self, F_TAR_D4);
        *t += DT(self);
        if (*t > 210.0f) { em089_snd_tar_chest(self); *t = 0.0f; }   /* 0x2fcc50 = sound 203 at joint 2 */
    }
    tar_vis(self);
}

/* 4U slot 50 [0x8c8da0] bits: W+0x7814 |= 0x8000 (head) / 0x10000 (tail) when the part's transition to Solid
 * ends and steady Solid starts; cleared every frame the part is not Solid. Hides g3 / g14 (tar_vis). */
void em089_tar_steady(void *self, uint32_t entered)
{
    uint32_t *w = &FIELD(uint32_t, self, F_TAR_WORD);
    uint8_t *mode = &FIELD(uint8_t, self, F_TAR_MODE);
    if (mode[0] != TAR_SOLID) *w &= ~0x8000u;
    else if (entered & 1u) *w |= 0x8000u;
    if (mode[4] != TAR_SOLID) *w &= ~0x10000u;
    else if (entered & 0x10u) *w |= 0x10000u;
    tar_vis(self);
}

/* ==== lights (material type 6, em089_light_play) and the state-word bits 18-22 that show their meshes ====
 * 4U light indices work+0xa8 + 4*k = anim index of name k of table 0xff6fb4 (slot 39 [0x8b9ee4..0x8b9f1c]), so
 * "0x8c62c0(this, [work+0xa8 + 4k])" = em089_light_play(self, k). Bits (k_tar_vis rows): 18 g17, 19 g18, 20 g19,
 * 21 g5, 22 g2 shown while set. */
#define LW_B18 0x40000u
#define LW_B19 0x80000u
#define LW_B20 0x100000u
#define LW_B21 0x200000u
#define LW_B22 0x400000u

/* 4U slot 47 tail [0x8c8a40..0x8c8be4], every action start: clear bits 18-20; for category 7 by number:
 * breath attacks (107 110 114 115 118 120 126 127 129 135 136 137 143 146 147 148): light 0 (Light_Gas_Bress),
 * bit 22, work+0xc8 = 1, bit 21 if the chest tar (work+0x56) is not Solid; 139 light 2 + bit 18; 27 light 2 + bit 19;
 * 112 light 3 + bit 19; 144 light 4 + bit 18; 145 light 4 + bit 19; 140 light 5 + bit 18; 141 light 5 + bit 19;
 * 133 light 6 + bit 20; 19 / 20 light 7 + bit 20 (jump table 0x8c8b58 for 135..148). */
static void lights_action_start(void *self, uint32_t cat, uint32_t num)
{
    static uint32_t s_n;
    uint32_t *w = &FIELD(uint32_t, self, F_TAR_WORD);
    *w &= ~(LW_B18 | LW_B19 | LW_B20);
    int k = -1;
    uint32_t bit = 0;
    if (cat == 7) {
        switch (num) {
        case 107: case 110: case 114: case 115: case 118: case 120: case 126: case 127: case 129:
        case 135: case 136: case 137: case 143: case 146: case 147: case 148:
            k = 0; bit = LW_B22;
            FIELD(uint8_t, self, F_LIGHT) = 1;
            if (FIELD(uint8_t, self, F_TAR_MODE + 1) != TAR_SOLID) bit |= LW_B21;
            break;
        case 139: k = 2; bit = LW_B18; break;
        case 27:  k = 2; bit = LW_B19; break;
        case 112: k = 3; bit = LW_B19; break;
        case 144: k = 4; bit = LW_B18; break;
        case 145: k = 4; bit = LW_B19; break;
        case 140: k = 5; bit = LW_B18; break;
        case 141: k = 5; bit = LW_B19; break;
        case 133: k = 6; bit = LW_B20; break;
        case 19: case 20: k = 7; bit = LW_B20; break;
        default: break;
        }
    }
    if (k >= 0) {
        em089_light_play(self, k);
        *w |= bit;
        if (++s_n <= 40) logf("gogport: em089 light %d for 7/%u, word %x", k, num, *w);
    }
    tar_vis(self);
}

/* the light material (type 6) and whether its slot-0 animation is Light_Gas_Bress_End at / past its last frame
 * (4U 0x8c6354..0x8c63a0: 0x636b54(ctrl, 0) == work+0xac and ctrl+76 frame >= the entry's frame count) */
typedef int (*tar_find_anim_t)(void *set, const char *name);
typedef int (*tar_cur_anim_t)(void *mat, int slot);
static int light_end_done(void *self)
{
    int n = FIELD(int32_t, self, TAR_MAT_COUNT);
    void **arr = FIELD(void **, self, TAR_MAT_ARRAY);
    for (int i = 0; arr && i < n; i++) {
        void *mat = arr[i];
        if (!mat || ((FIELD(uint32_t, mat, TAR_MAT_TYPE_WORD) >> 22) & 0xff) != 6) continue;
        void *set = FIELD(void *, mat, TAR_MAT_ANIMSET);
        if (!set) continue;
        int idx = FN(tar_find_anim_t, TAR_GU_FIND_ANIM)(set, "Light_Gas_Bress_End");
        if (idx < 0 || FN(tar_cur_anim_t, TAR_GU_CUR_ANIM)(mat, 0) != idx) return 0;
        uint32_t *list = FIELD(uint32_t *, set, 0x10);
        if (!list || (uint32_t)idx >= list[0] || !list[1 + idx]) return 0;
        return FIELD(float, mat, TAR_MAT_FRAME0) >= (float)*(uint32_t *)list[1 + idx];
    }
    return 0;
}

/* 4U 0x8c6300 (per frame from slot 77): during a breath attack (category 7, numbers as above except 133 / 139..145 /
 * 19 / 20 / 27 / 112) work+0xc8 = 1 and bit 21 follows the chest tar (not Solid -> set); when such an action is over
 * (any other action) state 1 -> 2 -> light 1 (Light_Gas_Bress_End), state 3; in state 3, once that animation reached
 * its end: state 0, bits 21 and 22 cleared. */
static void lights_frame(void *self)
{
    static uint32_t s_n;
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_NUM);
    uint8_t *st = &FIELD(uint8_t, self, F_LIGHT);
    uint32_t *w = &FIELD(uint32_t, self, F_TAR_WORD), w0 = *w;
    int breath = 0;
    if (cat == 7)
        switch (num) {
        case 107: case 110: case 114: case 115: case 118: case 120: case 126: case 127: case 129:
        case 135: case 136: case 137: case 143: case 146: case 147: case 148: breath = 1; break;
        default: break;
        }
    if (breath) {
        *st = 1;
        if (FIELD(uint8_t, self, F_TAR_MODE + 1) != TAR_SOLID) *w |= LW_B21; else *w &= ~LW_B21;
    } else if (*st == 1) {
        *st = 2;
    }
    if (*st == 2) {
        em089_light_play(self, 1);
        *st = 3;
        if (++s_n <= 40) logf("gogport: em089 light 1 (breath end), word %x", *w);
    }
    if (*st == 3 && light_end_done(self)) {
        *st = 0;
        *w &= ~(LW_B21 | LW_B22);
        if (++s_n <= 40) logf("gogport: em089 light off, word %x", *w);
    }
    if (*w != w0) tar_vis(self);
}

/* 4U 0x8c5768 (first call of slot 77, every frame): by current motion, switch the mode byte W+0x1c9 (GU rec+0x1bb)
 * and the attack id at fixed motion frames, raise the em089 flag work+0xe4 and arm the cooldown work+0xd0. This is
 * what brings Gogmazios back to mode 0 (quadruped) after its biped / flying attacks: 0x24b / 0x24c (7/122, 7/123
 * small sweeps) at frame 220, 0x24d / 0x24e (big sweeps) at 290, 0x246 (7/109, sweep landings) at 250, 0x47 (1/24)
 * at 90; mode 1 starts at 0x3d (1/21) 230, 0x41 / 0x42 / 0x50 / 0x51 100, 0x23f 184, 0x244 160.
 * Then the map-hit sphere (maphit_frame, below) and the work+0xe4 / work+0xca tail. */

/* Map-hit sphere = the monster's map (wall) collision sphere. 4U 0x91df20(this)->+0x48 = emd word 20 = GU dtbase
 * +0x84 (dt_convert, 34/40 vote), returned directly by GU 0x712a4 (NULL when dtbase+0xc5 == 0; + 52 when
 * rec+0x5cb6 == 103): 52 B = 4 offsets {x, y, z} (+0 stand, +12 fly, +24 wall, +36) + radius +48. em089: (0, 250,
 * 375), (0, -200, 0), (0, 0, 0), (0, -200, 0), 1125. GU 0xbc8b0 = 4U 0x9167ec (setTargetMode = state setter) copies
 * the offset of state rec+0x1ba (1 / 2 fly, 5 wall, 6 +36, else stand) to rec+0x900; GU 0xa71ac (per frame, from
 * 0xa6400 / 0xa6478) puts the sphere at pos + rotated rec+0x900 * rec+0x910 with radius +48 * rec+0x914 (0xa756c:
 * x size factor rec+0x1b0 only outside 0.6..1.95), adjusts it on the map (0x49a84) and moves pos x / z by the push.
 * Facing a wall: stop at 375 + 1125 = 1500 in front of it (test 6: always z 1903 at the z 3403 platform face).
 * 4U em089 [0x8c5d68..0x8c5e34] (every frame, state rec+0x1ba == 0 only) morphs the block IN PLACE (the shared
 * resource; x / y kept), then re-applies the offset with setState(state) [0x8c5e28]:
 *   mode 1 (flying): radius -> 750, stand z -> 0, at 25 per tick on motions 0x41 / 0x42 / 0x50 / 0x51 (1/22, 1/23,
 *     1/33, 1/34 turns), else 10 [0x8c5ec4..0x8c5fd4];
 *   mode 0, motions 0x217..0x219 (7/45, 7/47 dash, 7/47 stop): radius -> 1125, z -> 950 at 10 [0x8c5fd8..0x8c602c];
 *   mode 0, other motions: radius -> 1125 at 10, z -> 375 (+10 per tick from below, snapped down from above)
 *     [0x8c5d84..0x8c5e24].
 * Steps are x the time scale (4U this+20 = GU this+28). The float-bit integer compares of 4U equal float compares
 * here (non-negative limits). */
typedef float *(*mapHitBlock_t)(void *self);
#define mapHitBlock  FN(mapHitBlock_t, 0x712a4)
typedef float (*mapHitRadius_t)(void *self);
#define mapHitRadius FN(mapHitRadius_t, 0xa756c)   /* effective radius: +48 * rec+0x914 (* size factor) */
#define REC_MAPHIT_OFS 0x900                       /* float[4]: offset of the current state (GU 0xbc8b0) */

static void maphit_frame(void *self, uint32_t m)
{
    uint8_t *rec = REC(self);
    if (FIELD(uint8_t, rec, REC_STATE) != 0) return;
    float *b = mapHitBlock(self);
    if (!b) return;
    float dt = DT(self), r = b[12], z = b[2];
    if (FIELD(uint8_t, rec, REC_MODE) == 1) {
        float k = (m == 0x041 || m == 0x042 || m == 0x050 || m == 0x051) ? 25.0f : 10.0f;
        r -= dt * k;
        if (r < 750.0f) r = 750.0f;
        z -= dt * k;
        if (z <= 0.0f) z = 0.0f;
    } else if (m >= 0x217 && m <= 0x219) {
        r += dt * 10.0f;
        if (r > 1125.0f) r = 1125.0f;
        z += dt * 10.0f;
        if (z > 950.0f) z = 950.0f;
    } else {
        r += dt * 10.0f;
        if (r > 1125.0f) r = 1125.0f;
        z += (z > 375.0f ? -10.0f : 10.0f) * dt;
        if (z > 375.0f) z = 375.0f;
    }
    b[2] = z;
    b[12] = r;
    setTargetMode(self, FIELD(uint8_t, rec, REC_STATE));   /* [0x8c5e28] 0x9167ec: re-copy the offset (same state) */
}

/* port-only check (high ground): where 1/24 (the mode-1 landing before a re-dash) starts, with the map-hit sphere;
 * the mode-1 think re-dashes unless the monster is within 1500 of point 14..17 (point 14 = (-128, 0, 3625)) */
static void log_maphit_1_24(void *self)
{
    static uint32_t s_n;
    if (++s_n > 20) return;
    uint8_t *rec = REC(self);
    float *b = mapHitBlock(self);
    const float *o = (const float *)(rec + REC_MAPHIT_OFS);
    logf("gogport: em089 1/24 start: pos %d %d, map-hit radius %d (block %d) offset z %d (block %d), state %u mode %u, "
         "point 14 at %d", (int32_t)FIELD(float, rec, REC_POS_X), (int32_t)FIELD(float, rec, REC_POS_Z),
         b ? (int32_t)mapHitRadius(self) : -1, b ? (int32_t)b[12] : -1, (int32_t)o[2], b ? (int32_t)b[2] : -1,
         FIELD(uint8_t, rec, REC_STATE), FIELD(uint8_t, rec, REC_MODE), (int32_t)arena_dist(self, 14));
}

static void motion_mode(void *self)
{
    uint32_t m = curMotion(self) & 0xffff;
    int to0 = 0, to1 = 0, e4 = 0, cool = 0;
    int mc2 = 0;
    switch (m) {
    case 0x03d: to1 = at_frame(self, 230.0f); break;
    case 0x047: to0 = at_frame(self, 90.0f); break;
    case 0x041: case 0x042: case 0x050: case 0x051: to1 = at_frame(self, 100.0f); break;
    case 0x10b: to0 = at_frame(self, 12.0f); cool = 1; break;
    case 0x316: cool = 1; break;
    case 0x23f: to1 = at_frame(self, 184.0f); break;
    case 0x244: to1 = at_frame(self, 160.0f); break;
    case 0x246: to0 = at_frame(self, 250.0f); break;
    case 0x24b: case 0x24c: to0 = at_frame(self, 220.0f); break;
    case 0x24d: case 0x24e: to0 = at_frame(self, 290.0f); break;
    case 0x268: case 0x269: e4 = at_frame(self, 50.0f); break;
    case 0x249: case 0x26a: case 0x26c: case 0x278: case 0x330: case 0x331: case 0x332: case 0x333:
        e4 = mc(self, 2, 10.0f, 0.0f); break;
    case 0x26f: e4 = mc(self, 3, 490.0f, 1400.0f); break;
    case 0x302: if (mc(self, 2, 10.0f, 0.0f)) to0 = e4 = 1; break;
    case 0x303: case 0x306: e4 = mc(self, 2, 10.0f, 0.0f); to0 = at_frame(self, 300.0f); break;
    case 0x304: case 0x307: e4 = mc(self, 2, 10.0f, 0.0f); to0 = isMotionEnd(self); break;
    case 0x305: case 0x308: to0 = mc(self, 2, 10.0f, 0.0f); break;
    case 0x318:
        mc2 = mc(self, 2, 10.0f, 0.0f);
        if (mc2 || FIELD(uint8_t, REC(self), REC_MODE) == 1) to0 = e4 = 1;
        break;
    case 0x328: case 0x329: to0 = at_frame(self, 264.0f); break;
    case 0x337: e4 = mc(self, 2, 10.0f, 0.0f); to0 = at_frame(self, 530.0f); break;
    default: break;
    }
    if (to1) { set_mode(self, 1); setAttackId(self, 1); }
    if (to0) { set_mode(self, 0); setAttackId(self, 0); }
    if (e4) FIELD(uint8_t, self, F_FLAG_E4) = 1;
    if (cool && FIELD(float, self, F_COOL) <= 0.0f) FIELD(float, self, F_COOL) = 10800.0f;
    maphit_frame(self, m);   /* [0x8c5d68..0x8c5e34] */
    /* tail [0x8c5e38..0x8c622c], every frame after the switch: with work+0xe4 == 1 in phase 2 (work+0xca), the flag
     * is kept only while a "glow" motion runs (0x249 0x26a 0x26c 0x278 0x303 0x304 0x306 0x307 0x318 0x330 0x331 0x332
     * 0x333 0x337, 0x26f inside kind-3 490..1400, 0x302 inside 0..260, 0x268 / 0x269 inside 50..800); otherwise
     * work+0xe4 = 0 and 4U re-posts the phase-2 aura uEffect002 57 (0xc0bd38, param 4 in state 1 / 3, 2 flying,
     * else 1). The aura of em089_efx_aura watches work+0xe4 and comes back by itself on this reset. */
    uint8_t *fe4 = &FIELD(uint8_t, self, F_FLAG_E4);
    if (*fe4 == 1 && FIELD(uint8_t, self, F_SHAKE)) {
        int keep = 0;
        switch (m) {
        case 0x249: case 0x26a: case 0x26c: case 0x278: case 0x303: case 0x304: case 0x306: case 0x307:
        case 0x318: case 0x330: case 0x331: case 0x332: case 0x333: case 0x337: keep = 1; break;
        case 0x26f: keep = mc(self, 3, 490.0f, 1400.0f); break;
        case 0x302: keep = mc(self, 3, 0.0f, 260.0f); break;
        case 0x268: case 0x269: keep = mc(self, 3, 50.0f, 800.0f); break;
        default: break;
        }
        if (!keep) {
            static uint32_t s_n;
            *fe4 = 0;
            if (++s_n <= 20) logf("gogport: em089 work+0xe4 reset (motion %x): phase-2 aura back", m);
        }
    }
}

/* 4U slot 77 [0x8c99a0] (per frame, after slot 40; GU slot 170 by position, called from our slot 119 instead):
 * 0x8c5768 above; motion 0x31f: yaw += 18/17 degrees per tick in window 82..252, motion 0x32c: +3 in 10..40 (arena
 * gimmick motions); 0x8c64b8 wing size (em089_wing_update, em089_tar.c) -> word bit 17; 0x8c6300 lights
 * (lights_frame); cooldown work+0xd0 countdown. Not ported: the work+0xe8 timer clearing work+0xe5 (work+0xe5 /
 * +0xe8 are only set by the slot-47 category-10 branch, not ported). */
static void em089_slot77(void *self)
{
    motion_mode(self);
    uint32_t m = curMotion(self) & 0xffff;
    {   /* item 7 trace: when the monster goes more than 300 above / comes back to its ground (motion 264 itself has no
         * root lift: its root track is constant 0, bone 0 stays below y 545) */
        static uint8_t s_high;
        static uint32_t s_n;
        float h = FIELD(float, REC(self), REC_POS_X + 4) - FIELD(float, REC(self), 0x5b4);
        uint8_t high = h > 300.0f;
        if (high != s_high && ++s_n <= 40)
            logf("gogport: em089 height %s: y %d ground %d action %u/%u motion %x frame %d mode %u",
                 high ? "up" : "down", (int32_t)FIELD(float, REC(self), REC_POS_X + 4),
                 (int32_t)FIELD(float, REC(self), 0x5b4), FIELD(uint8_t, self, EN_ACT_CAT),
                 FIELD(uint8_t, self, EN_ACT_NUM), m, (int32_t)motionFrame(self), FIELD(uint8_t, REC(self), REC_MODE));
        s_high = high;
    }
    float f = 1.0f;
    if (m == 0x31f && motionCheck(self, 9, &f, 82.0f, 252.0f)) yaw_add(self, 18.0f / 17.0f, f);
    if (m == 0x32c && motionCheck(self, 9, &f, 10.0f, 40.0f)) yaw_add(self, 3.0f, f);
    {   /* 0x8c64b8 [0x8c9aa0]: wing size animations (em089_tar.c) -> state-word bit 17 (group 102) */
        static uint32_t s_n;
        int r = em089_wing_update(self);
        if (r) {
            uint32_t *w = &FIELD(uint32_t, self, F_TAR_WORD);
            if (r == EM089_WING_SET) *w |= EM089_WING_WORD_BIT; else *w &= ~EM089_WING_WORD_BIT;
            if (++s_n <= 40) logf("gogport: em089 wing %s (motion %x), word %x", r == EM089_WING_SET ? "large" : "small", m, *w);
            tar_vis(self);
        }
    }
    lights_frame(self);   /* 0x8c6300 [0x8c9aac] */
    timerDown(self, &FIELD(float, self, F_COOL), 1.0f);
}

/* GU slot 119 (base bx lr, per frame from 0xadb3c) = 4U slot 40 [0x8ba258], per-frame state logic:
 *  - data set: 2 when the state class (W+0x1c8 = GU rec+0x1ba) is 1 or 3 (4U also sets W+0x7948 = 1, unmapped),
 *    1 in mode 1 (flying), else 0 (0x947438 = GU 0xc833c; 4U calls it every frame, here on change);
 *  - 0x8c2518 (tar refill while work+0xca) and 0x8c352c (per-part tar decay -> Solid / Liquid / Gas via 0x8c69b8):
 *    tar_refill / tar_machine above, same order;
 *  - rage roll work+0xcc from the HP percentage (W+0x3e8 / 0x3ec = GU rec+0x370 / 0x374) and the action serial
 *    % 100 (W+0x1d2 = this+0x73e8): set when (hp < 40 and r != 0) or (hp < 60 and r > 25) or (hp < 80 and r > 50)
 *    or r > 75 (read by AI condition 9);
 *  - not ported: the reset of the attack slots' timer +72 / flag 4 (GU slot layout differs).
 * Also the cooldown work+0xd0 countdown of 4U slot 77 (0x8c99a0, timerDown each frame). */
void em089_state_update(void *self)
{
    uint8_t st = FIELD(uint8_t, REC(self), REC_STATE), mode = FIELD(uint8_t, REC(self), REC_MODE);
    uint32_t set = (st == 1 || st == 3) ? 2 : mode == 1 ? 1 : 0;
    if (FIELD(uint8_t, self, F_DATASET) != set) {
        FIELD(uint8_t, self, F_DATASET) = (uint8_t)set;
        selectDataSet(self, set);
        logf("gogport: em089 data set %u (state %u mode %u)", set, st, mode);
    }
    em089_react_status_immune(self);   /* 4U em089 has no status data: no paralysis 10/31 cutting the phase-2 roar */
    tar_refill(self);
    tar_machine(self);
    int32_t hp = FIELD(int32_t, REC(self), REC_HP), mx = FIELD(int32_t, REC(self), REC_HP + 4);
#ifdef TEST_HP_PCT
    /* test builds: start at TEST_HP_PCT % of max HP once, so the HP-gated phases are reachable in a short session */
    static void *s_hp_set;
    if (s_hp_set != self && mx > 0 && hp == mx) {
        s_hp_set = self;
        hp = mx * TEST_HP_PCT / 100;
        FIELD(int32_t, REC(self), REC_HP) = hp;
        logf("gogport: em089 test HP %d / %d", hp, mx);
    }
#endif
    int32_t pct = mx > 0 ? (int16_t)(int32_t)((float)hp / (float)mx * 100.0f) : 100;
    {   /* damage report (polled per frame): the first 20 HP drops, then one line per 5 % of max HP lost */
        static void *s_self;
        static int32_t s_last, s_mark;
        static uint32_t s_drops;
        if (s_self != self) { s_self = self; s_last = s_mark = hp; s_drops = 0; }
        if (hp < s_last) {
            s_drops++;
            if (s_drops <= 20 || (mx > 0 && s_mark - hp >= mx / 20)) {
                s_mark = hp;
                logf("gogport: em089 damage #%u: -%d -> hp %d / %d (action %u/%u)", s_drops, s_last - hp, hp, mx,
                     FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM));
            }
        }
        s_last = hp;
    }
    {   /* report: HP in 10 % steps, and every state / mode change (tools/gogreport.py) */
        static int32_t s_dec = -1;
        static uint8_t s_st = 0xff, s_mode = 0xff;
        if (pct != s_dec) {   /* 1 % steps (10 % hid a slow HP drop); + the HP floor of setHP 0x9a764 */
            s_dec = pct;
            logf("gogport: em089 hp %d%% (%d / %d) floor x1000 %d", pct, hp, mx,
                 (int32_t)(FIELD(float, REC(self), 0x380) * 1000.0f));
        }
        if (st != s_st || mode != s_mode) {
            s_st = st; s_mode = mode;
            logf("gogport: em089 state %u mode %u", st, mode);
        }
    }
    {   /* phase-2 path (EMC): rage -> group 6 s0 -> HP <= 50 % and no work+0xca yet -> roar 1/25 (1/31 flying) ->
         * work+0xca -> g0 s16 picks the s10 dispatcher (cond 2). Log the inputs: rage edges (rage timer rec+0x514),
         * anger counter, spawn byte 3. */
        static void *s_self;
        static uint8_t s_angry;
        static uint32_t s_n;
        uint8_t angry = FIELD(float, REC(self), REC_RAGE_TIMER) > 0.0f;
        if (s_self != self) {
            s_self = self; s_angry = angry;
            logf("gogport: em089 phase inputs: spawn byte3 %u (GU %u), enraged %u, anger %d, work+0xca %u, hp %d%%",
                 spawn_b3(self), FIELD(uint8_t, REC(self), REC_SPAWN_B3), angry, FIELD(int16_t, REC(self), REC_ANGER),
                 FIELD(uint8_t, self, F_SHAKE), pct);
        }
#ifdef TEST_RAGE
        {   /* test builds: GOG_DEFINES="TEST_RAGE=S" feeds the engine's own anger path once, S seconds (60 units/s)
             * after spawn: addAnger 0xbcc04(this, 2000) -> threshold -> think event 4 -> EMC group 6. (Test 2 used
             * 30000: the s16 anger rec+0x510 overflowed negative and addAnger clamps < 0 to 0 -> "anger 0". 2000 x
             * the dttune gains 0.9..2.0 stays below 32767 and above the threshold 700 = Kushala's table.) */
            typedef void (*add_anger_t)(void *self, int32_t dmg);
            static void *s_rage_self;
            static float s_t;
            if (s_rage_self != self) { s_rage_self = self; s_t = 0.0f; }
            if (s_t >= 0.0f) {
                s_t += DT(self);
                if (s_t >= (float)(TEST_RAGE) * 60.0f) {
                    s_t = -1.0f;
                    FN(add_anger_t, 0xbcc04)(self, 2000);
                    logf("gogport: em089 test rage: addAnger -> anger %d, think events %x", FIELD(int16_t, REC(self), REC_ANGER),
                         FIELD(uint16_t, REC(self), 0x362));
                }
            }
        }
#endif
        if (s_self == self && angry != s_angry && ++s_n <= 40) {
            s_angry = angry;
            logf("gogport: em089 rage %s (hp %d%%, anger %d, work+0xca %u, action %u/%u)", angry ? "on" : "off", pct,
                 FIELD(int16_t, REC(self), REC_ANGER), FIELD(uint8_t, self, F_SHAKE), FIELD(uint8_t, self, EN_ACT_CAT),
                 FIELD(uint8_t, self, EN_ACT_NUM));
        }
    }
    uint32_t r = FIELD(uint16_t, self, EN_ACT_SERIAL) % 100;
    FIELD(uint8_t, self, F_RAGE) = (pct < 40 && r != 0) || (pct < 60 && r > 25) || (pct < 80 && r > 50) || r > 75;
    em089_slot77(self);   /* 4U runs slot 77 right after slot 40 in its per-frame update 0x94d26c */
}

static void log_action(void *self, uint32_t cat, uint32_t num, const char *how)
{
    static uint32_t s_logs;
    uint16_t *last = &FIELD(uint16_t, self, F_LAST_ACTION);
    uint16_t key = (uint16_t)(cat << 8 | num | 0x8000);
    if (*last == key) return;
    *last = key;
    /* setTarget lasts one turn (1); an EMC arena point (2) lasts until slot 0 is re-targeted (set_target_c) */
    if (FIELD(uint8_t, self, F_NOSYNC) == 1 && !(cat == 2 && (num == 1 || num == 2))) FIELD(uint8_t, self, F_NOSYNC) = 0;
    float t[4];
    int hunter = target_pos(self, t);
    const float *d = (const float *)(REC(self) + REC_TARGET);
    const uint8_t *k = REC(self) + REC_TGT_KIND;
    if (s_logs == 0) {   /* multiplayer diagnostic: the hunter list against the local hunter */
        uint8_t *list = *(uint8_t **)HUNTER_LIST;
        logf("gogport: em089 hunters %x %x %x %x local %x", list ? FIELD(uint32_t, list, 0x1c) : 0,
             list ? FIELD(uint32_t, list, 0x20) : 0, list ? FIELD(uint32_t, list, 0x24) : 0,
             list ? FIELD(uint32_t, list, 0x28) : 0, (uint32_t)local_hunter());
    }
    if (++s_logs <= 4000)   /* whole sessions: tools/gogreport.py counts action coverage; the tail compares machines */
        logf("gogport: em089 %x action %u/%u (%s) motion %x pos %d,%d %s %d,%d dest %d,%d hunter y %d em y %d ground %d "
             "mode %u slot0 %u/%u/%u tgt %u local %d ctl %u serial %u yaw %x", (uint32_t)self, cat, num, how,
             curMotion(self), (int32_t)FIELD(float, REC(self), REC_POS_X),
             (int32_t)FIELD(float, REC(self), REC_POS_Z), hunter ? "hunter" : "no-hunter", (int32_t)t[0], (int32_t)t[2],
             (int32_t)d[0], (int32_t)d[2], (int32_t)t[1], (int32_t)FIELD(float, REC(self), REC_POS_X + 4),
             (int32_t)FIELD(float, REC(self), 0x5b4), FIELD(uint8_t, REC(self), REC_MODE), k[0], k[2], k[4],
             FIELD(uint8_t, self, F_TGT), local_index(), FIELD(uint8_t, self, EN_CONTROLLED),
             FIELD(uint16_t, self, EN_ACT_SERIAL), FIELD(uint32_t, REC(self), REC_YAW) & 0xffff);
}

/* GU slots 171 / 172 (base 0xb17d8 / 0xb17f4: AI bytes this+0x7305 / 0x7306) = 4U slots 78 / 79 [0x8c9d50 /
 * 0x8c9d38]: the monster's own bytes in the host's action message (pack slot 267 0xcb330 -> buffer + 132, 20 bytes;
 * unpack slot 268 0xcc154 on the other machines). 4U em089 sends work+0xda only and drops the base bytes, as
 * Rathian's GU override 0xd0bdc0 does. Port-only bytes 1 and 2, for state 4U does not have: F_NOSYNC (the host's AI
 * hook set_target_c sets 2) and F_TGT. */
void em089_net_get(void *self, uint8_t *out, uint32_t size)
{
    static uint32_t s_n;
    if (size < 3) return;
    out[0] = FIELD(uint8_t, self, F_HEADING);
    out[1] = FIELD(uint8_t, self, F_NOSYNC);
    out[2] = FIELD(uint8_t, self, F_TGT);
    if (++s_n <= 20) logf("gogport: em089 net send heading %u nosync %u tgt %u", out[0], out[1], out[2]);
}

void em089_net_set(void *self, const uint8_t *in, uint32_t size)
{
    static uint32_t s_n;
    if (size < 3) return;
    FIELD(uint8_t, self, F_HEADING) = in[0];
    FIELD(uint8_t, self, F_NOSYNC) = in[1];
    FIELD(uint8_t, self, F_TGT) = in[2];
    if (++s_n <= 40) logf("gogport: em089 net receive heading %u nosync %u tgt %u", in[0], in[1], in[2]);
}

/* hook 0x76154 setAction(this, cat, num, mode): diagnostic, logs who changes em089's action. regs: r0..r5, r12, lr. */
int set_action_c(uint32_t *regs)
{
    void *self = (void *)regs[0];
    static uint32_t s_n;
    if (FIELD(uint16_t, self, EN_ID) != EM089_ID || s_n >= 200) return 0;
    s_n++;
    logf("gogport: em089 %x setAction %u/%u -> %u/%u mode %u lr %x", regs[0], FIELD(uint8_t, self, EN_ACT_CAT),
         FIELD(uint8_t, self, EN_ACT_NUM), regs[1], regs[2], regs[3], regs[7] - MAIN_BASE);
    return 0;
}

/* hook 0xc6e14 setTarget(this, kind, sub, param, [sp] slot), em089 only: kind 5 sub 8 = the 4U arena point
 * (EMC `01 00 05 08 n` -> 4U op 0x01 0x94fc14 -> 0x92ce98: setTarget 0x916bcc stores the bytes (0x92ed9c resolves
 * kind 5 only for subs 0..3 / 10..15 / 253), then 0x92d0d4 -> 0x93aab4 sub 8 [0x93b2a0] -> 0x689f7c = k_arena_pts[n]
 * (see arena_point). GU resolves sub 8 in map_info (0xc5724 -> 0xb3d5c), Kushala's placeholder here, and falls back
 * to the monster's own position (the move ends on the spot). Same conversion GU applies to the subs it resolves at
 * once (0xc6ed4 -> 0xc6e70): position written into the slot, kind 6 sub 254. Slot 0 then keeps the point (F_NOSYNC
 * 2) until the next setTarget on it. regs: r0..r5, r12, lr, then the caller's stack. */
int set_target_c(uint32_t *regs)
{
    void *self = (void *)regs[0];
    if (FIELD(uint16_t, self, EN_ID) != EM089_ID) return 0;
    uint32_t slot = regs[8] & 0xff;
    uint8_t *nosync = &FIELD(uint8_t, self, F_NOSYNC);
    if ((regs[1] & 0xff) != 5 || (regs[2] & 0xff) != 8) {
        /* slot 0 re-targeted (e.g. cond 26 restoring the saved target after the move): the hunter copy resumes */
        static uint32_t s_c;
        if (slot == 0 && *nosync == 2) {
            *nosync = 0;
            if (++s_c <= 40)
                logf("gogport: em089 arena point released by setTarget %u/%u/%u lr %x", regs[1] & 0xff, regs[2] & 0xff,
                     regs[3] & 0xff, regs[7] - MAIN_BASE);
        }
        return 0;
    }
    uint32_t n = regs[3] & 0xff;
    float *p = &FIELD(float, REC(self), REC_TARGET + 16 * slot);
    arena_point(n, p);   /* 4U 0x93b2a0 (resolver 0x93aab4 kind 5 sub 8, via 0x92d0d4 right after setTarget) */
    if (slot == 0) *nosync = 2;   /* sync_target must not overwrite it: 4U moves to the point (g1 s101..s104) */
    static uint32_t s_n;
    if (++s_n <= 40)
        logf("gogport: em089 arena point %u (slot %u) -> (%d, %d, %d), monster at %d %d", n, slot, (int32_t)p[0],
             (int32_t)p[1], (int32_t)p[2], (int32_t)FIELD(float, REC(self), REC_POS_X),
             (int32_t)FIELD(float, REC(self), REC_POS_Z));
    regs[1] = 6;
    regs[2] = 254;
    regs[3] = 0;
    return 0;
}

void em089_act_run(void *self)
{
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_NUM);

    atk_unshorten(self);
    s_cam_self = self;   /* net_event's owner (handlers call it without self) */
    for (uint32_t i = 0; i < sizeof s_ported / sizeof s_ported[0]; i++)
        if (s_ported[i].cat == cat && s_ported[i].num == num) {
            log_action(self, cat, num, "ported");
            s_ported[i].fn(self, s_ported[i].var);
            return;
        }
    if (cat == 17) { log_action(self, cat, num, "base"); action_base17(self); return; }
    /* 10: em089's own reactions (4U 0x8c2784 -> em089_react.c, GU sequence player 0xa134c); the placeholder only for
     * 10/108, 109, 200, 202, 203, 228 and category 11 (0x8b6ac8 / 0x8b6da4 / 0x8b6b80, ends through the unmapped
     * 0x926044) */
    if (cat == 10 || cat == 11) { log_action(self, cat, num, "reaction"); if (!em089_react_run(self, cat, num)) act_react(self, cat == 11); return; }
    if (cat == 0) { log_action(self, cat, num, "idle"); act_idle(self, 0); return; }  /* 0/7 etc. (end slots) */
    log_action(self, cat, num, "unhandled -> end");
    act_end(self);
}
