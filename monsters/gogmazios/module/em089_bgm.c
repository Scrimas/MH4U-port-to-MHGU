/* em089_bgm.c: Gogmazios' own battle themes (4U bgm_em089 / bgm_em089_2).
 *
 * Files (tools/snd_bgm.py, all ADDITIONAL to the game's): sound/bgm/battle/wav/bgm_em089_Gogmazios1/2.opus (loose)
 * and the STQR sound\bgm\battle\bgm_em089 in the em089 arc (2 streams, sequences EM089_BGM_ID1 / ID2). GU loads
 * its own bgm_bt from loc/arc/quest.arc (a loose bgm_bt.stqr is never read: test 2), so bgm_stqr_c below points
 * the lookups of our two ids at our STQR.
 *
 * GU picks a quest boss's battle theme in 0x4e60d4(ctl, entry, u8 *has_theme, u32 *id) (callers 0x4de1bc,
 * 0x4e4524, 0x4e567c, 0x4e5b00 in sSoundControl): entry = {u16 em descriptor (low byte = em type), ..., u16 unit
 * key @+6}; a switch on em types 12..88 sets the id (Kushala 24 -> bgm_em024_Daola), em > 88 falls to the map
 * theme. The id is a sequence id of bgm_bt.stqr. Hook (entry, both instructions displaceable): our monster (the unit
 * found by the key has em type 0x59, or the entry says 0x59, or it says Kushala 0x18 - the quest's loader stand-in -
 * while quest 11491 runs) -> *has = 1, *id = ID1, or ID2 once the 4U phase-2 latch is set.
 * 4U (C): 0x30e5a4 returns 33 (bgm_em089_2) when sound state +0x1838 == 1, else 32 (bgm_em089); 0x309004 sets the
 * state to 1 when an em089 has work+0xca == 1 (phase-2 roar 1/25 / 1/31) = module F_SHAKE (em089_act.c).
 * Not ported: state 2 (4U event 0x6a1b40) -> id 29 bgm_Eiyu. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define EM089_BGM_ID1   GOGMAZIOS_BGM_ID0   /* allocations.toml bgm_ids (tools/snd_bgm.py writes them) */
#define EM089_BGM_ID2   GOGMAZIOS_BGM_ID1
#define EM_TYPE_GOG     (GOGMAZIOS_EM_ID & 0xffu)
#define EM_TYPE_STANDIN (GOGMAZIOS_STANDIN_ID & 0xffu)
#define UNIT_MGR_PTR    0x1851fe0u  /* read by 0x4e6104 (GOT 0x1838bc0), passed to 0x5cf90 */
#define UNIT_EM_TYPE    0xb5f4u     /* u8 em type of a monster unit (sSoundControl 0x4ed904 reads it) */
#define EM089_F_PHASE2  (SIZE_uFestaEnemy + 0x25)   /* = em089_act.c F_SHAKE [4U work+0xca] */

typedef void *(*unit_by_key_t)(void *mgr, uint32_t key);   /* unit whose rec+0x1b6 == key */
#define unit_by_key FN(unit_by_key_t, 0x5cf90)
typedef void *(*file_res_t)(void *unused, uint32_t file_id);   /* loaded resource by file ID (our file_id hook) */
#define fileResource FN(file_res_t, 0x152960)
/* = em089_files.inc EM089_FILE_BGM_STQR (that .inc defines globals and is included by main.c only): the arc entry
 * sound\bgm\battle\bgm_em089 (rSoundStreamRequest, tools/snd_bgm.py build_em089_stqr) */
#define EM089_FILE_BGM_STQR 0x10725u

int gog_quest_index(void);     /* stage.c: 1 / 2 = our quests 11491 / 11492, 0 = other */

