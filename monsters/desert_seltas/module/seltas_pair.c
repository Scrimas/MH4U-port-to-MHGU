/* seltas_pair.c: the Desert Seltas stays with his Desert Seltas Queen and comes when she calls. C = read in code, S = strong.
 *
 * 4U (v1.1, C): a male of either species takes either Queen as his partner (0x77cdc4 / 0x784a80: em 26 or 95 into
 * [W+0x8d88]+0x50) and a Queen either male (0x78c008: em 25 or 94). Before an area move the male's slot 66 (0x788c64, no
 * species test on this path) moves him to his partner's area ([W+0x1f4] = her [W+0x14c]) or keeps him where she is.
 * GU (C): the same through GU's area-move engine: the Queen's slot 9 (0xf8c108) every 300 frames, and her call 0xf96230 in
 * its first phase, hand her area to the monster with ID 0x4c through 0xbe5ec (which sets its record +0x5dc4 bit 0 and
 * +0x5dc5 = the area, if it is alive, elsewhere and can go there); the male's slot 152 (0xfc768c, asked by the area-move
 * requester 0xb8568 before it requests a move) finds a Queen with ID 0x45, sets this+0x1404 bit 27 (no random move,
 * 0xb83ec) and keeps him in her area (0 = stay, 1 = he may leave). Both compare the full 16-bit ID (`ldrh [+0xb5f0]`),
 * variant byte included, so a Desert Queen (0x145) calls a normal Seltas and her Desert Seltas (0x14c) never finds her:
 * he wandered on his own (the 0.1.3 test, log 21-19-17: the two in the same area 210 of 720 s). GU's other partner
 * searches of the Seltas class (0xfc72bc, 0xfc7340, 0xfc75a0) compare the em byte and find her, so his joint attacks ran.
 * Port: two entry hooks. 0xbe5ec: at the Queen's two calls (lr 0xf8c17c / 0xf962dc) a Desert Queen calls ID 0x14c, her
 * Desert Seltas (every one of her quests brings him; 4U would call either male). 0xfc768c: for the Desert Seltas GU's
 * own logic, the Queen found by her em number 0x45 as in GU's other searches and 4U's pairing (either Queen).
 * Her call out of the sand (C): buried (6/3, GU 0xfd440c = 4U 0x784308), he jumps out at her (6/4, motion 0x45c) when
 * his partner plays 0x465 (her 7/72, 0xf99504) and passes its frame 328: 4U 0x784498 asks the partner's frame
 * (0x91ab1c(partner, 1, 0, 328.0, 0.0)), GU 0xfd4590 his own (`mov r0, r4` before 0xb0a24), and his buried loop (motion
 * 1, 301 frames) never gets there: the 0.1.3 test shows him 60 s buried through six of her calls, then digging out
 * (6/1). A mid hook after that `mov r0, r4` (0xfd4594) hands the frame test his partner, as 4U's.
 * The normal Seltas and Queen keep GU's code. Multiplayer: every machine runs them as GU's own code. All addresses
 * through MAIN / FN. Logs: "dsport:". */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define IS_DS(p)     ((p) && FIELD(uint16_t, (p), EN_ID) == DESERT_SELTAS_EM_ID)
#define IS_DSQ(p)    ((p) && FIELD(uint16_t, (p), EN_ID) == DESERT_SELTAS_QUEEN_EM_ID)
#define EN_AREA      0x1054          /* u8 current area */
#define EN_FLAGS     0x1404          /* u32; bit 27 = a Queen keeps him (0xb83ec makes no random move) */
#define EN_STATE     0x73e0          /* u8 the running action's category (slot 125 switches on it); her 11 / 12 / 14 let
                                        the male go (GU 0xfc7740) */
#define ENEMY_MGR    0x1851fe0u      /* the enemy manager (module/main.c) */
#define SELTAS_ID    0x4cu           /* GU's Seltas, the ID the Queen's calls name */
#define QUEEN_EM     0x45u           /* the Seltas Queen's em number (ID + 4) */
#define MAX_LOG      60u

