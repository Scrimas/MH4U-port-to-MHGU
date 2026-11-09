/* em068_01.c: Tidal Najarala (GU Najarala variant 1, GU's class uEm068_00 runs her; notes/plan.md). GU kept 4U uEm023's tests of her as
 * variant tests (attack indexes 42..46, speeds, skipped Najarala effects), so her own moves come from her AI table and GU's handlers. This
 * file holds what GU dropped from 4U (C unless marked, 4U addresses read 2026-11-06); her water jet is in em068_01_jet.c:
 *  - her water scales: GU's f7d634 fires Najarala's. Her launches are kinds of our shell family (build_em068_01_arc.py KINDS):
 *      4U slot 47 (0x76ace4: GU slot 129 lost these cases): 7/45 (9, 1) 7/47 (9, 2) 7/53 (11, 1) 7/55 (11, 2) 7/57 (13, 2) 7/59 (15, 2);
 *      4U 0x7638a0 7/3 7/60 7/61: (9), (10) with the handler's parameter 0 / 2 / 3; GU's f844a0 lost the parameter;
 *      4U 0x7651ec 7/25: (9, 2) at its own offset.
 *  - 7/24's blasts (4U 0x764e88: uShell003 156 / 158, the same records as Najarala's 58 / 65): GU skips its post for variant != 0. GU's post runs
 *    for her with the variant byte at 0 between the two mid hooks, the Tigerstripe way (em067_01_shells.c); the code between is straight-line
 *    (C) and our shell family's data are hers.
 *  - her reactions hold 60 frames longer (4U 0x768094: tables for em != 23 wait 420 instead of 360, 660 instead of 600).
 *  - 7/20 at G rank plays at speed 1.5 (4U 0x764790, em != 23 and rank >= 5).
 *  - a shiny drop chance of 3 % when one of her scales is shot down (4U 0xc698f0 in uShell015, em != 23).
 * Multiplayer: GU's handlers run on every machine and shells are local to each, as GU's own (notes of Tigerstripe's shells): nothing here is gated
 * on the controlling machine, and the inputs are the action number and the quest rank. All addresses go through MAIN / FN; no fixed ranges.
 * Logs: prefix "tnport:". */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define EN_VARIANT (EN_ID + 5)      /* u8, set by setup 0x6fb14 from ID bits 8-11 */
#define EN_AREA    0x1054           /* u8 current area */
#define EN_SCRIPT  0x72fc           /* u8 group, u8 script of the running AI script */
#define MAX_LINES  3000u            /* a few minutes of fight */
#define IS_HER(p)  ((p) && FIELD(uint16_t, (p), EN_ID) == TIDAL_NAJARALA_EM_ID)

typedef void *(*param_alloc_t)(uint32_t size, uint32_t align);
#define paramAlloc   FN(param_alloc_t, 0x419c3c)           /* cSetupParamEmBase36, as GU's f7d738 */
typedef void *(*shell_request_t)(void *mgr, void *param, uint32_t a, uint32_t b);
#define shellRequest FN(shell_request_t, 0x48c4f0)
typedef uint32_t (*area_of_t)(void *mgr);
#define areaOf       FN(area_of_t, 0x16b920)
typedef void *(*shell_owner_t)(void *shell);
#define shellOwner   FN(shell_owner_t, 0x4a1b6c)
typedef void (*item_drop_t)(void *enemy, const void *pos, uint32_t chance, uint32_t zero);
#define itemDrop     FN(item_drop_t, 0xac0ec)
typedef uint32_t (*quest_rank_t)(void *mgr);
#define questRank    FN(quest_rank_t, 0x3a8d68)            /* rank class, >= 5 = G */
#define QUEST_MGR    (*(void **)MAIN(0x188ad90))
#define RAGE_ON(p)   (FN(int (*)(void *), 0x8172c)(p))      /* [4U 0x954e48] */

void em068_01_jet_frame(void *self);                        /* em068_01_jet.c */

