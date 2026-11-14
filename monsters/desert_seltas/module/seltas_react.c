/* seltas_react.c: the Desert Seltas Queen's 4U reactions (category 10). C = read in code, S = strong.
 *
 * 4U (v1.1): the Queen's dispatcher 0x7957c4 sends category 10 to 0x79463c, which tests the species (W+0x1c0 == 26 -> the
 * normal Queen's switch at 0x7946a4, else em 95's at 0x794660). Each case tail-calls the reaction player 0x9197c0(this,
 * table, flag), 7 and 20 after the hit direction 0x938620, 155 after [W+0x8d88]+4; numbers without a case go to 0x791504,
 * for both species (C).
 * GU: 0xf9be10 (uEm069_00 category 10) keeps the normal Queen's switch and returns at once for any variant (`ldrb
 * [this+0xb5f5]; cmp #0; popne`), so a Desert Queen never ends a reaction: the test log of 2026-11-09 shows her in 10/7 with
 * her last attack's motion until her death (69 s and 53 s) (C).
 * Port: an entry hook on 0xf9be10 runs em 95's switch for her. GU 0xa134c is 4U 0x9197c0 (monsters/gogmazios/module/
 * em089_react.c, C), 0x9e994 = 0x938620, [this+0xcac0]+4 = [W+0x8d88]+4 (GU's own case 155 reads it, C). Her own 4U tables
 * are converted by monsters/desert_seltas/tools/react_seltas.py (8-byte ops; 24-byte motion descriptors with float blend /
 * start; 4U's .bss movement data 0x10b6820 from its static initializer 0xd26260). The numbers whose 4U table is the normal
 * Queen's (30 31 42 43 96..105 112 161 169 187 197) play GU's normal-Queen table: GU shortened some of those (30 31 99..102
 * 105 187), and for these the Desert Queen does what GU's normal Queen does (a DEVIATION from 4U's longer tables there).
 * Numbers without a case: GU's default, slot 247 (0x76144), as GU's own path does. Multiplayer: every machine runs its
 * reactions as GU's own do. All addresses go through MAIN / FN. */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "port.h"

typedef struct { uint32_t op; const void *arg; } rx_op;
typedef struct {
    uint16_t motion, pad;      /* +0 motion id (bank << 8 | index) */
    float blend, start;        /* +4 / +8 (4U s32) */
    uint32_t flags;            /* +0xc setMotionEx flags */
    uint16_t kind;             /* +0x10 */
    uint8_t move, b13;         /* +0x12 movement type, +0x13 */
    const void *mv;            /* +0x14 movement data */
} rx_desc;
_Static_assert(sizeof(rx_op) == 8, "rx_op");
_Static_assert(sizeof(rx_desc) == 24, "rx_desc");

/* reaction-sequence player (this, table, flag) [4U 0x9197c0] (C, em089_react.c) */
typedef void (*reactPlay_t)(void *self, const rx_op *table, uint32_t flag);
#define reactPlay FN(reactPlay_t, 0xa134c)
/* hit direction: bits 3..5 of rec+0x5ccb [4U 0x938620] (C, em089_react.c) */
typedef uint32_t (*hitDir_t)(void *self);
#define hitDir FN(hitDir_t, 0x9e994)
/* GU's default of 0xf9be10: vcall slot 247 (`ldr r1, [r0]; ldr r1, [r1, #0x3dc]; bx r1`) [4U 0x791504 for both species] */
typedef void (*selfFn_t)(void *self);
#define reactDefault FN(selfFn_t, 0x76144)

#define I(x)          ((const void *)(uintptr_t)(x))
#define GU_T(a)       ((const rx_op *)MAIN(a))
#define IS_DSQ(p)     ((p) && FIELD(uint16_t, (p), EN_ID) == DESERT_SELTAS_QUEEN_EM_ID)
#define MALE_BYTE(p)  (FIELD(uint8_t, FIELD(uint8_t *, (p), 0xcac0), 4))   /* [this+0xcac0]+4 = 4U [W+0x8d88]+4 */

