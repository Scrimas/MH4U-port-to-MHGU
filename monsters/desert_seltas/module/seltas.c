/* seltas.c: Desert Seltas (GU Seltas variant 1, ID 0x14c) and Desert Seltas Queen (GU Seltas Queen variant 1, ID 0x145): GU's own classes uEm076_00 /
 * uEm069_00 run them (package.toml gu_classes; notes/plan.md). GU kept 4U's species tests of em 94 / 95 as variant tests (C: 31 / 86 reads of the
 * variant byte), and their moves come from their AI tables (tools/build_seltas_arc.py). This file holds what his 4U death and entry need, on his
 * slot 125 (the action dispatcher, every frame; C unless marked):
 *  - launch_end (0.1.7, 0.1.11): the Desert Seltas dies when his launched flight ends, by 4U's death by impact (11/8, the burst);
 *  - buried_entry (0.1.10, 0.1.12): a new Desert Seltas enters buried for his Queen's pull, 4U's 12/1;
 *  - quiet_frame, seltas_sting, seltas_mark (0.1.13 .. 0.1.16): her dug-out male joins her fight silently, announced by nothing.
 * Her reactions (category 10) are ported in seltas_react.c, the pair in seltas_pair.c, their shots in seltas_shots.c.
 * Multiplayer: not tested. All addresses go through MAIN / FN; no fixed ranges. Logs: prefix "dsport:". */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define EN_AREA    0x1054           /* u8 current area */
#define IS_DS(p)   ((p) && FIELD(uint16_t, (p), EN_ID) == DESERT_SELTAS_EM_ID)
#define N_UNITS    6                /* one state per unit: the Queen's quests run her and her Desert Seltas, who comes back */

static int unit_gone(void *u) { return !u || !FIELD(uint32_t, u, EN_ID); }

/* His launched flights (0.1.5; C = read in code): 7/64 and 7/66 are his rides on the Queen (GU 0xfd8fb0 / 0xfd9d94 = 4U
 * 0x78292c / 0x7835b4); each ends by setting 7/65 / 7/67, the launched flight 0xfd9438(this, 0 / 1) = 4U 0x782da8. The
 * Queen's 16/5 launch that leads to 7/67 is the Desert pair's own (only 4U's em095_cmd g14 s0 starts a 16/x action; GU's
 * own tables never do). The flight's steps (rec+0x1a1): 0 set up, 1 aimed approach (mode 0), 2 flight until a wall
 * contact (rec+0x8f0, counted by GU's stage contact 0xa75f4) or its timer rec+0x1bc runs out (36 frames in mode 1, 60 in
 * mode 0, counted down at this+0x1c), 3 the crash (attack 35), 4 nothing more: neither game's handler ends the action
 * itself. The 0.1.4 test has him 101 s in 7/67 until the quest ended (GU's same-action watchdog 0xad7b4 = 4U 0x93f6e4
 * ends an action only after 7200 frames of this+0x13f8).
 * The launched male's end (0.1.7; the user, 2026-11-10: "Ja, so einbauen"). 4U, per monsterhunterwiki.org
 * Desert_Seltas_Queen_(MH4U) (S, not code): her "Beetle Cannon" fires him from her tail pincers and "shatters him",
 * her tail launch kills him "leaving behind no carvable remains", and she digs up a new one. The 4U code that kills him
 * is NOT found (his crash step posts uShell003 240: power 10, type 10, no kill; neither class writes his HP). What both
 * games have (C): his flight handler ends no action (above), and in his death state (category 12) after a launched
 * flight the corpse time rec+0x5cc4 (set at death from 0xbd7e0, counted down at 0xc93e4) is zeroed: GU slot 119
 * 0xfc9104..0xfc9168 when the pair's +0x6a is set (his crash step sets it), 4U 0x77cfdc / 0x77d214. So he is meant to
 * die after the flight, with no corpse to carve.
 * Here: SHATTER_DELAY frames after his crash step (rec+0x1a1 past 3, the pair's +0x6a set) his HP goes to 0 through
 * GU's setHP (0x9a764, a negative value = 0); GU's death and its corpse-time rule do the rest, and her quests bring
 * him back (restore count). Normal Seltas untouched. Multiplayer: every machine runs it at the same step (as GU's own
 * handler); not tested.
 * His death reaction (0.1.11, C; the user on 0.1.9 after playing 4U: in 4U he always bursts, ours never did). 0.1.7
 * took GU's down decision 0x9b2bc(this, 0), which picks the death by movement state: 11/1, a plain death in the air.
 * 4U's em message dispatcher (0x687998) has two death messages: type 5 = that decision (0x92c0a4 = GU 0x9b2bc), type 6
 * = 0x948614 (= GU 0x9c2b4, the same body: 0x921dfc(13) bits into W+0x7993, then 11/8). His 11/8 (4U 0x77c91c case 8
 * = GU 0xfdbdb4 case 8, kept by GU) runs, after a launched flight (7/65 / 7/67 or the pair's +0x6a), its own script
 * (4U 0xfdd684 = GU 0x17ee3e0: a jump arc, then motion 0x350); motion 0x350 is Desert-only (4U em094 bank 3 slot 0x50;
 * GU's em076_00 bank 3 has 71 slots) and posts MEF id 14 = em094_204 at frame 1 (our PSL and PEL carry both): the
 * burst. So the death here goes through GU's type-6 reaction 0x9c2b4: 11/8 with that script. What sends 4U's type-6
 * message at his crash is not traced (S: the crash blast uShell003 240, the post GU dropped). Also not ported: 4U's
 * stun check 0x78968c at the end of that 11/8 (GU's twin stores rec+0x2bd into the pair's +0x78 instead). */