#define SHELL_SCALE  0x126          /* GU's shell id of uShellEm068_sp_36 */
#define SHELL_SLOTS  4u             /* work +4..+0x10: the scale handles */

/* the GU kinds of tools/build_em068_01_arc.py KINDS (asserted there by their launch values) */
enum { K_9_P2 = 11, K_10_P2 = 12, K_9_P3 = 13, K_10_P3 = 14, K_13 = 15, K_14 = 16, K_15 = 17, K_16 = 18, K_9_OFF3 = 19, K_10_OFF3 = 20 };

/* GU f7d634's request for given kinds: free handles in order, nothing when too few are free */
static void fire(void *self, uint32_t k0, uint32_t k1, uint32_t count)
{
    static uint32_t s_n;
    uint8_t *work = FIELD(uint8_t *, self, EN_WORK);
    uint32_t busy = 0, fired = 0, kinds[2] = { k0, k1 };
    for (uint32_t s = 1; s <= SHELL_SLOTS; s++) busy += FIELD(void *, work, 4 * s) != 0;
    if (count > SHELL_SLOTS - busy) return;
    uint32_t area = areaOf(*(void **)MAIN(0x1857830));
    void *mgr = *(void **)MAIN(0x1892550);
    for (uint32_t s = 1; s <= SHELL_SLOTS && fired < count; s++) {
        if (FIELD(void *, work, 4 * s)) continue;
        uint8_t *p = paramAlloc(28, 16);
        busy = 0;
        for (uint32_t i = 1; i <= SHELL_SLOTS; i++) busy += FIELD(void *, work, 4 * i) != 0;
        FIELD(uint32_t, p, 0) = (uint32_t)MAIN(0x1758a24) + 8;
        FIELD(uint32_t, p, 4) = SHELL_SCALE;
        FIELD(uint32_t, p, 8) = kinds[fired];
        FIELD(void *, p, 0xc) = self;
        FIELD(uint32_t, p, 0x10) = s - 1;
        FIELD(uint32_t, p, 0x14) = busy + 1;
        FIELD(uint16_t, p, 24) = (uint16_t)area;
        FIELD(void *, work, 4 * s) = shellRequest(mgr, p, 0, 0);
        fired++;
    }
    if (++s_n <= 40) logf("tnport: scale kinds %u %u x %u (action %u/%u)", k0, k1, count, FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM));
}

/* what each of her scale shells became: its kind, state, flight effect (GU's first effect handle, 0 = none was made) and place when it appears, then each change of state with
 * its hits left (1 flight, 2 planted, 3 rattle, 4 end). The test log of "no scales": GU's setup makes the effect from the kind's ef file (0x419e84, handle +0x1678) */
static void scale_watch(void *self)
{
    static void *s_seen[SHELL_SLOTS];
    static uint8_t s_state[SHELL_SLOTS];
    static uint32_t s_n, s_m;
    uint8_t *work = FIELD(uint8_t *, self, EN_WORK);
    if (!work) return;
    for (uint32_t s = 0; s < SHELL_SLOTS; s++) {
        uint8_t *sc = FIELD(uint8_t *, work, 4 + 4 * s), *param;
        if (!sc) {
            s_seen[s] = 0;
            continue;
        }
        if (sc == s_seen[s]) {
            if (sc[4] != s_state[s]) {
                s_state[s] = sc[4];
                if (++s_m <= 96)
                    logf("tnport: scale %x slot %u state %u hits %u efx %x %x at %d %d %d", (uint32_t)sc, s, sc[4], sc[0x1644], FIELD(uint32_t, sc, 0x1680), FIELD(uint32_t, sc, 0x1690),
                         (int32_t)FIELD(float, sc, 0x40), (int32_t)FIELD(float, sc, 0x44), (int32_t)FIELD(float, sc, 0x48));
            }
            continue;
        }
        s_seen[s] = sc;
        s_state[s] = sc[4];
        if (++s_n > 48) continue;
        param = FIELD(uint8_t *, sc, 0x136c);
        logf("tnport: scale %x slot %u kind %u state %u hits %u efx %x %x at %d %d %d", (uint32_t)sc, s, param ? FIELD(uint32_t, param, 8) : 999, sc[4], sc[0x1644],
             FIELD(uint32_t, sc, 0x1678), FIELD(uint32_t, sc, 0x15c8), (int32_t)FIELD(float, sc, 0x40), (int32_t)FIELD(float, sc, 0x44), (int32_t)FIELD(float, sc, 0x48));
    }
}

