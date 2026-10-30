/* ms_act.c: the Magnet Spike's inputs, mechanics and actions (MS_SLICE; notes/phase3.md, notes/mechanics.md).
 *
 * Inputs (slot 139, +0x22c, the class translator; GS's is 0x1160058): GU turns the pad into virtual buttons (player
 * +0x13f4 held, +0x13f8 pressed) and press combos (+0x1444, after a short simultaneity window: bit 2 = X alone, 4 = A
 * alone, 0x40 = X + A); the translator sets the class's input ids (+0x1424, 0x285e54) that plcmd_w05 commands test
 * (cmd_type 8, 0xc = stick tilted + id). Id k (+ MS_ID_IMPACT in Impact) = the MHF (input, condition) pair
 * ms_pairs[k]: it is set while MHF's input test and cancel condition both hold (mechanics.md 2). MHF -> Switch by
 * position: tri = X, circle = A, special(A) = B, R1 = GU's R role, R2 = ZR, SELECT = Minus, L2 (aim) = L / ZL;
 * R1 + evade = R + Y, as R + B is R1 + special (S, user to confirm).
 *
 * Mechanics (MHF ticks of 1/30 s = dt / 2, dt = player +0x1c in 1/60-s frames): the magnet gauge and Magnetise
 * (every update, from the translator), the marker, the attraction, the pin, the Triple Strike charge and the guard
 * counter (ms_act, the guard / hit callbacks). MHF's constants are its MS block parameters (mechanics.md); S values
 * are marked.
 *
 * Actions (slot 201, +0x324; act_st 0x10, act_no = MHF action number): MHF's step machine (msact.py) on GU's motion
 * and command calls. Step 0: MHF's action start (flags kept 0x1 / 0x10 / 0x40 / 0x1000 / 0x8000, the motion fields
 * cleared, the gauge bar of the costed actions paid, the mode) and GS's action flags and drawn flag (0x282fd8,
 * vt+0x46c(p, 1)); then each step: motion 5000 + slot from its start frame with its blend, the step's command table
 * (2000 + k; later steps keep the buffered presses, 0x2e9c50 keep 1), its events by MHF id. Step kinds: 3 play
 * (loops), 4 until a frame, 5 hold (until the code that drives it ends it: landing, the attraction, the pin),
 * 0 / 1 / 2 go to an action. After the last step: back to GU's drawn neutral (0x2b6e94 as GS). MHF's shared 207
 * (guard counter success) and 208 (charge release) pick their action here; unknown numbers: GU's base handler. */
#include "ms.h"
#include "ms_data.inc"

#define BTN_B 0x10
#define BTN_X 0x20
#define BTN_Y 0x80
#define BTN_A 0x100
#define BTN_SELECT 0x200            /* Minus, ZR: the user's Back / RT (test 1 runs 5-6) */
#define BTN_AIM 0x400               /* L / ZL */
#define BTN_R2 0x800
typedef uint32_t (*ms_mask_t)(void);
#define R_MASK FN(ms_mask_t, 0x65f93c)   /* GU's R role: 0x40, or 0x800 under the other option (GS's translator) */
typedef void (*ms_pre_t)(void *p);
#define INPUT_PRE FN(ms_pre_t, 0x27e770)   /* GS's translator calls it first */

/* MHF's MS parameters (mhfdat block 0xdc1a20 + 0x14, mechanics.md) */
#define BAR 2000                    /* prm19: one gauge bar */
#define GAUGE_MAX 10000             /* prm17 */
#define REGEN 200                   /* prm20 every prm21 = 30 ticks */
#define HIT_GAIN 600                /* prm37: gauge + 600 * MV / 100 per hit */
#define MAG_CHARGE 80               /* prm58: Magnetise charge + MV * 80 / 100 per hit */
#define MAG_READY 1000              /* prm56 */
#define MAG_TIME 2400               /* prm60 */
#define MAG_LOCK 3000               /* prm59 */
#define MARKER_TIME 9000            /* prm14 */
#define FALL_HEIGHT 200             /* prm36: condition 9 */
#define CHARGE_T 45                 /* S: MHF's shared charge base (not traced) + prm31 30 */
#define MARKER_Y 300                /* S: the marker's height over the monster's origin (no shot point in GU) */
#define MARKER_RANGE 5000           /* S: the shot's reach (a projectile in MHF, its range not traced) */
#define PIN_HOLD 60                 /* S: the pin's initial hold (MHF's comes from the monster, 0x101bc490) */
#define PIN_HOLD_MAX 90             /* S */
#define QTE_WIN 70                  /* prm41 70 %, of a 100-point bar (S) */

static const uint8_t s_cost[] = {11, 12, 38, 39, 51, 53, 58, 61, 62, 66, 67, 68, 71, 72, 94, 97, 106, 107, 108, 116,
                                 117, 135, 136, 138, 146, 158};      /* MS list +0x24: one bar at the start */