#define SHATTER_DELAY 10u           /* frames: GU's crash attack 35 (em076_00 attackdata) hits in frames 0..10 */
typedef void (*set_hp_t)(void *self, int32_t hp);
typedef int (*react_t)(void *self);
#define setHP     FN(set_hp_t, 0x9a764)
#define fallDeath FN(react_t, 0x9c2b4)   /* [0x948614] death message type 6: 11/8 */

static void launch_end(uint8_t *self)
{
    static struct { uint8_t *self; uint32_t frames; } s_l[N_UNITS];
    uint32_t act = (uint32_t)FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM);
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD), *pair = FIELD(uint8_t *, self, 0xcac0);
    int ended = (act == (7u << 8 | 65) || act == (7u << 8 | 67)) && rec && rec[0x1a1] > 3 && pair && pair[0x6a];
    __typeof__(&s_l[0]) u = 0;
    for (int i = 0; i < N_UNITS && !u; i++) if (s_l[i].self == self) u = &s_l[i];
    if (!ended) { if (u) u->self = 0; return; }
    if (!u) {
        for (int i = 0; i < N_UNITS && !u; i++) if (unit_gone(s_l[i].self)) u = &s_l[i];
        if (!u) u = &s_l[0];
        u->self = self; u->frames = 0;
    }
    if (++u->frames != SHATTER_DELAY || FIELD(int32_t, rec, REC_HP) <= 0) return;
    logf("dsport: ds shatters at the end of his launched flight %u/%u (hp %d, wall %u, movement state %u): 4U's death "
         "by impact (11/8, motion 350, burst em094_204), no corpse", act >> 8, act & 0xff, FIELD(int32_t, rec, REC_HP),
         rec[0x8f0], rec[0x1ba]);
    setHP(self, -1);
    fallDeath(self);
}