/* her part counters (rec+0x3bc + 12 * part, GU 0x9d428): slot 132 shows a part as broken when its counter reaches dtbparts' value: head 2, parts 2, 3, 6, 7 one (C). Log only: a line at each change, so that a
 * test log shows the breaks. Parts: 0 head, 1 body, 2 neck (bones 100..103, outer volumes), 3 tail, 4 / 5 front legs, 6 / 7 hind legs */
static void part_watch(void *self)
{
    static void *s_self;
    static uint8_t s_count[8];
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    if (!rec) return;
    if (s_self != self) {
        s_self = self;
        for (int p = 0; p < 8; p++) s_count[p] = rec[0x3bc + 12 * p];
        return;
    }
    for (int p = 0; p < 8; p++) {
        uint8_t c = rec[0x3bc + 12 * p];
        if (c == s_count[p]) continue;
        s_count[p] = c;
        logf("tnport: part %d count %u (action %u/%u, area %u)", p, c, FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM), FIELD(uint8_t, self, EN_AREA));
    }
}

/* 0xf7ced8 = slot 129 (action start: r1 category, r2 number): 4U slot 47's cases GU dropped. GU's own start then runs on */
int em068_01_start_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (!IS_HER(self) || regs[R1] != 7) return 0;
    switch (regs[R2]) {
    case 45: fire(self, 0, 1, 1); break;              /* 4U (9, 1): the launch of GU's kind 0 */
    case 47: fire(self, 0, 1, 2); break;              /* 4U (9, 2) */
    case 53: fire(self, 2, 3, 1); break;              /* 4U (11, 1): GU's kind 2 */
    case 55: fire(self, 2, 3, 2); break;              /* 4U (11, 2) */
    case 57: fire(self, K_13, K_14, 2); break;
    case 59: fire(self, K_15, K_16, 2); break;
    default: break;
    }
    return 0;
}

/* 0xf7d634(self, case, count): GU's scale request, from its handlers. Kinds 9 / 10 of our family are her 7/3 launches, so that one runs as GU's */
int em068_01_fire_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (!IS_HER(self) || FIELD(uint8_t, self, EN_ACT_CAT) != 7) return 0;
    uint32_t num = FIELD(uint8_t, self, EN_ACT_NUM), c = regs[R1];
    if ((num == 60 || num == 61) && (c == 4 || c == 5)) {       /* 4U 0x7638a0 with parameter 2 / 3 */
        fire(self, num == 60 ? (c == 4 ? K_9_P2 : K_10_P2) : (c == 4 ? K_9_P3 : K_10_P3), 0, 1);
        return 1;
    }
    if (num == 25 && c == 0) {                                  /* 4U 0x7651ec: (9, 2) at (-289.4, 213.8, 596.6) */
        fire(self, K_9_OFF3, K_10_OFF3, 2);
        return 1;
    }
    return 0;
}

/* 7/24's blast posts. 0xf85944 (movw r0, #0xb5f5; cmp r5, #0), r4 = monster: GU's test skips the post for variant != 0; 0xf85aa4 (mov r0, r4; mov
 * r1, #11): both paths meet here after the post. Mid hooks: always 0 */
static void *s_blast_owner;

int em068_01_blast_c(uint32_t *regs)
{
    void *self = (void *)regs[R4];
    if (IS_HER(self) && FIELD(uint8_t, self, EN_VARIANT) == 1) {
        FIELD(uint8_t, self, EN_VARIANT) = 0;
        s_blast_owner = self;
    }
    return 0;
}