static const uint8_t s_attract[] = {58, 61, 62, 68, 71, 72};
static const uint8_t s_pinned[] = {98, 99, 105, 157};                /* the hunter rides the pinned monster */
static const uint8_t s_pin_keep[] = {98, 99, 100, 105, 156, 157};    /* MHF keeps the motion fields */
static int in(const uint8_t *l, uint32_t n, uint32_t v) { for (uint32_t i = 0; i < n; i++) if (l[i] == v) return 1; return 0; }
#define IN(l, v) in(l, sizeof l, v)

static float sq(float x) { return x * x; }
static float root(float x) { float r; __asm__("vsqrt.f32 %0, %1" : "=t"(r) : "t"(x)); return r; }
static float *pos_of(uint8_t *p) { return &FIELD(float, p, 0x40); }
static uint32_t yaw_to(float dx, float dz) { return (uint32_t)(int32_t)(atan2f_gu(dx, dz) * 10430.378f) & 0xffff; }
static void face(uint8_t *p, uint32_t yaw) { FIELD(uint16_t, p, 0xfec) = (uint16_t)yaw; FIELD(uint16_t, p, 0x14a0) = (uint16_t)yaw; }
static float tick_len(uint8_t *p) { return FIELD(float, p, 0x1c) * 0.5f; }

/* diagnostic (tests): every change of the action, its step, the body motion, the weapon's motion (part 0 object
 * +0x23a0, its +0x4b4 = list << 8 | slot) and the command table (+0x24ac id, +0x24a8 table, +0x24f0 the class list) */
static void trace(uint8_t *p)
{
    static uint32_t s_last[5];
    static int s_n;
    uint8_t *w = FIELD(uint8_t *, p, 0x23a0);
    uint32_t now[5] = {(uint32_t)FIELD(uint16_t, p, 0x2506) << 16 | FIELD(uint16_t, p, 0x250a), FIELD(uint8_t, p, 5),
                       CUR_MOTION(p), w ? FIELD(uint16_t, w, 0x4b4) : 0xffffu, FIELD(uint32_t, p, 0x24ac)};
    int same = 1;
    for (int i = 0; i < 5; i++) same &= now[i] == s_last[i];
    if (same || s_n >= 600) return;
    s_n++;
    for (int i = 0; i < 5; i++) s_last[i] = now[i];
    logf("msport: state action %u/%u step %u motion %u frame %d weapon %x table %u", now[0] >> 16, now[0] & 0xffff,
         now[1], now[2], (int)MS_FRAME(p), now[3], now[4]);
}

/* ------------------------------------------------------------------------------------------------ monsters */

static uint8_t *em_rec(uint8_t *m) { return FIELD(uint8_t *, m, 0x1428); }
static int em_ok(uint8_t *m)        /* a large monster the hit pass would test (spawned, active, here) and alive */
{
    if (!m || !FIELD(uint8_t, m, 0xb5f9) || FIELD(uint8_t, m, 0x7652) != 1 || FIELD(uint8_t, m, 0xb5f7)) return 0;
    uint8_t *r = em_rec(m);
    return r && FIELD(uint8_t, r, 0x1a0) && !FIELD(uint8_t, r, 0x444) && FIELD(int32_t, r, 0x370) > 0;
}

static int marker(struct ms_state *s, float t[3])
{
    if (!s->mk_mon) return 0;
    uint8_t *r = em_rec(s->mk_mon);
    t[0] = FIELD(float, r, 0x40); t[1] = FIELD(float, r, 0x44) + MARKER_Y; t[2] = FIELD(float, r, 0x48);
    return 1;
}

static float marker_dist(uint8_t *p, struct ms_state *s)   /* 3-D, -1 = no marker */
{
    float t[3], *q = pos_of(p);
    return marker(s, t) ? root(sq(t[0] - q[0]) + sq(t[1] - q[1]) + sq(t[2] - q[2])) : -1.0f;
}

/* the shot (82 / 84 event 4, special #1): MHF fires a projectile that sticks where it hits. Stand-in (S): the nearest
 * large monster within 0.6 rad of the hunter's facing (the camera's, set at the action start) and MARKER_RANGE */
static void marker_shot(uint8_t *p, struct ms_state *s)
{
    void *mgr = MS_EM_MGR;
    float *q = pos_of(p), a0 = FIELD(uint16_t, p, 0xfec) * MS_U16_RAD, best_d = 0;
    uint8_t *best = 0;
    for (int i = 0; mgr && i < 10; i++) {
        uint8_t *m = MS_EM_GET(mgr, i);
        if (!em_ok(m)) continue;
        uint8_t *r = em_rec(m);
        float dx = FIELD(float, r, 0x40) - q[0], dz = FIELD(float, r, 0x48) - q[2], d = sq(dx) + sq(dz);
        float da = atan2f_gu(dx, dz) - a0;
        while (da > 3.1415927f) da -= 6.2831853f;
        while (da < -3.1415927f) da += 6.2831853f;
        if (da > 0.6f || da < -0.6f || d > sq(MARKER_RANGE)) continue;
        if (!best || d < best_d) { best = m; best_d = d; }
    }
    if (!best) { logf("msport: marker shot missed"); return; }
    s->mk_mon = best; s->mk_t = MARKER_TIME;
    logf("msport: marker on monster %x (em %u) at %d", (uint32_t)(uintptr_t)best, FIELD(uint8_t, best, 0xb5f4),
         (int)root(best_d));
}

