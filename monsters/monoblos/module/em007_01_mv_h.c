/* em007_01_mv_h.c: Monoblos, ported 4U uEm101 handlers, batch H: category 6 (resting, burrowed, waking up). Literal
 * translations (MH4U v1.1), run by em007_01_moves_run. C = confirmed in code, S = strong, G = guess.
 * - 4U 0x911ad0 = setTargetMode(4) + action (0, 7) unless category 11 = GU slot 250 0x753ec (C: the same body).
 * - 4U 0x93e7b4 = a per-species float (record of 0x688854 +116); GU keeps two such getters, 0xbf590 (+12, 4U +100 =
 *   restValue) and 0xbf6e8 (+16): 0xbf6e8 (S: GU's Diablos calls it right before vertSet, as these handlers do).
 * - 4U 0x916140 = GU vertSet 0xbf7bc (tigerstripe em067_01_moves.c). 4U 0x92e864 / 0x94c5c4 = GU 0xc2768 / 0xc2780 (C:
 *   the same bodies: rec+0x5e38 / 0x5e34 = v and bit 32 / 64 of 4U W+0x420 cleared through 0x9ce40).
 * - 4U class work+9 = 1 in the resting actions = GU work+8 (S: GU's slot 125 clears work+8 before each action and its
 *   tail resets the work+12 timer when a handler set it; 4U's flag byte sits one higher, as the charge flag work+1 =
 *   GU work+0, C). Class work fields of 4U Monoblos with no GU place (the shake timer work+0x10, which GU's tail owns,
 *   the effect handle work+0x84 and sound timer work+0x58) live in mb_state.
 * - Ground effect: GU's Diablos' look, not 4U's (the user, 2026-11-05; 4U posted group 76 elements 14 / 15 = em101_019
 *   the burrow mound and em101_020 the dust trail, 0.4.1..0.4.3 shipped them as code records). GU's burrow travel
 *   0xd3eb74 (6/3 6/6 6/16 6/33..35 6/42) ends its step 0 with 0xa4a58(this, 2): common effect 2 (slot 116, the ground
 *   trail) in this+0xb7c4 for up to 3600 frames (table 0x159fb08: 30, 60, 3600); GU's per-frame code 0xa4878 reposts it
 *   when the ground type changes and finishes it at the slot (rec+0x1f0 below 1.19e-7) (C). His travels do the same;
 *   his runs can end before the slot, so mb_mound_frame finishes a trail of ours through GU's 0xa4a14 when the action
 *   is no travel any more. His 6/8 6/9 (4U's mound, GU's Diablos has no such action) post the same effect 2 with GU's
 *   request this+0xb640 (0xa4aa0..0xa4ac4) into a handle of ours, guarded as Black Gravios' laser handles, finished
 *   through 0x32a400 mode 0 at 4U's end points (mb_mound_frame). Sound 201 (4U 0x312484 = GU 0x4efb98, stygian
 *   em057_01_efx.c) plays with 4U's id on GU's em007 sound list (G: the same id as 4U Diablos', whose list GU kept).
 * - 4U W+0x978 (set by 6/15 and by 6/16's stage probe) has no GU field (dalamadur notes): left out with the probe
 *   (0x934b64 / 0x9355c8 / 0x2b9df8 and its hit-list reset). 6/16's overshoot snap needs W+0x3a0 (not mapped): left
 *   out (G). */
#include "em007_01.h"

typedef float (*speciesF_t)(void *self);
#define sleepHeight  FN(speciesF_t, 0xbf6e8)        /* [0x93e7b4] */
typedef void (*selfF_t)(void *self, float v);
#define vertSet      FN(selfF_t, 0xbf7bc)           /* [0x916140] rec+0x5c = v, rec+0x1b9 = 1 */
typedef void (*selfU_t)(void *self, uint32_t v);
#define stateFlag32  FN(selfU_t, 0xc2768)           /* [0x92e864] */
#define stateFlag64  FN(selfU_t, 0xc2780)           /* [0x94c5c4] */
typedef void *(*sndPos_t)(void *mgr, uint32_t id, void *owner, const float *pos, uint32_t area, int32_t m2);
#define sndPos       FN(sndPos_t, 0x4efb98)         /* [0x312484] */
#define SND_MGR      0x1896f5c                      /* [*0xfccd6c] (stygian em057_01.h) */
#define SLOT_ACTION_END_7 250
#define WK_REST      8                              /* [4U work+9] (see above) */

