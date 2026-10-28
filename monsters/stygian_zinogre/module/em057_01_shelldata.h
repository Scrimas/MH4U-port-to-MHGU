/* em057_01_shelldata.h: Stygian Zinogre's shell data from MH4U v1.1 (notes/b5-shells.md step 1): the orb records of
 * the uShell046 posts, the pillar frame tables of the uShell044 posts and the orb's arc axis. [4U address] at each
 * table. 4U keeps the vectors at 0 in its image and fills them in static initializers (uEm048 statics 0xd27970, MT
 * constants 0xd1daf0); tools/shelldata4u_em057_01.py runs them under unicorn and prints every value below (C), and
 * its --check mode compares this file with them. The orb floats f0..f5 and the frames are 4U .data (C, same tool).
 * Neither init reads data / bss (C), so the init order does not matter. Include from one .c (static tables). */
#pragma once
#include <stdint.h>

#define SZ_N(a) (sizeof(a) / sizeof((a)[0]))

/* ---- uShell046 orb records [4U 0x856900(this, out, kind, idx), rank = questRank 0x69ae70]: rank < 5: kind 0 ->
 * sz_orb_hr0, else sz_orb_hr1; rank >= 5: kind 1 -> sz_orb_g1, kind 2 -> sz_orb_g2 (idx <= 9), else sz_orb_g0
 * (idx <= 3) (C, design 1a). off / a / b are in the owner's frame: the ctor 0xc8a754 turns them by Ry Rx Rz(owner
 * angles W+424 / W+428 / W+0x1b0) and adds the owner position W+408 (C). f[] names are uses, not 4U names (design
 * 1a): f0 speed to A (+0x298), f1 speed to B (+0x29c), f2 age limit (+0x2a0), f3 arc (+0x2e0), f4 wobble radius
 * (|f4| -> +0x2f8), f5 wobble speed (+0x2fc / +0x300). */
typedef struct {
    float off[4];   /* +0x00 spawn offset -> shell position +0x100 */
    float a[4];     /* +0x10 point A, end of leg 1 -> +0x278 */
    float b[4];     /* +0x20 point B, end of leg 2 -> +0x288 (homing subtypes replace it, design 1a) */
    float f[6];     /* +0x30 f0..f5 */
} sz_orb_rec;
_Static_assert(sizeof(sz_orb_rec) == 72, "sz_orb_rec = 4U 72-B record");

#define SZ_4U_ORB_HR0 0xfebc18u
#define SZ_4U_ORB_HR1 0xfebd38u
#define SZ_4U_ORB_G0  0xfebe58u
#define SZ_4U_ORB_G1  0xfebf78u
#define SZ_4U_ORB_G2  0xfec098u

