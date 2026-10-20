/* em089_shell051.h: the generic MH4U ground shell uShell051 (em089_shell051.c): tar splashes / puddles of the blobs and
 * the scorch / explosion shells of the breath and beam attack shells. Each one has its own attack. */
#pragma once
#include <stdint.h>

/* post one ground shell (4U 0x663d88 / 0x663a60 -> 0x662b44 -> event type 51).
 *   subtype: 1 / 6 / 16 / 17 / 19 / 20 = blob splash (em089_shell.c k_splash), 3 / 9-12 = 7/136 explosions, 13 / 14
 *   = finale (52 / 55 / 56) ground hits, 15 = beam (41 / 54) scorch; 4 / 5 / 8 / 18 = the explosions a ground shell
 *   posts when it ends (4U 0xc906d8, posted by em089_shell051.c itself); other values are dropped (logged).
 *   pos: ground point; yaw: u16 heading (only 13 / 15 move, along it); blob splashes pass 0 (4U zero angles).
 * Returns the shell or 0. */
void *em089_shell051_post(void *owner, uint32_t subtype, const float *pos, uint32_t yaw);
