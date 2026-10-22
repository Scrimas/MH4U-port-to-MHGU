/* Dalamadur AI: the floor class of the target, head condition 3 / tail condition 4 of the command tables (GU slot
 * 133 = 4U slot 51: head 0x774888, tail 0x8a2864).
 *
 * 4U (C): cond = W+0x27c (target slot 0 param) == 255 ? 0 : class[0x93e074(this, 0, 0)]. 0x93e074(this, flags, slot)
 * = 0x9463d0(this, flags, slot, kind W+0x278+slot, sub W+0x27a+slot, param W+0x27c+slot), which returns the FLOOR ID
 * of the target (byte 5 of a 0x30-byte ground record): 255 for param 255; kind 1 hunter -> its ground record
 * ([p+0xe30]+0x475); kind 2 Palico (unless flags & 0x80) -> W+0x2dfd when active; kind 3 enemy (unless flags & 0x40)
 * -> W+0x5f5; any other kind (and kind 7 unless W+0xb0c == 10) -> stage collision probe 0x2b9fa8 at the slot's
 * position W+0x218 + 16 * slot in area W+0x14c, byte 5 of the hit record (preset 255).
 * GU 0x979cc is the same function (C, read): kinds 1 / 2 / 3 -> the character's this+0x1065 (hunter 0xc2eb4, Palico
 * 0xc2f88 + vt+0x88 == 1, enemy 0xc3050), kind 7 with this+0x72fc == 10 -> 0x48cba4, else the probe 0x49ba8 (->
 * 0x18192c, = 4U 0x2b9fa8) at rec+464 + 16 * slot in area this+0x1054, record copied from this+0x1060, byte 5 preset
 * 255. Its caller 0xb73c8 (= 4U 0x93ed2c, EMC op 0x79 "class of the slot-0 target": same 64 / 192 / 256 / 512 /
 * 1536 result bits, S) passes this byte with its own this+0x1065 to the route lookup 0x498d0 -> 0x50350c = the
 * area's RouteFindData
 * (stage+0x3c0 + 4 * area, C), whose rows are the collision groups' w1 byte 3 (stage4u2gu.py "monster route
 * finding", S). sbc.convert_4u keeps w1 byte 3, so Speartip Crag (GU m29 area 1 = 4U m08a01d-a-g00) has 4U's
 * floors (C, scratchpad ai/floors.py; head faces +z from the origin):
 *   1 k00 platform z 4600..7600 y 0 | 2 k01 bridge + spire base y 0 | 3 spire ring y 300 | 4 / 11 / 12 spire tops
 *   y 1340 / 1660 / 2850 | 5 slope in front z 1500..5400 y 0..320 | 6 x < 0 terrace y 650 | 7 x -3900..-2900 ledge
 *   y 3400 | 8 x -4100..-2600 ledge y 1200 | 9 x -4100..-2850 top y 5000 | 10 low floor y -850 (x < -1200, and
 *   under the bridge after the k01 break) | 0 walls, fall planes (y -5000), unassigned
 * The selector (EMC op 0x6f -> slot 133) calls this only on the machine that controls the half (GU think check
 * 0x82538); the hunter's ground byte may differ between machines, the chosen action reaches them through GU's action
 * sync, so nothing here can make the halves diverge. */
#include "game.h"
#include "util.h"
#include "em090.h"

/* GU 0x979cc(this, flags, slot, kind, sub, param) -> floor id (u8, 255 = none) [4U 0x9463d0] (C) */
typedef uint32_t (*targetFloor_t)(void *self, uint32_t flags, uint32_t slot, uint32_t kind, uint32_t sub,
                                  uint32_t param);
#define targetFloor FN(targetFloor_t, 0x979cc)

/* floor id 0..10 -> condition value; 11.. (and 255) -> 4. Head jump table 0x774984 (floor 7: the state test below),
 * tail 0x8a29ac (C) */
static const uint8_t k_class[2][11] = {
    {4, 1, 0, 0, 2, 1, 1, 0, 2, 3, 0},
    {4, 1, 0, 0, 2, 1, 1, 0, 1, 3, 0},
};

static uint8_t s_class[2] = {255, 255};   /* the last answer per half, for the tally line (255 = never asked) */

