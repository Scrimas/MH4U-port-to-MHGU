/* Code shared by both Dalamadur halves (em090.h): fields, push flag, controller log, the action framework. */
#include "game.h"
#include "util.h"
#include "em090.h"

void dala_fields_init(void *self)
{
    for (uint32_t o = SIZE_uFestaEnemy + 4; o < DALA_SIZE; o++) FIELD(uint8_t, self, o) = 0;
    FIELD(uint8_t, self, F_CTL) = 0xff;
}

/* GU slot 119 (per frame from 0xade84, after the update's flag clear 0xa5198): the halves never push each other or
 * other monsters apart and GU never moves them onto the ground; both stay on their common spawn point as in 4U
 * (em090.h REC_NO_ENEMY_PUSH, REC_NO_GROUND; the spawn setups put y back to 4U's 0) */
void dala_state_frame(void *self)
{
    uint8_t *rec = FIELD(uint8_t *, self, EN_RECORD);
    FIELD(uint8_t, rec, REC_NO_ENEMY_PUSH) = 1;
    FIELD(uint8_t, rec, REC_NO_GROUND) = 1;   /* the object stays on 4U's spawn point (em090.h) */
    /* test log (2026-10-21: ~55 s of idle 1/0 in the arena): the AI's root idles unless the combat byte rec+0x2c0
     * (GU setBattleState 0xbcb9c, set at spawn) is 1 and target slot 0 has a param != 255 (rec+0x230 kind, +0x234
     * param; dala_ai.c). One line per change, both halves. */
    static uint32_t s_last[2] = {~0u, ~0u}, s_n;
    uint32_t tail = (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff);
    uint32_t sig = (uint32_t)rec[0x2c0] << 24 | (uint32_t)rec[0x230] << 16 | FIELD(uint16_t, rec, 0x234);
    if (sig != s_last[tail] && ++s_n <= 80) {
        s_last[tail] = sig;
        logf("dalaport: %s combat %u target kind %u param %u action %u/%u frame %u", tail ? "tail" : "head",
             rec[0x2c0], rec[0x230], FIELD(uint16_t, rec, 0x234), FIELD(uint8_t, self, EN_ACT_CAT),
             FIELD(uint8_t, self, EN_ACT_NUM), FIELD(uint32_t, self, F_FRAMES));
    }
}

/* One line whenever this machine's control of the half changes (GU writers: spawn 0xb167c, takeover 0xb16e0,
 * message 0xb161c). Both halves must always name the same owner (plan.md, multiplayer rules). */
void dala_ctl_log(void *self, const char *half)
{
    uint8_t ctl = FIELD(uint8_t, self, EN_CONTROLLED), owner = FIELD(uint8_t, self, EN_OWNER);
    if (ctl == FIELD(uint8_t, self, F_CTL) && owner == FIELD(uint8_t, self, F_OWNER)) return;
    FIELD(uint8_t, self, F_CTL) = ctl;
    FIELD(uint8_t, self, F_OWNER) = owner;
    logf("dalaport: ctl %s %x variant %u controlled %u owner %u frame %u", half, (uint32_t)self,
         FIELD(uint8_t, self, EN_VARIANT), ctl, owner, FIELD(uint32_t, self, F_FRAMES));
}

/* the local hunter (main+0x2126F48 chain, as Gogmazios' stage_cannon.c), 0 while its joints are not set up */
static void *local_hunter(void)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    return (pl && *(void **)((uint8_t *)pl + 0x498) && *(void **)((uint8_t *)pl + 0x494)) ? pl : 0;
}

/* where the body is (object, joints 0 / 200 = body root, 107 / 154 = 4U map icon joints of head / tail) against
 * the local hunter, every 300 frames, 6 times */
