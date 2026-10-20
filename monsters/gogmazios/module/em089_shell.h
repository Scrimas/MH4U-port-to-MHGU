/* em089_shell.h: Gogmazios tar blobs (MH4U uShell050) as a GU shell class (em089_shell.c). */
#pragma once
#include <stdint.h>

/* 4U kinds of uShell050 (param byte +0xfd): 0 / 1 drip (1 after the first roar, work+0xca), 2 / 3 thrown blob
 * (no 4U caller found), 4 / 5 tar shot lobbed to a point (0x8c9dd4), 6 / 7 rare drip (r % 500 == 0), 8 arena
 * drip (W+0x797e, never in GU), 9 unused. */
enum { EM089_SHELL_KINDS = 10 };

/* spawn one tar blob (4U event 0x660e88 type 50 + uShell050 init). owner = the em089 object, joint = 4U joint id
 * of the spawn point (255 = the owner position), target = landing point for kinds 4 / 5 (0 otherwise).
 * Returns the shell or 0 (logged). */
void *em089_shell_post(void *owner, uint32_t kind, uint32_t joint, const float *target);
