/* em089_pile_port.c - MH4U v1.1 em089 falling Dragonator spear, faithful port.
 * See em089_pile_port.h for conventions. Freestanding: no libc.
 *
 * Remote copy (4U obj+0xe2f == 1) differences, NOT ported:
 *  - launch 0xc2e944: fall time 2T = 320, no velocity; position driven by the
 *    net smoothing 0x945c88 toward e58 instead of 0xc2f95c;
 *  - 0x918364 would use curve list entries 3..5 if present (none for em089);
 *  - landing c2d6d8: skips 0x945c88, rest position, final angles, SE 211, dust,
 *    and the g+0xcb0 placement; ground follow / record y offset use 0 instead of
 *    20*scale (rec+8 is read only when e2f == 0);
 *  - controller 0xc2e96c, gimmick 0x33c7c8 and the record creation run the same
 *    on every machine.
 * Inert copy (e2f == 2, restore path): the update returns at once.
 */
#include "em089_pile_port.h"

#pragma clang fp contract(off)   /* 4U VFP vmla / vmls are not fused */

/* ------------------------------------------------------------------ */
/* constants (exact 4U float literals)                                 */
/* ------------------------------------------------------------------ */
#define K_TWOPI   6.2831855f       /* 0x40c90fdb */
#define K_INV64K  1.5258789e-05f   /* 0x37800000 = 1/65536 */
#define K_Q182    182.04445f       /* 0x43360b61 = 65536/360 */
#define K_INV360  0.0027777778f    /* 0x3b360b61 */
#define K_PI8     0.3926991f       /* 0x3ec90fdb */

/* emd em089 k1 record @0x1310: +2 s16 T, +4 g, +8 rest height */
#define REC_T     160
#define REC_G     (-0.45f)
#define REC_H     20.0f

/* Non-faithful test knob: 1 = joint 1 rotation set to identity at landing.
 * 4U (0 = default) leaves joint 1 at R(fall curves) = Rx(-390 deg) after landing
 * while the object X angle also becomes -390 deg (see report). */
#ifndef PILE_LANDING_J1_IDENTITY
#define PILE_LANDING_J1_IDENTITY 0
#endif

typedef struct { float k, v; } pile_key_t;

/* emd em089 rotation curves (deg) for the fall, list @0x16a0 = {X, Y, Z, 0} */
static const pile_key_t F_X[4] = { /* emd 0x1700 */
    {0.0f, 7.7f}, {2.0f, 13.0f}, {156.0f, -390.0f}, {-1.0f, -390.0f} };
static const pile_key_t F_Y[3] = { /* emd 0x1720 */
    {0.0f, 30.0f}, {156.0f, 0.0f}, {-1.0f, 0.0f} };
static const pile_key_t F_Z[3] = { /* emd 0x1738 */
    {0.0f, 3.5f}, {156.0f, 0.0f}, {-1.0f, 0.0f} };

/* collapse (t' = e34-1500, 0..296): joint 0 translation, joint 1 X (-390 based), Z */
static const pile_key_t C_J0X[7] = { /* 4U 0xe0e720 */
    {0.0f, 0.0f}, {132.0f, 0.0f}, {138.0f, 2.3f}, {202.0f, 21.8f}, {254.0f, 35.7f}, {296.0f, 41.4f}, {-1.0f, 41.4f} };
static const pile_key_t C_J0Y[17] = { /* 4U 0xe0e758 */
    {0.0f, 0.0f}, {1.0f, 0.3f}, {2.0f, 0.5f}, {14.0f, -5.9f}, {24.0f, -16.2f}, {36.0f, -32.2f}, {46.0f, -48.3f},
    {68.0f, -38.3f}, {84.0f, -38.3f}, {103.0f, -58.7f}, {116.0f, -90.2f}, {128.0f, -139.1f}, {132.0f, -148.7f},
    {138.0f, -149.2f}, {254.0f, -149.2f}, {296.0f, -149.4f}, {-1.0f, -149.4f} };
static const pile_key_t C_J0Z[17] = { /* 4U 0xe0e7e0 */
    {0.0f, 0.0f}, {1.0f, 0.1f}, {2.0f, 0.3f}, {14.0f, 37.2f}, {24.0f, 61.5f}, {36.0f, 81.3f}, {46.0f, 92.3f},
    {68.0f, 106.7f}, {84.0f, 108.3f}, {103.0f, 93.1f}, {116.0f, 67.3f}, {128.0f, 32.0f}, {132.0f, 23.1f},
    {138.0f, 17.9f}, {254.0f, 17.9f}, {296.0f, 17.8f}, {-1.0f, 17.8f} };
static const pile_key_t C_J1X[13] = { /* 4U 0xe0e868 */
    {0.0f, -390.0f}, {2.0f, -392.0f}, {46.0f, -340.7f}, {68.0f, -338.0f}, {84.0f, -337.3f}, {103.0f, -340.6f},
    {116.0f, -346.9f}, {122.0f, -351.1f}, {132.0f, -360.1f}, {136.0f, -360.6f}, {138.0f, -360.0f},
    {296.0f, -360.0f}, {-1.0f, -360.0f} };