int em068_01_blast2_c(uint32_t *regs)
{
    void *self = (void *)regs[R4];
    if (self && self == s_blast_owner) {
        FIELD(uint8_t, self, EN_VARIANT) = 1;
        s_blast_owner = 0;
    }
    return 0;
}

/* 0xa134c(self, table, ..) = the reaction runner, every frame of a reaction: her copies of GU's Najarala tables that wait 360 / 600 frames wait 60
 * more (4U's tables for em != 23 differ in exactly that op, C: 0xfdb274 / 0xfdb2a4 and the 3 pairs after it). Tables with op 0x3a keep theirs (4U has
 * one such table for both, 0xfdb394). Rows {u32 op, u32 arg}, closed by op 0xfd..0xff; pointers relocated, so copied at run time. */
#define RX_TABLES 8
#define RX_ROWS   16
#define RX_LO     0x17e6800u       /* uEm068_00's tables */
#define RX_HI     0x17e7d00u
static struct { uint32_t from; uint32_t rows[2 * RX_ROWS]; } s_rx[RX_TABLES];

int em068_01_rx_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    uint32_t t = regs[R1];
    if (!IS_HER(self) || t < (uint32_t)MAIN(RX_LO) || t >= (uint32_t)MAIN(RX_HI)) return 0;
    for (int i = 0; i < RX_TABLES; i++) {
        if (s_rx[i].from == t) {
            if (s_rx[i].rows[0] != 0xffffffffu) regs[R1] = (uint32_t)s_rx[i].rows;
            return 0;
        }
        if (s_rx[i].from) continue;
        const uint32_t *r = (const uint32_t *)t;
        int n = 0, wait = -1;
        for (; n < RX_ROWS; n++) {
            if (r[2 * n] == 3 && (r[2 * n + 1] == 360 || r[2 * n + 1] == 600)) wait = n;
            if (r[2 * n] == 0x3a) wait = -2;
            if (r[2 * n] >= 0xfd) break;
        }
        s_rx[i].from = t;
        if (wait < 0 || n == RX_ROWS) {
            s_rx[i].rows[0] = 0xffffffffu;
            return 0;
        }
        for (int k = 0; k < 2 * (n + 1); k++) s_rx[i].rows[k] = r[k];
        s_rx[i].rows[2 * wait + 1] += 60;
        logf("tnport: reaction table %x waits %u", t - (uint32_t)MAIN_BASE, s_rx[i].rows[2 * wait + 1]);
        regs[R1] = (uint32_t)s_rx[i].rows;
        return 0;
    }
    return 0;
}

/* 0x41b1dc (movw r0, #0x1669; strb r6, [r4, r0]), r4 = the scale, its end time out (state 4, 0x41b170): 4U 0xc698f0 at the end of its state 3, every scale of em != 23 that ends, hit or
 * timed out: 3 % chance of a shiny drop there. Until 0.2.1 this sat after the blast post (0x41b104), which her scales never reach (the signal, em068_01_jet.c header) */
int em068_01_drop_c(uint32_t *regs)
{
    uint8_t *shell = (uint8_t *)regs[R4];
    void *owner = shell ? shellOwner(shell) : 0;
    if (IS_HER(owner)) itemDrop(owner, shell + 0x40, 3, 0);
    return 0;
}