/* ------------------------------------------------------------------------------------------------ gauge, inputs */

static void gauge_add(struct ms_state *s, int32_t n)
{
    int32_t old = s->gauge / BAR;
    s->gauge += n;
    if (s->gauge < 0) s->gauge = 0;
    if (s->gauge > GAUGE_MAX) s->gauge = GAUGE_MAX;
    static int s_n;
    if (s->gauge / BAR != old && s_n++ < 300) logf("msport: magnet gauge %d bars (%d)", s->gauge / BAR, s->gauge);
}

static int cond(uint8_t *p, struct ms_state *s, uint32_t c)   /* MHF cancel conditions (mechanics.md 2) */
{
    float d;
    switch (c) {
    case 0: return 1;
    case 1: case 2: case 3: case 4: case 5: return MS_STAMINA_NOW(p) >= 1 && s->gauge >= (int32_t)c * BAR;
    case 6: return (s->flags & 8) != 0;                 /* guarded during 112's window */
    case 7: return !s->pin_mon;
    case 8: return s->gc_hits >= 1;
    case 9: return pos_of(p)[1] - MS_GROUND_Y(p) >= FALL_HEIGHT;
    case 10: d = marker_dist(p, s); return MS_STAMINA_NOW(p) >= 1 && s->gauge >= BAR && d > 1400 && d < 4000;
    case 11: d = marker_dist(p, s); return MS_STAMINA_NOW(p) >= 1 && s->gauge >= BAR && d > 0 && d < 1400;
    case 12: return (s->flags & 0x20000) != 0;
    case 13: return s->mag[s->mode] == 0 && s->mag_v[s->mode] >= MAG_READY;
    }
    return 0;
}

static int input(struct ms_state *s, uint32_t inp, uint32_t held, uint32_t trig, uint32_t combo, uint32_t r)
{
    int rh = (held & r) != 0, aim = (s->flags & 1) != 0;
    switch (inp) {
    case 2: return (combo & 2) != 0;                    /* tri (22 = stick + tri: cmd_type 0xc adds the stick) */
    case 3: return (combo & 4) != 0;                    /* circle (6 = stick + circle) */
    case 4: return (combo & 0x40) != 0;                 /* tri + circle */
    case 5: return (trig & BTN_SELECT) != 0;
    case 7: return rh && (combo & 2);
    case 8: return rh && (combo & 4);
    case 9: return rh && (combo & 0x40);
    case 10: return rh && (trig & BTN_B);
    case 11: return rh && (trig & BTN_SELECT);
    case 13: return (trig & BTN_R2) != 0;
    case 14: return (held & BTN_A) != 0;
    case 15: return !(held & BTN_A);                    /* circle not held (a level) */
    case 16: return (trig & r) != 0;
    case 17: return rh && (trig & BTN_Y);
    case 19: return aim && (combo & 4);
    case 20: return 1;
    case 21: return !(held & BTN_X);
    case 23: return aim && (trig & BTN_B);
    case 24: return aim && (combo & 2);
    }
    return 0;                                           /* 0 / 1: GU's common evade / move commands; 12 / 18 never */
}

/* every update, drawn or not: gauge regen, Magnetise timers, the marker's life, mode reset when sheathed */
static void tick(uint8_t *p, struct ms_state *s, float tk)
{
    if (s->gauge < GAUGE_MAX && (s->regen += tk) >= 30) { s->regen -= 30; gauge_add(s, REGEN); }
    for (int m = 0; m < 2; m++) {
        if (!s->mag[m] || (s->mag_v[m] -= tk) > 0) continue;
        s->mag[m] = s->mag[m] == 1 ? 2 : 0;
        s->mag_v[m] = s->mag[m] == 2 ? MAG_LOCK : 0;
        logf("msport: %s Magnetise %s", m ? "Impact" : "Cutting", s->mag[m] == 2 ? "over: lockout" : "charging");
    }
    if (s->mk_mon) {
        if (!s->att) s->mk_t -= tk;                     /* frozen during the attraction */
        if (s->mk_t <= 0 || !em_ok(s->mk_mon)) { s->mk_mon = 0; logf("msport: marker gone"); }
    }
    if (!ms_drawn(p)) { s->mode = 0; s->flags &= ~(1u | 0x8000u); }
    if (FIELD(uint16_t, p, 0x2506) != 0x10) {          /* GU's own action (hit, roll...): no flight, no pin */
        s->air = 0; s->att = 0; s->pin_mon = 0; s->pin_pending = 0;
        s->flags &= ~0x1010u;
    }
}

