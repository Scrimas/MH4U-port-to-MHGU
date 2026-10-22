/* Per-frame parts of the head's 4U slot 77 (uEm024 0x774aa8; vtable address point 0xe66c20; per frame after slot
 * 40, as Gogmazios' slot 77; Shah shares the class; the file name keeps the index first read from a wrong address
 * point): the heat zone pulse and the 10/114 attack window. Its other parts: the per-motion byte W+0x7eec (written by
 * other classes too, no reader found in any addressing form: S, no effect), the effect-28 draw test 0x19fbf0 (open,
 * behaviour.md); this+0xca8 (table 0x775030 by motion and area class) has no
 * effect (per-class scratch nothing reads, em090_act7.c render_flag). Runs from the head's GU slot 119 on every
 * machine: its inputs (motion, rage byte) reach all machines through GU's action and state sync (MP).
 *
 * Heat zone (4U, C): slot 25 sets W+0x7e64 = 2 (0x934048) and the zone selector work+0x40 while
 *   - motion 3, or motion 0x204 from frame 400 (motionCheck kind 2) -> zone 1,
 *   - the head is enraged (0x954e48: W+0x530 == 1) -> zone 0 (checked last, so it wins);
 * the base update counts W+0x7e64 down by one per frame (0x917358). The heat test 0x689c08(mgr, area, pos) asks
 * each enemy in the hunter's area whose W+0x7e64 > 0 (0x92d774): em 24 / 110 zone 1 = joint 101 + rows (500, 1300,
 * -700), radius 1700; zone 0 = joint 4 + rows (0, -500, 1100), radius 1250; radius * size scale (0x911cb4); inside
 * -> 2. Its callers treat 2 like Teostra's 1 except for the burn effect variant of the heat tick (flag 0x80000000
 * instead of 8, 0xb30a30). User (2026-10-22): the heat is around the torso and only while enraged (= zone 0).
 * GU 0x6a160(mgr, area, pos) is the same test with Teostra (id 27) only, returning 0 / 1; its callers 0x2a3814 /
 * 0x2a5344 OR it with the hot-area test 0x48d4cc into the heat damage (C). Core hook dala_heat_zone on its entry:
 * 1 inside our head's zone, else GU's own test. GU's burn effect is Teostra's (deviation: no second variant). */
#include "game.h"
#include "util.h"
#include "em090.h"
#include "dala_efx.h"
#include "dala_shah.h"

#define EN_AREA   0x1054   /* u8 map area */
#define rageOn    FN(int (*)(void *), 0x8172c)   /* [4U 0x954e48: W+0x530 == 1] (dala_parts.c) */
#define W_HEAT    0x10     /* s32 heat pulse [4U W+0x7e64] */
#define W_HEAT_Z  0x40     /* u8 heat zone [4U work+0x40] */
typedef void (*joint_mtx_t)(void *unit, uint32_t joint, float *out);
#define jointMtx  FN(joint_mtx_t, 0xc1660)   /* = 4U 0x930894 */

void dala_head25_frame(void *self)
{
    int32_t *pulse = &DALA_WORK(int32_t, self, W_HEAT);
    uint8_t *zone = &DALA_WORK(uint8_t, self, W_HEAT_Z);
    uint32_t m = curMotion(self), was = *pulse > 0;
    if (*pulse > 0) --*pulse;
    if (m == 3 || (m == 0x204 && motionCheck(self, 2, 0, 400.0f, 0.0f))) { *pulse = 2; *zone = 1; }
    uint32_t rage = rageOn(self) != 0;
    if (rage) { *pulse = 2; *zone = 0; }
    if (was != (*pulse > 0)) {
        static uint32_t s_n;
        if (++s_n <= 40)
            logf("dalaport: heat zone %s (zone %u, motion %x, rage %u) frame %u", *pulse > 0 ? "on" : "off", *zone, m,
                 rage, FIELD(uint32_t, self, F_FRAMES));
    }
    dala_efx_heat(self, *pulse > 0 ? (*zone ? 16 : 8) : 0);   /* 4U slot 48 bits 3 / 4 -> uMhEftCtrl004 */
    /* 10/114 (4U 0x774d44, C): while motion 0x304 plays, frame 1 arms attack 10 in slot 0 with param 2 (attack kind
     * noted in work+0x58 by dala_attack, as 4U does here from the record's byte 0x19), frame 60 resets slot 0 */
    if (FIELD(uint8_t, self, EN_ACT_CAT) == 10 && FIELD(uint8_t, self, EN_ACT_NUM) == 114 && m == 0x304) {
        if (atFrame(self, 1.0f)) dala_attack(self, 0, 10, 2);
        else if (atFrame(self, 60.0f)) attackFlag(self, 0);
    }
}