/* His entry as 4U's (0.1.10; the user, 2026-11-11, after playing 4U: the Queen soon digs a new one out of the ground,
 * ours never did). 4U (C): the Seltas class's entry slot 54 (0x7890a8) gives category 12 number 0 to the Seltas (em
 * 25) and number 1 to the Desert Seltas, and clears the pair's +0x6a for him; his 12/1 (0x777c6c) runs sleepFlagA,
 * sleepFlagB, W+0x978 = 1, setTargetMode(4), vertSet(this, 0x93e7b4(this)), then setActionNext(6, 3): he enters
 * BURIED. In 6/3 (GU 0xfd440c = 4U 0x784308) he waits for his partner's pull (her 7/72, motion 0x465) and comes out
 * with 6/4, or digs out himself (6/1) when he has no partner (GU 0xfd4548).
 * GU (C): slot 137 (0xfc96dc) gives 12/0 to every variant (12/1 only on its stage 15: GU's 12/1 keeps 4U's first
 * three steps, rec+0x918 = 4U W+0x978, then flies to a fixed point, 0xfdc218). So the Desert Seltas flew in like a
 * Seltas (0.1.9 test, her m10924 quest: 12/0, motion 0x101, 188 s of play after his death).
 * Here, on the first frame of a Desert Seltas' 12/0: the pair's +0x6a cleared (4U slot 54); with his Queen in his
 * area, 4U's 12/1 body with GU's twins (sleepFlagA 0x7fcbc, sleepFlagB 0xc0410, setTargetMode 0xbc8b0, vertSet
 * 0xbf7bc of 0xbf6e8 = 4U 0x93e7b4 (S: monsters/monoblos/module/em007_01_mv_h.c), setActionNext 0x76984) in place of
 * GU's fly-in. GU's 6/3 puts him at the point rec+0x1d0 on its first step (4U: W+0x218); what 4U holds there at an
 * entry is not traced, so that point is his Queen's position (her pull brings him out at her side, as the user saw
 * in 4U; S). Without his Queen in the area his entry stays GU's fly-in (a DEVIATION: 4U buries him there too).
 * His wait for her pull (0.1.12, C unless marked; the 0.1.11 log, her m10924 quest: 2.4 s after his burst the new one was
 * in 6/3 and the next frame in 6/1, out by himself; the user: "warum spawnt nach dem platzen sofort wieder eine desert
 * seltas"). 6/3 (4U 0x784308 = GU 0xfd440c, the same tests) digs him out (6/1) when the pair's timer +0x54 runs out
 * (timerDown 0x72128 = 4U 0xb0709c) before his partner starts her pull (7/72). Only his dig-in sets that timer (GU
 * 0xfd3ec4 at its motion end: 3600 frames, 4U the same), and 4U's 12/1 skips the dig-in: what fills it for a new male
 * in 4U is NOT found. So the timer is set here to his dig-in's 3600 frames, which gives her the time to pull him out as
 * the user saw in 4U (a DEVIATION until 4U's source of it is found). The restore itself comes as soon as his body is
 * gone (2.4 s after the burst, no corpse: both games' rule after a launched flight, C).
 * Multiplayer: every machine runs the dispatcher; setActionNext starts 6/3 on the controlling machine and replays it
 * elsewhere (module/game.h); not tested.
 * No discovery sound for him (0.1.13, C unless marked; the user on 0.1.12: when she pulls the new one out, the sound
 * that a new monster discovered the hunter plays, "das darf nicht passieren"). A unit's alert state rec+0x2c0 (0 calm,
 * 1 set by GU's damage handlers, 2 by its noticing the hunter, 0x7eb28 / 0x7eee0) changes only through 0xbcb9c(this,
 * v), and its 0xa4444 plays the unit's sound request 22 only on 0 -> 2 (23 on 2 -> 0). GU's reset (0xb8c54) puts the
 * restored male at 0, so noticing the hunter after her pull played 22. Here, when his Queen is not calm, his entry
 * takes state 1 through 0xbcb9c (silent: no sound for 1, and 1 -> 2 plays none). Whether 4U plays it there is not
 * traced (a DEVIATION by the user's rule: her new male joins her fight, he discovers nothing).
 * 0.1.14 (the user on 0.1.13: the discovery sound still plays at each pull-out; S unless marked): GU's own restore
 * entry 12/0 (0xfcf3bc mode 2, 0xfcf3e4..0xfcf400) also sets rec+0x5c8c = 1 (and rec+0x990, which his 6/3 sets each
 * frame); 4U's 12/1 does not, but GU's restored Seltas flew in with it and no discovery sound was reported then
 * (tests up to 0.1.9). GU's own entries of many classes set it (0xcf8fe0 ...); 0xaf3f8 reads it with rec+0x5dfc for
 * the unit's flag this+0x10 bit 3. So the buried entry sets it too (the sound itself is sSoundControl's: below). */
#define DIG_WAIT    3600.0f         /* frames: GU 0xfd4014 (his dig-in's end) */
#define QUIET_MAX   3600u           /* frames: no discovery sting for him at most this long (seltas_sting, below) */
#define QUIET_AFTER 180u            /* frames after he left the ground */
static void *s_quiet;               /* her new male while his restore must not be announced */
static uint32_t s_quiet_left, s_quiet_quest;
typedef void (*alert_t)(void *self, uint32_t state);
#define setAlert    FN(alert_t, 0xbcb9c)
#define QUEEN_EM_NUM 0x45u          /* the Seltas Queen class's em number (ID low byte): 0x45 normal, 0x145 Desert */
typedef float (*speciesF_t)(void *self);
typedef void (*selfF_t)(void *self, float v);
#define sleepHeight FN(speciesF_t, 0xbf6e8)   /* [0x93e7b4] */
#define vertSet     FN(selfF_t, 0xbf7bc)      /* [0x916140] rec+0x5c = v, rec+0x1b9 = 1 */