void ms_input(uint8_t *p)
{
    INPUT_PRE(p);
    trace(p);
    struct ms_state *s = ms_of(p);
    tick(p, s, tick_len(p));
    uint32_t combo = FIELD(uint32_t, p, 0x1444), r = R_MASK();
    uint32_t held = FIELD(uint16_t, p, 0x13f4), trig = FIELD(uint16_t, p, 0x13f8);
    if ((held & BTN_AIM) && ms_drawn(p)) s->flags |= 1; else s->flags &= ~1u;
    uint32_t base = s->mode ? MS_ID_IMPACT : 0;
    for (uint32_t k = 0; k < MS_NPAIRS; k++)
        if (input(s, ms_pairs[k].inp, held, trig, combo, r) && cond(p, s, ms_pairs[k].cond))
            MS_SET_CLASS_ID(p, base + k);
    if (held & r) {                     /* R + B = R1 + special: not GU's roll (common ids 49 / 50, the plcmd_com
                                           0x0001_013a / 014a ids; S: +0x1414 = the common ids' words) */
        static int s_n;
        if ((trig & BTN_B) && s_n++ < 8) logf("msport: R + B: common ids %x", FIELD(uint32_t, p, 0x1418));
        FIELD(uint32_t, p, 0x1418) &= ~(3u << 17);
    }
    if (held != s->held) {
        static int s_n;
        if (s_n == 0) logf("msport: GU's R role mask %x, dt %d/100", r, (int)(FIELD(float, p, 0x1c) * 100));
        if (s_n++ < 300) logf("msport: buttons held %x (was %x) pressed %x combo %x", held, s->held, trig, combo);
    }
    s->held = held;
}

/* ------------------------------------------------------------------------------------------------ hits, guard */

static void arm(uint8_t *p, struct ms_state *s, uint32_t hit)
{
    if (!hit) return;
    if (s->mag[s->mode] == 1) hit += MS_MAG_BASE;       /* Magnetise: MV x 1.1 (msbuild's copies) */
    s->slot ^= 1;                                       /* two slots: an attack may still be live when the next arms */
    s->armed[s->slot] = (uint16_t)hit;
    MS_ARM(p, s->slot, hit, 0);
}

/* slot 37 (+0x94): GU calls it after the damage of the owner's attack on a monster (kind 1). MHF on hit: gauge
 * + 600 * MV / 100, this mode's Magnetise charge + MV * 80 / 100 while charging; the pin attack starts the pin */
void ms_on_hit(uint8_t *p, uint8_t *atk, uint8_t *mon, uint32_t kind)
{
    if (kind != 1 || !mon) return;
    struct ms_state *s = ms_of(p);
    uint32_t slot = (uint32_t)(atk - (p + 0x3020)) / 0xb8, hit = slot < 2 ? s->armed[slot] : 0;
    uint32_t mv = hit < MS_NHITS ? ms_hit_mv[hit] : 0, m = s->mode;
    gauge_add(s, HIT_GAIN * (int32_t)mv / 100);
    if (s->mag[m] == 0 && s->mag_v[m] < MAG_READY) {
        s->mag_v[m] += mv * MAG_CHARGE / 100.0f;
        if (s->mag_v[m] >= MAG_READY) { s->mag_v[m] = MAG_READY; logf("msport: %s Magnetise ready", m ? "Impact" : "Cutting"); }
    }
    if ((s->action == 94 || s->action == 97) && !s->pin_mon && em_ok(mon)) s->pin_pending = mon;
    static int s_n;
    if (s_n++ < 300) logf("msport: hit %u (MV %u) slot %u on monster %x in action %u", hit, mv, slot,
                          (uint32_t)(uintptr_t)mon, s->action);
}

/* slot 356 (+0x590): the guard reaction (p, level 0 / 1 / 2, attack info p+0x3214, damage). MHF: a guarded hit
 * counts (MS+0x66, the Guard Counter's 207 -> 57 / 76 / 77) and sets MS flag 0x8 (112 -> 113). The action goes on:
 * GU's default reaction (0x2f4b20: guard knock-back actions with class motions) is not run; guard stamina as GU's */
void ms_guarded(uint8_t *p, uint32_t level, uint8_t *info, int32_t *dmg)
{
    (void)info;
    struct ms_state *s = ms_of(p);
    if (s->gc_hits < 255) s->gc_hits++;
    s->flags |= 8;
    MS_GUARD_STAMINA(p);
    logf("msport: guarded hit %u (level %u, damage %d) in action %u", s->gc_hits, level, dmg ? (int)*dmg : 0,
         s->action);
}

/* ------------------------------------------------------------------------------------------------ motion */

static void set_air(uint8_t *p, struct ms_state *s)
{
    if (s->air) return;
    s->air = 1; s->vy = 0;
    MS_MOVE_STATE(p, 2);
}

/* the attraction (mechanics.md 5): 1 lift v = 90 (0.2t)(2 - 0.2t) for 10 ticks, 2 fly 90 / tick toward the marker
 * until 300 short (re-targeted each tick; S: 90-tick cap), y kept in [target - 550, target + 1000], 3 fall:
 * horizontal 90 * 0.97^t, vertical v0 + g t (g = 2.3 or event 31's). Returns 1 on landing */