typedef uint8_t *(*enemy_at_t)(void *mgr, uint32_t k);
#define enemyAt FN(enemy_at_t, 0x5ceb4)  /* the k-th of the 10 monster slots, or 0 (GU 0xfc76e0) */

static uint32_t log_room(void)
{
    static uint32_t s_n, s_quest;
    if (port_quest_id() != s_quest) { s_quest = port_quest_id(); s_n = 0; }
    return s_n++ < MAX_LOG;
}

/* 0xbe5ec(caller, id, area) entry: 0 = on into GU's function (with the ID changed for her) */
int seltas_dsq_call_c(uint32_t *regs)
{
    int timer = regs[LR] == MAIN(0xf8c17c);
    if (regs[R1] != SELTAS_ID || (!timer && regs[LR] != MAIN(0xf962dc)) || !IS_DSQ((void *)regs[R0])) return 0;
    regs[R1] = DESERT_SELTAS_EM_ID;
    if (log_room())
        logf("dsport: dsq calls her Desert Seltas to area %u (%s)", FIELD(uint8_t, (void *)regs[R0], EN_AREA),
             timer ? "every 300 frames" : "her call");
    return 0;
}

/* 0xfd4594 in his 6/3 (r4 = him, r0 = him for the frame test 0xb0a24 at 0xfd45a0, his partner already tested to play 0x465):
 * 0 = on, with r0 = his partner for him */
int seltas_ds_popout_c(uint32_t *regs)
{
    uint8_t *self = (uint8_t *)regs[R4], *pair, *q;
    if (!IS_DS(self) || !(pair = FIELD(uint8_t *, self, 0xcac0)) || !(q = FIELD(uint8_t *, pair, 0x50))) return 0;
    regs[R0] = (uint32_t)(uintptr_t)q;
    return 0;
}

/* 0xfc768c (this) entry, uEm076_00 slot 152: for the Desert Seltas GU's code with the Queen found by her em number;
 * nonzero = done, the result in r0 */
int seltas_ds_stay_c(uint32_t *regs)
{
    static void *s_self;
    static int s_last = -1;
    uint8_t *self = (uint8_t *)regs[R0], *rec, *mgr, *q = 0;
    if (!IS_DS(self)) return 0;
    rec = FIELD(uint8_t *, self, EN_RECORD);
    if (rec && FIELD(uint8_t, rec, 0x1ba) == 5) { regs[R0] = 0; return 1; }    /* GU 0xfc76a0 */
    FIELD(uint32_t, self, EN_FLAGS) &= ~(1u << 27);
    mgr = *(uint8_t **)MAIN(ENEMY_MGR);
    for (uint32_t k = 0; mgr && k < 10 && !q; k++) {
        uint8_t *m = enemyAt(mgr, k);
        if (!m || FIELD(uint8_t, m, EN_ID + 7)) continue;                          /* a small monster */
        if (((int (*)(void *))((*(uint32_t **)m)[34]))(m) != 1) continue;          /* slot 34 (vt+0x88), as GU's */
        if (FIELD(uint8_t, m, EN_ID + 4) == QUEEN_EM) q = m;
    }
    if (!q) regs[R0] = 1;
    else {
        uint8_t st = FIELD(uint8_t, q, EN_STATE);
        if (st <= 14 && ((0x5800u >> st) & 1)) regs[R0] = 1;
        else {
            FIELD(uint32_t, self, EN_FLAGS) |= 1u << 27;
            regs[R0] = FIELD(uint8_t, q, EN_AREA) != FIELD(uint8_t, self, EN_AREA);
        }
    }
    if ((int)regs[R0] != s_last || self != s_self) {
        s_last = (int)regs[R0]; s_self = self;
        if (log_room())
            logf("dsport: ds %s (he in area %u, %s)", regs[R0] ? "may leave his area" : "stays with his Queen",
                 FIELD(uint8_t, self, EN_AREA), q ? "his Queen found" : "no Queen");
    }
    return 1;
}