int dala_floor_class(void *self, uint32_t tail)
{
    static uint16_t s_last[2];
    static uint32_t s_n;
    const uint8_t *k = REC(self) + REC_TGT_KIND;   /* target slot 0: kind +0, sub +2, param +4 */
    tail = tail ? 1 : 0;
    if (k[4] == 255) { s_class[tail] = 0; return 0; }
    uint32_t floor = targetFloor(self, 0, 0, k[0], k[2], k[4]) & 0xff;
    uint32_t c = floor < 11 ? k_class[tail][floor] : 4;
    /* head, floor 7 (4U 0x7749b8): hunter -> 3 if 0xd05d2c(hunter, 0, 0) (player work [p+0xa29c]+0xf0 bit 14),
     * Palico (0x92c90c) -> 3 if 0x981a14 ([obj+0x3c78]+0x7d0 bit 1), else 0. Neither state has a GU counterpart yet:
     * taken as false (G), the value 4U gives whenever the target is not in that state. */
    if (!tail && floor == 7 && (k[0] == 1 || k[0] == 2))
        dala_stub(self, k[0] == 1 ? "head cond 3 floor 7: hunter state 0xd05d2c as 0" :
                                    "head cond 3 floor 7: Palico state 0x981a14 as 0", k[2], k[4]);
    uint16_t key = (uint16_t)(0x8000 | floor << 4 | c);
    if (s_last[tail] != key && ++s_n <= 300)
        logf("dalaport: %s %x target floor %u -> cond %u (slot 0 kind %u sub %u param %u) ctl %u", tail ? "tail" : "head",
             (uint32_t)self, floor, c, k[0], k[2], k[4], FIELD(uint8_t, self, EN_CONTROLLED));
    s_last[tail] = key;
    s_class[tail] = (uint8_t)c;
    /* think trace (next test): this condition is asked once per pick in the peak / ground / placement-1 branches of
     * every selector, so each line marks one AI think; with the "ai .. start" lines it shows picks replaced before
     * they ran. 150 per half. */
    static uint32_t s_t[2];
    if (++s_t[tail] <= 150)
        logf("dalaport: ai %s think class %u (floor %u) during %u/%u frame %u", tail ? "tail" : "head", c, floor,
             FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM), FIELD(uint32_t, self, F_FRAMES));
    return (int)c;
}

/* ---- the em switch of the head's root (4U EMC op 0x46) ----
 * 4U op 0x46 (interpreter 0x94f488, handler 0x951ff0) = switch on the em number W+0x1c0. GU dropped it: its jump table
 * 0x837ac sends 0x46 to 0x8470c (`return 0`), which only skips the token, so the case labels are skipped too and every
 * body runs in turn (C; GU's own em001_00 table has no op 0x46 left where 4U em001 has one). The head's root g0 s0
 * holds seven such blocks: `46 00 | 46 01 6e: 20 (7+k) | 46 02: 6a 00 | 6a 01 05: 20 (7+k) | 6a 02: 20 k | 6a ff | 46
 * ff` (k = 1..7 by HP band; s8..s14 = the Shah selectors, s1..s7 the regular ones; op 0x20 = call a group-0 script and
 * return, C in both games: 4U 0x950b4c stack W+0xb17 / +0xb24, GU 0x8572c stack this+0x7307 / +0x7314). So in GU
 * every root pass called the Shah selector and then the rank switch's one: two picks per pass, and in High Rank
 * (op 0x6a = quest rank tier, GU 0x3a8d68: 1 / 3 / 5; 4U 0x69ae70) the regular head reached Shah's 7/86, 7/87, 7/88.
 * Fix (build_dalamadur_arc.py emc_em_switch): each 0x46 block becomes the same block on op 0x6f (monster condition,
 * GU slot 133) with the port-only id 70; em090_cond answers it here with the em number. Checked in scratch on every
 * condition combination: the rebuilt table under GU's rules reaches the same actions as 4U's under 4U's (C). */
#define questRank FN(uint32_t (*)(void), 0x49938)   /* GU 0x3a8d68(*quest mgr): rank tier 1 / 3 / 5 (G), else 0 */

int dala_cond_em(void *self)
{
    static uint8_t s_logged;
    uint32_t shah = FIELD(uint8_t, self, EN_VARIANT) ? 1 : 0;
    if (!(s_logged & (1u << shah))) {
        s_logged |= (uint8_t)(1u << shah);
        logf("dalaport: head %x cond 70 (4U op 0x46, em switch) -> %u, quest rank %u ctl %u", (uint32_t)self,
             shah ? 110u : 24u, questRank(), FIELD(uint8_t, self, EN_CONTROLLED));
    }
    return shah ? 110 : 24;
}

