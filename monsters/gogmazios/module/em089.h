#pragma once
#include "game.h"
#include "alloc.h"          /* allocations.toml (tools/alloc.py) */

#define EM089_ID    GOGMAZIOS_EM_ID   /* (variant 0 << 8) | em 089: first free large-monster number in MHGU */
#define EM089_INDEX GOGMAZIOS_INDEX   /* first free slot of the 137-entry id -> index table */
#define EM089_DONOR_INDEX GOGMAZIOS_DONOR_INDEX  /* Kushala (em024_00): placeholder data + per-index records */
#define EM089_SAVE_ID GOGMAZIOS_SAVE_ID   /* 'dummy1' = registry index 105 (unused by the game): Gogmazios' hunt /
                                             capture / size records in the save's 137-entry arrays (main.c stats_add) */

void em089_register_class(void);
void em089_act_run(void *self);   /* em089_act.c: slot 125 body */
int em089_think_blocked(void *self);  /* em089_act.c: slot 253 */
void em089_fields_init(void *self);   /* em089_act.c: zero our fields (ctor) */
int em089_cond(void *self, uint32_t id);   /* em089_act.c: GU slot 133 = 4U slot 51 (AI conditions) */
void em089_state_update(void *self);  /* em089_act.c: GU slot 119 = 4U slot 40 (per-frame state) */
void em089_action_start(void *self, uint32_t cat, uint32_t num);  /* GU slot 129 = 4U slot 47 */
void em089_action_remap(void *self, uint8_t *cat, uint8_t *num);  /* GU slot 127 = 4U slot 46 */
int em089_motion_frame(void *self);   /* GU slot 130 = 4U slot 48 (per-motion camera shakes) */
void em089_net_get(void *self, uint8_t *out, uint32_t size);       /* GU slot 171 = 4U slot 78 (net message) */
void em089_net_set(void *self, const uint8_t *in, uint32_t size);  /* GU slot 172 = 4U slot 79 */
void *em089_target_hunter(void *self);   /* em089_act.c: the hunter target slot 0 points at (same on every machine) */
uint32_t em089_drop_set(void *self);                /* em089_act.c: GU slot 149, shiny-drop table set (4U work+0xed) */
void em089_set_drop_flag(void *self, uint32_t v);   /* em089_act.c: 4U work+0xed, written before an item drop */
MtDTI *em089_dti(void);
void *em089_create_object(void);