static int attraction(uint8_t *p, struct ms_state *s, float tk)
{
    float t[3], *q = pos_of(p);
    s->att_t += tk;
    if (s->att < 3 && !marker(s, t)) { s->att = 3; s->att_t = 0; s->att_h = 90; }
    if (s->att == 1) {
        float u = 0.2f * s->att_t;
        if (u > 2) u = 2;
        q[1] += 90 * u * (2 - u) * tk;
        if (s->att_t >= 10) { s->att = 2; s->att_t = 0; }
        return 0;
    }
    if (s->att == 2) {
        float d[3] = {t[0] - q[0], t[1] - q[1], t[2] - q[2]}, n = root(sq(d[0]) + sq(d[1]) + sq(d[2]));
        float go = 90 * tk, left = n - 300;
        if (left < go) go = left > 0 ? left : 0;
        for (int i = 0; i < 3; i++) { s->dir[i] = n > 1 ? d[i] / n : 0; q[i] += s->dir[i] * go; }
        if (q[1] > t[1] + 1000) q[1] = t[1] + 1000;
        if (q[1] < t[1] - 550) q[1] = t[1] - 550;
        face(p, yaw_to(d[0], d[2]));
        if (left <= 90 * tk || s->att_t > 90) {
            s->att = 3; s->att_t = 0; s->att_h = 90; s->vy = s->dir[1] * 90;
            logf("msport: attraction: falling (%d left)", (int)left);
        }
        return 0;
    }
    float h = root(sq(s->dir[0]) + sq(s->dir[2]));
    s->att_h *= 1 - 0.03f * tk;
    s->vy -= ((s->flags & 0x80) ? s->fall_g : 2.3f) * tk;
    if (h > 0.01f) { q[0] += s->dir[0] / h * s->att_h * tk; q[2] += s->dir[2] / h * s->att_h * tk; }
    q[1] += s->vy * tk;
    return s->vy <= 0 && MS_LANDED(p, 0.0f, 0);
}

/* airborne actions: event 28's drive, event 25's y -= g * 0.1 * t, event 31's gravity (or 2.3 when nothing drives
 * the fall, S). Returns 1 on landing */
static int fall(uint8_t *p, struct ms_state *s, float tk)
{
    float dy = s->vert - s->grav * 0.1f * s->grav_t;
    if ((s->flags & 0x80) || (!s->grav && s->vert <= 0)) {
        s->vy -= ((s->flags & 0x80) ? s->fall_g : 2.3f) * tk;
        dy += s->vy;
    }
    pos_of(p)[1] += dy * tk;
    return dy <= 0 && MS_LANDED(p, 0.0f, 0);
}

/* ------------------------------------------------------------------------------------------------ pin */

static void pin_end(uint8_t *p, struct ms_state *s)
{
    s->pin_mon = 0; s->flags &= ~0x10u;
    if (pos_of(p)[1] > MS_GROUND_Y(p) + 30) { s->air = 0; set_air(p, s); }
}

static void pin_start(uint8_t *p, struct ms_state *s)
{
    uint8_t *m = s->pin_pending, *r = em_rec(m);
    float *q = pos_of(p);
    s->pin_pending = 0;
    s->pin_mon = m; s->flags |= 0x10;
    for (int i = 0; i < 3; i++) s->pin_off[i] = q[i] - FIELD(float, r, 0x40 + 4 * i);
    s->pin_yaw_m = FIELD(uint16_t, r, 0x54); s->pin_yaw_p = FIELD(uint16_t, p, 0xfec);
    s->air = 0; s->att = 0;
    s->pin_hold = PIN_HOLD; s->pin_cd = 0; s->qte = 0;
    logf("msport: Magnetic Pin on monster %x (em %u)", (uint32_t)(uintptr_t)m, FIELD(uint8_t, m, 0xb5f4));
    MS_SET_ACTION(p, 0x10, 98, 0);
}

/* the hunter rides the pinned monster (S: GU's monster is not held yet, mechanics.md "Pin"); 99 = the QTE: X / A
 * presses (one per 4 ticks) add 4 to the bar and the hold; 70 -> the finisher (105 / 157 when the pin came from
 * Impact, flag 0x8000), the hold out -> 100 / 156. Returns 1 when the action changed */