void dala_place_log(void *self)
{
    static const uint32_t joints[] = {0, 200, 107, 154};
    uint32_t f = ++FIELD(uint32_t, self, F_FRAMES);
    const float *o = (const float *)(REC(self) + REC_POS_X);
    {   /* every move of the object over 10 units: 4U keeps it at the spawn point (0, 0, 0); test 2026-10-21 had y 301
         * from the first frame and a body far too low on the peak after the arena breaks */
        static float s_o[2][3];
        static uint32_t s_n;
        uint32_t t = (FIELD(uint16_t, self, EN_ID) & 0xff) == (EM091_ID & 0xff);
        float dx = o[0] - s_o[t][0], dy = o[1] - s_o[t][1], dz = o[2] - s_o[t][2];
        if (dx * dx + dy * dy + dz * dz > 100.0f && s_n < 60) {
            s_n++;
            logf("dalaport: obj %s at %d %d %d action %u/%u motion %x mode %u frame %u", t ? "tail" : "head", (int)o[0],
                 (int)o[1], (int)o[2], FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM),
                 curMotion(self), MODE(self), f);
            for (int i = 0; i < 3; i++) s_o[t][i] = o[i];
        }
    }
    if (f % 300 != 30 || f >= 1800) return;
    float p[4], h[4] = {0, 0, 0, 0};
    void *pl = local_hunter();
    if (pl) jointPos(pl, 0, h);
    logf("dalaport: place %x variant %u obj %d %d %d hunter %d %d %d", (uint32_t)self, FIELD(uint8_t, self, EN_VARIANT),
         (int)o[0], (int)o[1], (int)o[2], (int)h[0], (int)h[1], (int)h[2]);
    for (uint32_t k = 0; k < sizeof joints / sizeof *joints; k++) {
        jointPos(self, joints[k], p);
        logf("dalaport: place %x joint %u at %d %d %d", (uint32_t)self, joints[k], (int)p[0], (int)p[1], (int)p[2]);
    }
}

/* ---- action framework (notes/port.md; Gogmazios' em089_act.c is the model) ---- */

/* block the AI while this action runs: the GU AI re-picks an action about every 5 s even mid-action. Keyed by the
 * action serial (this+0x73e8, bumped by every setAction), so our own end or an engine reaction lifts it. */
void dala_busy(void *self)
{
    FIELD(uint16_t, self, F_BUSY) = (uint16_t)(FIELD(uint16_t, self, EN_ACT_SERIAL) + 1);
}

/* GU slot 253 (base 0x7ff90). Only the AI think check 0x82538 (returning to 0x82554) sees the busy block: ~130
 * engine sites call this slot, among them the damage update 0x97ddc, which skips all damage on 1 (Gogmazios test,
 * 2026-10-19). */
int dala_think_blocked(void *self)
{
    if (__builtin_return_address(0) == (void *)MAIN(0x82554) &&
        FIELD(uint16_t, self, F_BUSY) == (uint16_t)(FIELD(uint16_t, self, EN_ACT_SERIAL) + 1)) return 1;
    return think_blocked_base(self);
}

/* step 0 of every 4U handler: "strb 1, [W, #0x144]" */
void dala_begin(void *self)
{
    dala_busy(self);
    STEP(self) = 1;
}

/* 4U setActionNext 0x94ef9c: GU's (0x76984) starts the action on the controlling machine and queues it as a local
 * replay elsewhere (this+0x73e5..7), so every machine runs the chain; the AI stays blocked until it starts */
void dala_chain(void *self, uint32_t cat, uint32_t num)
{
    setActionNext(self, cat, num);
    dala_busy(self);
}

/* 4U "vcall vt+0x164" (slot 89): every handler ends this way; our classes override it (dala_end_slot) */
void dala_end(void *self) { VCALL0(self, SLOT_ACTION_END); }

/* GU slot 247 = 4U slot 89 of both classes (head 0x76c700, tail 0x89fab8, identical): in body placement 1 / 2 the
 * idle of that placement (1/1, 1/2) follows, else the base end (4U 0x911b80 = GU 0x75224) */
#define end_base FN(act_base_t, 0x75224)
void dala_end_slot(void *self)
{
    uint32_t m = MODE(self);
    if (m != 1 && m != 2) { end_base(self); return; }
    setTargetMode(self, 0);
    setActionW(self, 1, m);
    thinkRequest(self, 0);
}

