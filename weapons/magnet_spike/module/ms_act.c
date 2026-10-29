/* ms_act.c: the Magnet Spike's inputs and actions (Phase 2 slice, MS_SLICE).
 *
 * Inputs (slot 139, +0x22c, the class translator; GS's is 0x1160058): GU turns the pad into virtual buttons (player
 * +0x13f4 held, +0x13f8 pressed) and press combos (+0x1444, after a short simultaneity window: bit 2 = X alone, 4 = A
 * alone, 0x40 = X + A); the translator sets the class's input ids (+0x1424, 0x285e54) that plcmd_w05 commands test
 * (cmd_type 8). MHF -> Switch, by position (notes/phase2.md): tri = X, circle = A, tri+circle = X + A. Ids are per
 * mode (Impact = +MS_ID_IMPACT), so one idle table serves both modes. MS_BTN_SELECT / MS_BTN_R2: the virtual bits
 * of MHF's SELECT / R2 positions (Minus / ZR), from the button log (it prints every held-button change).
 *
 * Actions (slot 201, +0x324; act_st 0x10, act_no = MHF action number): MHF's step machine (msact.py) on GU's motion
 * and command calls. Step 0: action flags and the drawn flag as GS's attacks (0x282fd8(p, 0, 1, 0), vt+0x46c(p, 1)),
 * the mode, then each step: motion 5000 + slot from its start frame with its blend, the step's command table
 * (2000 + k; later steps keep the buffered presses, 0x2e9c50 keep 1), its events (attacks arm pl_we05_hitdata at the
 * event frame). Step kinds: 3 play (loops), 4 until a frame, 5 hold, 0 / 1 / 2 go to an action (2 = MHF's weapon
 * callback, S). After the last step: back to GU's drawn neutral (common 1/0, 0x2b6e94 as GS). Unknown numbers: GU's
 * base handler (vt+0x2f4). Transitions are GU's command step (the tables carry MHF's cancel windows). */
#include "ms.h"
#include "ms_data.inc"

/* MHF's SELECT / R2 by position = Minus / ZR: 0x200 / 0x800 (the user's Back / RT in test 1 runs 5-6: the mode switches
 * and Guard Counter ran from them). GU's own role masks (0x65f808..0x65facc) move roles between 0x40 / 0x100 / 0x200 /
 * 0x400 / 0x800 under the control option +0x446e; the log prints R's. */
#define MS_BTN_SELECT 0x200
#define MS_BTN_R2 0x800
typedef uint32_t (*ms_mask_t)(void);
#define R_MASK FN(ms_mask_t, 0x65f93c)   /* GU's R role: 0x40, or 0x800 under the other option (GS's translator) */
#define BTN_X 0x20
#define BTN_A 0x100

typedef void (*ms_pre_t)(void *p);
#define INPUT_PRE FN(ms_pre_t, 0x27e770)   /* GS's translator calls it first */

/* diagnostic (Phase 2 tests): every change of the action, its step, the body motion, the weapon's motion (part 0
 * object +0x23a0, its +0x4b4 = list << 8 | slot, 0x308b3c) and the command table (+0x24ac id, +0x24a8 table,
 * +0x24f0 the class list, 0x2e9b7c) */
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
    uint8_t *t = FIELD(uint8_t *, p, 0x24a8);           /* +8 count, +0x14 commands; a command's +8 = its CmdBase */
    uint32_t n = t ? FIELD(uint32_t, t, 8) : 0, bad = 0;
    for (uint32_t i = 0; i < n && i < 64; i++) {
        uint8_t *c = FIELD(uint8_t **, t, 0x14)[i];
        if (!c || !FIELD(uint32_t, c, 8)) bad++;
    }
    logf("msport: state action %u/%u step %u motion %u frame %d weapon %x table %u: %u commands, %u unresolved "
         "(class list %s)", now[0] >> 16, now[0] & 0xffff, now[1], now[2], (int)MS_FRAME(p), now[3], now[4], n, bad,
         FIELD(uint32_t, p, 0x24f0) ? "loaded" : "MISSING");
}