static const pile_key_t C_J1Z[6] = { /* 4U 0xe0e8d0 */
    {0.0f, 0.0f}, {132.0f, 0.0f}, {202.0f, -19.3f}, {254.0f, -31.2f}, {296.0f, -37.7f}, {-1.0f, -37.7f} };
/* sink (t2 = e34-2000, 0..292): joint 0 y/z (x kept), joint 1 X (-390 based), Z */
static const pile_key_t C_S0Y[5] = { /* 4U 0xe0e900 */
    {0.0f, -149.4f}, {40.0f, -156.1f}, {72.0f, -169.2f}, {292.0f, -259.0f}, {-1.0f, -259.0f} };
static const pile_key_t C_S0Z[5] = { /* 4U 0xe0e928 */
    {0.0f, 17.8f}, {40.0f, 13.9f}, {72.0f, 6.4f}, {292.0f, -45.5f}, {-1.0f, -45.5f} };
static const pile_key_t C_S1X[4] = { /* 4U 0xe0e950 */
    {0.0f, -360.0f}, {40.0f, -360.8f}, {292.0f, -368.4f}, {-1.0f, -368.4f} };
static const pile_key_t C_S1Z[6] = { /* 4U 0xe0e970 */
    {0.0f, -37.7f}, {72.0f, -41.2f}, {146.0f, -27.5f}, {222.0f, -16.4f}, {292.0f, -12.4f}, {-1.0f, -12.4f} };

static const float ZERO3[3] = { 0.0f, 0.0f, 0.0f };

/* ------------------------------------------------------------------ */
/* math helpers                                                        */
/* ------------------------------------------------------------------ */

/* 4U 0xaac930: piecewise-linear curve over float (key, value) pairs.
 * A negative key ends the table and its value is returned (so t past the
 * last key, or t below the first key, returns the terminator value). */
static float curve(const pile_key_t *c, float t)
{
    for (;;) {
        float k0 = c[0].k;
        if (k0 < 0.0f) return c[0].v;
        if (t >= k0) {
            float k1 = c[1].k;
            if (k1 >= t) {
                float f = (t - k0) / (k1 - k0);
                return c[0].v + (c[1].v - c[0].v) * f;
            }
        }
        c++;
    }
}

/* 4U 0xd136c0 fmodf, for x >= 0, y > 0 (exact for the small ranges used) */
static float fmod_pos(float x, float y)
{
    int32_t q;
    float r;
    if (!(x >= y)) return x;
    q = (int32_t)(x / y);
    r = x - (float)q * y;
    while (r < 0.0f) r += y;
    while (r >= y) r -= y;
    return r;
}

/* u16 binary angle (in u32) -> radians, as 4U: (float)u * 2pi * (1/65536) */
static float u2rad(uint32_t u)
{
    return ((float)u * K_TWOPI) * K_INV64K;
}

/* 4U 0x918364 / c2da38: u16(int(0.5 + deg*182.04445)) */
static uint32_t q182(float deg)
{
    return (uint32_t)(uint16_t)(int32_t)(0.5f + deg * K_Q182);
}

/* 4U 0xc2e96c: u16(int(0.5 + (deg*65536)*(1/360))) */
static uint32_t qdeg(float deg)
{
    return (uint32_t)(uint16_t)(int32_t)(0.5f + (deg * 65536.0f) * K_INV360);
}

/* 4U 0x568bf0 / 0x568bb8: 256-entry (sin, cos, dsin, dcos) table, linear
 * interpolation on the low byte. Nodes rebuilt with pj_sin/pj_cos. */
#define K_TAB_STEP 0.024543693f   /* 2pi/256 */
static float sin_t(uint32_t a)
{
    uint32_t i = (a >> 8) & 255u;
    float f = (float)(a & 255u) * 0.00390625f;
    float s0 = pj_sin((float)i * K_TAB_STEP);
    float s1 = pj_sin((float)(i + 1u) * K_TAB_STEP);
    return s0 + (s1 - s0) * f;
}
static float cos_t(uint32_t a)
{
    uint32_t i = (a >> 8) & 255u;
    float f = (float)(a & 255u) * 0.00390625f;
    float c0 = pj_cos((float)i * K_TAB_STEP);
    float c1 = pj_cos((float)(i + 1u) * K_TAB_STEP);
    return c0 + (c1 - c0) * f;
}

/* Euler (x, y, z radians) -> rotation, 4U rotation order 4 (uCoord default,
 * 0x6d4edc) as built inline at c2d8dc / c2dca8 / c2eb6c / c2ef70 / c2f5d0 and
 * by 0x6d4708 case 4. Row vectors: rows are the images of the X, Y, Z axes.
 *   m0 = cy cz + sx sy sz   m1 = cx sz   m2 = sx cy sz - sy cz
 *   m4 = sx sy cz - cy sz   m5 = cx cz   m6 = sy sz + sx cy cz
 *   m8 = cx sy              m9 = -sx     m10 = cx cy
 * Translation 0, m15 = 1. */