/* 4U timerDown(this, &W+468) 0xb0709c: t -= this+20, 1 once <= 0 */
int dala_timer(void *self) { return timerDown(self, &TIMER(self), 1.0f); }

/* 4U motionCheck(this, 0, 0, frame, 0) 0x91ab1c: the motion reached `frame` */
int dala_at(void *self, float frame) { return motionCheck(self, 0, 0, frame, 0.0f); }

/* 4U 0x920058(this, motion, flags, blend, start): setMotionEx unless the motion already plays (guard 0xb059a4 =
 * vt+0x84 == motion; GU 0x72788 the same, C) */
void dala_motion_keep(void *self, uint32_t motion, uint32_t flags, float blend, float start)
{
    if (curMotion(self) != motion) setMotionEx(self, motion, flags, blend, start);
}

/* 4U attackEx 0x933144 (param) / attack 0x914dfc (= attackEx with param 0, both games, C). The head also notes the
 * armed attack's kind in work+0x58 (slot 0) / +0x5c (slot 1): byte +0x19 of the 40-byte attack record from the
 * parameter table 0x911cc8 (= the etd attack table: every site reads 40 * index + 0x19). Its slot 48 turns it into
 * the hit bits work+0x54 when the attack connects (kinds 13 / 4, 1 / 12, 8 / 14 / 20 / 24). Dalamadur and Shah
 * share the values (4U etd, rxgen-style dump 2026-10-21). */
static const uint8_t k_atk_kind[70] = {
    0, 0, 1, 19, 2, 3, 1, 19, 6, 7, 22, 4, 23, 2, 13, 13, 3, 12, 13, 13, 13, 13, 11, 13, 11, 2, 2, 12, 3, 3, 3, 3,
    2, 12, 2, 3, 2, 1, 3, 12, 14, 15, 3, 3, 3, 2, 0, 15, 15, 2, 3, 2, 8, 3, 16, 8, 3, 8, 19, 1, 19, 25, 3, 3, 1, 8,
    0, 24, 16, 0,
};
void dala_attack(void *self, uint32_t slot, uint32_t index, uint32_t param)
{
    if ((FIELD(uint16_t, self, EN_ID) & 0xff) == (EM090_ID & 0xff) && slot <= 1 && index < sizeof k_atk_kind)
        DALA_WORK(uint32_t, self, 0x58 + 4 * slot) = k_atk_kind[index];
    attackEx(self, slot, index, param);
}

void dala_stub(void *self, const char *what, uint32_t a, uint32_t b)
{
    static uint32_t s_n;
    if (++s_n <= 80) logf("dalaport: %x stub %s (%u, %u)", (uint32_t)self, what, a, b);
}

void dala_log_action(void *self, const char *half, const char *how)
{
    static uint32_t s_n;
    uint16_t a = (uint16_t)(0x8000 | FIELD(uint8_t, self, EN_ACT_CAT) << 8 | FIELD(uint8_t, self, EN_ACT_NUM));
    if (FIELD(uint16_t, self, F_LASTACT) == a) return;
    FIELD(uint16_t, self, F_LASTACT) = a;
    if (++s_n <= 400)
        logf("dalaport: %s %x action %u/%u (%s) mode %u motion %x ctl %u frame %u", half, (uint32_t)self,
             FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM), how, MODE(self), curMotion(self),
             FIELD(uint8_t, self, EN_CONTROLLED), FIELD(uint32_t, self, F_FRAMES));
}

/* Shared HP (class-study.md "Shared HP", plan.md MP rules). 4U keeps one pool for both halves (mgr+0x328; the damage
 * function 0x920104 runs on the controlling machine only and copies the pool into each half's HP). GU has no pool:
 * on the machine that controls the head, every frame the HP both halves lost since the last sync is taken from both
 * (new = HP head + HP tail - last), through setHP 0x9a764 (so the HP floor rec+0x380 applies). Other machines never
 * write HP: GU's own HP sync carries the result. A new controller (migration) starts from the lower of the two. */
