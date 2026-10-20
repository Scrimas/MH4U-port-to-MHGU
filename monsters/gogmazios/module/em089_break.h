/* em089 part breaks (break agent). How GU does it (MHGU 1.4 main, read from the code):
 *  - 0x9d6f8 (hit code) adds part damage to rec+0x488+2*part. The generic per-frame damage code 0xa5900 then
 *    runs 0x97ddc: for each part 0..7 whose dttune part table HP (data +100 -> +4, 10-byte rows) is nonzero, the
 *    flinch HP left (rec+0x3be+12p) drops; at 0 the part flinches (reaction rec+0x3ae), its BREAK COUNT
 *    rec+0x3bc+12p goes up (cap 14), 0x99db8 refills the flinch HP and 0x99f98 checks the dtbparts break records
 *    (obj+0x64, 4 B {part, LR count, HR count, group}, count obj+0x8c): count == required -> 0xa44e8 (break event:
 *    slot 214 + net) and the reward break flag bit (group & 127) of rec+0x5cbe (0x49964 net + quest stat).
 *  - Sever: parts with row +2 (sever count limit) > 0: rec+0x3c0+12p (HP from row +6, damage types row +4/+5) runs
 *    down, then rec+0x3b3 = part, SEVER COUNT rec+0x3bd+12p++ and reaction 14. The cut object is the monster's own
 *    job: Rathian / Kushala call spawnCutPart(this, 0, 0, 143, 0) at the start of their sever reaction (Kushala
 *    slot 129, action (10, 114)), which sets the detached bit rec+0x3b4 |= 1, the tail reward flag (bit 7 via
 *    0x9d458) and drops the embedded cut-tail object (this+0x7720, model = manifest field 1) at the joint.
 *  - Visibility is monster code too: Rathian slot 132 (0xcf56b4) applies the XFS state of each break pair from
 *    the break counts every frame. 4U does the same with its emd rows: cond 6 = break count(param) >= threshold,
 *    cond 1 = detached bits W+0x42c (= GU rec+0x3b4) & param (4U row evaluator 0x948378).
 * So for em089 the framework already counts flinches / breaks / severs from the converted dttune part table;
 * this file supplies the em089 parts: break records, visibility, cut tail, detach bits. */
#pragma once
#include <stdint.h>
#include "game.h"

/* ---- GU declarations (main offsets) ---- */
#define BRK_REC_PART      0x3bc   /* rec: 12-byte per-part records: +0 u8 break count, +1 u8 sever count,
                                     +2 u16 flinch HP left, +4 u16 sever HP left (getters 0x9d428 / 0x9d440) */
#define BRK_REC_DETACHED  0x3b4   /* rec: u16 detached-part bits (948): 1 cut object type 1 (tail), 2 type 2,
                                     8 type 3; set by spawnCutPart, tested by slot 220 = 4U W+0x42c */
#define BRK_REC_FLAGS     0x5cbe  /* rec: s8 reward break flags (bit = dtbparts group, 7 = tail sever) */
#define BRK_EN_DTBPARTS   0x75f0  /* enemy: dtbparts object (setter 0x70a4c); +0x64 break records, +0x8c count */
#define BRK_DTP_RECORDS   0x64
#define BRK_DTP_COUNT     0x8c

/* spawnCutPart(this, k, flags, joint, pos) [0xc2330]: activates embedded cut object k (this+0x7720 + k*0x14f0,
 * type byte +0x1474 = 1 when manifest field 1 (tail model) exists): rec+0x3b4 |= 1 / 2 / 8 by type, reward flag
 * 0x9d458(this, 7 / 6 / 5, 1), start position = joint `joint` of the monster model (index table this+0x498, 0xff /
 * unknown -> monster position), pos = optional float[3] (0 = this+64). flags: 0 normal (bit 2 = only mark). */
typedef void (*spawnCutPart_t)(void *self, uint32_t k, uint32_t flags, uint32_t joint, const float *pos);
#define spawnCutPart FN(spawnCutPart_t, 0xc2330)
/* setDetached(this, bits): rec+0x3b4 |= bits [0xa3c94] */
typedef void (*setDetached_t)(void *self, uint32_t bits);
#define setDetached FN(setDetached_t, 0xa3c94)
/* MT heap new[] / delete[] [0x7af3a0 (size) / 0x7af3e4 (p)]: what the dtbparts loader 0x5575c / clear 0x56180 use */
typedef void *(*gu_new_t)(uint32_t size);
typedef void (*gu_delete_t)(void *p);
#define gu_new    FN(gu_new_t, 0x7af3a0)
#define gu_delete FN(gu_delete_t, 0x7af3e4)

/* em089 constants (4U em089 data, notes/data.md) */
#define BRK_TAIL_PART     6       /* tail: dttune row +2 = 1, damage type 1 (cut), sever HP 1500 */
#define BRK_SPEAR_PART    1       /* back + bone 200 (Dragonator spear): row +2 = 1, type 126, detach HP 1200 */
#define BRK_TAIL_JOINT    141     /* first bone of the 4U em089 sever chain 141-143 (emd word 35); Kushala's GU
                                     143 = its own 4U chain start (0x8f) */
#define BRK_DETACH_TAIL   1       /* 4U cond-1 param 1 = GU cut object type 1 */
#define BRK_DETACH_SPEAR  8       /* 4U cond-1 param 8 = GU type-3 bit; the falling spear object itself is GU cut
                                     slot 1 (type 2, bit 2), em089_pile.c */

/* Per frame, once, AFTER the tar code (it rewrites g13 / g14 / g19 / g34 when the tar word changes): best at the
 * end of object slot 132 (after em089_tar_steady), the last per-frame monster hook. Lazily installs the em089
 * break records into the dtbparts object (once per loaded resource), turns break / sever counts into XFS states
 * 7-10 + direct group bits, spawns the cut tail (spawnCutPart) and sets the spear detach bit. */
void em089_break_update(void *self);

/* optional, end of slot 118 (em089_spawn_setup): forget per-monster state and install the break records now */
void em089_break_spawn(void *self);

/* bit p = part p broken (4U: count >= threshold), bits 8.. = detached bits rec+0x3b4 << 8 (tail 0x100, spear 0x800).
 * For the 4U 7/32 part-break interruption (em089_act.c) and diagnostics. */
uint32_t em089_break_state(void *self);