static void rot_xyz(float m[16], float x, float y, float z)
{
    float sx = pj_sin(x), sy = pj_sin(y), sz = pj_sin(z);
    float cx = pj_cos(x), cy = pj_cos(y), cz = pj_cos(z);
    m[0]  = cy * cz + (sx * sy) * sz;
    m[1]  = cx * sz;
    m[2]  = (sx * sz) * cy - cz * sy;
    m[3]  = 0.0f;
    m[4]  = (cz * sx) * sy - cy * sz;
    m[5]  = cx * cz;
    m[6]  = sy * sz + (sx * cy) * cz;
    m[7]  = 0.0f;
    m[8]  = cx * sy;
    m[9]  = -sx;
    m[10] = cx * cy;
    m[11] = 0.0f;
    m[12] = 0.0f; m[13] = 0.0f; m[14] = 0.0f; m[15] = 1.0f;
}

static void copy3(float d[3], const float s[3]) { d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; }

/* rotation from u16 angles, translation taken from the joint's current local
 * (4U: read 0xb052ec, keep m[12..15], set 0xb05754) */
static void set_joint_rot_keep_t(void *obj, int joint, uint32_t ax, uint32_t ay, uint32_t az)
{
    float cur[16], r[16];
    pj_joint_get_local(obj, joint, cur);
    rot_xyz(r, u2rad(ax), u2rad(ay), u2rad(az));
    r[12] = cur[12]; r[13] = cur[13]; r[14] = cur[14]; r[15] = cur[15];
    pj_joint_set_local(obj, joint, r);
}

static float yaw_deg(uint32_t u) { return (float)(u & 0xffffu) * 0.0054931641f; } /* 360/65536 */

/* ------------------------------------------------------------------ */
/* gimmick type 2 sub 3 (4U 0x33c7c8, r6 = 1, (r0, r1, r3) = (150, 30, 55),  */
/* stage 19)                                                           */
/* ------------------------------------------------------------------ */
static void gimmick_matrix(pile_t *p)
{
    /* 4U 0x33ccb8 tail: pos = base + thrust * (sin ry cos rx, -sin rx, cos ry cos rx);
     * angles -> quat (0x6d4708, order 4) -> world matrix (0x6d3ee4/0x6d3fd0, scale 1).
     * Built here directly from the Euler angles. */
    float ox = 0.0f, oy = 0.0f, oz = 0.0f;
    float th = p->g_thrust;
    if (th != 0.0f) {
        float sx = pj_sin(p->g_rot[0]), cx = pj_cos(p->g_rot[0]);
        float a  = sx * 0.0f + cx * th;          /* s21 */
        float sy, cy;
        oy = cx * 0.0f - sx * th;                /* s17 */
        sy = pj_sin(p->g_rot[1]); cy = pj_cos(p->g_rot[1]);
        ox = cy * 0.0f + sy * a;                 /* s19 */
        oz = cy * a - sy * 0.0f;                 /* s18 */
    }
    rot_xyz(p->g_mtx, p->g_rot[0], p->g_rot[1], p->g_rot[2]);
    p->g_mtx[12] = p->g_base[0] + ox;            /* g+0x40 */
    p->g_mtx[13] = p->g_base[1] + oy;
    p->g_mtx[14] = p->g_base[2] + oz;
}