static inline void end_to_7(void *self) { VCALL0(self, SLOT_ACTION_END_7); }       /* [0x911ad0] */

static void snd201(void *self, const float *pos)
{
    void *mgr = *(void **)MAIN(SND_MGR);
    if (mgr) sndPos(mgr, 201, self, pos, FIELD(uint8_t, self, EN_AREA), -2);
}

typedef void (*efx_stop_t)(void *eff, uint32_t mode);
#define efx_stop     FN(efx_stop_t, 0x32a400)       /* mode 0: asks it to finish */
typedef void (*digFx_t)(void *self, uint32_t kind);
#define digFx        FN(digFx_t, 0xa4a58)           /* GU's ground trail, kind 2 = up to 3600 frames (see above) */
typedef void (*digFxEnd_t)(void *self);
#define digFxEnd     FN(digFxEnd_t, 0xa4a14)        /* finishes the trail of this+0xb7c4 (mode 0), its timer = 0 */
typedef void *(*fxPost_t)(void *self, uint32_t id, void *req);
#define SLOT_FX_POST 116                            /* vt+0x1d0 0xd48748: id < 1000 = common effect 0xa3e98 */
#define FX_TRAIL     2u                             /* GU's ground trail (0xa4aa8) */
#define EN_FX_REQ    0xb640                         /* request of the common effects: +0xc area, +8 kind */

/* GU 0xa4a88..0xa4ad0: effect 2 on the monster with GU's request; the caller keeps the handle */
static void *trail_post(void *self)
{
    void *e;
    FIELD(uint8_t, self, EN_FX_REQ + 0xc) = FIELD(uint8_t, self, EN_AREA);
    FIELD(uint32_t, self, EN_FX_REQ + 8) = 2;
    e = ((fxPost_t)(*(uint32_t **)self)[SLOT_FX_POST])(self, FX_TRAIL, (uint8_t *)self + EN_FX_REQ);
    FIELD(uint32_t, self, EN_FX_REQ + 8) = 0;
    return e;
}

static void travel_trail(void *self, struct mb_state *st)  /* GU 0xd3f130: step 0 of the burrow travel */
{
    static uint32_t s_lines;
    digFx(self, 2);
    st->trail = 1;
    if (s_lines < 4) {
        s_lines++;
        logf("mbport: em007_01 burrow trail (GU effect 2) -> %x", FIELD(uint32_t, self, 0xb7c4));
    }
}

static int efx_alive(void *eff)                     /* unit state 1 / 2 (stygian sz_efx_alive, dala_efx.c) */
{
    return eff && (FIELD(uint32_t, eff, 0xc) & 7) - 1 < 2;
}

/* The mound handle is a raw pointer: GU can free an effect and reuse its memory without telling us (Black Gravios'
 * laser crash, test 2026-11-03). So it is used only while its object keeps the vtable it had at the post, is in state
 * 1 / 2 and keeps the transform pointers (+0x150 / +0x154: 0 or word-aligned, only compared, never followed) of its
 * first alive frame (black_gravios em005_01_laser.c beam_ok); otherwise it is dropped untouched. No address range:
 * where Ryujinx, yuzu / Eden or the PC recomp put the heap differs (game.h MAIN_BASE). */
#define EFX_XF       0x150
static int xf_ok(uint32_t p) { return !(p & 3); }
static int mound_ok(struct mb_state *st)
{
    void *eff = st->mound;
    if (!eff) return 0;
    uint32_t vt = FIELD(uint32_t, eff, 0), a = FIELD(uint32_t, eff, EFX_XF), c = FIELD(uint32_t, eff, EFX_XF + 4);
    int ok = vt == st->mound_vt && efx_alive(eff) && xf_ok(a) && xf_ok(c);
    if (ok && !st->mound_seen) {
        st->mound_seen = 1;
        st->mound_xf[0] = a;
        st->mound_xf[1] = c;
    } else if (ok) {
        ok = a == st->mound_xf[0] && c == st->mound_xf[1];
    }
    if (!ok && (vt != st->mound_vt || st->mound_seen)) st->mound = 0;      /* gone (not merely not started yet) */
    return ok;
}

