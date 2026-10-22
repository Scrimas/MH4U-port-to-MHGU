/* dala_gather.h: GU gather / carve points created at runtime (dala_gather.c): the meteor scales' mining points (4U
 * uShell038, dala_shell038.c) and the head's on-body carve point (4U uEm024 slot 39 / 48). C = read in code, S =
 * strong, G = guess. */
#pragma once
#include <stdint.h>

/* GU point types (+0x64; GU dispatch 0x3007c4: 1 / 17 carve, 2 / 18 mining, C) */
#define DALA_GP_CARVE   1u
#define DALA_GP_MINING  2u
/* item lists of the data file section GPTS (monsters/dalamadur/tools/gather_em090.py) = 4U record byte 12 */
#define DALA_GL_METEOR  0u    /* uShell038's point (4U record 0x102fab4) */
#define DALA_GL_HEAD    1u    /* the head's on-body point (4U record 0xfdc924) */
/* head work field of the on-body point's handle (4U work+0x50, s32; -1 = none: em090.c's ctor) */
#define DALA_W_GATHER   0x50

/* a point (4U 0x9357ec) of `type` with icon / radius / height / gathers at pos in `area`, items = list `list` of the
 * running quest's rank from the owner variant's GPTS; the handle (s16 point +0x4c), -1 = none (no list for the rank,
 * manager full: logged under `what`) */
int32_t dala_gather_new(void *owner, uint32_t list, uint32_t type, uint32_t icon, float radius, float height,
                        uint32_t gathers, const float *pos, uint32_t area, const char *what);
/* 4U 0x5b90c0 + 0x5b9ebc: release by handle; 0 when the point is already gone (used up points free themselves) */
int dala_gather_free(int32_t h, const char *why);
/* the live point's position (float x, y, z at +0x4) of a handle, 0 = gone (was dala_carve.c's point_of) */
float *dala_gather_pos(int32_t h);
/* the head's on-body carve point: created at spawn (em090.c slot 118 = 4U slot 39), moved every frame (dala_parts.c
 * slot 130 = 4U slot 48), released by the head's destructor */
void dala_head_point_spawn(void *self);
void dala_head_point_frame(void *self);
void dala_head_point_release(void *self);