static int buried_entry(uint8_t *self)
{
    static uint8_t *s_done[N_UNITS];
    uint32_t act = (uint32_t)FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM);
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD), *pair = FIELD(uint8_t *, self, 0xcac0), *q, *qrec;
    int slot = -1;
    for (int i = 0; i < N_UNITS; i++) if (s_done[i] == self) slot = i;
    if (act != 12u << 8) { if (slot >= 0) s_done[slot] = 0; return 0; }
    if (slot >= 0 || !rec || rec[0x1a1] != 0 || FIELD(int32_t, rec, REC_HP) <= 0) return 0;   /* once, first frame */
    for (int i = 0; i < N_UNITS && slot < 0; i++) if (!s_done[i] || unit_gone(s_done[i])) slot = i;
    s_done[slot < 0 ? 0 : slot] = self;
    if (pair) pair[0x6a] = 0;                                            /* 4U slot 54 (0x789120) */
    q = pair ? FIELD(uint8_t *, pair, 0x50) : 0;
    qrec = q ? FIELD(uint8_t *, q, EN_RECORD) : 0;
    if (!qrec || (FIELD(uint16_t, q, EN_ID) & 0xff) != QUEEN_EM_NUM || FIELD(int32_t, qrec, REC_HP) <= 0 ||
        FIELD(uint8_t, q, EN_AREA) != FIELD(uint8_t, self, EN_AREA)) {
        logf("dsport: ds enters as GU's Seltas (12/0, flies in): no Queen in his area %u", FIELD(uint8_t, self, EN_AREA));
        return 0;
    }
    sleepFlagA(self);
    sleepFlagB(self);
    rec[0x918] = 1;
    setTargetMode(self, 4);
    vertSet(self, sleepHeight(self));
    for (int k = 0; k < 3; k++) FIELD(float, rec, 0x1d0 + 4 * k) = FIELD(float, qrec, REC_POS_X + 4 * k);
    FIELD(float, pair, 0x54) = DIG_WAIT;
    if (FIELD(uint8_t, qrec, 0x2c0) && FIELD(uint8_t, rec, 0x2c0) == 0) setAlert(self, 1);   /* in her fight, silently */
    FIELD(uint8_t, rec, 0x5c8c) = 1;                                     /* as GU's restore entry 12/0 (0xfcf3f8) */
    s_quiet = self; s_quiet_left = QUIET_MAX; s_quiet_quest = port_quest_id();   /* no sting for him (seltas_sting) */
    setActionNext(self, 6, 3);
    logf("dsport: ds enters buried as in 4U (12/1 -> 6/3) under his Queen in area %u, waits up to %d frames for her pull "
         "(alert: his %u, hers %u)", FIELD(uint8_t, self, EN_AREA), (int)DIG_WAIT, FIELD(uint8_t, rec, 0x2c0),
         FIELD(uint8_t, qrec, 0x2c0));
    return 1;
}

/* No discovery sting for her new male (0.1.15, C unless marked; the user on 0.1.14: the discovery sound still plays at
 * each pull-out, "die Königin zieht im Laufe des Kampfes ja viele Desert Seltas aus dem Boden"). The 0.1.14 log (her
 * m10924 quest): 4.4 s after his restore, while he was still in the ground, sSoundControl requested ch 4 kind 6 slot 0 id 0xa
 * (from 0x4e5288), the same request as the first discovery at the quest start; his own alert went 0 -> 1 silently.
 * sSoundControl's unit scan 0x4e4224 raises its sting flag ctl+0x1b9d (0x4e4ef8) for a unit in battle whose slot is
 * not yet announced (+0x1b5c, set to 1 there), and clears that mark while the unit's alert state is 0 (0x4e4b18): his
 * death set it to 0 (0x75c40), so every restored male was announced again. 0x4e51c8 posts the sting when the flag is
 * set (0x4e5240..0x4e5288: id 10, 14 for variant 4). Here: from his buried entry until 180 frames after he left the
 * ground (6/3, 6/4; at most 60 s), a mid hook at 0x4e5240 clears the flag before that post. A DEVIATION from GU's
 * sound control by the user's rule (4U announces none of her dug-out males, as the user hears in 4U); every other first
 * discovery stays. */
