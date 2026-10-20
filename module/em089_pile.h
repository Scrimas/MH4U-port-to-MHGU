/* em089_pile.h: the fallen Dragonator spear (4U em089 cut object 1 = a one-shot pile bunker), em089_pile.c. */
#pragma once
#include <stdint.h>

/* em089_break.c, every frame once part 1 (the spear) is severed: spawns GU cut slot 1 and starts the 4U spear port
 * (idempotent; also takes over a cut object GU spawned first) */
void em089_pile_sever(void *self);
/* stage_cannon.c's kind-11 prompt check (0x503b88 from the interaction, local hunter): -1 = the hunter is not at the
 * spear record, else 0 / 1 = 4U ready check 0xb0f498 */
int em089_pile_ready(void *hunter);
/* stage_cannon.c's switch press (0x503bb0 from the switch action, any player on every machine): 1 = the press was
 * at the spear record (handled: 4U 0x6a1f18), 0 = not ours. remote = 1: a replayed press of another machine's
 * hunter, matched with a wider radius (the spear lands from each machine's own monster copy) and queued until this
 * machine's spear has landed */
int em089_pile_fire(void *player, int remote);
/* stage manager cleanup (quest end): free the interaction record */
void em089_pile_cleanup(void);
/* em089 deleting destructor: drop everything keyed to this monster */
void em089_pile_forget(void *self);