static void gimmick_update(pile_t *p, float dt)
{
    float rate = 0.0f;                           /* s16: spin rate (rad) */
    switch (p->g_state) {
    case 0:  /* 4U 0x33c86c: wait dd28 && dd29 bit (1 << r6) */
        if (p->dd28 && (p->dd29 & 2u)) {
            p->g_state = 1;
            p->g_timer = -55.0f;                 /* -(r3) */
            p->g_thrust = 0.0f;
            p->g_cd0 = 0;
            p->g_state = 7;                      /* stage 19 && r6 != 0 */
            pj_log("pile: gimmick 0->7");
        }
        break;
    case 7:  /* 4U 0x33c8fc: timer += dt; >= 30 -> state 1 and FALL THROUGH (timer += dt again) */
        p->g_timer += dt;
        if (!(p->g_timer >= 30.0f)) break;
        p->g_state = 1;
        pj_log("pile: gimmick 7->1");
        /* fallthrough */
    case 1:  /* 4U 0x33c91c: spin-up */
        p->g_timer += dt;
        if (p->g_timer >= 30.0f) {
            rate = ((2.5f + (p->g_timer - 30.0f) * 0.5f) * K_TWOPI) * K_INV360;
            if (!p->g_cd0) {                     /* 4U: only if em089 exists (0x68fd44) */
                pj_se(218, p->g_tip);            /* em089_se_ship_pilebunker_pre at g+0xcb0 */
                p->g_cd0 = 1;
            }
        }
        if (p->g_timer >= 90.0f) {               /* 4U 0x33c9cc */
            p->g_timer = 0.0f;
            pj_se(219, p->g_tip);                /* em089_se_ship_pilebunker_hassya */
            p->g_state = 2;
            pj_log("pile: gimmick 1->2");
        }
        break;
    case 2:  /* 4U 0x33ca4c: thrust 22.5/f to 180 in 8 f */
        rate = dt * K_PI8;                       /* tail multiplies by dt again */
        p->g_timer += dt;
        p->g_thrust = p->g_timer * 22.5f;        /* 180 * 0.125 */
        if (p->g_timer >= 8.0f) {
            p->g_thrust = 180.0f;
            p->g_timer = 0.0f;
            p->g_state = 3;
        }
        break;
    case 3:  /* 4U 0x33caa0: 180 -> 150 over 8 f, hold to 180 f */
        rate = K_PI8;
        p->g_timer += dt;
        if (p->g_timer >= 8.0f) p->g_thrust = 150.0f;
        else                    p->g_thrust = 180.0f - p->g_timer * 3.75f;
        if (p->g_timer >= 180.0f) {
            p->g_timer = 0.0f;
            p->g_thrust = 150.0f;
            p->g_state = 4;
            p->g_state = 5;                      /* stage 19 && r6 == 1 */
            pj_log("pile: gimmick 3->5");
        }
        break;
    case 5:  /* 4U 0x33cc0c */
        p->g_state = 6;
        pj_log("pile: gimmick 5->6");
        break;
    case 6:  /* 4U 0x33cc14: stage 19 && r6 == 1: stays 6 */
    default: /* state 4 is not reachable for sub 3 in stage 19 */
        break;
    }
    /* 4U 0x33cd60: rot z -= rate * dt */
    p->g_rot[2] = p->g_rot[2] - rate * dt;
    gimmick_matrix(p);
}

/* ------------------------------------------------------------------ */
/* spear controller 4U 0xc2e96c (obj state >= 3, every frame)          */
/* ------------------------------------------------------------------ */

/* 4U 0x33c490: stored effect alive? clears the handle when not */
static int g_efx_alive(pile_t *p)
{
    if (p->g_efx == 0) return 0;
    if (!pj_efx_alive(p->g_efx)) { p->g_efx = 0; return 0; }
    return 1;
}

/* 4U 0x33bc98: kill the stored effect (if alive), clear the handle */
static void g_efx_kill(pile_t *p)
{
    if (p->g_efx != 0) {
        if (pj_efx_alive(p->g_efx)) pj_efx_kill(p->g_efx);
        p->g_efx = 0;
    }
}

static void ctl_sink(pile_t *p, void *obj, float dt);