/* ---- next-test log: what the AI picks, repeats included ----
 * The "action" lines (dala_log_action) skip an action equal to the last one, so a spammed move shows once. Here every
 * action start (GU slot 129, every machine: GU replays the actions) counts its (cat, num) and the frames the previous
 * action ran (F_FRAMES = slot-125 runs; < 4 = "short": a handler that ended at once or a pick replaced before it
 * ran). The first 150 starts per half get one line each; every 16 finished actions of a half one line with the
 * counts / mean run time and the AI's inputs at that moment: HP band (head cond 2 / tail cond 3), arena breaks, body
 * placement, rage byte rec+0x518 (EMC op 0x1c), the last target floor class (head cond 3 / tail cond 4) and the quest
 * rank (op 0x6a). 40 lines per half at most. */
int dala_hp_band(void *self);    /* em090_act.c */
int dala_broken(void *self);     /* dala_stage.c */

#define TALLY_N 24
typedef struct { uint16_t act; uint16_t n; uint32_t frames; } tally_t;
typedef struct { tally_t t[TALLY_N]; void *self; uint32_t starts, ended, last_f, lines, shorts; uint16_t cur; } tallies_t;
static tallies_t s_tally[2];

static char *put_s(char *p, char *e, const char *s) { while (*s && p < e) *p++ = *s++; return p; }
static char *put_u(char *p, char *e, uint32_t v)
{
    char d[10];
    int n = 0;
    do { d[n++] = (char)('0' + v % 10); v /= 10; } while (v);
    while (n && p < e) *p++ = d[--n];
    return p;
}

void dala_ai_tally(void *self, uint32_t tail, uint32_t cat, uint32_t num)
{
    tallies_t *T = &s_tally[tail ? 1 : 0];
    uint32_t f = FIELD(uint32_t, self, F_FRAMES), i, d = 0, closed = 0;
    uint16_t prev = T->cur;                           /* bit 15 = set (1/0 is a real action), cat << 8 | num */
    if (T->self != self) {                            /* a new half (next quest): forget the last one's counts */
        for (i = 0; i < TALLY_N; i++) T->t[i].n = 0, T->t[i].frames = 0;
        T->self = self;
        T->shorts = 0;
        prev = 0;
    } else if (prev) {                                /* close the previous action: count it with its run time */
        d = f - T->last_f;
        if (d < 4) T->shorts++;
        for (i = 0; i < TALLY_N; i++)
            if (!T->t[i].n || T->t[i].act == prev) { T->t[i].act = prev; T->t[i].n++; T->t[i].frames += d; break; }
        closed = ++T->ended;
    }
    if (++T->starts <= 150)                           /* every start, repeats included (first 150 per half) */
        logf("dalaport: ai %s start %u/%u after %u/%u ran %u f (frame %u)", tail ? "tail" : "head", cat, num,
             (prev >> 8) & 0x7f, prev & 0xff, d, f);
    T->cur = (uint16_t)(0x8000 | (cat & 0x7f) << 8 | (num & 0xff));
    T->last_f = f;
    if (!closed || closed % 16 || T->lines >= 40) return;
    T->lines++;
    char buf[400], *p = buf, *e = buf + sizeof buf - 1;
    for (i = 0; i < TALLY_N && T->t[i].n; i++) {
        p = put_u(p, e, (T->t[i].act >> 8) & 0x7f); p = put_s(p, e, "/"); p = put_u(p, e, T->t[i].act & 0xff);
        p = put_s(p, e, " x"); p = put_u(p, e, T->t[i].n);
        p = put_s(p, e, " "); p = put_u(p, e, T->t[i].frames / T->t[i].n); p = put_s(p, e, "f, ");
        T->t[i].n = 0;
        T->t[i].frames = 0;
    }
    *p = 0;
    logf("dalaport: ai %s %x tally band %u broken %u mode %u rage %u floor-class %u rank %u variant %u ctl %u short %u: %s",
         tail ? "tail" : "head", (uint32_t)self, dala_hp_band(self), dala_broken(self), MODE(self),
         REC(self)[0x518], s_class[tail ? 1 : 0], questRank(), FIELD(uint8_t, self, EN_VARIANT),
         FIELD(uint8_t, self, EN_CONTROLLED), T->shorts, buf);
    T->shorts = 0;
}