typedef void (*setHP_t)(void *self, int32_t hp);
#define setHP FN(setHP_t, 0x9a764)
#define HP_OF(e) FIELD(int32_t, REC(e), REC_HP)
void dala_hp_sync(void *head)
{
    void *tail = dala_partner(head);
    if (!tail || !FIELD(uint8_t, head, EN_CONTROLLED)) { FIELD(int32_t, head, F_POOL) = 0; return; }
    int32_t h = HP_OF(head), t = HP_OF(tail), last = FIELD(int32_t, head, F_POOL);
    if (last < 0) return;                       /* the pool reached 0: both halves are down, nothing to share */
    if (last == 0) {
        last = h < t ? h : t;
#ifdef TEST_HP_PCT
        /* test builds (GOG_DEFINES="TEST_HP_PCT=5"): both halves start at that share of the head's max HP, once per
         * head object, so a kill test is short (Gogmazios' em089_act.c does the same) */
        static void *s_hp_set;
        int32_t mx = FIELD(int32_t, REC(head), REC_HP + 4);
        if (s_hp_set != head && mx > 0 && h == mx) {
            s_hp_set = head;
            last = h = t = mx * TEST_HP_PCT / 100;
            setHP(head, h);
            setHP(tail, t);
            h = HP_OF(head); t = HP_OF(tail);
        }
#endif
        logf("dalaport: pool start %d (head %d / %d, tail %d / %d)", last, h, FIELD(int32_t, REC(head), REC_HP + 4), t,
             FIELD(int32_t, REC(tail), REC_HP + 4));
    }
    int32_t v = h + t - last;
    if (v < 0) v = 0;
    if (h != v) setHP(head, v);
    if (t != v) setHP(tail, v);
    FIELD(int32_t, head, F_POOL) = HP_OF(head) > 0 ? HP_OF(head) : -1;   /* -1: dead, keeps "set" */
    if (h != t || h != v) {
        static uint32_t s_n;
        if (++s_n <= 60) logf("dalaport: pool head %d tail %d last %d -> %d (now %d / %d)", h, t, last, v, HP_OF(head),
                              HP_OF(tail));
    }
}

/* One pool, one death (test 2026-10-21 sixth install: the head died, the tail kept attacking with HP 0).
 * Death trigger (C, both games): only the damage function starts a death, on a frame with damage (or the net
 * damage field) and HP <= 0: GU 0x97ddc (controller only, 0x97e10): no damage -> 0x98be4 tests rec+0x5d66, then
 * 0x98cbc HP <= 0, rec+0x3a2..0x3a4 == 0, 0x8187c -> reaction kind rec+0x3ae = 1 (0x99134) -> dispatcher 0x9a828
 * kind 1 -> death chooser 0x9b2bc -> request 11/n (0x76afc). 4U the same: 0x920a24 / 0x920b28 (W+0x7a6e) /
 * 0x920b3c -> W+0x426 = 1. A plain HP write (dala_hp_sync) therefore never kills the half that was not hit.
 * 4U's pool sets HP = 0 on both halves every frame (0x9201cc); how 4U then starts em083's death was NOT found
 * (tail class, its partner-lookup sites, the death chooser 0x92c0a4 and its callers checked: none kills the
 * partner). Port: once either half is dead (category 11 or 12/255), the controller sets the other half's HP to the
 * pool's 0 and one point of GU's net damage rec+0x5d66 (written by GU's damage message 0xa26f8), so the other half
 * dies through GU's own path above; after 60 frames without a death it requests 11/0 directly (0x76afc). Other
 * machines get the death action like any death (setAction replay; op 7 -> 12/255 is GU's own). */
