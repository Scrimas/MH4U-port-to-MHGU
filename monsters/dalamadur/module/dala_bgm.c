/* dala_bgm.c: Dalamadur's theme (4U bgm_em024 / bgm_em024_2, both variants) through the core's BGM hooks
 * (module/bgm.c). C = read in code, S = strong, G = guess.
 *
 * 4U (C, notes/speartip-crag.md section 5): the battle-music selector 0x30e16c gives em 24 / 110 the Speartip stage
 * theme, sequence 12 (bgm_em024_2) once 0x6c3b94(stage, area 1, kobj 1) holds (k00 broken: tail 7.60, HP < 90 %),
 * else 11 (bgm_em024); the tails 83 / 111 get none (flag 255). Files: tools/bgm_dalamadur.py -> GU ids
 * DALAMADUR_BGM_ID0 / ID1 in the STQR sound\bgm\battle\bgm_em090 (em090_00 / em090_01 / em091_00 arcs, one file ID).
 * Port: the head's entries / units (0x5a, Shah 0x15a: same em type) and the quests' stand-in Kushala; also the tail
 * (0x5b) and its stand-in Gendrome 0x0f, with the same theme (deviation, G: a tail boss entry left to GU could pick
 * Gendrome's theme while the quest runs). Phase = k00 broken, read on every machine from its own arena state, as
 * 4U's local sound state. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

int dala_arena_broken(uint32_t mid);   /* dala_stage.c: 4U 0x6c3b94(stage, area 1, mId) */

/* build_dalamadur_arc.py EXTRA_ORDER[0] = 'bgm_stqr' (tools/em090_00_manifest.json "bgm_stqr"; IDs only ever grow) */
#define DALA_FILE_BGM_STQR 0x107a0u

static int dala_quest(void)
{
    int m = port_running_quest(0);
    return m == DALAMADUR_PORT || m == SHAH_DALAMADUR_PORT;
}

static int dala_phase2(void *unit)
{
    (void)unit;
    return dala_arena_broken(1);
}

static const struct port_bgm k_bgm = {
    "dalaport", "em090", {DALAMADUR_EM_ID & 0xffu, DALAMADUR_TAIL_EM_ID & 0xffu},
    {DALAMADUR_STANDIN_ID & 0xffu, DALAMADUR_TAIL_STANDIN_ID & 0xffu}, dala_quest, DALA_FILE_BGM_STQR,
    {DALAMADUR_BGM_ID0, DALAMADUR_BGM_ID1}, dala_phase2,
};

void dala_bgm_register(void) { port_bgm_register(&k_bgm); }