static void diag(void *self)
{
    static void *s_self;
    static uint32_t s_act, s_mot, s_lines, s_quest;
    if (port_quest_id() != s_quest) {                      /* each quest logs its first Tidal Najarala */
        s_quest = port_quest_id();
        s_self = 0;
        s_lines = 0;
    }
    if (s_self && self != s_self) s_self = 0;              /* the same quest played again: there is only ever one of her (log 21-51-59 went silent on the second run) */
#ifdef TN_TEST_HP_PCT
    {   /* test builds (GOG_DEFINES=TN_TEST_HP_PCT=n): she starts at n % of her max HP once (short kill / capture tests) */
        static void *s_hp_set;
        uint8_t *r = FIELD(uint8_t *, self, EN_RECORD);
        int32_t hp = FIELD(int32_t, r, REC_HP), mx = FIELD(int32_t, r, REC_HP + 4);
        if (s_hp_set != self && mx > 0 && hp == mx) {
            s_hp_set = self;
            FIELD(int32_t, r, REC_HP) = mx * TN_TEST_HP_PCT / 100;
        }
    }
#endif
    if (s_lines >= MAX_LINES) return;
    if (!s_self) {
        s_self = self;
        s_act = s_mot = ~0u;
        s_lines++;
        logf("tnport: em068_01 %x first dispatch, variant %u, index %u, quest %u", (uint32_t)(uintptr_t)self,
             FIELD(uint8_t, self, EN_VARIANT), FIELD(uint8_t, self, EN_ID + 6), port_quest_id());
    }
    if (self != s_self) return;
    uint32_t act = (uint32_t)FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM);
    uint32_t mot = curMotion(self);
    if (act != s_act) {
        uint8_t *r = FIELD(uint8_t *, self, EN_RECORD);
        int32_t mx = r ? FIELD(int32_t, r, REC_HP + 4) : 0;
        s_lines++;
        logf("tnport: em068_01 action %u/%u (motion %x) area %u script %u/%u hp %d%% rage %u", act >> 8, act & 0xff, mot,
             FIELD(uint8_t, self, EN_AREA), FIELD(uint8_t, self, EN_SCRIPT), FIELD(uint8_t, self, EN_SCRIPT + 1),
             mx > 0 ? FIELD(int32_t, r, REC_HP) * 100 / mx : -1, (uint32_t)RAGE_ON(self));
    } else if (mot != s_mot) {
        s_lines++;
        logf("tnport: em068_01 motion %x (action %u/%u)", mot, act >> 8, act & 0xff);
    }
    s_act = act;
    s_mot = mot;
}

/* 0xb0170(self, motion, second motion, flags, s0 = blend frames, s1) [4U 0x93947c]: the pair start of 2/45 [4U 0x76019c..]. When the AI stops her in the middle of her slither (2/4, motions 0x2b..0x2d: her
 * body stretched out) for the turn to the hunter, both games blend for 8 frames only. The log of 0.2.2 (21-51-59) shows it, one frame before the roar's turn: joint 6 moves 222 units in the first
 * frame of 0x10, 27 the frame before, her body still far from 0x10's pose (815 from her origin, 595 once it is there), so S: the whole body whips across in 0.14 s, the user's "teleports a little
 * right after the discovery". 4U has the same 8 (C), so this is cosmetic and a DEVIATION, wanted: she takes 30 frames for this one case. The trampoline's saved d0..d7 lie right below regs. */
#define BLEND_STOP   60.0f        /* 0.2.6: 30 -> 60. The log of 0.2.5 (2026-11-07 20-15-35, 13:36.656): no cut any more, but joint 6 still moved about 80 units a
                                     * frame for 6 frames (some 600 units in 0.25 s), the user: "teleportiert sich am Anfang des Kampfes immer noch". Twice as long. */
static void *s_stop_self;           /* em068_01_pair2_c: the cut of her slither is still blending, for s_stop_left more frames */
static int32_t s_stop_left;

int em068_01_pair_c(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R0];
    float *fp = (float *)(void *)(regs - 16);
    uint32_t from, to = regs[R1];
    if (!IS_HER(self) || to < 0xb || to > 0x18) return 0;
    from = curMotion(self);
    if (from < 0x2b || from > 0x2d || fp[0] < 0.0f || fp[0] >= BLEND_STOP) return 0;
    if (++s_n <= 40) logf("tnport: long blend %x -> %x, %d -> %d frames", from, to, (int32_t)fp[0], (int32_t)BLEND_STOP);
    fp[0] = BLEND_STOP;
    s_stop_self = self;
    s_stop_left = (int32_t)BLEND_STOP;
    return 0;
}

