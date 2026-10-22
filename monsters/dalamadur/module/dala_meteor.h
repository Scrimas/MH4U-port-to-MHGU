/* dala_meteor.h: Dalamadur's meteor showers (dala_meteor.c): the head's meteor machine (4U uEm024 0x77274c / slot
 * 40 0x76db4c..0x76de94) and the meteor shell (4U uShell029) as a GU uShellEnemy subclass. */
#pragma once
#include <stdint.h>

/* 4U 0x77274c(this, kind, pattern, s0 duration, s1 delay): arm a shower at action start (GU slot 129 = 4U 47).
 * kind 1..3 = around target slot 0 (3 = with the mining meteor, 7200-frame cooldown, else 2), 4..9 = fixed arena
 * centres; pattern 0..2 = offset list. */
void dala_meteor_set(void *self, uint32_t kind, uint32_t pattern, float duration, float delay);
/* per frame from the head's GU slot 119 (4U slot 40 0x76db4c..0x76de94): delay, interval, posts, end, cooldown */
void dala_meteor_frame(void *self);
/* 4U 0x772ac4: machine off (kind 0, fields cleared; the cooldown work+0x3c is kept) */
void dala_meteor_reset(void *self);
/* 4U 0x66242c(mgr, 1, owner, kind, &pos, area, 0xffff, s0) = shell type 29 request + uShell029 ctor 0xc7da60:
 * one falling meteor. kind 2..7 (2 / 5 first, 3 / 6 mining meteor, 4 / 7 rain; 5..7 = Shah). Returns the shell
 * or 0 (logged). */
void *dala_meteor_post(void *owner, uint32_t kind, const float *pos, uint32_t area, uint32_t group, float arm_delay);
