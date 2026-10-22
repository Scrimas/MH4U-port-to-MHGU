/* dala_shah.h: Shah Dalamadur's crimson part states and their zones (goal D8, dala_shah.c). Head half only, Shah
 * variant only (4U em 110; every entry returns at once for Dalamadur, as 4U's em-24 tests do). */
#pragma once
#include <stdint.h>

/* GU object slots 171 / 172 (base 0xb17d8 / 0xb17f4: bytes 0 / 1 = this+0x7305 / 0x7306) = 4U slots 78 / 79: the
 * monster bytes of the network action message (pack 0xcb330 -> slot 171 (this, buf + 132, 20), unpack 0xcc154 ->
 * slot 172 at 0xcc830, before the action is applied) */
#define DALA_SLOT_NET_GET 171
#define DALA_SLOT_NET_SET 172

void dala_shah_spawn(void *self);                    /* 4U slot 39 0x76d8ac..0x76da78 */
void dala_shah_frame(void *self);                    /* 4U slot 40 0x76de94..0x76df08 (every machine) */
void dala_shah_reset(void *self, uint32_t var);      /* 4U 0x7753f4(this, var): the crimson re-roll at action end */
void dala_shah_slot(void *self, uint32_t k, float value);   /* 4U 0x7756d4(this, -, k, value): arm zone k */
void dala_shah_release(void *self);                  /* delete: kill the zone effects still alive */
void dala_shah_net_get(void *self, uint8_t *out, uint32_t size);        /* GU slot 171 = 4U 0x7751cc */
void dala_shah_net_set(void *self, const uint8_t *in, uint32_t size);   /* GU slot 172 = 4U 0x7751a4 */
/* 4U 0x687280's Shah part: 1 when a hunter at pos (area, floor byte) stands in an armed zone (heat tick) */
int dala_shah_zone_hit(void *head, const float *pos, uint32_t area, uint32_t floor);