/* Map icons (4U map UI 0xb9b390: head 24 / 110 at joint 107, tails 83 / 111 at joint 154, icon classes 22 / 23,
 * class-study.md, C). GU's icon loop 0x61a07c places each enemy's icon at its object position: 0xc09c8(out, enemy)
 * copies enemy+0x40..0x48, called at 0x61a10c with the enemy in r1 and the map transform after it (C). Both halves
 * stay on their spawn point and move through bone 0 (class-study.md "Position"), so the core hook dala_map_pos on
 * 0xc09c8 (2 callers) answers the icon loop's call with the 4U icon joint instead. The size class stays Kushala's 18
 * (allocations.toml): GU writes the class out as the icon frame (0x61aa68), uses 22 once and 23 never, so 4U's
 * 22 / 23 may have no GU frame (deviation until checked in game). */
int dala_map_pos_c(uint32_t *regs)
{
    void *e = (void *)regs[1], *head = dala_head();
    if (regs[7] != MAIN(0x61a110) || !head || (e != head && dala_partner(head) != e)) return 0;
    float *out = (float *)regs[0];
    jointPos(e, e == head ? 107 : 154, out);
    out[3] = 0.0f;
    return 1;
}

/* core hook (module/build.py) on GU 0x6a160: regs[0] = mgr, [1] = area, [2] = float *pos */
int dala_heat_zone_c(uint32_t *regs)
{
    void *head = dala_head();
    /* both callers (hunter 0x2a3814, 0x2a5344) pass their own position: pos = character + 0x40 (area +0x1054, C), so
     * the character's floor byte is at pos - 0x40 + 0x1065 (dala_shah.c) */
    const uint8_t *chr = (const uint8_t *)regs[2] - 0x40;
    if (dala_shah_zone_hit(head, (const float *)regs[2], regs[1] & 0xff, chr[0x1065])) { regs[0] = 1; return 1; }
    if (!head || DALA_WORK(int32_t, head, W_HEAT) <= 0 || FIELD(uint8_t, head, EN_AREA) != (regs[1] & 0xff)) return 0;
    static const float k_off[2][4] = {{0.0f, -500.0f, 1100.0f, 1250.0f}, {500.0f, 1300.0f, -700.0f, 1700.0f}};
    const float *o = k_off[DALA_WORK(uint8_t, head, W_HEAT_Z) ? 1 : 0], *pos = (const float *)regs[2];
    float mt[16], d2 = 0.0f, r = o[3] * speedFactor(head);
    jointMtx(head, DALA_WORK(uint8_t, head, W_HEAT_Z) ? 101 : 4, mt);
    for (int i = 0; i < 3; i++) {
        float c = mt[i] * o[0] + mt[4 + i] * o[1] + mt[8 + i] * o[2] + mt[12 + i] - pos[i];
        d2 += c * c;
    }
    if (d2 > r * r) return 0;
    static uint32_t s_n;
    if (++s_n <= 20)
        logf("dalaport: heat zone hit at %d %d %d (zone %u, distance^2 %d, radius %d)", (int)pos[0], (int)pos[1],
             (int)pos[2], DALA_WORK(uint8_t, head, W_HEAT_Z), (int)d2, (int)r);
    regs[0] = 1;
    return 1;
}