/* [4U 0xfebc18] High Rank, kind 0 */
static const sz_orb_rec sz_orb_hr0[4] = {
    {{-400.0f, 300.0f, -300.0f, 0.0f}, {-1000.0f, 250.0f, -500.0f, 0.0f}, {-550.0f, 150.0f, 900.0f, 0.0f},
     {4.0f, 50.0f, 600.0f, -300.0f, 50.0f, 50.0f}},
    {{-200.0f, 200.0f, -100.0f, 0.0f}, {-400.0f, 200.0f, -300.0f, 0.0f}, {-150.0f, 150.0f, 700.0f, 0.0f},
     {2.0f, 50.0f, 600.0f, -500.0f, 50.0f, 50.0f}},
    {{400.0f, 300.0f, -300.0f, 0.0f}, {1000.0f, 250.0f, -500.0f, 0.0f}, {650.0f, 150.0f, 900.0f, 0.0f},
     {25.0f, 35.0f, 600.0f, 300.0f, 50.0f, 50.0f}},
    {{200.0f, 200.0f, -100.0f, 0.0f}, {400.0f, 200.0f, -300.0f, 0.0f}, {200.0f, 150.0f, 700.0f, 0.0f},
     {20.0f, 35.0f, 600.0f, 500.0f, 50.0f, 50.0f}},
};
/* [4U 0xfebd38] High Rank, kind 1 */
static const sz_orb_rec sz_orb_hr1[4] = {
    {{-200.0f, 200.0f, 100.0f, 0.0f}, {-250.0f, 200.0f, 800.0f, 0.0f}, {-300.0f, 170.0f, 2000.0f, 0.0f},
     {70.0f, 7.0f, 300.0f, 500.0f, 50.0f, 3.0f}},
    {{-200.0f, 200.0f, 100.0f, 0.0f}, {-700.0f, 200.0f, 600.0f, 0.0f}, {-1300.0f, 170.0f, 2000.0f, 0.0f},
     {70.0f, 15.0f, 300.0f, 500.0f, 50.0f, 3.0f}},
    {{200.0f, 200.0f, 100.0f, 0.0f}, {250.0f, 200.0f, 800.0f, 0.0f}, {300.0f, 170.0f, 2000.0f, 0.0f},
     {70.0f, 7.0f, 300.0f, 500.0f, 50.0f, 3.0f}},
    {{200.0f, 200.0f, 100.0f, 0.0f}, {700.0f, 200.0f, 600.0f, 0.0f}, {1300.0f, 170.0f, 2000.0f, 0.0f},
     {70.0f, 15.0f, 300.0f, 500.0f, 50.0f, 3.0f}},
};
/* [4U 0xfebe58] G Rank, kind 0 (the vectors of sz_orb_hr0, other speeds) */
static const sz_orb_rec sz_orb_g0[4] = {
    {{-400.0f, 300.0f, -300.0f, 0.0f}, {-1000.0f, 250.0f, -500.0f, 0.0f}, {-550.0f, 150.0f, 900.0f, 0.0f},
     {6.0f, 35.0f, 600.0f, -300.0f, 50.0f, 50.0f}},
    {{-200.0f, 200.0f, -100.0f, 0.0f}, {-400.0f, 200.0f, -300.0f, 0.0f}, {-150.0f, 150.0f, 700.0f, 0.0f},
     {3.0f, 35.0f, 600.0f, -500.0f, 50.0f, 50.0f}},
    {{400.0f, 300.0f, -300.0f, 0.0f}, {1000.0f, 250.0f, -500.0f, 0.0f}, {650.0f, 150.0f, 900.0f, 0.0f},
     {6.0f, 35.0f, 600.0f, 300.0f, 50.0f, 50.0f}},
    {{200.0f, 200.0f, -100.0f, 0.0f}, {400.0f, 200.0f, -300.0f, 0.0f}, {200.0f, 150.0f, 700.0f, 0.0f},
     {3.0f, 35.0f, 600.0f, 500.0f, 50.0f, 50.0f}},
};
/* [4U 0xfebf78] G Rank, kind 1 (the vectors of sz_orb_hr1) */
static const sz_orb_rec sz_orb_g1[4] = {
    {{-200.0f, 200.0f, 100.0f, 0.0f}, {-250.0f, 200.0f, 800.0f, 0.0f}, {-300.0f, 170.0f, 2000.0f, 0.0f},
     {4.2f, 7.0f, 800.0f, 500.0f, 50.0f, 3.0f}},
    {{-200.0f, 200.0f, 100.0f, 0.0f}, {-700.0f, 200.0f, 600.0f, 0.0f}, {-1300.0f, 170.0f, 2000.0f, 0.0f},
     {4.5f, 15.0f, 800.0f, 500.0f, 50.0f, 3.0f}},
    {{200.0f, 200.0f, 100.0f, 0.0f}, {250.0f, 200.0f, 800.0f, 0.0f}, {300.0f, 170.0f, 2000.0f, 0.0f},
     {2.1f, 7.0f, 900.0f, 500.0f, 50.0f, 3.0f}},
    {{200.0f, 200.0f, 100.0f, 0.0f}, {700.0f, 200.0f, 600.0f, 0.0f}, {1300.0f, 170.0f, 2000.0f, 0.0f},
     {2.25f, 15.0f, 900.0f, 500.0f, 50.0f, 3.0f}},
};
/* [4U 0xfec098] G Rank, kind 2 = the vt77 orbs (0x855fe4 case k posts records (2,3) (0,1) (4,5) (6,7) (8,9) (0) (1)
 * for k = 0..6, A.y += 300 at 0x856148: design 1a) */
