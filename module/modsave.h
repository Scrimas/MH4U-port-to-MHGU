/* modsave.h: the mod's save files (notes/mod-save-format.md): split and merge of one character's slot (modsave.c,
 * pure: no game call; tools/modsave.py is the reference, tools/test_modsave.py compares them) */
#pragma once
#include <stdint.h>

#define MS_SLOT_SIZE 0x11F8C4u      /* one character's bytes in GU's image */
#define MS_FILE_SIZE 0x8000u        /* each file's fixed size, the budget */
#define MS_HEADER 32u
#define MS_RESERVED 0x50BEu         /* the reserved block (sUserInfo +0x3684) in the slot; the link record at its start */
#define MS_LINK_N 16u
#define MS_SPLIT 1u
#define MS_FULL 2u

struct ms_quest { uint32_t index, id; };       /* a quest list index that is the mod's, and its quest */

struct ms_stats {
    uint32_t exact;                 /* the slot's hash matched the file's: unchanged since the split */
    uint32_t placed, moved, kept;   /* records put back, put back elsewhere, left as GU's slot has them */
    uint32_t aside;                 /* records that found no place (kept for the next file) */
};

uint32_t ms_fnv(const uint8_t *p, uint32_t n, uint32_t h);

/* the split: writes the mod file into file[cap] and returns its size, or -1 when the slot cannot be split (the
 * hunter holds an added weapon and the box has neither a vanilla weapon nor an empty entry). With clean, the slot
 * loses what the file holds and gets the link record "split". aside[aside_n] = records a merge could not place,
 * appended as aside records. *left = records the budget kept in the slot. */
int ms_split(uint8_t *slot, const struct ms_quest *q, uint32_t qn, uint32_t link, uint32_t gen,
             const uint8_t *aside, uint32_t aside_n, uint8_t *file, uint32_t cap, int clean, uint32_t *left);

/* the file's header fields; 0 = a valid file */
int ms_parse(const uint8_t *file, uint32_t len, uint32_t *used, uint32_t *link, uint32_t *gen, uint32_t *slot_hash);

/* the merge: the file's records back into the slot. Every byte it overwrites goes to journal[jcap] first (*jlen);
 * records without a place go to aside[acap] (*alen). 0 = merged; -1 = not a valid file, -2 = the journal or the aside
 * buffer is full (the slot is then put back as it was) */
int ms_merge(uint8_t *slot, const uint8_t *file, uint32_t len, const struct ms_quest *q, uint32_t qn,
             uint8_t *journal, uint32_t jcap, uint32_t *jlen, uint8_t *aside, uint32_t acap, uint32_t *alen,
             struct ms_stats *st);

/* the slot back as it was before the merge */
void ms_restore(uint8_t *slot, const uint8_t *journal, uint32_t jlen);

/* the link record of a slot: 1 = found (link, generation, state) */
int ms_link(const uint8_t *slot, uint32_t *link, uint32_t *gen, uint32_t *state);
void ms_set_link(uint8_t *slot, uint32_t link, uint32_t gen, uint32_t state);