static void mound_release(struct mb_state *st)      /* [0xc470dc] on the handle, then the handle = 0 */
{
    if (mound_ok(st)) efx_stop(st->mound, 0);
    st->mound = 0;
}

static void mound_post(void *self, struct mb_state *st)
{
    if (st->mound) mound_release(st);               /* 0xc470dc on the old handle */
    st->mound = trail_post(self);
    st->mound_vt = st->mound ? FIELD(uint32_t, st->mound, 0) : 0;
    st->mound_seen = st->mound_xf[0] = st->mound_xf[1] = 0;
}

/* 4U uEm101 slot 45 0x8df784 (every frame) ends with 0x8e0254..0x8e02a4: the mound (class work+0x84) is released
 * unless the action (W+0x1ca / +0x1cb) is 6/8, 6/9 or 6/10; slot 13 0x8e1060 (the unit's cleanup, before uEnemy's
 * 0x94ccdc) releases it too (C). Here every frame from em007_01_moves_run, whatever action runs (GU slot 125). GU's
 * death action 12/255 runs outside slot 125 (em007_01_diag.c), so HP 0 releases it too (G: in place of 4U's cleanup
 * slot, which has no hook here). The travel's trail lives in GU's handle: GU's own code finishes it at the slot and
 * validates the handle (0xa4878, 0xad81c); a trail of ours ends here when the action is no travel any more (a run
 * that stopped early, a reaction). */
void mb_mound_frame(void *self, int lying, int travel)
{
    struct mb_state *st = mb_state(self);
    int dead = FIELD(int32_t, REC(self), REC_HP) <= 0;
    if (st->trail && (!travel || dead)) {
        st->trail = 0;
        digFxEnd(self);
    }
    if (!st->mound || !mound_ok(st)) return;
    if (!lying || dead) mound_release(st);
}

/* the 4U turn record 0xe0e090 (em007_01_mv_d.c has the same copy) */
static const seq_rec s_seq_e0e090 = {0.0f, 90.0f, 0.0f, 0x0e394000u,
                                     {{0x0d, 4.0f, 4.0f, 0}, {0x09, 10.0f, 0.0f, 0}, {0x0a, 10.0f, 0.0f, 0}}};

/* ---- 6/1 6/7: the 4U sub-dispatcher 0x8dc83c's cases 1 / 7 (0x8dc8c4 / 0x8dca74): rest (target mode 4, motion 1
 * looped, the species height), the rest flag every frame; 6/1 ends with the motion on the controlling machine, 6/7
 * at a 180 timer and the motion end. p[0] = 7 for 6/7 */
void mbmv_6_rest(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    WORK(self)[WK_REST] = 1;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 4);
        setMotionLoop(self, 1, 10.0f, 0.0f);
        vertSet(self, sleepHeight(self));
        if (p[0] == 7) RF(rec, REC_TIMER) = 180.0f;
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (p[0] == 7) {
        if (timerDown(self, &RF(rec, REC_TIMER), 1.0f) && isMotionEnd(self)) end_to_7(self);
    } else {
        if (FIELD(uint8_t, self, EN_CONTROLLED) && isMotionEnd(self)) end_to_7(self);
    }
}

/* ---- 6/3 6/13 (cases 3 / 13: 0x8dc96c / 0x8dcb64 -> 0x8dcba8) and 6/11 6/18 6/19 (4U 0x8dd624, kind = r1 0..2):
 * a resting turn (target mode 4, record 0xe0e090, the species height); 6/13 and 0x8dd624 at motion speed 10; kind 1
 * sets sleepFlagA, kind 2 both flags every frame. p = (speed 10?, sleep flags: 1 = A, 2 = A + B) */