static void ctl_update(pile_t *p, void *obj, float dt)
{
    float m[16], v[3], off[3];

    if (p->g_state == 6) {
        /* ---- 4U 0xc2ea08: explosion / collapse / sink ---- */
        int done = 0, fire = 0, alive;
        if (p->ec0 == 6) return;
        if (!(p->e34 > 1500.0f)) p->e34 = 1500.0f;
        if (p->e34 <= 2000.0f) {                 /* unsigned bits range [1500, 2000] */
            float t = p->e34 - 1500.0f, tn;
            float jx, jy, jz, ax, az;
            if (t >= 296.0f) { t = 296.0f; done = 1; }
            jx = curve(C_J0X, t); jy = curve(C_J0Y, t); jz = curve(C_J0Z, t);
            pj_joint_get_local(obj, 0, m);       /* keep rotation, new translation */
            m[12] = jx; m[13] = jy; m[14] = jz; m[15] = 1.0f;
            pj_joint_set_local(obj, 0, m);
            ax = curve(C_J1X, t) + 390.0f;
            az = curve(C_J1Z, t);
            set_joint_rot_keep_t(obj, 1, qdeg(ax), 0u, qdeg(az));
            p->e34 += dt;                        /* 4U c2ecbc */
            tn = p->e34 - 1500.0f;
            if (tn >= 127.0f && 127.0f > t) fire = 1;
        }
        if (fire && p->ec0 <= 2) {               /* 4U c2ecfc: t' crosses 127 */
            pj_joint_world_pos(obj, 1, v);
            off[0] = 0.0f; off[1] = 0.0f; off[2] = 100.0f;
            pj_efx(8u, 0x2420u, v, ZERO3, 1, off);  /* req +0x60 = 1, +0x28 = (0,0,100), 0xc088d8 */
            p->ec0 = 3;
            pj_se(212, v);                       /* em089_se_spear_vanish at joint 1 */
            pj_log("pile: collapse t'=127 (efx 8, SE 212)");
        }
        alive = g_efx_alive(p);                  /* 4U c2ee34: mask-4 effect */
        if (done && p->ec0 == 3) {               /* 4U c2f118 */
            if (alive) return;
            p->e34 = 2000.0f;
            p->ec0 = 4;
            pj_log("pile: collapse done -> sink");
            ctl_sink(p, obj, dt);
            return;
        }
        if (p->ec0 < 4) {
            if (p->ec0 == 1) {                   /* 4U 0xc2f138: explosion, first g-state-6 frame */
                float id[16];
                rot_xyz(id, 0.0f, 0.0f, 0.0f);   /* identity 0x10e6448 */
                pj_joint_set_local(obj, 0, id);
                g_efx_kill(p);                   /* mask-2 charge effect */
                copy3(v, p->pos);
                p->g_efx = pj_efx(4u, 0x2400u, v, ZERO3, PILE_ATTACH_ROOT, ZERO3); /* 0xc088d8 -> g+0xcc4 */
                pj_joint_world_pos(obj, 0, v);
                pj_se(214, v);                   /* em089_se_spear_exp at joint 0 */
                p->model_flags &= ~0x18u;
                p->ec0 = 2;
                pj_log("pile: explode (efx 4, SE 214)");
            }
            return;
        }
        ctl_sink(p, obj, dt);
        return;
    }

    /* g type 2 (+0xc79): states 0 and 7 idle, 1..5 active (4U c2f2b8) */
    if (p->g_state == 0 || p->g_state == 7) {
        /* ---- 4U 0xc2f31c idle ---- */
        if (p->g_state == 7 && p->g_timer >= 0.0f) {
            p->model_flags = (p->model_flags & ~6u) | 4u;
            if (!(p->e34 > 1000.0f)) p->e34 = 1000.0f;
        } else {
            p->model_flags = (p->model_flags & ~4u) | 2u;
        }
        p->model_flags &= ~8u;                   /* 4U c2f370 */
        p->ec0 = 0;
        return;
    }

    {
        /* ---- 4U 0xc2f2c4 active (g states 1..5) ---- */
        float t = p->e34 - 1000.0f;
        float sx, cx, sy, cy, a700, offx, offy, offz;
        float amp, a1, a2;
        pile_key_t w1[6], w2[6];
        uint32_t u1, u2;
        if (t < 0.0f) t = 0.0f;

        if (p->rec_live) {                       /* 4U c2f390: rec+0x60 = rec+0x78 = 1, e68 = -1 */
            pj_record_disable();
            p->rec_live = 0;
            pj_log("pile: record disabled");
        }

        /* tip offset 700 along the object Z axis from obj X/Y (4U c2f3a0) */
        sx = pj_sin(u2rad(p->ang[0])); cx = pj_cos(u2rad(p->ang[0]));
        a700 = sx * 0.0f + cx * 700.0f;          /* s18 */
        offy = cx * 0.0f - sx * 700.0f;          /* s25 */
        sy = pj_sin(u2rad(p->ang[1])); cy = pj_cos(u2rad(p->ang[1]));
        offx = cy * 0.0f + sy * a700;            /* s24 */
        offz = cy * a700 - sy * 0.0f;            /* s23 */

        if (p->g_state >= 2)                     /* 4U c2f450 */
            p->model_flags = (p->model_flags & ~12u) | 8u;

        if (p->e34 >= 1000.0f && p->e34 <= 1500.0f)   /* 4U c2f460 */
            p->e34 += dt;

        /* wobble on joint 0 (4U c2f484): X period 15, Y period 20, +-amp/2 deg */
        amp = (p->g_state >= 2) ? 3.0f : 1.5f;
        w1[0].k = 0.0f;   w1[0].v = 0.0f;
        w1[1].k = 3.75f;  w1[1].v = amp * 0.5f;
        w1[2].k = 7.5f;   w1[2].v = 0.0f;
        w1[3].k = 11.25f; w1[3].v = amp * -0.5f;
        w1[4].k = 15.0f;  w1[4].v = 0.0f;
        w1[5].k = -1.0f;  w1[5].v = 0.0f;        /* 4U: no terminator (never reached) */
        w2[0].k = 0.0f;   w2[0].v = 0.0f;
        w2[1].k = 5.0f;   w2[1].v = amp * 0.5f;
        w2[2].k = 10.0f;  w2[2].v = 0.0f;
        w2[3].k = 15.0f;  w2[3].v = amp * -0.5f;
        w2[4].k = 20.0f;  w2[4].v = 0.0f;
        w2[5].k = -1.0f;  w2[5].v = 0.0f;
        a1 = curve(w1, fmod_pos(t, 15.0f));
        u1 = qdeg(a1);
        a2 = curve(w2, fmod_pos(t, 20.0f));
        u2 = qdeg(a2);
        rot_xyz(m, u2rad(u1), u2rad(u2), 0.0f);  /* translation 0, m15 = 1 */
        pj_joint_set_local(obj, 0, m);

        /* joint 2 <- gimmick world matrix (4U c2f6f8) */
        pj_joint_set_local(obj, 2, p->g_mtx);

        /* g+0xcb0 = joint-2 world pos + offset (4U c2f71c) */
        pj_joint_world_pos(obj, 2, v);
        p->g_tip[0] = v[0] + offx;
        p->g_tip[1] = v[1] + offy;
        p->g_tip[2] = v[2] + offz;

        if (p->ec0 != 1) {                       /* 4U c2f75c: first active frame */
            copy3(v, p->pos);
            p->g_efx = pj_efx(2u, 0x2400u, v, ZERO3, PILE_ATTACH_ROOT, ZERO3); /* 0xc08698, req +0x64 = 2 */
            pj_log("pile: charge (efx 2)");
        } else {                                 /* 4U c2f800: spark SE every 20 f */
            p->ec4 += dt;
            if (p->ec4 > 20.0f) {
                pj_joint_world_pos(obj, 0, v);
                pj_se(213, v);                   /* em089_se_spark at joint 0 */
                p->ec4 = 0.0f;
            }
        }

        /* 4U c2f854: t_old <= 218 <= t_new (fires on 2 frames with integer dt) */
        if (!(t > 218.0f) && !(218.0f > p->e34 - 1000.0f)) {
            pj_joint_world_pos(obj, 2, v);
            pj_efx(16u, 0x2401u, v, ZERO3, 2, ZERO3);   /* req +0x60 = 2, 0xc088d8, handle not kept */
            pj_log("pile: t=218 (efx 16)");
        }
        p->ec0 = 1;
    }
}

