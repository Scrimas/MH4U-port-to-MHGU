/* em089_shell016.h: Gogmazios' breath / beam / explosion attack shells (MH4U uShell016), em089_shell016.c. */
#pragma once
#include <stdint.h>

/* 4U subtypes used by em089 (event byte +8 of 0x6620c4) and their 4U call sites:
 *   53 7/105 0x8be100, 36 7/105 0x8be138 (the two branches of one site), 37 7/106 0x8be3c8,
 *   41 7/107.. 0x8be84c, 7/114 0x8bf560, 7/126 0x8bffcc, 7/135 0x8c0620, 51 7/136 0x8beac8, 54 7/143 0x8c14e0,
 *   52 / 55 / 56 7/146 0x8c23b0 / 0x8c246c / 0x8c248c (one site: action serial % 3 == 1 -> 55, == 2 -> 56, else 52).
 * Every em089 site passes joint 3, length 10000 and, per subtype, the same offset / angles (stored here). */
enum {
    EM089_S016_BREATH_A = 36, EM089_S016_BREATH_SWEEP = 37, EM089_S016_BEAM = 41, EM089_S016_BEAM_136 = 51,
    EM089_S016_FINALE = 52, EM089_S016_BREATH_B = 53, EM089_S016_BEAM_143 = 54, EM089_S016_FINALE_2 = 55,
    EM089_S016_FINALE_3 = 56,
};

/* post one attack shell (4U 0x6620c4 -> uShell016). pos: optional joint-space offset (x, y, z) replacing the 4U one
 * (0 = the 4U value for the subtype: (0, 0, 0) for 36 / 37 / 53, (0, -50, 130) for the others). Returns the shell
 * or 0 (logged). */
void *em089_shell016_post(void *self, uint32_t subtype, const float *pos);

/* effects hook (effects agent): called at the shell's init with the 4U uEffect002 id it posts there through 0xc0b470
 * (36 / 53 -> 48, 37 -> 50, 41 / 52 / 54 / 55 / 56 -> 53, 51 -> 54). Null = no effect. */
extern void (*em089_shell016_fx)(void *shell, void *owner, uint32_t subtype, uint32_t efx_id);