static int pin_tick(uint8_t *p, struct ms_state *s, float tk, uint32_t no)
{
    uint32_t imp = (s->flags & 0x8000) != 0;
    if (!em_ok(s->pin_mon)) {
        logf("msport: pinned monster gone");
        pin_end(p, s);
        if (no == 105 || no == 157) return 0;
        MS_SET_ACTION(p, 0x10, imp ? 156 : 100, 0);
        return 1;
    }
    uint8_t *r = em_rec(s->pin_mon);
    uint16_t dyaw = (uint16_t)(FIELD(uint16_t, r, 0x54) - s->pin_yaw_m);
    float a = dyaw * MS_U16_RAD, c = cosf_gu(a), sn = sinf_gu(a), *o = s->pin_off, *q = pos_of(p);
    q[0] = FIELD(float, r, 0x40) + o[0] * c + o[2] * sn;
    q[1] = FIELD(float, r, 0x44) + o[1];
    q[2] = FIELD(float, r, 0x48) + o[2] * c - o[0] * sn;
    face(p, (uint16_t)(s->pin_yaw_p + dyaw));
    if (no != 99) return 0;
    MS_IFRAMES(p, 8.0f, 1);                             /* MHF: P+0x4ee = 4 ticks while pinned */
    s->pin_cd -= tk; s->pin_hold -= tk;
    if ((FIELD(uint16_t, p, 0x13f8) & (BTN_X | BTN_A)) && s->pin_cd < 1) {
        s->pin_cd += 4; s->qte += 4; s->pin_hold += 4;
        if (s->pin_hold > PIN_HOLD_MAX) s->pin_hold = PIN_HOLD_MAX;
    }
    if (s->qte >= QTE_WIN) {
        logf("msport: pin QTE success: Pin Finisher");
        MS_SET_ACTION(p, 0x10, imp ? 157 : 105, 0);
        return 1;
    }
    if (s->pin_hold > 0) return 0;
    logf("msport: pin over (QTE %d)", (int)s->qte);
    pin_end(p, s);
    MS_SET_ACTION(p, 0x10, imp ? 156 : 100, 0);
    return 1;
}

/* ------------------------------------------------------------------------------------------------ actions */

static const struct ms_action *find(uint32_t no)
{
    for (uint32_t i = 0; i < sizeof ms_actions / sizeof ms_actions[0]; i++)
        if (ms_actions[i].no == no) return &ms_actions[i];
    return 0;
}

static float drive(uint32_t v) { return (float)(int8_t)(uint8_t)v; }

static void event(uint8_t *p, struct ms_state *s, const struct ms_event *e, int i)
{
    uint32_t v = e->prm;
    s->fired |= 1u << i;
    switch (e->id) {
    case 1: if (v & 1) set_air(p, s); s->end_on_land = (v & 2) != 0; break;   /* airborne / ends on landing */
    case 2: case 24: break;             /* drawn (set at the start); guard level 5 (class 5 = GS's guard rules) */
    case 3: case 42: case 43: arm(p, s, e->hit); break; /* attack; special #11; #8 on the pinned monster */
    case 4:                                             /* special: 82 / 84's #1 = the marker shot */
        arm(p, s, e->hit);
        if (s->action == 82 || s->action == 84) marker_shot(p, s);
        break;
    case 44: break;                     /* #8 again for the pinned monster's non-host side (S: multiplayer) */
    case 7: case 8: {                   /* i-frames (ticks), 8 with Evasion's +5 / +10 (prm9 / prm10) */
        float n = (float)v;
        if (e->id == 8) { int l = MS_EVASION(p, 0x1f); n += l >= 2 ? 10 : l == 1 ? 5 : 0; }
        MS_IFRAMES(p, 2 * n, 0);
        s->keep_if = 0;
        break; }
    case 9: s->keep_if = 1; break;      /* i-frames >= 2 ticks until 7 / 8 */
    case 11: MS_STAMINA(p, -150.0f, 0); break;          /* MHF 75 = a roll (GU 150) */
    case 45: MS_STAMINA(p, -60.0f, 0); break;           /* MHF prm80 30 */
    case 12: MS_SHAKE(p, 0xf, 0); break;                /* S: GU preset 0xf for MHF's presets */
    case 13: MS_MOT_SPEED(p) = v * 0.01f; break;
    case 21:                            /* guard window: 0 open, 1 close, 2 / 3 close without the Guard skills (S) */
        if (v == 0) MS_BITS_SET(p, 0, MS_GUARDING, 0); else MS_BITS_CLEAR(p, 0, MS_GUARDING, 0);
        break;
    case 25: s->grav = (float)v; s->grav_t = 0; break;
    case 26: s->flags |= 0x20; break;   /* charge counting */
    case 27: s->fwd = drive(v); break;
    case 28: s->vert = drive(v); if (s->vert > 0) set_air(p, s); break;
    case 31: s->flags |= 0x80; s->fall_g = v * 0.01f; break;
    case 33: s->hold_v = (float)v; break;
    case 36: s->att = 0; break;         /* attraction vector reset */
    case 37: s->fwd = 0; break;
    case 38: s->vert = 0; break;
    case 39:                            /* face the pinned monster */
        if (s->pin_mon) {
            uint8_t *r = em_rec(s->pin_mon);
            float *q = pos_of(p);
            uint32_t y = yaw_to(FIELD(float, r, 0x40) - q[0], FIELD(float, r, 0x48) - q[2]);
            s->pin_yaw_p = (uint16_t)(y - (uint16_t)(FIELD(uint16_t, r, 0x54) - s->pin_yaw_m));
            face(p, y);
        }
        break;
    case 40: if (s->mode) s->flags |= 0x8000; else s->flags &= ~0x8000u; break;
    default: {                          /* 6 (P+0x4f0, unknown), 17 (effect task), 29 / 30 (drive curves), 41 */
        static uint64_t s_seen;
        if (!(s_seen & 1ull << e->id)) logf("msport: event %u (param %u) not run", e->id, v);
        s_seen |= 1ull << e->id;
    } }
}