static const sz_orb_rec sz_orb_g2[10] = {
    {{-350.0f, 250.0f, 250.0f, 0.0f}, {-100.0f, 150.0f, 450.0f, 0.0f}, {-100.0f, 0.0f, 1300.0f, 0.0f},
     {4.0f, 55.0f, 600.0f, -300.0f, 50.0f, 50.0f}},
    {{-400.0f, 350.0f, 100.0f, 0.0f}, {-550.0f, 250.0f, 350.0f, 0.0f}, {-100.0f, 0.0f, 1300.0f, 0.0f},
     {2.8f, 55.0f, 600.0f, -500.0f, 50.0f, 50.0f}},
    {{350.0f, 250.0f, 250.0f, 0.0f}, {100.0f, 150.0f, 450.0f, 0.0f}, {100.0f, 0.0f, 1300.0f, 0.0f},
     {4.0f, 55.0f, 600.0f, 300.0f, 50.0f, 50.0f}},
    {{400.0f, 350.0f, 100.0f, 0.0f}, {550.0f, 250.0f, 350.0f, 0.0f}, {100.0f, 0.0f, 1300.0f, 0.0f},
     {2.8f, 55.0f, 600.0f, 500.0f, 50.0f, 50.0f}},
    {{-300.0f, 250.0f, -400.0f, 0.0f}, {-400.0f, 150.0f, -500.0f, 0.0f}, {-1300.0f, 0.0f, -500.0f, 0.0f},
     {2.6f, 55.0f, 600.0f, 300.0f, 50.0f, 50.0f}},
    {{-450.0f, 350.0f, -150.0f, 0.0f}, {-550.0f, 250.0f, -50.0f, 0.0f}, {-1300.0f, 0.0f, -500.0f, 0.0f},
     {2.0f, 55.0f, 600.0f, 500.0f, 50.0f, 50.0f}},
    {{0.0f, 250.0f, 450.0f, 0.0f}, {100.0f, 150.0f, 800.0f, 0.0f}, {100.0f, 0.0f, 1700.0f, 0.0f},
     {4.5f, 55.0f, 600.0f, -300.0f, 50.0f, 50.0f}},
    {{-200.0f, 350.0f, 300.0f, 0.0f}, {-400.0f, 250.0f, 650.0f, 0.0f}, {100.0f, 0.0f, 1700.0f, 0.0f},
     {3.8f, 55.0f, 600.0f, -500.0f, 50.0f, 50.0f}},
    {{50.0f, 150.0f, -450.0f, 0.0f}, {200.0f, 150.0f, -650.0f, 0.0f}, {-100.0f, 0.0f, -1300.0f, 0.0f},
     {3.5f, 55.0f, 600.0f, -300.0f, 50.0f, 50.0f}},
    {{-250.0f, 150.0f, -450.0f, 0.0f}, {-400.0f, 150.0f, -650.0f, 0.0f}, {-100.0f, 0.0f, -1300.0f, 0.0f},
     {3.5f, 55.0f, 600.0f, -500.0f, 50.0f, 50.0f}},
};
_Static_assert(SZ_N(sz_orb_hr0) == 4 && SZ_N(sz_orb_hr1) == 4 && SZ_N(sz_orb_g0) == 4 && SZ_N(sz_orb_g1) == 4 &&
               SZ_N(sz_orb_g2) == 10, "orb record counts (0x856900: idx <= 3, kind 2 idx <= 9)");
/* the five tables are contiguous in 4U, in this order (C): the counts above fill them exactly */
_Static_assert(SZ_4U_ORB_HR0 + sizeof(sz_orb_hr0) == SZ_4U_ORB_HR1 && SZ_4U_ORB_HR1 + sizeof(sz_orb_hr1) ==
               SZ_4U_ORB_G0 && SZ_4U_ORB_G0 + sizeof(sz_orb_g0) == SZ_4U_ORB_G1 && SZ_4U_ORB_G1 +
               sizeof(sz_orb_g1) == SZ_4U_ORB_G2, "orb tables = the 4U layout");

/* ---- the orb's arc axis [4U 0x10e63a8, an MT constant = (1, 0, 0, 0), C]: uShell046 0xc89508 copies its x, y, z
 * to shell +0x2e8 and turns them by the leg's pitch, then yaw (0xc8952c..0xc895d0); phase 3 offsets the shell by
 * f3 * sin(pi t / T) along it (0xc8a664..0xc8a6f8). The pitch turn keeps (1, 0, 0) and the yaw turn makes it (cos
 * yaw, 0, -sin yaw): a horizontal arc to the side of the leg (C, em057_01_shell046.c orb_leg_b). */
#define SZ_4U_ORB_ARC_AXIS 0x10e63a8u
static const float sz_orb_arc_axis[4] = {1.0f, 0.0f, 0.0f, 0.0f};
/* the 4U effect request ctor 0xc0ca90 defaults (C, same MT block): position and rotation = 0x10e6378 (0, 0, 0, 0),
 * scale = 0x10e6388 (1, 1, 1, 0): no Stygian effect post changes the scale (PEL records scale 1.0, step 3) */