/* 0xb0230(self, motion, second motion, s0 = blend frames, s1 = frame): why the 30 frames above changed nothing (log of 0.2.3, 2026-11-07: joint 6 moves 669 and 534 units in the one frame after the start, then 1 unit a frame, so a cut; C for the numbers).
 * 2/45 starts the pair for the quadrant it remembers; on its next frame 0xf81abc sees her body angle on the other side and starts the pair again with blend 0.0 (0xf81b34, the word at 0xf81c0c; the frame is kept). Between two turns that is right: the angle is near 0, so the
 * layer weight is near 0 and the pose does not change. On a pose from her slither it throws the blend away and she snaps into the turn's pose: the user's "teleports at the start of the fight". 4U has the same code (S: 0x7601d4..). So while the blend of the cut runs, a pair
 * switch takes what is left of it. The engine saves the model's joints as the blend's start at each motion start (0x951504..0x951734, C), so the second start goes on from where she is. A DEVIATION, cosmetic and wanted. */
int em068_01_pair2_c(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R0];
    float *fp = (float *)(void *)(regs - 16);
    if (!IS_HER(self) || self != s_stop_self || s_stop_left <= 0 || fp[0] >= (float)s_stop_left) return 0;
    if (++s_n <= 40) logf("tnport: pair switch %x / %x keeps the blend, %d frames left", regs[R1], regs[R2], s_stop_left);
    fp[0] = (float)s_stop_left;
    return 0;
}

/* 0xf8672c, GU f861b0 (7/48-51 62-65, her spit, = 4U 0x765810), its start of 0x403 (r0 = this; s0 = s1 = 0.0 from f86708) at frame 134 of 0x402: both games start 0x403 with blend 0, a cut (C: 4U 0x765e80 s0 = s1 = s19 = 0.0, frame test 134.0 at 0x765fe4). The logs of 0.2.5 show it
 * (19-27-11 03:10.208, 20-15-35 13:49.873): joint 6 moves 74 / 61 units in that one frame, 15 to 30 in the frames around it, about 13 s after the discovery
 * in both fights. A DEVIATION, cosmetic, as the blends above: 8 frames. Only s0 (the blend); s1 (the start frame) stays 0. */
#define SPIT_BLEND   8.0f
int em068_01_spit403_c(uint32_t *regs)
{
    static uint32_t s_n;
    void *self = (void *)regs[R0];
    float *fp = (float *)(void *)(regs - 16);
    if (!IS_HER(self) || curMotion(self) != 0x402 || fp[0] >= SPIT_BLEND) return 0;
    if (++s_n <= 40) logf("tnport: spit 402 -> 403, blend %d -> %d frames", (int32_t)fp[0], (int32_t)SPIT_BLEND);
    fp[0] = SPIT_BLEND;
    return 0;
}

/* Log only: a motion start other than a pair (0xafda4 via 0x72628 / 0x53a164) clears the second layer at once (0x53a164: layer 1 -> motion 0xffff, blend 0;
 * 0xafeb4: weight this+0x638 = 0.0, C). After 2/45 that layer holds the turned pose with the body angle's weight, so the body may jump by that part (S: the
 * log of 0.2.5 19-27-11 03:23.292, 2/45 -> 7/29, joint 6 moves 58 units in the first frame of 0x20e, then 4, 6, 8 ...). This line names the weight it lost. */
#define EN_LAYER_W   0x638
static void layer_watch(void *self)
{
    static void *s_self;
    static float s_w;
    static uint32_t s_mot, s_n;
    float w = FIELD(float, self, EN_LAYER_W);
    uint32_t mot = curMotion(self);
    if (s_self == self && mot != s_mot && s_w > 0.05f && w == 0.0f && s_n < 60) {
        s_n++;
        logf("tnport: layer weight %d%% dropped at once, motion %x -> %x (action %u/%u)", (int32_t)(s_w * 100.0f), s_mot, mot,
             FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM));
    }
    s_self = self;
    s_w = w;
    s_mot = mot;
}