void ms_input(uint8_t *p)
{
    INPUT_PRE(p);
    trace(p);
    struct ms_state *s = ms_of(p);
    uint32_t combo = FIELD(uint32_t, p, 0x1444);
    uint16_t held = FIELD(uint16_t, p, 0x13f4), trig = FIELD(uint16_t, p, 0x13f8);
    uint32_t b = s->mode ? MS_ID_IMPACT : 0;
    if (combo & 2) MS_SET_CLASS_ID(p, b + MS_ID_TRI);
    if (combo & 4) MS_SET_CLASS_ID(p, b + MS_ID_CIRCLE);
    if (combo & 0x40) MS_SET_CLASS_ID(p, b + MS_ID_TRICIRCLE);
    if (held & BTN_A) MS_SET_CLASS_ID(p, b + MS_ID_CIRCLE_HELD);
    if ((s->held & BTN_A) && !(held & BTN_A)) MS_SET_CLASS_ID(p, b + MS_ID_CIRCLE_REL);
    if ((s->held & BTN_X) && !(held & BTN_X)) MS_SET_CLASS_ID(p, b + MS_ID_TRI_REL);
    if (trig & MS_BTN_SELECT) MS_SET_CLASS_ID(p, b + MS_ID_SELECT);
    if (trig & MS_BTN_R2) MS_SET_CLASS_ID(p, b + MS_ID_R2);
    if (held != s->held) {
        static int s_n;
        if (s_n == 0) logf("msport: GU's R role mask %x", R_MASK());
        if (s_n++ < 400) logf("msport: buttons held %x (was %x) pressed %x combo %x", held, s->held, trig, combo);
    }
    s->held = held;
}

static const struct ms_action *find(uint32_t no)
{
    for (uint32_t i = 0; i < sizeof ms_actions / sizeof ms_actions[0]; i++)
        if (ms_actions[i].no == no) return &ms_actions[i];
    return 0;
}

static void event(uint8_t *p, struct ms_state *s, const struct ms_event *e, int k)
{
    s->fired |= 1u << k;
    switch (e->id) {
    case MS_EV_ATTACK:
        MS_ARM(p, k & 1, e->arg, 0);            /* two slots: an attack may still be live when the next arms */
        logf("msport: action %u attack hit %u (frame %u)", s->action, e->arg, e->frame);
        break;
    case MS_EV_CHARGED:
        s->charged = 1;
        break;
    default: {                                  /* guard / armor / speed / turns / shake: later (log once) */
        static uint32_t s_seen;
        if (!(s_seen & 1u << e->id)) logf("msport: event %u (param %u) not run yet", e->id, e->arg);
        s_seen |= 1u << e->id;
    } }
}

static void start_step(uint8_t *p, struct ms_state *s, const struct ms_action *a, int k)
{
    const struct ms_step *st = &ms_steps[a->step0 + k];
    FIELD(uint8_t, p, 5) = (uint8_t)(k + 1);
    s->loops = 0;
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

static int step_done(uint8_t *p, struct ms_state *s, const struct ms_step *st)
{
    float f = MS_FRAME(p);
    if (f + 0.5f < s->last_frame) s->loops++;   /* the motion looped */
    s->last_frame = f;
    switch (st->kind) {
    case 3: return MS_MOTION_END(p) || (st->loops > 1 && s->loops >= st->loops);
    case 4: return s->loops + 1 >= st->loops && MS_REACHED(p, (float)st->frame);
    default: return 0;                          /* 5: hold until a command changes the action */
    }
}

void ms_act(uint8_t *p)
{
    uint32_t no = FIELD(uint16_t, p, 0x250a);
    struct ms_state *s = ms_of(p);
    if (no == MS_RELEASE) {                     /* MHF shared 208: the charge released, charged = Charged Strike */
        MS_SET_ACTION(p, 0x10, s->charged ? 35 : 36, 0);
        return;
    }
    const struct ms_action *a = find(no);
    if (!a) {
        logf("msport: action %u has no Magnet Spike data: neutral", no);
        ((void (*)(void *))MS_VT(p, 0x2f4))(p);
        return;
    }
    uint32_t step = FIELD(uint8_t, p, 5);
    if (step == 0) {
        s->action = no; s->fired = 0; s->charged = 0;
        s->mode = a->mode;
        MS_ACTION_FLAGS(p, 0, 1, 0);
        ((void (*)(void *, uint32_t))MS_VT(p, 0x46c))(p, 1);
        if (no == 78 || no == 79) MS_DRAW_FLAG(p, 1);   /* the draw attacks, as GS's */
        logf("msport: action %u (%s)", no, a->mode ? "Impact" : "Cutting");
        start_step(p, s, a, 0);
        return;
    }
    int k = (int)step - 1;
    if (k >= a->nsteps) return;
    const struct ms_step *st = &ms_steps[a->step0 + k];
    for (int i = 0; i < a->nevents; i++) {
        const struct ms_event *e = &ms_events[a->ev0 + i];
        if (e->step == k && e->when == 1 && !(s->fired & 1u << i) && MS_REACHED(p, (float)e->frame)) event(p, s, e, i);
    }
    if (!step_done(p, s, st)) return;
    if (k + 1 < a->nsteps) { start_step(p, s, a, k + 1); return; }
    static int s_n;
    if (s_n++ < 100) logf("msport: action %u done: drawn neutral", no);
    MS_TO_NEUTRAL(p, 0, 4, 0, 0, 0, 0);
}