static void start_step(uint8_t *p, struct ms_state *s, const struct ms_action *a, int k)
{
    const struct ms_step *st = &ms_steps[a->step0 + k];
    FIELD(uint8_t, p, 5) = (uint8_t)(k + 1);
    s->loops = 0; s->step_t = 0;
    if (st->kind <= 2) {                        /* go to another action */
        MS_SET_ACTION(p, 0x10, st->mot, 0);
        return;
    }
    MS_SET_MOTION(p, 5000 + st->mot, (float)st->blend, (float)st->start);
    if (k == 0) MS_SET_TABLE(p, st->table, 0); else MS_SET_TABLE_KEEP(p, st->table, 0, 1);
    s->last_frame = (float)st->start;
    for (int i = 0; i < a->nevents; i++) {
        const struct ms_event *e = &ms_events[a->ev0 + i];
        if (e->step == k && e->when == 0) event(p, s, e, i);
    }
}

static void action_start(uint8_t *p, struct ms_state *s, const struct ms_action *a)
{
    uint32_t no = a->no;
    float t[3], *q = pos_of(p);
    s->action = (uint16_t)no; s->fired = s->code_fired = 0;
    s->flags &= 0x1 | 0x10 | 0x40 | 0x1000 | 0x8000;
    s->end_on_land = 0; s->keep_if = 0;
    if (!IN(s_pin_keep, no)) { s->gc_hits = 0; s->fwd = s->vert = s->grav = s->grav_t = s->fall_g = s->hold_v = 0; }
    if (no != 94 && no != 97) s->pin_pending = 0;
    if (s->pin_mon && !IN(s_pinned, no)) pin_end(p, s);
    if (!IN(s_attract, no)) { s->att = 0; s->flags &= ~0x1000u; }
    s->mode = a->mode;
    if (IN(s_cost, no)) gauge_add(s, -BAR);
    MS_ACTION_FLAGS(p, s->air || s->pin_mon ? 2 : 0, 1, 0);
    ((void (*)(void *, uint32_t))MS_VT(p, 0x46c))(p, 1);
    if (no == 78 || no == 79) MS_DRAW_FLAG(p, 1);       /* the draw attacks, as GS's */
    switch (no) {
    case 34: s->charge = 0; s->charge_lvl = 0; break;
    case 58: case 61: case 62: case 68: case 71: case 72:
        if (!marker(s, t)) { logf("msport: attraction without a marker"); break; }
        face(p, yaw_to(t[0] - q[0], t[2] - q[2]));
        s->att = 1; s->att_t = 0; s->flags |= 0x1000;
        set_air(p, s);
        break;
    case 66: case 67:                                   /* repulsion: face the marker, the motion pushes away */
        if (marker(s, t)) face(p, yaw_to(t[0] - q[0], t[2] - q[2]));
        break;
    case 82: case 84: {                                 /* the shot: aim with the camera */
        uint8_t *cm = MS_CAM_MGR, *cam = cm ? FIELD(uint8_t *, cm, 0x54) : 0;
        if (cam) face(p, yaw_to(FIELD(float, cam, 0x60) - FIELD(float, cam, 0x40),
                                FIELD(float, cam, 0x68) - FIELD(float, cam, 0x48)));
        break; }
    case 163: case 164:
        if (s->mag[s->mode] == 0 && s->mag_v[s->mode] >= MAG_READY) {
            s->mag[s->mode] = 1; s->mag_v[s->mode] = MAG_TIME;
            logf("msport: %s Magnetise on", s->mode ? "Impact" : "Cutting");
        }
        break;
    }
    static int s_n;
    if (s_n++ < 400) logf("msport: action %u (%s) gauge %d, Magnetise %u/%d", no, a->mode ? "Impact" : "Cutting",
                          s->gauge, s->mag[s->mode], (int)s->mag_v[s->mode]);
}

static int step_done(uint8_t *p, struct ms_state *s, const struct ms_step *st)
{
    float f = MS_FRAME(p);
    if (f + 0.5f < s->last_frame) s->loops++;   /* the motion looped */
    s->last_frame = f;
    switch (st->kind) {
    case 3: return MS_MOTION_END(p) || (st->loops > 1 && s->loops >= st->loops);
    case 4: return s->loops + 1 >= st->loops && MS_REACHED(p, (float)st->frame);
    default: return 0;                          /* 5: hold */
    }
}

/* hits MHF's code spawns (0x103339d0): the Guard Counter successes 57 / 76 / 77 special #5 / #6 / #7 at f32, the
 * Finishing Slashes 152 / 154 / 155 special #10 after f38 when magnetised */
