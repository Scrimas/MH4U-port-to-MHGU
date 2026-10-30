/* em057_01_fix.c: Stygian Zinogre fixes inside the GU handlers it keeps (verdict KEEP, notes/phase2-actions.md 2;
 * notes/plan.md W4 / B4).
 *
 * Attack indices (phase1-variant-map.md 1B): GU's charged-attack ladders send variant 1 to the uncharged Zinogre index
 * whatever the charge (C, 13 ladders); 4U's em==49 branches arm Stygian's own records (4U em049 attack data, indices
 * 48..73, our em057_01_attackdata). Entry hook on GU attackEx 0x7dc2c (self, slot, index, flags; GU's plain attack
 * 0x7df94 is `mov r3, #0; b 0x7dc2c`): for a variant-1 Zinogre in one of the actions of s_atk, the index GU passes
 * becomes 4U's (C: the 4U site named per row, read 2026-10-28). The charge test is GU 0x81790 (= 4U 0x90f90c; GU's own
 * ladders call it). 1/4 and 1/21 slot 1 arm nothing when uncharged in 4U: index -1, GU's own "none" (its variant-0
 * path at ef3fc8). GU's flags are kept (S: equal to 4U's at the sites read). Actions served by our ports pass 4U's
 * indices themselves and are not in the table. Multiplayer: attacks are armed on every machine, as GU's; damage stays
 * with the controlling machine (GU's rule). */
#include "em057_01.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

enum { ALWAYS, CHARGED, CHARGED_ELSE_NONE };
struct atk { uint8_t cat, num, slot, gu_idx, mode, sz_idx; };

static const struct atk s_atk[] = {
    {1, 4, 1, 25, CHARGED_ELSE_NONE, 51},  {1, 21, 1, 25, CHARGED_ELSE_NONE, 51},     /* 846dc4 */
    {1, 4, 0, 33, ALWAYS, 54},             {1, 21, 0, 33, ALWAYS, 54},                /* 846e5c */
    {2, 46, 0, 11, CHARGED, 60},                                                      /* 843720 */
    {7, 0, 0, 1, CHARGED, 59}, {7, 1, 0, 1, CHARGED, 59},                             /* 847e74 8480d4 */
    {7, 207, 0, 1, CHARGED, 59}, {7, 208, 0, 1, CHARGED, 59},
    {7, 22, 0, 10, ALWAYS, 50}, {7, 112, 0, 10, ALWAYS, 50}, {7, 201, 0, 10, ALWAYS, 50},   /* 84b0d4 */
    {7, 89, 0, 28, CHARGED, 69},                                                      /* 84dc44 */
    {7, 109, 0, 31, CHARGED, 66},                                                     /* 84f24c */
    {7, 126, 0, 26, ALWAYS, 52},                                                      /* 84f38c (param 1) */
};

/* GU attackEx 0x7dc2c(self, slot, index, flags) */
int em057_01_atk_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (!self || FIELD(uint16_t, self, EN_ID) != STYGIAN_ZINOGRE_EM_ID) return 0;
    uint8_t cat = FIELD(uint8_t, self, EN_ACT_CAT), num = FIELD(uint8_t, self, EN_ACT_NUM);
    for (uint32_t i = 0; i < sizeof s_atk / sizeof s_atk[0]; i++) {
        const struct atk *a = &s_atk[i];
        if (a->cat != cat || a->num != num || a->slot != regs[R1] || a->gu_idx != regs[R2]) continue;
        if (a->mode == ALWAYS || isCharged(self)) regs[R2] = a->sz_idx;
        else if (a->mode == CHARGED_ELSE_NONE) regs[R2] = 0xffffffffu;
        break;
    }
    return 0;
}

/* GU uEm057_00 slot 132 0xef3214(self): the charge glow through material animations, GU only (C). The init 0xeeed64
 * keeps the material of type 52 (this+0xcac4; its 'normal_Loop' / 'tyoutaiden_Loop' / 'Death' at +0xcacc..+0xcad4)
 * and the one of type 3 (+0xcac8; +0xcad8 / +0xcadc); slot 132 is the only reader of +0xcac4..+0xcae0 in the class.
 * 4U's slot 50 (between 47 = GU 129 and 51 = GU 133) is the empty default 0x9428d4 `bx lr`, and Stygian's 4U model has
 * no type-52 material (its animations: 'Normal_to_VirusLv1' / 'VirusLv1_to_Normal', the frenzy, and the effect's
 * 'Animation'), so +0xcac4 stayed 0 and slot 132 wrote through it (test 1: 0xb0cab0 from 0xef3434). Skipped for
 * Stygian, as 4U (return 1 = the hooked function returns at once).
 * But slot 132 starts with the parts visibility (C: ef321c..ef323c): variant byte +0xb5f5 == 4 (Thunderlord) ->
 * 0xef34e8, else 0xef37b4 = applyPartsState of the charge (state 1 / 0, 19 frenzy) and of every break / sever pair.
 * Skipping it left every mesh group drawn (issue #8: charged spikes at spawn, breaks and the tail cut never shown),
 * so Stygian (variant 1) runs 0xef37b4 itself; it reads none of the glow fields +0xcac4..+0xcae0. */
typedef void (*em057_parts_t)(void *self);
#define em057Parts FN(em057_parts_t, 0xef37b4)

int em057_01_glow_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    if (!self || FIELD(uint16_t, self, EN_ID) != STYGIAN_ZINOGRE_EM_ID) return 0;
    em057Parts(self);
    return 1;
}