/* Log only, the proof for the user's "after the roar she teleports a little" (test of 0.2.1). The log of that test shows no stop in the game's frame time and no code that moves her
 * there (notes/plan.md). Per frame: her position step, yaw step and the step of a body joint (the visible body, motion included). A line when a step is at least 3 times the last one and over
 * 30 units (joint: 40), or the yaw over about 11 degrees; and every frame for a while after each roar (motion 0x32), and after each such step: its shape tells a cut from a blend. */
#define JUMP_LINES   400u
#define AFTER_ROAR   45             /* frames logged after motion 0x32 ends */
#define AFTER_JUMP   14             /* frames logged after a sudden step */
static void jump_watch(void *self)
{
    static void *s_self;
    static float s_pos[3], s_joint[3], s_step, s_jstep;
    static uint32_t s_yaw, s_mot, s_n;
    static int s_after;
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    float j[4], d[3], e[3], step, jstep;
    uint32_t yaw, dyaw, mot = curMotion(self);
    int big;
    if (!rec) return;
    jointPos(self, 6, j);
    yaw = FIELD(uint32_t, rec, REC_YAW) & 0xffff;
    for (int i = 0; i < 3; i++) {
        d[i] = FIELD(float, rec, REC_POS_X + 4 * i) - s_pos[i];
        e[i] = j[i] - s_joint[i];
    }
    step = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];             /* squared: the tests below compare squares */
    jstep = e[0] * e[0] + e[1] * e[1] + e[2] * e[2];
    dyaw = (yaw - s_yaw) & 0xffff;
    if (dyaw > 0x8000) dyaw = 0x10000 - dyaw;
    if (s_self == self) {
        if (s_mot == 0x32 && mot != 0x32) s_after = AFTER_ROAR;
        big = (step > 900.0f && step > 9.0f * s_step) || (jstep > 1600.0f && jstep > 9.0f * s_jstep) || dyaw > 0x800;
        if (big && s_after < AFTER_JUMP) s_after = AFTER_JUMP;
        if ((big || s_after > 0) && s_n < JUMP_LINES) {
            s_n++;
            logf("tnport: jump%s motion %x frame %d (was %x) step2 %d (was %d) joint step2 %d (was %d) yaw %d at %d %d %d joint %d %d %d", big ? "!" : "", mot, (int32_t)motionFrame(self), s_mot,
                 (int32_t)step, (int32_t)s_step, (int32_t)jstep, (int32_t)s_jstep, dyaw, (int32_t)FIELD(float, rec, REC_POS_X), (int32_t)FIELD(float, rec, REC_POS_X + 4),
                 (int32_t)FIELD(float, rec, REC_POS_X + 8), (int32_t)j[0], (int32_t)j[1], (int32_t)j[2]);
        }
        if (s_after > 0) s_after--;
    }
    s_self = self;
    s_step = step;
    s_jstep = jstep;
    s_yaw = yaw;
    s_mot = mot;
    for (int i = 0; i < 3; i++) {
        s_pos[i] = FIELD(float, rec, REC_POS_X + 4 * i);
        s_joint[i] = j[i];
    }
}

/* 0xf8903c = slot 125 (action dispatcher, every frame) */
int em068_01_act_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (!IS_HER(self)) return 0;
    diag(self);
    scale_watch(self);
    part_watch(self);
    jump_watch(self);
    layer_watch(self);
    if (s_stop_left > 0 && self == s_stop_self) s_stop_left--;
    em068_01_jet_frame(self);
    /* 4U 0x764790: 7/20's second step at G rank */
    if (FIELD(uint8_t, self, EN_ACT_CAT) == 7 && FIELD(uint8_t, self, EN_ACT_NUM) == 20 &&
        FIELD(uint8_t, FIELD(uint8_t *, self, EN_RECORD), REC_STEP0) == 1 && questRank(QUEST_MGR) >= 5)
        setMotionSpeed(self, 1.5f);
    return 0;
}