void mbmv_6_turn(void *self, const uint8_t *p)
{
    uint8_t *rec;
    if (p[1] >= 1) sleepFlagA(self);
    if (p[1] >= 2) sleepFlagB(self);
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 4);
        seqStart1(self, &s_seq_e0e090, 0, 0, 0);
        vertSet(self, sleepHeight(self));
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (p[0]) setMotionSpeed(self, 10.0f);
    if (seqPoll1(self, &s_seq_e0e090)) end_to_7(self);
}

/* ---- 6/0 6/17: 4U 0x8dc5b4(kind = r1 0 / 1), lying down: motion 0x17 (unless it plays; kind 1 lets it end twice
 * more, W+0x145 = rec+0x1a2), then 0x18 with both sleep flags and target mode 4, resting (the rest flag) until its
 * end (0, 7). GU's version 0xd3e74c attacks; his does not: ported */
void mbmv_8dc5b4(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    uint32_t kind = p[0];
    switch (rec[REC_STEP0]) {
    case 0:
        rec[REC_STEP0] = 1;
        rec[REC_STEP1] = kind == 1 ? 2 : 0;
        setTargetMode(self, 0);
        if (curMotion(self) == 0x17) return;
        setMotion(self, 0x17, 10.0f, 0.0f);
        return;
    case 1:
        if (!isMotionEnd(self)) return;
        if (rec[REC_STEP1] != 0) {
            rec[REC_STEP1]--;
            return;
        }
        rec[REC_STEP0]++;
        setMotion(self, 0x18, 0.0f, 0.0f);
        sleepFlagA(self);
        sleepFlagB(self);
        setTargetMode(self, 4);
        return;
    case 2:
        WORK(self)[WK_REST] = 1;
        sleepFlagA(self);
        sleepFlagB(self);
        if (isMotionEnd(self)) end_to_7(self);
        return;
    default:
        return;
    }
}

/* ---- 6/2: 4U 0x8dc708, waking up: motion 0x212 (unless it already plays) with target mode 4; target mode 0 and the
 * vertical speed 0 at frame 1, the two state flags over frames 10..40, the end with the motion */
void mbmv_8dc708(void *self, const uint8_t *p)
{
    uint8_t *rec;
    (void)p;
    sleepFlagB(self);
    sleepFlagA(self);
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        if (curMotion(self) == 0x212) return;
        setMotion(self, 0x212, 6.0f, 0.0f);
        setTargetMode(self, 4);
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (motionCheck(self, 0, 0, 1.0f, 0.0f)) {
        setTargetMode(self, 0);
        vertSet(self, 0.0f);
    }
    if (motionCheck(self, 3, 0, 10.0f, 40.0f)) {
        stateFlag32(self, 1);
        stateFlag64(self, 1);
    }
    if (isMotionEnd(self)) end_action(self);
}

/* ---- 6/8 6/9: 4U 0x8dd310(kind = r1 0 / 1; 2 = 6/10), lying burrowed: rest (motion 1 looped, target mode 4, the
 * species height) for 60 / 80 / 100 frames (4U table 0xff9680) with the mound effect and sound 201 (again every 60
 * frames), then waking up (motion 0x212 looped, as 6/2's frames 1 and 10..40), the end with the motion */