int bgm_select_c(uint32_t *regs)
{
    const uint16_t *e = (const uint16_t *)regs[R1];
    if (!e || !regs[R2] || !regs[R3]) return 0;
    uint32_t type = e[0] & 0xff;
    void *mgr = *(void **)MAIN(UNIT_MGR_PTR);
    void *mon = mgr ? unit_by_key(mgr, e[3]) : 0;
    int gog = mon && FIELD(uint8_t, mon, UNIT_EM_TYPE) == EM_TYPE_GOG;
    if (!gog && type != EM_TYPE_GOG && !(type == EM_TYPE_STANDIN && gog_quest_index())) return 0;
    uint32_t id = (gog && FIELD(uint8_t, mon, EM089_F_PHASE2)) ? EM089_BGM_ID2 : EM089_BGM_ID1;
    if (!fileResource(0, EM089_FILE_BGM_STQR)) {     /* our STQR not loaded: keep GU's choice instead of silence */
        static uint32_t s_miss;
        if (++s_miss <= 5) logf("gogport: em089 bgm stqr %x not loaded, GU theme kept", EM089_FILE_BGM_STQR);
        return 0;
    }
    *(uint8_t *)regs[R2] = 1;
    *(uint32_t *)regs[R3] = id;
    static uint32_t s_last, s_n;
    if (id != s_last && ++s_n <= 20) {
        s_last = id;
        logf("gogport: em089 bgm theme %x (entry em %x key %u, unit %s)", id, e[0], e[3], gog ? "em089" : "none");
    }
    return 1;
}

/* 0xb6d72c(stqr, id) -> 140-B sequence entry or 0: rSoundStreamRequest "get sequence by id" (u16 table +0xb4, else
 * a scan of +0x68 entries at +0x6c). 52 callers: sSoundControl 0x4e1f54..0x4ebc10 and the stream player
 * 0xbe7e28..0xc03a4c, which re-resolve (stqr, id) every time and then read only entry fields (+8, +32, +0x88 the
 * pre-resolved stream object). Ids 0x900 / 0x901 exist only in our STQR, so for them the lookup is pointed at it
 * (r0 replaced, the original body runs); the returned entry carries our own stream objects. Test 2: without this
 * the id did not resolve in GU's bgm_bt (loaded from loc/arc/quest.arc) and the battle stayed silent. */
/* 0x4e34a4(ctl, r1 channel, r2 kind, r3 STQR slot 0..4 = ctl+0x1a80+4*slot, sp0 sequence id, sp4 follow-up id,
 * sp8 force): sSoundControl "play stream request". Log only (quest 11491, bounded): shows which area / jingle /
 * battle sequences GU asks for in the alias (slot, id) and whether the slot holds an STQR at all. */
enum { SP0 = 8 };
int bgm_play_c(uint32_t *regs)
{
    static uint32_t s_n;
    if (s_n >= 60 || !gog_quest_index()) return 0;
    uint32_t slot = regs[R3];
    void *stqr = slot <= 4 ? *(void **)(uintptr_t)(regs[R0] + 0x1a80 + 4 * slot) : 0;
    s_n++;
    logf("gogport: bgm play ch %u kind %u slot %u id %x next %x force %u stqr %x", regs[R1], regs[R2], slot,
         regs[SP0], regs[SP0 + 1] & 0xffff, regs[SP0 + 2], (uint32_t)(uintptr_t)stqr);
    return 0;
}

int bgm_stqr_c(uint32_t *regs)
{
    if (regs[R1] != EM089_BGM_ID1 && regs[R1] != EM089_BGM_ID2) return 0;
    void *res = fileResource(0, EM089_FILE_BGM_STQR);
    static uint32_t s_n;
    if (++s_n <= 12)
        logf("gogport: em089 bgm stqr lookup id %x stqr %x -> %x%s", regs[R1], regs[R0],
             (uint32_t)(uintptr_t)res, res ? "" : " (NOT LOADED: no entry)");
    if (res) regs[R0] = (uint32_t)(uintptr_t)res;
    return 0;
}
