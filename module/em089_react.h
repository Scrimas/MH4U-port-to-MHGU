/* em089 reactions (react agent, 2026-10-19): categories 10 / 11 requested by the GU engine.
 * em089_react_run(self, cat, num) runs one frame of the reaction; returns 1 when it handled the pair, 0 when the
 * caller should keep its placeholder (category 11 and the category-10 numbers not ported yet). */
#pragma once
#include <stdint.h>

int em089_react_run(void *self, uint32_t cat, uint32_t num);
/* clear the donor's status param pointers in em089's data block (4U em089 has none: no poison / sleep / paralysis
 * / stun, so no 10/29 / 10/31); call every frame (em089_state_update) */
void em089_react_status_immune(void *self);