/* 4U 0xc2ee5c: sink (ec0 >= 4) */
static void ctl_sink(pile_t *p, void *obj, float dt)
{
    float m[16], t2, ax, az;
    if (p->e34 < 2000.0f) return;
    t2 = p->e34 - 2000.0f;
    if (t2 > 292.0f) t2 = 292.0f;
    pj_joint_get_local(obj, 0, m);               /* keep rotation and x (41.4) */
    m[13] = curve(C_S0Y, t2);
    m[14] = curve(C_S0Z, t2);
    m[15] = 1.0f;
    pj_joint_set_local(obj, 0, m);
    ax = curve(C_S1X, t2) + 390.0f;
    az = curve(C_S1Z, t2);
    set_joint_rot_keep_t(obj, 1, qdeg(ax), 0u, qdeg(az));
    if (292.0f <= t2 && p->ec0 == 4) {
        p->ec0 = 5;                              /* hidden next (cut move 0xc2fab0) */
        pj_log("pile: sink done");
    }
    p->e34 += dt;
}

/* ------------------------------------------------------------------ */
/* cut object k1                                                       */
/* ------------------------------------------------------------------ */

/* 4U 0xc2f95c -> 0xc2e410: pos += v dt + a (dt^2/2); v += a dt */
static void ballistic(pile_t *p, float dt)
{
    float h = (dt * dt) * 0.5f;
    p->pos[0] = p->pos[0] + (p->vel[0] * dt + p->acc[0] * h);
    p->pos[1] = p->pos[1] + (p->vel[1] * dt + p->acc[1] * h);
    p->pos[2] = p->pos[2] + (p->vel[2] * dt + p->acc[2] * h);
    p->vel[0] = p->vel[0] + p->acc[0] * dt;
    p->vel[1] = p->vel[1] + p->acc[1] * dt;
    p->vel[2] = p->vel[2] + p->acc[2] * dt;
}

/* 4U 0x2bb2a8 vertical ray: start y = pos.y + max(ref.y - pos.y, 100)
 * (rise 100: query flags 0 / 0x911d34 without bits 2|8). Miss -> pos.y. */
static float ground_ray(const float pos[3], const float ref[3], int *hit)
{
    float from[3], d, gy;
    int h = 0;
    d = ref[1] - pos[1];
    if (100.0f > d) d = 100.0f;
    from[0] = pos[0]; from[1] = pos[1] + d; from[2] = pos[2];
    gy = pj_ground_y(from, -1.0f, &h);
    if (!h) gy = pos[1];
    *hit = h;
    return gy;
}