/* ---- tables (monsters/desert_seltas/tools/react_seltas.py c; names = 4U addresses) ---- */
static const uint32_t MV_fdeb04[2] = {0x00000000, 0xc0200000};   /* 0 -2.5 */
static const uint32_t MV_10b6820[6] = {0x00000000, 0x40a33333, 0x00000000, 0x00000000, 0xbdcccccd, 0x00000000};   /* 0 5.1 0 0 -0.1 0 */
static const uint32_t E_fdeea0[3] = {0x00000001, 0x00000000, 0x010101ff};
static const rx_desc D_fde99c = {0x33c, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_fde9cc = {0x33d, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_fde9e4 = {0x303, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fde9fc = {0x305, 0, 2.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_fdea14 = {0x307, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdea2c = {0x33e, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdea44 = {0x340, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdea5c = {0x332, 0, 4.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdea74 = {0x346, 0, 4.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdeaa4 = {0x306, 0, 2.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_fdead4 = {0x33f, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdeaec = {0x341, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdeb0c = {0x30a, 0, 4.0f, 0.0f, 0x11, 8, 2, 0, MV_10b6820};
static const rx_desc D_fdeb24 = {0x000, 0, 0.0f, 0.0f, 0x11, 2, 1, 0, MV_fdeb04};
static const rx_desc D_fdeb3c = {0x30b, 0, 0.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdeb54 = {0x305, 0, 2.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_fdeb84 = {0x340, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdebcc = {0x343, 0, 4.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdebe4 = {0x013, 0, 2.0f, 0.0f, 0x11, 256, 0, 0, 0};
static const rx_desc D_fdebfc = {0x308, 0, 10.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdec14 = {0x311, 0, 4.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdec2c = {0x341, 0, 10.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdec44 = {0x31a, 0, 0.0f, 0.0f, 0x11, 8, 0, 0, 0};
static const rx_desc D_fdec5c = {0x306, 0, 20.0f, 0.0f, 0x11, 256, 0, 0, 0};
static const rx_desc D_fdec8c = {0x341, 0, 0.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdeca4 = {0x311, 0, 10.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdecec = {0x342, 0, 4.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fded1c = {0x306, 0, 2.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_fded4c = {0x33f, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fded64 = {0x341, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fded94 = {0x342, 0, 4.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdee70 = {0x30d, 0, 4.0f, 0.0f, 0x11, 512, 0, 0, 0};
static const rx_desc D_fdee88 = {0x33c, 0, 20.0f, 0.0f, 0x11, 8, 0, 0, 0};
static const rx_desc D_fdeeac = {0x333, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdeedc = {0x305, 0, 2.0f, 0.0f, 0x11, 4, 0, 0, 0};
static const rx_desc D_fdef0c = {0x311, 0, 4.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdef24 = {0x33e, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdef3c = {0x340, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdef84 = {0x347, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdefcc = {0x341, 0, 4.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_desc D_fdeffc = {0x052, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_fdf014 = {0x005, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_fdf02c = {0x052, 0, 0.0f, 0.0f, 0x0, 4, 0, 0, 0};
static const rx_desc D_fdf044 = {0x312, 0, 2.0f, 0.0f, 0x11, 1, 0, 0, 0};
static const rx_desc D_fdf05c = {0x323, 0, 0.0f, 0.0f, 0x0, 1, 0, 0, 0};
static const rx_op T_fde1a4[] = {{0x0, &D_fde99c}, {0xff, I(0x0)}};
static const rx_op T_fde1c4[] = {{0x0, &D_fde9cc}, {0xff, I(0x0)}};
static const rx_op T_fde1fc[] = {{0x0, &D_fdea2c}, {0x3, I(0xf0)}, {0x0, &D_fde9fc}, {0x0, &D_fdea44}, {0xff, I(0x0)}};
static const rx_op T_fde234[] = {{0x0, &D_fdea74}, {0xfe, I(0x0)}, {0x25, I(0x0)}, {0x0, &D_fde9e4}, {0x3, I(0x12c)}, {0x0, &D_fde9fc}, {0x0, &D_fdea14}, {0xff, I(0x0)}};
static const rx_op T_fde274[] = {{0x25, I(0x0)}, {0x0, &D_fdea2c}, {0x3, I(0x12c)}, {0x0, &D_fdea44}, {0x0, &D_fdea5c}, {0xff, I(0x0)}};
static const rx_op T_fde2cc[] = {{0x0, &D_fdead4}, {0x3, I(0x168)}, {0x0, &D_fdeaa4}, {0x0, &D_fdeaec}, {0xff, I(0x0)}};
static const rx_op T_fde3b4[] = {{0x4, I(0x80000001)}, {0x5, I(0x1c)}, {0x0, &D_fdeb0c}, {0xb, I(0x12c)}, {0x28, I(0x0)}, {0x27, I(0x0)}, {0x1, &D_fdeb24}, {0x4, I(0x0)}, {0x0, &D_fdeb3c}, {0x3, I(0xf0)}, {0x0, &D_fdeb54}, {0x0, &D_fdeb84}, {0xff, I(0x0)}};
static const rx_op T_fde41c[] = {{0x4, I(0x80000001)}, {0x5, I(0x1c)}, {0x0, &D_fdeb0c}, {0xb, I(0x12c)}, {0x28, I(0x0)}, {0x27, I(0x0)}, {0x1, &D_fdeb24}, {0x4, I(0x0)}, {0x0, &D_fdeb3c}, {0x0, &D_fdeb84}, {0xff, I(0x0)}};
static const rx_op T_fde494[] = {{0x0, &D_fdebcc}, {0xfd, I(0x0)}, {0x0, &D_fdebe4}, {0xfe, I(0x0)}, {0x0, &D_fdebfc}, {0x0, &D_fdec14}, {0xff, I(0x0)}};
static const rx_op T_fde4cc[] = {{0x0, &D_fdec2c}, {0x0, &D_fdec14}, {0xff, I(0x0)}};
static const rx_op T_fde50c[] = {{0x5, I(0x92)}, {0x0, &D_fdec44}, {0x0, &D_fdec5c}, {0x0, &D_fdec8c}, {0xfe, I(0x0)}, {0x0, &D_fdeca4}, {0xff, I(0x0)}};
static const rx_op T_fde564[] = {{0x0, &D_fdecec}, {0xff, I(0x0)}};
static const rx_op T_fde5a4[] = {{0x0, &D_fded4c}, {0x3, I(0x168)}, {0x0, &D_fded1c}, {0x0, &D_fded64}, {0x3a, I(0xf0)}, {0xff, I(0x0)}};
static const rx_op T_fde5e4[] = {{0x0, &D_fded94}, {0xff, I(0x0)}};
static const rx_op T_fde68c[] = {{0x6, I(0x0)}, {0x5, I(0x28)}, {0x0, &D_fdee88}, {0x0, &D_fdee70}, {0xfe, I(0x0)}, {0x2e, E_fdeea0}, {0x0, &D_fdeeac}, {0xff, I(0x0)}};
static const rx_op T_fde6fc[] = {{0x0, &D_fdef24}, {0x3, I(0x258)}, {0x0, &D_fdeedc}, {0x0, &D_fdef3c}, {0x0, &D_fdef0c}, {0xff, I(0x0)}};
static const rx_op T_fde74c[] = {{0x0, &D_fdef84}, {0xff, I(0x0)}};
static const rx_op T_fde794[] = {{0x0, &D_fdefcc}, {0xff, I(0x0)}};
static const rx_op T_fde7bc[] = {{0x3, I(0x3c)}, {0x0, &D_fdeffc}, {0xfe, I(0x0)}, {0x3, I(0x3c)}, {0x0, &D_fdf014}, {0xfe, I(0x0)}, {0x3, I(0x3c)}, {0x0, &D_fdf02c}, {0xfe, I(0x0)}, {0x0, &D_fdf044}, {0x0, &D_fdf05c}, {0xff, I(0x0)}};
static const rx_op T_fde7ec[] = {{0x3, I(0x3c)}, {0x0, &D_fdf02c}, {0xfe, I(0x0)}, {0x0, &D_fdf044}, {0x0, &D_fdf05c}, {0xff, I(0x0)}};

/* 0xf9be10 = uEm069_00 category 10 (entry hook, every frame of a reaction, as 4U's case code): for the Desert Queen her
 * em-95 switch (4U 0x794660..), else GU's own function */
int seltas_dsq_react_c(uint32_t *regs)
{
    void *self = (void *)regs[0];
    if (!IS_DSQ(self)) return 0;
    const rx_op *t = 0;
    uint32_t flag = 0, n = FIELD(uint8_t, self, EN_ACT_NUM);
    switch (n) {
    case 7: { uint32_t d = hitDir(self); t = (d == 6) ? T_fde1c4 : T_fde1a4; } break;
    case 8: case 83: case 181: case 225: t = T_fde3b4; flag = 1; break;
    case 20: { uint32_t d = hitDir(self); t = (d == 4 || d == 5) ? T_fde1fc : (d == 2 || d == 3) ? T_fde2cc : T_fde1c4; } break;
    case 27: t = T_fde564; break;
    case 29: t = T_fde494; break;
    case 30: t = GU_T(0x17e8b70); break;   /* 4U: the normal Queen's table */
    case 31: t = GU_T(0x17e8b40); break;   /* 4U: the normal Queen's table */
    case 32: t = T_fde50c; break;
    case 37: case 150: t = T_fde41c; flag = 1; break;
    case 42: case 112: t = GU_T(0x17e8b30); break;   /* 4U: the normal Queen's table */
    case 43: t = GU_T(0x17e8b50); break;   /* 4U: the normal Queen's table */
    case 68: case 69: t = T_fde4cc; break;
    case 82: case 180: t = T_fde5e4; break;
    case 96: case 103: t = GU_T(0x17e8ac0); break;   /* 4U: the normal Queen's table */
    case 97: t = GU_T(0x17e8ad0); break;   /* 4U: the normal Queen's table */
    case 98: case 104: t = GU_T(0x17e8ae0); break;   /* 4U: the normal Queen's table */
    case 99: t = GU_T(0x17e8af0); break;   /* 4U: the normal Queen's table */
    case 100: t = GU_T(0x17e8b00); break;   /* 4U: the normal Queen's table */
    case 101: case 102: t = GU_T(0x17e8b10); break;   /* 4U: the normal Queen's table */
    case 105: t = GU_T(0x17e8b20); break;   /* 4U: the normal Queen's table */
    case 110: t = T_fde68c; break;
    case 135: case 148: t = T_fde1a4; break;
    case 155: t = MALE_BYTE(self) == 1 ? T_fde274 : T_fde234; break;
    case 161: t = GU_T(0x17e8c00); break;   /* 4U: the normal Queen's table */
    case 167: t = T_fde6fc; break;
    case 169: case 197: t = GU_T(0x17e8b80); break;   /* 4U: the normal Queen's table */
    case 171: case 173: t = T_fde74c; break;
    case 187: t = GU_T(0x17e8da0); break;   /* 4U: the normal Queen's table */
    case 188: t = T_fde794; break;
    case 189: t = T_fde7bc; break;
    case 190: t = T_fde7ec; break;
    case 210: t = T_fde5a4; break;
    case 217: t = T_fde1fc; break;
    default: reactDefault(self); return 1;
    }
    {   /* one log line per reaction start (the player's step byte rec+0x1a1 is 0 on its first frame) */
        uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
        static uint32_t s_n;
        if (rec && rec[0x1a1] == 0 && s_n < 400) {
            s_n++;
            logf("dsport: dsq reaction 10/%u: her 4U table%s", n, (uintptr_t)t >= (uintptr_t)MAIN(0x17e8000) &&
                 (uintptr_t)t < (uintptr_t)MAIN(0x17e9000) ? " (GU's normal-Queen table)" : "");
        }
    }
    reactPlay(self, t, flag);
    return 1;
}
