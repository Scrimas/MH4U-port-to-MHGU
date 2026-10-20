/* em089 reactions (react agent, 2026-10-19). Static RE; C = confirmed in code, S = strong.
 *
 * 4U: action dispatch vt44 0x8c3ac0, category 10 -> 0x8c2784 = switch on the number W+0x1cb. Every case picks a
 * reaction-sequence table (sometimes by the flying mode W+0x1c9, the hit direction 0x938620 or the flag W+0x78bf)
 * and tail-calls the base player 0x9197c0(this, table, flag); the default ends the action (vt+0x164). The case
 * code runs every frame, but the player only uses table / flag on its first frame (step W+0x144 == 0), later
 * frames continue the stored table W+0x594 (C).
 *
 * GU: 0xa134c(this, table, flag) is the same player (C, structure matched instruction by instruction: step byte
 * rec+0x1a1 = 4U W+0x144, table rec+0x554 = W+0x594, index rec+0x548 = W+0x588, current descriptor rec+0x560 =
 * W+0x5a0; interpreter 0x9ef3c = 0x93188c with the same opcode numbers: 0/1/2/0x35 share the motion handler,
 * 0x13/0x14/0x2d no-op, 0x2c = 0x34, 0xfe / 0xff; motion movement setup 0x9ecac = 0x92a8d0 with the same types;
 * the end of a sequence calls the action-end slots 247/249/250/251/252 by state class like 4U). So the port calls
 * the GU player with the em089 tables converted to the GU format:
 *  - table: 8-byte entries {u32 op, u32 arg}, identical in both games (C);
 *  - motion descriptor (24 bytes, arg of ops 0/1/2): +0 u16 motion, +4 blend, +8 start frame, +0xc setMotionEx
 *    flags, +0x10 u16, +0x12 u8 movement type, +0x14 movement data. Only difference: 4U +4 / +8 are s32
 *    (vcvt.f32.s32 in 0x931a54), GU floats (vldr in 0x9ff64; Rathian 0x179b460 has 2.0f) (C);
 *  - movement data (type 1: {float, float}; types 2/3/7/8: 6 floats copied as is by both) (C). The type-2 data
 *    of em089 lives in 4U .bss (0x10b7cc8 / 0x10b7ce0) and is filled by the static init 0xd2ab1c (C);
 *  - op 0xe arg -> u32 value, op 0x2e arg -> {u32 id, float, u8} (4U 0x93457c, GU 0xaa418 camera event) (C).
 * Tables generated from 4U 0xff7024..0xff8164 (names = 4U addresses). Motions are em089's own ids.
 *
 * Mappings of the case conditions: W+0x1c9 -> rec+0x1bb (REC_MODE, S); 0x938620 -> 0x9e994 (C: both return bits
 * 3..5 of the reaction byte, 4U W+0x7993 = GU rec+0x5ccb); 0x940b50 (bits 0..2 of W+0x7993) -> rec+0x5ccb & 7 (C:
 * GU 0x9ab84 writes `0x9e454(this, k) & 7` into those bits as 4U 0x947f90 does with 0x921dfc); W+0x78bf ->
 * this+0x7585 (C: both are written from attack flag bit 18, 4U 0x92516c / GU 0xccbf0, and from vt+0x104 / vt+0x250
 * before requesting 10/154, 4U 0x946964 / GU 0x9c864). Reaction numbers: same in both games (C for the 110..115
 * family: 4U 0x943024 and GU 0x9c5d8 pick 110/113/114/115 by the same state classes; 10/7 is the state-0 flinch
 * of 4U 0x947ffc, and a GU monster's 10/7 also calls 0x9e994 before 0xa134c, 0x6bb74). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em089_react.h"

typedef struct { uint32_t op; const void *arg; } rx_op;
typedef struct {
    uint16_t motion, pad;      /* +0 motion id (bank << 8 | index) */
    float blend, start;        /* +4 / +8 (4U s32) */
    uint32_t flags;            /* +0xc setMotionEx flags */
    uint16_t kind;             /* +0x10 (2 + 2 in a row: second motion skipped) */
    uint8_t move, b13;         /* +0x12 movement type, +0x13 */
    const void *mv;            /* +0x14 movement data */
} rx_desc;
_Static_assert(sizeof(rx_op) == 8, "rx_op");
_Static_assert(sizeof(rx_desc) == 24, "rx_desc");