void mbmv_8dd310(void *self, const uint8_t *p)
{
    static const int8_t s_frames[3] = {60, 80, 100};       /* 4U 0xff9680 */
    uint8_t *rec;
    struct mb_state *st = mb_state(self);
    uint32_t kind = p[0];
    sleepFlagB(self);
    rec = REC(self);
    switch (rec[REC_STEP0]) {
    case 0:
        WORK(self)[WK_REST] = 1;
        rec[REC_STEP0]++;
        setTargetMode(self, 4);
        setMotionLoop(self, 1, 10.0f, 0.0f);
        vertSet(self, sleepHeight(self));
        RF(rec, REC_TIMER) = (float)s_frames[kind < 3 ? kind : 0];
        mound_post(self, st);
        snd201(self, &RF(rec, REC_POS_X));
        return;
    case 1:
        st->snd_t += FIELD(float, self, EN_DT);            /* 0xb052c4 */
        if (st->snd_t >= 60.0f) {
            snd201(self, &RF(rec, REC_POS_X));
            st->snd_t = 0.0f;
        }
        if (timerDown(self, &RF(rec, REC_TIMER), 1.0f)) {
            rec[REC_STEP0]++;
            if (st->mound) mound_release(st);
            st->snd_t = 0.0f;
        }
        return;
    case 2:
        rec[REC_STEP0] = 3;
        setMotionLoop(self, 0x212, 6.0f, 0.0f);
        sleepFlagA(self);
        return;
    case 3:
        if (motionCheck(self, 1, 0, 1.0f, 0.0f)) setTargetMode(self, 0);
        if (motionCheck(self, 3, 0, 10.0f, 40.0f)) {
            stateFlag32(self, 1);
            stateFlag64(self, 1);
        }
        if (isMotionEnd(self)) end_action(self);
        return;
    default:
        return;
    }
}

/* ---- 6/12: 4U 0x8dd704, the burrowed run: motion 0x20f from frame 100 with target mode 4, stop distance -400, the
 * species height; a camera shake every 16 frames (timer W+468, first after 4), GU's ground trail in place of 4U's dust
 * every 6 frames (W+488); after frame 150 or on reaching the slot (inRange: 0, 7) it ends (0, 7) once the slot distance
 * is not above 0 */
void mbmv_8dd704(void *self, const uint8_t *p)
{
    uint8_t *rec = REC(self);
    struct mb_state *st = mb_state(self);
    (void)p;
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 4);
        setMotion(self, 0x20f, 6.0f, 100.0f);
        setStopDist(self, 0, 0, -400.0f);
        vertSet(self, sleepHeight(self));
        travel_trail(self, st);
        RF(rec, REC_TIMER) = 4.0f;
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (timerDown(self, &RF(rec, REC_TIMER), 1.0f)) {
        camShakeJoint(self, 0, 1, 0);
        RF(rec, REC_TIMER) = 16.0f;
    }
    if (!motionCheck(self, 1, 0, 150.0f, 0.0f) && inRange(self, 0, 64)) end_to_7(self);
    if (RF(rec, REC_TGT_DIST) > 0.0f) return;
    end_to_7(self);
}

/* ---- 6/4 6/15 6/16 6/20: 4U 0x8dcc80(kind = r1 0..3), the burrowed travel: motion 0x20f from frame 100 with target
 * mode 4, stop distance -500 / 0 / 0 / -300, the species height; a camera shake every 16 frames (first after 4), GU's
 * ground trail in place of 4U's dust every 6; the end (0, 7) once the slot distance is not above 0. Kind 1 sets both
 * sleep flags every frame, kind 3 sleepFlagA */
void mbmv_8dcc80(void *self, const uint8_t *p)
{
    uint8_t *rec;
    struct mb_state *st = mb_state(self);
    uint32_t kind = p[0];
    if (kind == 1) {
        sleepFlagA(self);
        sleepFlagB(self);
    } else if (kind == 3) {
        sleepFlagA(self);
    }
    rec = REC(self);
    if (rec[REC_STEP0] == 0) {
        rec[REC_STEP0] = 1;
        setTargetMode(self, 4);
        setMotion(self, 0x20f, 6.0f, 100.0f);
        if (kind == 0) setStopDist(self, 0, 0, -500.0f);
        else if (kind == 1 || kind == 2) setStopDist(self, 0, 0, 0.0f);
        else if (kind == 3) setStopDist(self, 0, 0, -300.0f);
        vertSet(self, sleepHeight(self));
        travel_trail(self, st);
        st->shake_t = 4.0f;
        return;
    }
    if (rec[REC_STEP0] != 1) return;
    if (timerDown(self, &st->shake_t, 1.0f)) {
        camShakeJoint(self, 0, 1, 0);
        st->shake_t = 16.0f;
    }
    inRange(self, 0, 64);                                   /* 4U calls it, result unused */
    if (RF(rec, REC_TGT_DIST) > 0.0f) return;
    end_to_7(self);
}