static void code_hits(uint8_t *p, struct ms_state *s, uint32_t no)
{
    uint32_t hit = 0;
    float f = 32;
    if (s->code_fired) return;
    if (no == 57) hit = MS_HIT_SPECIAL_5;
    else if (no == 76) hit = MS_HIT_SPECIAL_6;
    else if (no == 77) hit = MS_HIT_SPECIAL_7;
    else if ((no == 152 || no == 154 || no == 155) && s->mag[s->mode] == 1) { hit = MS_HIT_SPECIAL_10; f = 38; }
    if (hit && MS_REACHED(p, f)) { s->code_fired = 1; arm(p, s, hit); }
}

static int charge_tick(uint8_t *p, struct ms_state *s, float tk)   /* 34: 1 = released by overcharging */
{
    if (!(s->flags & 0x20)) return 0;
    s->charge += tk;
    if (!s->charge_lvl && s->charge >= CHARGE_T) {
        s->charge_lvl = 1;
        MS_SHAKE(p, 0xf, 0);                            /* S: cue for MHF's charge effect 0xfc6/0x11 + rumble */
        logf("msport: Triple Strike charged");
    } else if (s->charge_lvl && s->charge >= 2 * CHARGE_T) {
        s->charge_lvl = 0;
        logf("msport: Triple Strike overcharged: released");
        MS_SET_ACTION(p, 0x10, 36, 0);
        return 1;
    }
    return 0;
}

static void finish(uint8_t *p, struct ms_state *s, const struct ms_action *a, int k)
{
    if (k + 1 < a->nsteps) { start_step(p, s, a, k + 1); return; }
    if (s->pin_mon) pin_end(p, s);
    if (s->air) { s->air = 0; s->att = 0; MS_MOVE_STATE(p, 0); }   /* GU's ground step starts its fall */
    static int s_n;
    if (s_n++ < 100) logf("msport: action %u done: drawn neutral", a->no);
    MS_TO_NEUTRAL(p, 0, 4, 0, 0, 0, 0);
}

void ms_act(uint8_t *p)
{
    uint32_t no = FIELD(uint16_t, p, 0x250a);
    struct ms_state *s = ms_of(p);
    if (no == MS_RELEASE) {                     /* MHF shared 208: the charge released */
        MS_SET_ACTION(p, 0x10, s->charge_lvl ? 35 : 36, 0);
        return;
    }
    if (no == MS_GC_HIT) {                      /* MHF shared 207: the Guard Counter by guarded hits */
        MS_SET_ACTION(p, 0x10, s->gc_hits >= 3 ? 77 : s->gc_hits == 2 ? 76 : 57, 0);
        return;
    }
    const struct ms_action *a = find(no);
    if (!a) {
        logf("msport: action %u has no Magnet Spike data: neutral", no);
        ((void (*)(void *))MS_VT(p, 0x2f4))(p);
        return;
    }
    uint32_t step = FIELD(uint8_t, p, 5);
    if (step == 0) { action_start(p, s, a); start_step(p, s, a, 0); return; }
    int k = (int)step - 1;
    if (k >= a->nsteps) return;
    const struct ms_step *st = &ms_steps[a->step0 + k];
    float tk = tick_len(p), *q = pos_of(p);
    s->step_t += tk;
    for (int i = 0; i < a->nevents; i++) {
        const struct ms_event *e = &ms_events[a->ev0 + i];
        if (e->step != k || (s->fired & 1u << i)) continue;
        if ((e->when == 1 && s->loops >= e->loop && MS_REACHED(p, (float)e->frame)) ||
            (e->when == 3 && s->charge_lvl >= e->lvl)) event(p, s, e, i);
    }
    code_hits(p, s, no);
    if (s->pin_pending && (no == 94 || no == 97)) { pin_start(p, s); return; }
    if (s->pin_mon && IN(s_pinned, no) && pin_tick(p, s, tk, no)) return;
    if (no == 34 && charge_tick(p, s, tk)) return;
    if (s->keep_if) MS_IFRAMES(p, 4.0f, 0);
    if (s->hold_v > 0) {
        s->hold_v -= tk;
        FIELD(float, p, 0x1010) = FIELD(float, p, 0x1014) = FIELD(float, p, 0x1018) = 0;
    }
    if (s->fwd != 0 && !s->pin_mon) {
        float y = FIELD(uint16_t, p, 0xfec) * MS_U16_RAD;
        q[0] += sinf_gu(y) * s->fwd * tk; q[2] += cosf_gu(y) * s->fwd * tk;
    }
    s->grav_t += tk;
    int landed = 0;
    if (!s->pin_mon) {
        if (s->att) landed = attraction(p, s, tk);
        else if (s->air) landed = fall(p, s, tk);
    }
    if (landed) {
        s->air = 0; s->att = 0; s->vy = 0; s->flags &= ~0x1000u;
        logf("msport: landed in action %u", no);
        if (s->end_on_land || st->kind == 5) { finish(p, s, a, k); return; }
    }
    if (st->kind == 5 && !s->att && !s->air && !s->pin_mon && s->step_t > 15) {
        logf("msport: action %u: hold step %d with nothing driving it: done", no, k);
        finish(p, s, a, k);
        return;
    }
    if (step_done(p, s, st)) finish(p, s, a, k);
}