/* reaction-sequence player (this, table, flag): flag 1 -> 0xbcae0(this, rec+0x1c8), else setTargetMode(flag)
 * on the first frame [4U 0x9197c0] (C) */
typedef void (*reactPlay_t)(void *self, const rx_op *table, uint32_t flag);
#define reactPlay FN(reactPlay_t, 0xa134c)
/* hit direction: bits 3..5 of rec+0x5ccb [4U 0x938620: W+0x7993] (C) */
typedef uint32_t (*hitDir_t)(void *self);
#define hitDir FN(hitDir_t, 0x9e994)

#define REC(self)    FIELD(uint8_t *, self, EN_RECORD)
#define RX_DIRLOW    0x5ccb   /* rec: reaction byte, bits 0..2 = 4U 0x940b50 */
#define RX_FLAG78BF  0x7585   /* enemy: 4U W+0x78bf (attack flag bit 18 / vt+0x104 result) */

/* ---- tables (4U 0xff7024..: converted by hand-checked script, see header) ---- */
static const uint32_t MV_ff7adc[2] = {0xc2340000, 0xc0a00000};   /* {-45, -5} */
static const uint32_t MV_ff7c88[2] = {0xc2340000, 0xc0a00000};   /* {-45, -5} */
static const uint32_t MV_10b7cc8[6] = {0x00000000, 0x42200000, 0x00000000, 0x00000000, 0xbf4ccccd, 0x00000000};   /* 0 40 0 0 -0.8 0 */
static const uint32_t MV_10b7ce0[6] = {0x00000000, 0x41a33333, 0x00000000, 0x00000000, 0xbecccccd, 0x00000000};   /* 0 20.4 0 0 -0.4 0 */
static const uint32_t W_ff7dc8 = 0x40000000;   /* 2.0f */
static const uint32_t E_ff7ebc[3] = {0x6, 0x00000000, 0x010101ff};   /* 4U 0x93457c (6, 0.0, 255) */
static const uint32_t E_ff7ee0[3] = {0x1c, 0x00000000, 0x010101ff};   /* 4U 0x93457c (28, 0.0, 255) */
static const rx_desc D_ff78e4 = {0x301, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff78fc = {0x324, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7914 = {0x325, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff792c = {0x302, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7944 = {0x303, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff795c = {0x304, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7974 = {0x305, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff798c = {0x30b, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff79a4 = {0x328, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff79bc = {0x304, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff79d4 = {0x305, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7a04 = {0x306, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7a1c = {0x307, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7a34 = {0x308, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7a4c = {0x329, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7a64 = {0x307, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7a7c = {0x308, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7a94 = {0x329, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7aac = {0x307, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7ac4 = {0x308, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7ae4 = {0x315, 0, 0.0f, 0.0f, 0x0, 8, 2, 0, MV_10b7cc8};
static const rx_desc D_ff7afc = {0x000, 0, 0.0f, 0.0f, 0x0, 2, 1, 0, MV_ff7adc};
static const rx_desc D_ff7b14 = {0x316, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7b2c = {0x307, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7b44 = {0x308, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7b5c = {0x314, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7bc8 = {0x306, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7be0 = {0x307, 0, 0.0f, 0.0f, 0x0, 256, 0, 0, 0};
static const rx_desc D_ff7bf8 = {0x308, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7c10 = {0x303, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7c28 = {0x304, 0, 0.0f, 0.0f, 0x0, 256, 0, 0, 0};
static const rx_desc D_ff7c40 = {0x305, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7c58 = {0x30b, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7c70 = {0x324, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7c90 = {0x315, 0, 0.0f, 0.0f, 0x0, 8, 2, 0, MV_10b7ce0};
static const rx_desc D_ff7ca8 = {0x000, 0, 0.0f, 0.0f, 0x0, 2, 1, 0, MV_ff7c88};
static const rx_desc D_ff7cc0 = {0x316, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7cd8 = {0x307, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7cf0 = {0x308, 0, 8.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7d08 = {0x318, 0, 4.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7d20 = {0x307, 0, 4.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7d38 = {0x308, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7d50 = {0x318, 0, 40.0f, 40.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7d68 = {0x307, 0, 4.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7d80 = {0x308, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7d98 = {0x320, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7db0 = {0x32d, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7dcc = {0x315, 0, 0.0f, 28.0f, 0x0, 8, 2, 0, MV_10b7cc8};
static const rx_desc D_ff7de4 = {0x000, 0, 0.0f, 0.0f, 0x0, 2, 1, 0, MV_ff7adc};
static const rx_desc D_ff7dfc = {0x316, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7e14 = {0x307, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7e2c = {0x307, 0, 20.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7e44 = {0x308, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7e5c = {0x30b, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7e74 = {0x30b, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7e8c = {0x325, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7ea4 = {0x325, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7ec8 = {0x321, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7eec = {0x32e, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7f04 = {0x31f, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7f1c = {0x32c, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7f34 = {0x108, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7f4c = {0x10c, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7f64 = {0x337, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7f7c = {0x304, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff7f94 = {0x305, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff7fc4 = {0x338, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7fdc = {0x337, 0, 0.0f, 92.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff7ff4 = {0x304, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff800c = {0x305, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff803c = {0x303, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff8054 = {0x304, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff806c = {0x305, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_ff809c = {0x328, 0, 6.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_ff80b4 = {0x304, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_ff80cc = {0x305, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
#define I(v) ((const void *)(v))
static const rx_op T_ff7024[] = {{0x0, &D_ff78e4}, {0xff, 0}};
static const rx_op T_ff7034[] = {{0x0, &D_ff78fc}, {0xff, 0}};
static const rx_op T_ff7044[] = {{0x0, &D_ff7914}, {0xff, 0}};
static const rx_op T_ff7054[] = {{0x0, &D_ff792c}, {0xff, 0}};
static const rx_op T_ff7064[] = {{0x0, &D_ff7944}, {0x3, I(0x168)}, {0x0, &D_ff795c}, {0x0, &D_ff7974}, {0xff, 0}};
static const rx_op T_ff708c[] = {{0x0, &D_ff7944}, {0x3, I(0x258)}, {0x0, &D_ff795c}, {0x0, &D_ff7974}, {0x0, &D_ff798c}, {0xff, 0}};
static const rx_op T_ff70bc[] = {{0x0, &D_ff79a4}, {0x3, I(0x168)}, {0x0, &D_ff79bc}, {0x0, &D_ff79d4}, {0xff, 0}};
static const rx_op T_ff70e4[] = {{0x0, &D_ff7a04}, {0x3, I(0x168)}, {0x0, &D_ff7a1c}, {0x0, &D_ff7a34}, {0xff, 0}};
static const rx_op T_ff710c[] = {{0x0, &D_ff7a4c}, {0x3, I(0x168)}, {0x0, &D_ff7a64}, {0x0, &D_ff7a7c}, {0xff, 0}};
static const rx_op T_ff7134[] = {{0x0, &D_ff7a04}, {0x3, I(0x168)}, {0x0, &D_ff7a1c}, {0x0, &D_ff7a34}, {0x3a, I(0xf0)}, {0xff, 0}};
static const rx_op T_ff7164[] = {{0x0, &D_ff7a94}, {0x3, I(0x168)}, {0x0, &D_ff7aac}, {0x0, &D_ff7ac4}, {0x3a, I(0xf0)}, {0xff, 0}};
static const rx_op T_ff7194[] = {{0xb, I(0x1e0)}, {0x5, I(0x34)}, {0x0, &D_ff7ae4}, {0x1, &D_ff7afc}, {0x4, I(0x0)}, {0x0, &D_ff7b14}, {0x3, I(0x168)}, {0x0, &D_ff7b2c}, {0x0, &D_ff7b44}, {0xff, 0}};
static const rx_op T_ff71e4[] = {{0x0, &D_ff7b5c}, {0xff, 0}};
static const rx_op T_ff723c[] = {{0x0, &D_ff7bc8}, {0x0, &D_ff7be0}, {0x0, &D_ff7bf8}, {0xfe, 0}};
static const rx_op T_ff725c[] = {{0x0, &D_ff7c10}, {0x0, &D_ff7c28}, {0x0, &D_ff7c40}, {0xfe, 0}};
static const rx_op T_ff727c[] = {{0x0, &D_ff7c58}, {0xff, 0}};
static const rx_op T_ff728c[] = {{0x0, &D_ff7c70}, {0xff, 0}};
static const rx_op T_ff729c[] = {{0xb, I(0x1e0)}, {0x5, I(0x34)}, {0x0, &D_ff7c90}, {0x1, &D_ff7ca8}, {0x4, I(0x0)}, {0x0, &D_ff7cc0}, {0x0, &D_ff7cd8}, {0x0, &D_ff7cf0}, {0xff, 0}};
static const rx_op T_ff72e4[] = {{0x0, &D_ff7d08}, {0x0, &D_ff7d20}, {0x0, &D_ff7d38}, {0xff, 0}};
static const rx_op T_ff7304[] = {{0x0, &D_ff7d50}, {0x0, &D_ff7d68}, {0x0, &D_ff7d80}, {0xff, 0}};
static const rx_op T_ff7324[] = {{0x0, &D_ff7d98}, {0xfe, 0}};
static const rx_op T_ff7334[] = {{0x0, &D_ff7db0}, {0xfe, 0}};
static const rx_op T_ff7344[] = {{0xb, I(0x1e0)}, {0x5, I(0x34)}, {0x0, &D_ff7dcc}, {0x1, &D_ff7de4}, {0x4, I(0x0)}, {0xe, &W_ff7dc8}, {0x0, &D_ff7dfc}, {0xfe, 0}};
static const rx_op T_ff7384[] = {{0x24, I(0x0)}, {0x3, I(0xb4)}, {0x0, &D_ff7e14}, {0x25, I(0x0)}, {0xfe, 0}};
static const rx_op T_ff73ac[] = {{0x24, I(0x0)}, {0x3, I(0xb4)}, {0x0, &D_ff7e2c}, {0x25, I(0x0)}, {0xfe, 0}};
static const rx_op T_ff73d4[] = {{0x0, &D_ff7e44}, {0xff, 0}};
static const rx_op T_ff73e4[] = {{0x3, I(0x3c)}, {0x6, I(0x0)}, {0x0, &D_ff7e5c}, {0xfe, 0}};
static const rx_op T_ff7404[] = {{0x3, I(0x3c)}, {0x6, I(0x0)}, {0x0, &D_ff7e74}, {0xfe, 0}};
static const rx_op T_ff7424[] = {{0x3, I(0x3c)}, {0x6, I(0x0)}, {0x0, &D_ff7e8c}, {0xfe, 0}};
static const rx_op T_ff7444[] = {{0x3, I(0x3c)}, {0x6, I(0x0)}, {0x0, &D_ff7ea4}, {0xfe, 0}};
static const rx_op T_ff7464[] = {{0x2d, I(0x0)}, {0x2e, E_ff7ebc}, {0x0, &D_ff7ec8}, {0xff, 0}};
static const rx_op T_ff7484[] = {{0x2d, I(0x0)}, {0x2e, E_ff7ee0}, {0x0, &D_ff7eec}, {0xff, 0}};
static const rx_op T_ff74a4[] = {{0x0, &D_ff7f04}, {0xff, 0}};
static const rx_op T_ff74b4[] = {{0x0, &D_ff7f1c}, {0xff, 0}};
static const rx_op T_ff74c4[] = {{0x0, &D_ff7f34}, {0x4, I(0x3)}, {0x0, &D_ff7f4c}, {0xff, 0}};
static const rx_op T_ff74e4[] = {{0x0, &D_ff7f64}, {0x3, I(0x258)}, {0x0, &D_ff7f7c}, {0x0, &D_ff7f94}, {0xff, 0}};
static const rx_op T_ff750c[] = {{0x0, &D_ff7fc4}, {0x0, &D_ff7fdc}, {0x3, I(0x258)}, {0x0, &D_ff7ff4}, {0x0, &D_ff800c}, {0xff, 0}};
static const rx_op T_ff753c[] = {{0x0, &D_ff803c}, {0x3, I(0x168)}, {0x0, &D_ff8054}, {0x0, &D_ff806c}, {0xff, 0}};
static const rx_op T_ff7564[] = {{0x0, &D_ff809c}, {0x3, I(0x168)}, {0x0, &D_ff80b4}, {0x0, &D_ff80cc}, {0xff, 0}};
#undef I

static int flying(void *self) { return FIELD(uint8_t, REC(self), REC_MODE) == 1; }   /* 4U W+0x1c9 == 1 */

/* one log line per reaction start (the player's step byte rec+0x1a1 is still 0 on the first frame); motion =
 * the sequence's first motion id */
static void rx_log(void *self, uint32_t num, const rx_op *t, uint32_t flag, uint32_t dir)
{
    static int s_n;
    uint32_t mot = 0xffff;
    if (FIELD(uint8_t, REC(self), REC_STEP0) != 0 || ++s_n > 80) return;
    for (const rx_op *e = t; e->op != 0xff && e->op != 0xfe; e++)
        if (e->op == 0) { mot = ((const rx_desc *)e->arg)->motion; break; }
    logf("gogport: em089 react 10/%u seq motion %x flag %u mode %u dir %u flag78bf %u", num, mot, flag,
         FIELD(uint8_t, REC(self), REC_MODE), dir, FIELD(uint8_t, self, RX_FLAG78BF));
}

/* 4U 0x8c2784, one case per 4U case, in 4U order of the jump targets */
static int react10(void *self, uint32_t num)
{
    const rx_op *t;
    uint32_t flag = 0, d = 0;
    int fly = flying(self), f78bf = FIELD(uint8_t, self, RX_FLAG78BF) != 0;

    switch (num) {
    case 7:      /* flinch (state class 0 request of 4U 0x947ffc): 0x8c2930 */
        d = hitDir(self);
        if (!fly) t = (d >= 2 && d <= 5) ? T_ff7024 : T_ff7054;                     /* 0x301 / 0x302 */
        else t = d == 1 ? T_ff710c : (d == 3 || d == 6 || d == 7) ? T_ff7044 : T_ff7034;   /* fall / 0x325 / 0x324 */
        break;
    case 8:      /* 0x8c2abc */
        d = hitDir(self);
        t = (d == 2 || d == 3 || d == 7) ? T_ff7194 : T_ff71e4;
        flag = 1;
        break;
    case 15: case 181:   /* 0x8c2eb0 */
        t = T_ff71e4; flag = 1; break;
    case 20:     /* 0x8c29b8 */
        d = hitDir(self);
        if (!fly) t = d == 3 ? T_ff70e4 : T_ff7064;
        else t = (d == 2 || d == 5 || d == 7) ? T_ff70bc : T_ff710c;
        break;
    case 21:     /* 0x8c2af0 (the 0x938620 result is not used) */
        d = hitDir(self); t = T_ff7194; flag = 1; break;
    case 27: case 148: case 175:   /* 0x8c2b74 */
        t = T_ff7054; break;
    case 32:     /* 0x8c2b14: 0x940b50 == 2 */
        d = FIELD(uint8_t, REC(self), RX_DIRLOW) & 7;
        t = d == 2 ? T_ff725c : T_ff723c;
        break;
    case 37:     /* 0x8c2b58 */
        t = T_ff729c; flag = 1; break;
    case 42: case 43: case 112:    /* 0x8c2d90 */
        t = T_ff727c; break;
    case 106:    /* 0x8c2f0c */
        t = fly ? T_ff7564 : T_ff753c; break;
    case 114:    /* 0x8c2a68 (sever reaction in GU, see em089_break.h; 0x938620 result unused) */
        d = hitDir(self); t = fly ? T_ff7304 : T_ff72e4; break;
    case 136:    /* 0x8c2ecc */
        t = fly ? T_ff750c : T_ff74e4; break;
    case 144:    /* 0x8c2e10 */
        t = T_ff74c4; break;
    case 150:    /* 0x8c2b90 */
        t = T_ff7194; break;
    case 155:    /* 0x8c2bac */
        t = fly ? T_ff7334 : T_ff7324; break;
    case 157:    /* 0x8c2bec */
        t = T_ff7344; flag = 1; break;
    case 161:    /* 0x8c2cfc */
        t = f78bf ? T_ff7484 : T_ff7464; break;
    case 167:    /* 0x8c2d44 */
        t = T_ff708c; break;
    case 169:    /* 0x8c2d60 */
        t = f78bf ? T_ff728c : T_ff727c; break;
    case 171: case 173:   /* 0x8c2dac / 0x8c2dc4 */
        t = f78bf ? T_ff74b4 : T_ff74a4; break;
    case 180:    /* 0x8c2e6c */
        t = fly ? T_ff7034 : T_ff7024; break;
    case 187:    /* 0x8c2c08 */
        t = f78bf ? T_ff73ac : T_ff7384; break;
    case 188:    /* 0x8c2c50 */
        t = T_ff73d4; break;
    case 189:    /* 0x8c2c6c */
        t = f78bf ? T_ff7424 : T_ff73e4; break;
    case 190:    /* 0x8c2cb4 */
        t = f78bf ? T_ff7444 : T_ff7404; break;
    case 210:    /* 0x8c2e2c */
        t = fly ? T_ff7164 : T_ff7134; break;
    case 108: case 109: case 202: case 203:
        /* 0x8c2f78 / 0x8c2f4c / 0x8c3440 / 0x8c33f0: [this+0x8d88]+0xe5 >= 2 -> 0xff758c, else em089 0x8bdaec
         * (step2 timer / setTarget / wanderPoint machine) + 0xff71f4; flag 3 (108, 202) or 1: not ported */
    case 200: case 228:
        /* 0x8c2fa4: step2 machine (setTarget(5, 8, 9 | 8) + wanderPoint, then motionCheck / turnToTarget per
         * motion 792 / 816 / 817 / ...) + 0xff75e4 (0xff7614 flying): not ported */
        if (FIELD(uint8_t, REC(self), REC_STEP0) == 0) {
            static int s_n;
            if (++s_n <= 20) logf("gogport: em089 react 10/%u not ported -> placeholder", num);
        }
        return 0;
    default:     /* 0x8c2914: vt+0x164 */
        {
            static int s_n;
            /* 10/29 / 10/31 = the state-0 sleep / paralysis reactions (GU 0x9b6d0 / 0x9b90c): 4U never sends them
             * to em089 (no status data, see em089_react_status_immune); seeing one means the immunity failed */
            if (++s_n <= 20) logf("gogport: em089 react 10/%u: no 4U case -> end%s", num,
                                  num == 29 || num == 31 ? " (status reaction: status immunity failed?)" : "");
        }
        VCALL0(self, SLOT_ACTION_END);
        return 1;
    }
    rx_log(self, num, t, flag, d);
    reactPlay(self, t, flag);
    return 1;
}

/* Category 11 = death (GU requests 11/0..37 by situation from the reaction dispatcher 0x9b2bc). 4U em089 0x8c3b7c ->
 * 0x8b6ac8 for every number: setTargetMode(0), setMotion(781 = 0x30d, blend 6, start 0), hold the last frame (then
 * 0x926044 x2, per-monster object spawns; 0x9399c0 = post-action think list). 11/0 in flying mode -> 0x8b6da4: the
 * same motion plus layer-1 motion 805, faded out (death_layer below). GU ends a death through the reaction player: a GU death table ends with op 7 then 0xff
 * (Kushala's category 11, dispatcher 0xdff8ec: 11/0 = 0x17bb4e8 {motion 0x312, op 7, 0xff}, flag 0; 11/1 =
 * 0x17bb6f0 {op 5 2, fall motion 0x30a type 8 / move 2, op 0xb 400, op 1 type 2 / move 1, op 4, landing motion
 * 0x30b, op 7, 0xff}, flag 1; other numbers {op 3 60, motion 339 type 4, 0xfe}, not deaths). Op 7 is what lets the
 * end hand a dead monster to 12/255 (0xa18ac / 0xa1b28), the corpse state that ends the hunt (C for the tables;
 * op 7's exact effect G). Test 2026-10-20 10:01: the old fallback (act_react: motion 0x10f + action end) restarted
 * the death; 10:13: {motion 781, 0xff} played the death but never reached 12/255 (no op 7).
 * em089: 11/0 = Kushala's shape with 4U's motion 781; 11/1 = Kushala's shape with 4U 0x8b6b80's motions and
 * movement (0x315 launched with MV_10b7ce0 = 4U's 20.4 / -0.4, falling {-45, -5} = MV_ff7c88, landing 0x317). */
static const rx_desc D_death = {0x30d, 0, 6.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_op T_death[] = {{0x0, &D_death}, {0x7, 0}, {0xff, 0}};
static const rx_desc D_death_fly0 = {0x315, 0, 4.0f, 0.0f, 0x0, 8, 2, 0, MV_10b7ce0};
static const rx_desc D_death_fly1 = {0x000, 0, 0.0f, 0.0f, 0x0, 2, 1, 0, MV_ff7c88};
static const rx_desc D_death_fly2 = {0x317, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_op T_death_fly[] = {{0x5, (const void *)2}, {0x0, &D_death_fly0}, {0xb, (const void *)400}, {0x1, &D_death_fly1},
                                    {0x4, 0}, {0x0, &D_death_fly2}, {0x7, 0}, {0xff, 0}};

/* 4U 0x8b6da4 (11/0 while W+0x1c9 == 1; 4U picks the death number by state class W+0x1c8, so this is a death in
 * flying mode on the ground class): flags this+0xca8 |= 8 (0x8b6ac8: |= 1; no GU reader mapped, both left out),
 * setTargetMode(0), setMotion(781, blend 6), then 0x9200a4(this, 805, 0, 0) = layer1MotionW at weight 1. Every frame:
 * motionCheck(9, 30, 70, &frac) -> layer weight -= this+0xd58 (time scale) * frac * 0.025, clamped at 0 (1 -> 0 over
 * frames 30..70); motionCheck(1, 70) -> weight 0; the motion end as 0x8b6ac8. Here the ground table runs the death
 * (op 7 -> 12/255) and this adds the layer: setMotion clears layer 1 and its weight, so a zero weight on motion 781
 * before frame 30 means 805 is not on yet (applied in the frame the table set the motion). 4U tests the mode every
 * frame (its dispatcher runs per frame), so does this. */
#define MOT_DEATH       0x30d
#define MOT_DEATH_LAYER 0x325
#define DT(self) FIELD(float, self, EN_DT)
static void death_layer(void *self)
{
    if (curMotion(self) != MOT_DEATH) return;
    if (motionFrame(self) < 30.0f && layer1Weight(self) == 0.0f) {
        layer1MotionW(self, MOT_DEATH_LAYER, 0.0f, 0.0f);
        logf("gogport: em089 death 11/0 in flying mode (4U 0x8b6da4): layer motion 805");
    }
    float frac = 0.0f;
    if (motionCheck(self, 9, &frac, 30.0f, 70.0f)) {
        float w = layer1Weight(self) - DT(self) * (frac * 0.025f);
        layer1SetWeight(self, w < 0.0f ? 0.0f : w);
    }
    if (motionCheck(self, 1, 0, 70.0f, 0.0f)) layer1SetWeight(self, 0.0f);
}

int em089_react_run(void *self, uint32_t cat, uint32_t num)
{
    if (cat == 10) return react10(self, num);
    if (cat == 11 && num <= 1) {
        const rx_op *t = num ? T_death_fly : T_death;
        if (FIELD(uint8_t, REC(self), 0x1a1) == 0)
            logf("gogport: em089 death 11/%u: %s death (4U %s), op 7 then 12/255 by the reaction player", num,
                 num ? "flying" : "ground", num ? "0x8b6b80" : flying(self) ? "0x8b6da4" : "0x8b6ac8");
        reactPlay(self, t, num);
        if (!num && flying(self)) death_layer(self);
        return 1;
    }
    return 0;
}

/* Status immunity (test 8: the phase-2 roar 1/25 was cut at 3.25 s by 10/31, so work+0xca / BGM 901 never came).
 * GU (C): 10/31 is the paralysis reaction. Dispatcher 0x9a828 switches on the pending reaction kind rec+0x3ae
 * (index kind - 1); kind 5 -> 0x9aa10 -> 0x9b90c, whose state switch on rec+0x1ba (state 0 = default) requests
 * 0x76afc(10, 31) at 0x9bab4. Kind 5 is written only at 0x995bc (per-frame part / status update 0x97ddc), when the
 * status evaluator 0x9a34c returned 2 = paralysis: 0xa2b10 builds rec+0x5cae against rec+0x5cac with the params
 * [0x71078() + 0x3c] = data block (this+0x75ec) +0xa0, and returns 0 when that pointer is 0 (0xa2b28).
 * 4U (C): same chain. Dispatcher 0x939c40 (kind W+0x426), kind 5 -> 0x9402a4 (state W+0x1c8 0 -> 10/31 at
 * 0x9403cc); requestAction 0x92b1d4 only refuses while W+0x1ca == 11 (as GU 0x76afc: +0x73e0 == 11), nothing for a
 * roar. Paralysis 0x917bf8 -> 0x93fcc4 returns at 0x93fcfc when its params pointer ([0x93863c()+0x40]) is 0, and
 * em089's only etd (em_data.arc) has header words 15..21 = 0: 4U em089 never builds poison, sleep, paralysis or
 * stun, so it never gets 10/29 / 10/31 (its own react10 0x8c2784 has no case for them either). The port's dttune
 * got these blocks from the donor (tools/dt_convert.py keeps the donor block when the 4U word is absent; GU +0x98 /
 * +0x9c / +0xa0 / +0xa4 <- etd words 17 / 18 / 19 / 20 by the 40-monster vote, S).
 * Fix: clear those four pointers (0x71078 base +0x34 poison, +0x38 sleep, +0x3c paralysis, +0x40 stun) whenever
 * they are set. Every 0x71078 reader of them checks for 0 (0xa2214 / 0xa227c, 0xa2360, 0xa2398, 0xa246c, 0xa2588,
 * 0xa2788, 0xa27d8, 0xa28c8, 0xa29dc, 0xa2adc, 0xa2b20, 0xa2c10, 0xa2ca0, 0xa2db8, 0xa2e28, 0xa2f18, 0xa2f8c,
 * 0xa3998..0xa3b14) and the dttune reset 0x564bc frees them only when non-zero (0x56b48 / 0x56b74 / 0x56ba4 ..),
 * so the donor blocks just stay allocated (4 x 12-16 B per load). Called every frame from em089_state_update. */
#define DT_STATUS (100 + 0x34)   /* data block: 4 status param pointers (poison, sleep, paralysis, stun) */
void em089_react_status_immune(void *self)
{
    static int s_n;
    uint8_t *data = FIELD(uint8_t *, self, EN_MEAT_DATA);
    if (!data) return;
    uint32_t *p = &FIELD(uint32_t, data, DT_STATUS);
    if (!(p[0] | p[1] | p[2] | p[3])) return;
    if (++s_n <= 8)
        logf("gogport: em089 status immunity: data %x poison %x sleep %x paralysis %x stun %x -> 0 (4U etd words "
             "17-20 = 0: no status, no 10/29 / 10/31)", (uint32_t)data, p[0], p[1], p[2], p[3]);
    p[0] = p[1] = p[2] = p[3] = 0;
}
