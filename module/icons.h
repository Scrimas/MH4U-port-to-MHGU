/* icons.h: icons.c's helpers for other modules */
#pragma once
#include <stdint.h>

/* sprite (obj, kind) of the .gui of UI object ui (ui +0x24), as 0x546f48 / 0x546f84 find it; 0 if none */
uint8_t *icons_sprite(uint32_t ui, uint32_t obj, uint32_t kind);
/* on: HUD status sprite spr draws our HUD atlas (tools/ui_icons.py HUD_ATLASES, GU's cell layout) in place of
 * HD_hud_icon; off: back to its own texture (no-op if it is not ours). Idempotent: call it every time the cell is set. */
void icons_hud_own(uint8_t *spr, int on);