#define REC_NET_DAMAGE 0x5d66   /* s16, GU damage update applies it and runs the death check (0x98ae4 / 0x98be4) */
typedef void (*reactRequest_t)(void *self, uint32_t cat, uint32_t num);
#define reactRequest FN(reactRequest_t, 0x76afc)   /* setAction(cat, num, mode 5) unless in category 11 */
static int half_dead(void *e)
{
    uint32_t cat = FIELD(uint8_t, e, EN_ACT_CAT), num = FIELD(uint8_t, e, EN_ACT_NUM);
    return cat == 11 || (cat == 12 && num == 255);
}
void dala_death_sync(void *head)
{
    static void *s_head;
    static uint32_t s_wait, s_log;
    void *tail = dala_partner(head);
    if (!tail) return;
    if (s_head != head) { s_head = head; s_wait = 0; s_log = 0; }
    int hd = half_dead(head), td = half_dead(tail);
    for (uint32_t k = 0; k < 2; k++) {   /* one line per half on 12/255 (the corpse) */
        void *e = k ? tail : head;
        if (FIELD(uint8_t, e, EN_ACT_CAT) == 12 && FIELD(uint8_t, e, EN_ACT_NUM) == 255 && !(s_log & 1u << k)) {
            s_log |= 1u << k;
            logf("dalaport: death %s reached 12/255 frame %u", k ? "tail" : "head", FIELD(uint32_t, head, F_FRAMES));
        }
    }
    if (hd == td) { s_wait = 0; return; }
    void *dead = hd ? head : tail, *live = hd ? tail : head;
    const char *ln = hd ? "tail" : "head";
    if (!FIELD(uint8_t, live, EN_CONTROLLED)) return;   /* HP and the death are the controller's (0x97e10) */
    if (!(s_log & 4)) {
        s_log |= 4;
        logf("dalaport: death sync %s dead (%u/%u) -> %s HP %d action %u/%u frame %u", hd ? "head" : "tail",
             FIELD(uint8_t, dead, EN_ACT_CAT), FIELD(uint8_t, dead, EN_ACT_NUM), ln, HP_OF(live),
             FIELD(uint8_t, live, EN_ACT_CAT), FIELD(uint8_t, live, EN_ACT_NUM), FIELD(uint32_t, head, F_FRAMES));
    }
    FIELD(float, REC(live), REC_HP_FLOOR) = -1.0f;   /* no floor on a dead pool */
    setHP(live, 0);
    FIELD(int16_t, REC(live), REC_NET_DAMAGE) = 1;
    /* 4U shares the death (kind 1) and the partner reacts one frame after the post (dala_react.c). GU's own death
     * check never fired on the live half here (test 2026-10-22: still alive after 60 frames, so the two death motions
     * ran 60 frames apart): request it on the next frame. */
    if (++s_wait == 2) {
        logf("dalaport: death sync %s not dead the frame after (HP %d, flags %u %u %u): request 11/0", ln, HP_OF(live),
             REC(live)[0x3a2], REC(live)[0x3a3], REC(live)[0x3a4]);
        reactRequest(live, 11, 0);
    }
}

/* GU slot 240 = paint mark (base 0xc0908: rec+0x1c4 = 36000 frames, net flag this+0x7429 bit 0, skipped when
 * this+0x15e9 bit 2). 4U 0x910650 paints every enemy whose em is 24 / 83 / 110 / 111, i.e. both halves
 * (common-branches.md). Remote machines get the paint through the flags message (slot 272 -> slot 240), so this
 * override paints the partner there too. */
#define paint_base FN(act_base_t, 0xc0908)
void dala_paint(void *self)
{
    paint_base(self);
    void *p = dala_partner(self);
    if (p) paint_base(p);
}

/* 4U 0x68fd44(mgr, em) scans the enemy slots for the partner em (head 24 <-> tail 83, Shah 110 <-> 111). A quest
 * holds one pair, so each machine remembers its two halves at spawn (slot 118) and forgets them on delete. */
static void *s_half[2];
void dala_register_half(void *self, uint32_t tail) { s_half[tail ? 1 : 0] = self; }
void dala_forget_half(void *self)
{
    for (uint32_t k = 0; k < 2; k++) if (s_half[k] == self) s_half[k] = 0;
}
void *dala_head(void) { return s_half[0]; }
void *dala_partner(void *self)
{
    void *p = s_half[0] == self ? s_half[1] : s_half[1] == self ? s_half[0] : 0;
    return (p && FIELD(uint8_t, p, EN_VARIANT) == FIELD(uint8_t, self, EN_VARIANT)) ? p : 0;
}