/* 4U 0xc2e478 launch (em89, mode 1, local) */
static void launch(pile_t *p, const float start[3])
{
    float s18, from[3], ref[3], gy, dx, dy, dz, T;
    int hit;

    p->e40 = REC_T;
    copy3(p->pos, start);                        /* obj+0xbc/cc/dc and obj+0xea0 */
    s18 = REC_H * p->scale;
    /* ray from (tgt.x, tgt.y + 350, tgt.z), ref.y = tgt.y - (20s - 350) */
    from[0] = p->tgt[0]; from[1] = p->tgt[1] + 350.0f; from[2] = p->tgt[2];
    ref[0]  = p->tgt[0]; ref[1]  = p->tgt[1] - (s18 - 350.0f); ref[2] = p->tgt[2];
    gy = ground_ray(from, ref, &hit);
    if (hit) {                                   /* 4U c2e694 */
        p->tgt[0] = from[0]; p->tgt[1] = gy; p->tgt[2] = from[2];
        p->tgt[1] = p->tgt[1] + s18;
        /* e44 = hit floor; moving floor (e45 = 1, offsets e48) dropped */
    }
    dz = p->tgt[2] - start[2];
    dx = p->tgt[0] - start[0];
    dy = p->tgt[1] - start[1];
    p->vel[0] = p->vel[1] = p->vel[2] = 0.0f;
    p->acc[0] = p->acc[1] = p->acc[2] = 0.0f;
    T = (float)p->e40;
    p->vel[0] = dx / T;
    p->vel[1] = dy / T - (REC_G * 0.5f) * T;
    p->vel[2] = dz / T;
    p->acc[1] = REC_G;
    p->ang[0] = 0u;
    p->ang[1] = p->w_yaw;
    p->ang[2] = 0u;
    /* 0x2fa2e4(mgr, 1, ...) common-bank SE for every cut object: not ported */
    pj_se(210, p->pos);                          /* em089_se_metal_imp, 4U c2e930 */
    p->se_follow = 210;
    pj_log("pile: launch hit=%d tgt=(%d,%d,%d)", hit,
           (int)p->tgt[0], (int)p->tgt[1], (int)p->tgt[2]);
}

void pile_init_ex(pile_t *p, const float launch_pos[3], const float monster_pos[3],
                  uint16_t monster_yaw, float scale)
{
    int i;
    unsigned char *b = (unsigned char *)p;
    for (i = 0; i < (int)sizeof(*p); i++) b[i] = 0;

    p->scale = scale;
    p->w_yaw = monster_yaw;
    copy3(p->w_pos, monster_pos);

    /* 4U 0xc2d278 cut setup */
    p->e2f = 0;
    p->ec0 = 0;
    p->ec4 = 0.0f;
    p->rec_live = 0;
    p->pos[0] = monster_pos[0]; p->pos[1] = monster_pos[1] + 50.0f; p->pos[2] = monster_pos[2];

    /* 4U 0x94e39c sever (em089 call 0x8c88a4: target NULL) */
    copy3(p->tgt, monster_pos);                  /* e58 = W+0x198 */
    p->tgt[1] = p->tgt[1] + REC_H * scale;       /* e5c += 20*scale (0xc2f9c4) */
    p->gf_enable = 1;                            /* e44 = W+0x5f3 / hit floor, static */

    /* gimmick ctor 0x33ce00 / stage state */
    p->g_state = 0;
    p->dd28 = 1;
    p->dd29 = 0;
    gimmick_matrix(p);

    /* 4U c2d49c: state 0 -> 1 (W+0x42c & 8), e34 = 0; c2d4d0: 1 -> 2 + launch */
    p->e34 = 0.0f;
    p->e2a = 2;
    copy3(p->prev, launch_pos);
    launch(p, launch_pos);
    p->inited = 1;
}

void pile_init(pile_t *p, const float launch_pos[3], uint16_t monster_yaw, float scale)
{
    pile_init_ex(p, launch_pos, launch_pos, monster_yaw, scale);
}

void pile_set_monster_yaw(pile_t *p, uint16_t yaw)
{
    p->w_yaw = yaw;
}

/* 4U c2d520: one falling frame (state 2) */
static void fall_frame(pile_t *p, void *obj, float dt)
{
    uint32_t a[3];
    float j1[3], y;
    int land = 0;

    p->e34 += dt;                                /* 0xb052c4 */
    /* 0x918364: base (0,0,0) for em89 + curves at e34 */
    a[0] = q182(curve(F_X, p->e34));
    a[1] = q182(curve(F_Y, p->e34));
    a[2] = q182(curve(F_Z, p->e34));

    /* c2d658: landing test on joint 1 (4U writes y back into the joint, unused) */
    pj_joint_world_pos(obj, 1, j1);
    y = j1[1] - p->scale * 127.7f;
    if (y <= p->tgt[1]) land = 1;

    if (p->e34 >= (float)p->e40 || land) {
        /* ---- 4U c2d6c4: landing (local) ---- */
        float k, sn, cs, l[3], rot[3];
        uint32_t yaw;
        p->e2a = 3;
        /* 0x945c88: pos += (tgt - pos) / (T*0.25); overwritten below for em89 */
        p->e34 = (float)p->e40;
        pj_joint_world_pos(obj, 1, j1);
        k = p->scale * -208.7f;
        yaw = p->w_yaw & 0xffffu;                /* live W+0x1ac */
        sn = sin_t(yaw); cs = cos_t(yaw);
        l[0] = j1[0] + (cs * 0.0f + sn * k);
        l[1] = p->tgt[1];
        l[2] = j1[2] + (cs * k - sn * 0.0f);
        copy3(p->pos, l);
#if PILE_LANDING_J1_IDENTITY
        set_joint_rot_keep_t(obj, 1, 0u, 0u, 0u);
#else
        set_joint_rot_keep_t(obj, 1, a[0], a[1], a[2]);   /* c2d8dc..c2da08 */
#endif
        p->ang[0] = q182(curve(F_X, (float)REC_T));       /* c2da0c: final angles */
        p->ang[1] = p->w_yaw;
        p->ang[2] = q182(curve(F_Z, (float)REC_T));
        pj_se(211, l);                           /* em089_se_spear_down */
        copy3(p->g_tip, l);                      /* g+0xcb0 = landing pos */
        rot[0] = 0.0f; rot[1] = yaw_deg(p->ang[1]); rot[2] = 0.0f;
        pj_efx(1u, 0u, l, rot, PILE_ATTACH_WORLD, ZERO3);   /* dust, 0xc08628 */
        p->se_follow = 0;
        pj_log("pile: landed (%s) pos=(%d,%d,%d)", land ? "ground" : "time",
               (int)l[0], (int)l[1], (int)l[2]);
        return;
    }

    /* ---- 4U c2dc3c: still falling ---- */
    ballistic(p, dt);
    if ((float)p->e40 > p->e34) {
        set_joint_rot_keep_t(obj, 1, a[0], a[1], a[2]);   /* c2dca8..c2dddc */
        p->se_follow = 210;                      /* 0x301074 SE-210 follow at obj pos */
    }
}