static void quiet_frame(uint8_t *self)
{
    uint32_t act = (uint32_t)FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM);
    if (self != s_quiet) return;
    if (port_quest_id() != s_quiet_quest) { s_quiet = 0; return; }
    if (act != (6u << 8 | 3) && act != (6u << 8 | 4) && s_quiet_left > QUIET_AFTER) s_quiet_left = QUIET_AFTER;
    if (s_quiet_left) s_quiet_left--;
    if (!s_quiet_left) s_quiet = 0;
}

/* No "new monster" at all for him (0.1.16, S unless marked; the user on 0.1.15: the sound is gone, but when the new
 * Desert Seltas appears under the ground the hunter stops briefly "wie erschrocken"). The 0.1.15 log: the sting flag was
 * raised 21 ms after his buried entry (C), the moment the hunter was startled; sSoundControl's scan announced him as a
 * new unit because it had cleared his announce mark at his death (0x4e4b18, C). Here that mark is kept for her Desert
 * Seltas while his Queen fights (a mid hook at the clear: r4 = the mark, r5 = the unit + 0x1428, C), so his restore is
 * no new unit to it and nothing is announced; seltas_sting stays as a second guard. Whether the hunter's startle hangs
 * on that announcement is not traced (S). */
#define ENEMY_MGR   0x1851fe0u
typedef uint8_t *(*enemy_at_t)(void *mgr, uint32_t k);
#define enemyAt FN(enemy_at_t, 0x5ceb4)     /* the k-th of the 10 monster slots, or 0 */
static int is_monster(void *p)
{
    void *mgr = *(void **)MAIN(ENEMY_MGR);
    for (uint32_t k = 0; mgr && k < 10; k++) if ((void *)enemyAt(mgr, k) == p) return 1;
    return 0;
}
static int queen_fights(uint8_t *self)
{
    uint8_t *pair = FIELD(uint8_t *, self, 0xcac0), *q = pair ? FIELD(uint8_t *, pair, 0x50) : 0;
    uint8_t *qrec = q ? FIELD(uint8_t *, q, EN_RECORD) : 0;
    return qrec && (FIELD(uint16_t, q, EN_ID) & 0xff) == QUEEN_EM_NUM && FIELD(int32_t, qrec, REC_HP) > 0 &&
           FIELD(uint8_t, qrec, 0x2c0) != 0;
}
int seltas_mark_c(uint32_t *regs)          /* 0x4e4b18; 1 = the clear skipped (MID_EXIT 0x4e4b20) */
{
    static uint32_t s_n;
    uint8_t *self = regs[R5] ? (uint8_t *)(uintptr_t)(regs[R5] - EN_RECORD) : 0;
    if (!self || !is_monster(self) || !IS_DS(self) || !queen_fights(self)) return 0;
    if (++s_n <= 20) logf("dsport: ds announce mark kept (his Queen fights): his next restore is no new monster");
    return 1;
}

/* 0x4e5240 in sSoundControl 0x4e51c8 (r4 = ctl), right before it reads the sting flag ctl+0x1b9d */
int seltas_sting_c(uint32_t *regs)
{
    static uint32_t s_n;
    uint8_t *ctl = (uint8_t *)regs[R4];
    if (!s_quiet || !ctl || !ctl[0x1b9d] || port_quest_id() != s_quiet_quest) return 0;
    ctl[0x1b9d] = 0;
    if (++s_n <= 20) logf("dsport: discovery sting for her new Desert Seltas not played (as in 4U)");
    return 0;
}

/* 0xfdc074 = uEm076_00 slot 125 (Seltas' action dispatcher, every frame): the Desert Seltas' quiet window, entry and
 * launch end. 1 = GU's dispatcher skipped this frame (his 4U entry ran instead) */
int seltas_ds_act_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (!IS_DS(self)) return 0;
    quiet_frame((uint8_t *)self);
    if (buried_entry((uint8_t *)self)) return 1;
    launch_end((uint8_t *)self);
    return 0;
}
