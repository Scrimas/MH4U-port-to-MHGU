/* Speartip Crag breakables (goal D6): Dalamadur breaks the arena's spire platforms k00 / k01 and the spire k02
 * (4U m08a01d-k00..k02 = our area-1 KowareObj mId 1..3, build_speartip.py; speartip-crag.md).
 *
 * 4U: stage command 0x6c3400(stage, area W+0x14c, mId, 0, 0) plays the kobj's action 0 (tail 7.60 frame 1238 mId 1,
 * tail 7.61 frame 810 mId 2, head 7.62 frame 1082 mId 3); 0x6c3b94(stage, area, mId) tells whether it has broken
 * (AI conditions, 0x7731a4 = highest broken mId). Every machine runs the actions (replayed), so every machine breaks
 * its own copy at the same motion frame.
 * GU (Capcom's port of the KowareObj, C): the gimmick manager [0x18977a0] lists the kobjs at +0x21c (24); command 0
 * (0x514f9c -> 0x515328) plays action 0, returns at once when that action is already the current one (+0x185), and
 * when online sends the kobj action to the other machines (0x21d028). So a machine whose message arrived first
 * ignores its own later call: one break per machine either way. GU plays the action, its SE and the collision swap
 * (part 2 * mId - 1 off / 2 * mId on) itself. The quest-start command 0 is held for area 1 (module/stage_alias.c,
 * package.toml hold_kobj_areas), so the pieces stand until Dalamadur breaks them. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em090.h"

#define STAGE_GIMMICK_MGR 0x18977a0u
#define MGR_KOBJ          0x21cu      /* uKowareObj *[24] (0x500d40 registers) */
#define MGR_KOBJ_N        24u
#define KOBJ_AREA         0x182u      /* u8 mAreaNo */
#define KOBJ_STATUS       0x184u      /* u8: 6 = action playing (0x513e24) */
#define KOBJ_ACT          0x185u      /* u8 current action id, 255 = none (0x513378) */
#define KOBJ_ID           0x188u      /* u8 mId */
#define ARENA_AREA        1u
typedef void (*kobj_cmd_t)(void *kobj, uint32_t cmd, uint32_t a, uint32_t b);
#define kobj_cmd FN(kobj_cmd_t, 0x514f9c)

static uint8_t *arena_kobj(uint32_t mid)
{
    uint8_t *mgr = *(uint8_t **)MAIN(STAGE_GIMMICK_MGR);
    if (!mgr) return 0;
    for (uint32_t i = 0; i < MGR_KOBJ_N; i++) {
        uint8_t *k = FIELD(uint8_t *, mgr, MGR_KOBJ + 4 * i);
        if (k && k[KOBJ_AREA] == ARENA_AREA && k[KOBJ_ID] == mid) return k;
    }
    return 0;
}

/* 4U 0x6c3400(stage, area, mId, 0, 0) */
void dala_arena_break(void *self, uint32_t mid)
{
    uint8_t *k = arena_kobj(mid);
    if (!k) { logf("dalaport: %x arena break mId %u: no KowareObj in area %u", (uint32_t)self, mid, ARENA_AREA); return; }
    logf("dalaport: %x arena break mId %u kobj %x status %u act %u ctl %u", (uint32_t)self, mid, (uint32_t)k,
         k[KOBJ_STATUS], k[KOBJ_ACT], FIELD(uint8_t, self, EN_CONTROLLED));
    kobj_cmd(k, 0, 0, 0);
}

/* 4U 0x6c3b94(stage, area, mId): action 0 started (it stays the current action once played) */
int dala_arena_broken(uint32_t mid)
{
    uint8_t *k = arena_kobj(mid);
    return k && k[KOBJ_ACT] == 0;
}

/* 4U slot 40 of both halves (head 0x76db14, tail 0x8a00a4): on stage 8 (Speartip Crag, [[0xfb6b7c]+0xc8c]) while
 * k00 stands, 0x91b268 every frame = W+0x539 = 2 = GU 0xbd114 (rec+0x521 = 2, callee map C). Here: while our area-1
 * kobj mId 1 exists (the alias is loaded) and has not broken. Meaning of the byte (rage-related, next to the rage
 * byte W+0x530 / rec+0x518) not traced. */
#define rageHold FN(act_base_t, 0xbd114)
void dala_arena_frame(void *self)
{
    uint8_t *k = arena_kobj(1);
    if (k && k[KOBJ_ACT] != 0) rageHold(self);
}

/* 4U 0x7731a4(area): the highest broken piece (3, 2, 1), 0 = none */
int dala_broken(void *self)
{
    (void)self;
    for (uint32_t m = 3; m >= 1; m--) if (dala_arena_broken(m)) return (int)m;
    return 0;
}