/* ---- uShell044 subtype-3 pillar frame tables: post a pillar at motion frame `frame` (atFrame 0x941dbc), offset
 * (x, y, z) turned by the owner's yaw (0x8470ec..0x847148: x' = x cos + z sin, z' = z cos - x sin, y as is, angle =
 * u16 [this+0x8d24], sin 0x568bf0 / cos 0x568bb8 = table 0xe36ec8 {sin, cos, ..}); a row with frame < 0 ends a table
 * (kept: 4U loops until it) (C). */
typedef struct {
    float frame;
    uint32_t pad4;  /* 0 */
    float x, y, z;  /* +0x08 offset (the init writes x, y, z and 0 at +0x14) */
    uint32_t pad20; /* 0 */
} sz_pillar_row;
_Static_assert(sizeof(sz_pillar_row) == 24, "sz_pillar_row = 4U 24-B row");

#define SZ_4U_PILLAR_STANCE 0xfeba98u
#define SZ_4U_PILLAR_WALK1  0xfebb28u
#define SZ_4U_PILLAR_WALK2  0xfebbb8u

/* [4U 0xfeba98] 1/6 15 16 17 28-33, the charge stance (loop 0x8470a4, em test 0x847098) */
static const sz_pillar_row sz_pillar_stance[6] = {
    {64.0f, 0, 0.0f, 0.0f, 500.0f, 0},
    {128.0f, 0, 400.0f, 0.0f, 200.0f, 0},
    {128.0f, 0, -400.0f, 0.0f, 200.0f, 0},
    {182.0f, 0, 400.0f, 0.0f, -300.0f, 0},
    {182.0f, 0, -400.0f, 0.0f, -300.0f, 0},
    {-1.0f, 0, 0.0f, 0.0f, 0.0f, 0},
};
/* [4U 0xfebb28] 2/40 (the charge walk, 0x84516c with r1 = 1) step W+0x144 == 1 (0x8452d4 .. post 0x84538c) */
static const sz_pillar_row sz_pillar_walk1[6] = {
    {40.0f, 0, 0.0f, 0.0f, 800.0f, 0},
    {90.0f, 0, 400.0f, 0.0f, 500.0f, 0},
    {90.0f, 0, -400.0f, 0.0f, 500.0f, 0},
    {140.0f, 0, 400.0f, 0.0f, 0.0f, 0},
    {140.0f, 0, -400.0f, 0.0f, 0.0f, 0},
    {-1.0f, 0, 0.0f, 0.0f, 0.0f, 0},
};
/* [4U 0xfebbb8] 2/40 step W+0x144 == 2 (0x845498 .. post 0x845580) */
static const sz_pillar_row sz_pillar_walk2[4] = {
    {30.0f, 0, 0.0f, 0.0f, 800.0f, 0},
    {78.0f, 0, 400.0f, 0.0f, 200.0f, 0},
    {78.0f, 0, -400.0f, 0.0f, 200.0f, 0},
    {-1.0f, 0, 0.0f, 0.0f, 0.0f, 0},
};
_Static_assert(SZ_N(sz_pillar_stance) == 6 && SZ_N(sz_pillar_walk1) == 6 && SZ_N(sz_pillar_walk2) == 4,
               "pillar row counts (5 / 5 / 3 posts + the frame < 0 row)");
/* contiguous in 4U and followed by the first orb table (C) */
_Static_assert(SZ_4U_PILLAR_STANCE + sizeof(sz_pillar_stance) == SZ_4U_PILLAR_WALK1 && SZ_4U_PILLAR_WALK1 +
               sizeof(sz_pillar_walk1) == SZ_4U_PILLAR_WALK2 && SZ_4U_PILLAR_WALK2 + sizeof(sz_pillar_walk2) ==
               SZ_4U_ORB_HR0, "pillar tables = the 4U layout");

/* GU's own copy of 4U 0xfeba98: bss 0x2132a50, 32-B rows {float frame, 3 words 0, float x, y, z, word 0}, filled by
 * GU's static init 0xf06104 (GU init_array slot 0x184a828; GU's 1/6.. loop 0xef4494 / 0xef44b4 reads its frames, its
 * post removed). Equal to sz_pillar_stance in frame and offset, all 6 rows (C: tools/shelldata4u_em057_01.py runs
 * that GU init under unicorn too): step 5 can use either table, no run-time cross-check is needed. */
#define SZ_GU_PILLAR_STANCE 0x2132a50u
#define SZ_GU_PILLAR_STRIDE 32u
