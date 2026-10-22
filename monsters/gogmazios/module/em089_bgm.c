/* em089_bgm.c: Gogmazios' own battle themes (4U bgm_em089 / bgm_em089_2), played by the core's BGM hooks
 * (module/bgm.c: the hooks and how GU picks a theme; they lived here until 2026-10-21, same rules and log lines).
 *
 * Files (tools/snd_bgm.py, all ADDITIONAL to the game's): sound/bgm/battle/wav/bgm_em089_Gogmazios1/2.opus (loose)
 * and the STQR sound\bgm\battle\bgm_em089 in the em089 arc (2 streams, sequences EM089_BGM_ID1 / ID2).
 * Ours: the unit's em type is 0x59, or the boss entry says 0x59, or it says Kushala 0x18 (the quest's loader
 * stand-in) while quest 11491 / 11492 runs -> ID1, or ID2 once the 4U phase-2 latch is set.
 * 4U (C): 0x30e5a4 returns 33 (bgm_em089_2) when sound state +0x1838 == 1, else 32 (bgm_em089); 0x309004 sets the
 * state to 1 when an em089 has work+0xca == 1 (phase-2 roar 1/25 / 1/31) = module F_SHAKE (em089_act.c).
 * Not ported: state 2 (4U event 0x6a1b40) -> id 29 bgm_Eiyu. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"
#include "port.h"

#define EM089_BGM_ID1   GOGMAZIOS_BGM_ID0   /* allocations.toml bgm_ids (tools/snd_bgm.py writes them) */
#define EM089_BGM_ID2   GOGMAZIOS_BGM_ID1
#define EM_TYPE_GOG     (GOGMAZIOS_EM_ID & 0xffu)
#define EM_TYPE_STANDIN (GOGMAZIOS_STANDIN_ID & 0xffu)
#define EM089_F_PHASE2  (SIZE_uFestaEnemy + 0x25)   /* = em089_act.c F_SHAKE [4U work+0xca] */
/* the arc entry sound\bgm\battle\bgm_em089 (rSoundStreamRequest, tools/snd_bgm.py build_em089_stqr): file ID from
 * build_em089_arc.py (asserted there; IDs only ever grow), served by module/port.c from the data file */
#define EM089_FILE_BGM_STQR 0x10725u

int gog_quest_index(void);     /* stage.c: 1 / 2 = our quests 11491 / 11492, 0 = other */

static int gog_phase2(void *unit) { return unit && FIELD(uint8_t, unit, EM089_F_PHASE2); }

static const struct port_bgm k_bgm = {
    "gogport", "em089", {EM_TYPE_GOG}, {EM_TYPE_STANDIN}, gog_quest_index, EM089_FILE_BGM_STQR,
    {EM089_BGM_ID1, EM089_BGM_ID2}, gog_phase2,
};

void em089_bgm_register(void) { port_bgm_register(&k_bgm); }
