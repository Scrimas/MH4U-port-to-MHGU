/* bgm.c: the ported monsters' own battle themes (core; moved from Gogmazios' em089_bgm.c, plan of 2026-10-21).
 * A package registers its themes from its class registration (port_bgm_register, port.h).
 *
 * Files (tools/snd_bgm.py, all ADDITIONAL to the game's): Opus streams (loose) and the monster's own STQR in its arc
 * (its sequences = allocations.toml bgm_ids). GU loads its own bgm_bt from loc/arc/quest.arc (a loose bgm_bt.stqr is
 * never read: Gogmazios test 2), so bgm_stqr_c below points the lookups of our ids at the monster's STQR.
 *
 * GU picks a quest boss's battle theme in 0x4e60d4(ctl, entry, u8 *has_theme, u32 *id) (callers 0x4de1bc,
 * 0x4e4524, 0x4e567c, 0x4e5b00 in sSoundControl): entry = {u16 em descriptor (low byte = em type), ..., u16 unit
 * key @+6}; a switch on em types 12..88 sets the id (Kushala 24 -> bgm_em024_Daola), em > 88 falls to the map
 * theme. The id is a sequence id of bgm_bt.stqr. Hook (entry, both instructions displaceable): a registered monster
 * (the unit found by the key has one of its em types, or the entry says one, or it says one of its stand-ins while
 * one of its quests runs) -> *has = 1, *id = phase 1 or 2 by its phase getter. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "port.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define UNIT_MGR_PTR    0x1851fe0u  /* read by 0x4e6104 (GOT 0x1838bc0), passed to 0x5cf90 */
#define UNIT_EM_TYPE    0xb5f4u     /* u8 em type of a monster unit (sSoundControl 0x4ed904 reads it) */

typedef void *(*unit_by_key_t)(void *mgr, uint32_t key);   /* unit whose rec+0x1b6 == key */
#define unit_by_key FN(unit_by_key_t, 0x5cf90)
typedef void *(*file_res_t)(void *unused, uint32_t file_id);   /* loaded resource by file ID (our file_id hook) */
#define fileResource FN(file_res_t, 0x152960)

#define BGM_MAX 4
static struct {
    const struct port_bgm *b;
    uint32_t miss, last, n_theme, n_stqr, n_play;     /* log budgets, per registration */
} s_bgm[BGM_MAX];
static uint32_t s_count;

void port_bgm_register(const struct port_bgm *b)
{
    for (uint32_t i = 0; i < s_count; i++) if (s_bgm[i].b == b) return;
    if (s_count >= BGM_MAX) { logf("mh4uport: bgm: no room for %s", b->name); return; }
    s_bgm[s_count++].b = b;
}

static int has_type(const uint8_t *types, uint32_t n, uint32_t t)
{
    for (uint32_t i = 0; i < n; i++) if (types[i] && types[i] == t) return 1;
    return 0;
}

int bgm_select_c(uint32_t *regs)
{
    const uint16_t *e = (const uint16_t *)regs[R1];
    if (!e || !regs[R2] || !regs[R3] || !s_count) return 0;
    uint32_t type = e[0] & 0xff;
    void *mgr = *(void **)MAIN(UNIT_MGR_PTR);
    void *mon = mgr ? unit_by_key(mgr, e[3]) : 0;
    uint32_t mtype = mon ? FIELD(uint8_t, mon, UNIT_EM_TYPE) : 0x100;
    for (uint32_t i = 0; i < s_count; i++) {
        const struct port_bgm *b = s_bgm[i].b;
        int ours = mon && has_type(b->em_types, sizeof b->em_types, mtype);
        if (!ours && !has_type(b->em_types, sizeof b->em_types, type) &&
            !(has_type(b->standins, sizeof b->standins, type) && b->quest())) continue;
        uint32_t id = b->phase2(ours ? mon : 0) ? b->ids[1] : b->ids[0];
        if (!fileResource(0, b->stqr_file)) {     /* our STQR not loaded: keep GU's choice instead of silence */
            if (++s_bgm[i].miss <= 5) logf("%s: %s bgm stqr %x not loaded, GU theme kept", b->port, b->name, b->stqr_file);
            return 0;
        }
        *(uint8_t *)regs[R2] = 1;
        *(uint32_t *)regs[R3] = id;
        if (id != s_bgm[i].last && ++s_bgm[i].n_theme <= 20) {
            s_bgm[i].last = id;
            logf("%s: %s bgm theme %x (entry em %x key %u, unit %s)", b->port, b->name, id, e[0], e[3],
                 ours ? b->name : "none");
        }
        return 1;
    }
    return 0;
}

/* 0xb6d72c(stqr, id) -> 140-B sequence entry or 0: rSoundStreamRequest "get sequence by id" (u16 table +0xb4, else
 * a scan of +0x68 entries at +0x6c). 52 callers: sSoundControl 0x4e1f54..0x4ebc10 and the stream player
 * 0xbe7e28..0xc03a4c, which re-resolve (stqr, id) every time and then read only entry fields (+8, +32, +0x88 the
 * pre-resolved stream object). Our ids exist only in the monster's STQR, so for them the lookup is pointed at it
 * (r0 replaced, the original body runs); the returned entry carries our own stream objects. Gogmazios test 2:
 * without this the id did not resolve in GU's bgm_bt (loaded from loc/arc/quest.arc) and the battle stayed silent. */
int bgm_stqr_c(uint32_t *regs)
{
    for (uint32_t i = 0; i < s_count; i++) {
        const struct port_bgm *b = s_bgm[i].b;
        if (regs[R1] != b->ids[0] && regs[R1] != b->ids[1]) continue;
        void *res = fileResource(0, b->stqr_file);
        if (++s_bgm[i].n_stqr <= 12)
            logf("%s: %s bgm stqr lookup id %x stqr %x -> %x%s", b->port, b->name, regs[R1], regs[R0],
                 (uint32_t)(uintptr_t)res, res ? "" : " (NOT LOADED: no entry)");
        if (res) regs[R0] = (uint32_t)(uintptr_t)res;
        return 0;
    }
    return 0;
}

/* 0x4e34a4(ctl, r1 channel, r2 kind, r3 STQR slot 0..4 = ctl+0x1a80+4*slot, sp0 sequence id, sp4 follow-up id,
 * sp8 force): sSoundControl "play stream request". Log only (while a registered monster's quest runs, bounded):
 * shows which area / jingle / battle sequences GU asks for (slot, id) and whether the slot holds an STQR at all. */
enum { SP0 = 8 };
int bgm_play_c(uint32_t *regs)
{
    for (uint32_t i = 0; i < s_count; i++) {
        const struct port_bgm *b = s_bgm[i].b;
        if (s_bgm[i].n_play >= 60 || !b->quest()) continue;
        uint32_t slot = regs[R3];
        void *stqr = slot <= 4 ? *(void **)(uintptr_t)(regs[R0] + 0x1a80 + 4 * slot) : 0;
        s_bgm[i].n_play++;
        logf("%s: bgm play ch %u kind %u slot %u id %x next %x force %u stqr %x", b->port, regs[R1], regs[R2], slot,
             regs[SP0], regs[SP0 + 1] & 0xffff, regs[SP0 + 2], (uint32_t)(uintptr_t)stqr);
        return 0;
    }
    return 0;
}