/* 4U c2dee4: static ground follow + record position (state >= 3 after controller) */
static void ground_follow(pile_t *p)
{
    if (p->gf_enable) {
        int hit;
        float gy = ground_ray(p->pos, p->prev, &hit);   /* 0x2ba114(col, enemy, pos, prev, area) */
        p->pos[1] = gy + REC_H * p->scale;
    }
    if (p->rec_live) copy3(p->rec_pos, p->pos);  /* c2e3d4 */
}

static void cut_update(pile_t *p, void *obj, float dt)
{
    if (p->e2f == 2) return;
    copy3(p->prev, p->pos);                      /* c2d41c */
    switch (p->e2a) {
    case 2:
        fall_frame(p, obj, dt);
        return;
    case 3: {                                    /* c2de74: record (0x926044(enemy,3,2,1)) */
        float rp[3];
        p->e2a = 4;
        rp[0] = p->tgt[0];
        rp[1] = p->tgt[1] - REC_H * p->scale;
        rp[2] = p->tgt[2];
        pj_record_create(rp, 100.0f * p->scale, 300.0f);
        p->rec_live = 1;
        copy3(p->rec_pos, rp);
        pj_log("pile: record created");
    }   /* fallthrough */
    default:
        ctl_update(p, obj, dt);                  /* c2dedc */
        ground_follow(p);
        return;
    }
}

void pile_obj_world(const pile_t *p, float m[16], int with_scale)
{
    /* 4U 0xc2f9e8 -> 0xb059f0 (angles -> 0x6d4708, order 4) -> 0xb05934 (pos)
     * -> 0x6d3ee4 / 0x6d3fd0 (rows scaled by obj+0x60 = scale) */
    rot_xyz(m, u2rad(p->ang[0]), u2rad(p->ang[1]), u2rad(p->ang[2]));
    if (with_scale) {
        int i;
        for (i = 0; i < 12; i++) m[i] = m[i] * p->scale;
    }
    m[12] = p->pos[0]; m[13] = p->pos[1]; m[14] = p->pos[2]; m[15] = 1.0f;
}

void pile_frame(pile_t *p, void *obj, float dt)
{
    float m[16];
    if (!p->inited) return;
    gimmick_update(p, dt);                       /* 0x33c7c8 */
    cut_update(p, obj, dt);                      /* 0xc2f9e8 -> 0xc2d364 */
    pile_obj_world(p, m, 0);
    pj_obj_set_world(obj, m);
    if (p->ec0 == 5) {                           /* 0xc2fab0: hide for good */
        p->ec0 = 6;
        pj_log("pile: hidden");
    }
}

void pile_activate(pile_t *p)
{
    /* 4U 0x6a1f18 (stage part; the uShell022 kind 10 spawn is the caller's) */
    if (p->dd28 && !(p->dd29 & 2u)) {
        p->dd29 |= 2u;
        pj_log("pile: activated");
    }
}

int pile_ready(const pile_t *p)
{
    return p->inited && p->e2a >= 4 && p->rec_live && p->dd28 && !(p->dd29 & 2u);
}

int pile_hidden(const pile_t *p)
{
    return p->ec0 == 6;
}

void pile_tip(const pile_t *p, float out[3])
{
    copy3(out, p->g_tip);
}

int pile_gimmick_state(const pile_t *p)
{
    return p->g_state;
}

int pile_se_follow(const pile_t *p, float out[3])
{
    if (p->se_follow) copy3(out, p->pos);
    return p->se_follow;
}
