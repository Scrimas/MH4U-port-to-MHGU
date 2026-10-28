/* em057_01_posts.c: Stygian Zinogre's shell posts from GU handlers that kept 4U's code without the posts
 * (notes/b5-shells.md 8f / 8g): the dragon pillars of the charge stance and charge walk (frame tables) and the dragon
 * orbs of the orb family (4U 0x84c280 = GU efa930). Mid hooks return 0 (the GU code then goes on unchanged), the
 * entry hook too. C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 * Multiplayer: GU runs these handlers on every machine (the synced action), as 4U, so each machine posts its own
 * shells; no controller test at any of the 4U sites (C). */
#include "em057_01.h"
#include "em057_01_shelldata.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR, SP0 };   /* SP0: the caller's [sp] at an entry hook */

#define WK_ANGLES 0x44  /* u32[3] the angle triple at the volley's start [4U work+68 / +72 / +0x4c] (GU efb044 /
                         * 4U 0x84c51c: rec+0x50..0x58 / W+424, W+428, W+0x1b0, after the turn 0x7bdd4 / 0x91b3f4) */

static int is_stygian(const void *self) { return self && FIELD(uint16_t, self, EN_ID) == STYGIAN_ZINOGRE_EM_ID; }

/* ---- the pillar frame tables: 4U 0x8470a4 (charge stance), 0x8452d4 / 0x845498 (charge walk steps 1 / 2): every
 * frame of the step, each row whose frame is now (atFrame 0x941dbc) posts a pillar at its offset turned by the yaw
 * (u16 4U this+0x8d24 -> REC_YAW, S as em057_01_mv_f.c), rot = 4U this+0x8d20 -> REC_ANGLES, grp 0xffff, b8 0, f 0.0;
 * a row with frame < 0 ends the table (C). GU kept each loop with its post removed (it only calls atFrame per row,
 * GU's rows = 4U's: em057_01_shelldata.h): the hooks below run the 4U loop at the start of GU's */
static void pillar_rows(void *self, const sz_pillar_row *t, uint32_t site)
{
    uint8_t *rec = REC(self);
    for (uint32_t i = 0; t[i].frame >= 0.0f; i++) {
        float ofs[4] = {t[i].x, t[i].y, t[i].z, 0.0f};
        if (!atFrame(self, t[i].frame)) continue;
        rot_y(ofs, RU(rec, REC_YAW));
        sz_shell044(self, 3, ofs, &RU(rec, REC_ANGLES), 0xffff, 0, 0.0f, site);
    }
}

/* GU 0xef4484 (r4 = this): ef4280's 1/6 15 16 17 28-33 step 1 with r1 == 0 (4U 0x846ec4 -> 0x847094, em 49 only),
 * before GU's `variant == 1` loop */
int em057_01_pstance_c(uint32_t *regs)
{
    void *self = (void *)regs[R4];
    if (is_stygian(self)) pillar_rows(self, sz_pillar_stance, 0x84716c);
    return 0;
}

/* GU 0xef6450 (r1 = the 4U r1, r4 = this): ef62e4's step 1; 2/40 passes r1 = 1 (4U 0x84516c: the r1 == 1 loop, no em
 * test; GU Zinogre stays GU's) */
int em057_01_pwalk1_c(uint32_t *regs)
{
    void *self = (void *)regs[R4];
    if (regs[R1] == 1 && is_stygian(self)) pillar_rows(self, sz_pillar_walk1, 0x84538c);
    return 0;
}

/* GU 0xef6338 (r1, r4 as above): ef62e4's step 2 (4U 0x845484) */
int em057_01_pwalk2_c(uint32_t *regs)
{
    void *self = (void *)regs[R4];
    if (regs[R1] == 1 && is_stygian(self)) pillar_rows(self, sz_pillar_walk2, 0x845580);
    return 0;
}

/* ---- the orb volleys: 4U 0x84c280(this, r1, r2, r3, [sp]) posts at frame 88 of step 1 (0x84c6b0..0x84cae0) and frame
 * 58 of step 2 (0x84cd60..0x84d23c), Stygian branch (em 49; 48 / 114 take Zinogre's): k = 0 when r2 is 0 or 1, else
 * 1; record index 0 (step 1) or 2 (step 2) (0x856900); uncharged one orb, charged two (index + 1); homing when [sp] ==
 * 5 or quest rank >= 5: subtype 2 uncharged, 3 then 2 charged, else subtype 0; origin = the position W+408 now,
 * angles = work+68 (C, both blocks read in full). GU efa930 (= 4U 0x84c280, the same parameters) keeps r2 in r6 and
 * [sp] in r9 (0xefa944..0xefa964), out of a mid hook's reach: the entry hook keeps them; at its two post points
 * (0xefaa6c after atFrame 88, 0xefaab4 after atFrame 58) GU posts its own orb for variant 0 (f03708), Thunderlord's
 * for 4 (f04260) and nothing for 1, so the mid hooks post Stygian's there. Rows: em057_01_moves.c 7/32-34 61-63 66 87
 * call efa930 with 4U's parameters; GU's dispatcher calls it for 7/211 212 (KEEP). */
static struct {
    void *self;
    uint8_t p[4];
} s_vp[4];

/* 0x856900(this, out, kind, idx) (C: literals 0x856a2c..0x856a3c) */
static const sz_orb_rec *orb_record(uint32_t kind, uint32_t idx)
{
    if (questRank(QUEST_GLOBAL) < 5) {
        if (idx > 3) return 0;
        return kind == 0 ? &sz_orb_hr0[idx] : &sz_orb_hr1[idx];
    }
    if (kind == 1) return idx <= 3 ? &sz_orb_g1[idx] : 0;
    if (kind == 2) return idx <= 9 ? &sz_orb_g2[idx] : 0;
    return idx <= 3 ? &sz_orb_g0[idx] : 0;
}

static const uint8_t *volley_params(void *self)
{
    for (uint32_t i = 0; i < SZ_N(s_vp); i++)
        if (s_vp[i].self == self) return s_vp[i].p;
    return 0;
}

static void orb_volley(void *self, uint32_t step, uint32_t site)
{
    static uint32_t s_lines;
    const uint8_t *p = volley_params(self);
    const float *origin = &RF(REC(self), REC_POS_X);
    const uint32_t *ang = (const uint32_t *)(WORK(self) + WK_ANGLES);
    const sz_orb_rec *r0, *r1 = 0;
    uint32_t k, idx = 2 * step, charged, homing, seed;
    if (!p) {
        if (++s_lines <= 40) logf("szport: orb volley (4U %x): no parameters kept", site);
        return;
    }
    k = p[1] <= 1 ? 0 : 1;
    charged = isCharged(self) != 0;
    homing = p[3] == 5 || questRank(QUEST_GLOBAL) >= 5;
    r0 = orb_record(k, idx);
    if (charged) r1 = orb_record(k, idx + 1);
    seed = (uint32_t)FIELD(uint16_t, self, EN_ACT_SERIAL) << 8 | idx << 1;
    if (++s_lines <= 40)
        logf("szport: orb volley %u/%u (%u, %u, %u, %u) step %u (4U %x): rank %d charged %u record (%u, %u) sub %u%s",
             FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM), p[0], p[1], p[2], p[3], step + 1,
             site, questRank(QUEST_GLOBAL), charged, k, idx, homing ? (charged ? 3 : 2) : 0,
             charged ? (homing ? " + 2" : " + 0") : "");
    if (!r0 || (charged && !r1)) return;
    sz_shell046(self, homing ? (charged ? 3 : 2) : 0, r0, origin, ang, 0xffff, seed, site);
    if (charged) sz_shell046(self, homing ? 2 : 0, r1, origin, ang, 0xffff, seed | 1, site);
}

/* GU 0xefa930 entry (r0 = this, r1-r3 and [sp] = 4U 0x84c280's parameters) */
int em057_01_vparams_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    uint32_t i = 0;
    if (!is_stygian(self)) return 0;
    while (i < SZ_N(s_vp) && s_vp[i].self && s_vp[i].self != self) i++;
    if (i == SZ_N(s_vp)) i = 0;                             /* more than four Stygians: reuse the first slot */
    s_vp[i].self = self;
    s_vp[i].p[0] = (uint8_t)regs[R1];
    s_vp[i].p[1] = (uint8_t)regs[R2];
    s_vp[i].p[2] = (uint8_t)regs[R3];
    s_vp[i].p[3] = (uint8_t)regs[SP0];
    return 0;
}

/* GU 0xefaa6c (r4 = this): atFrame 88 was true (step 1) */
int em057_01_volley1_c(uint32_t *regs)
{
    void *self = (void *)regs[R4];
    if (is_stygian(self)) orb_volley(self, 0, 0x84c6b0);
    return 0;
}

/* GU 0xefaab4 (r4 = this): atFrame 58 was true (step 2) */
int em057_01_volley2_c(uint32_t *regs)
{
    void *self = (void *)regs[R4];
    if (is_stygian(self)) orb_volley(self, 1, 0x84cd60);
    return 0;
}

/* ---- 4U vt77 0x857ba8's orb events: its motion tree (0x857f2c.., reached from every branch of the preamble, S) calls
 * 0x855fe4(this, k) for Stygian (em 48 / 114 take Zinogre's 0x856680 with the same k) at these (motion, frame) (C,
 * the tree read in full; correction 2026-10-28: the frame register s18 is reloaded with 138 at 0x858030 for motions
 * above 0x21a, so 0x225 / 0x226 post at 138, not 81); the same branches' sounds: em057_01_vt77.c.
 * GU's vt170 ef27b0 kept seven such sites but moved some (its k 5 at frame 89, k 6 at 138, k 1 for variant 0 only)
 * and posts nothing for variant 1, so the 4U table runs here every frame from the slot-125 hook (as the paw-slam
 * ground hit of the same vt77, em057_01_mv_d.c; atFrame answers there as in the handlers). */
static const struct {
    uint16_t mot;
    uint8_t k;
    float frame;
    uint32_t site;
} k_orb_events[7] = {
    {0x20f, 0, 117.0f, 0x857fb0},   /* 0x857f78 */
    {0x212, 1, 117.0f, 0x8587ec},   /* 0x857f60 -> 0x8587bc (frame 117 loaded at 0x857f54) */
    {0x218, 2, 6.0f, 0x858718},     /* 0x857ff4 -> 0x858668 .. 0x8586e4 */
    {0x21a, 3, 72.0f, 0x858620},    /* 0x857f48 -> 0x85856c .. 0x8585ec */
    {0x21e, 4, 89.0f, 0x858844},    /* 0x858040 -> 0x858810 */
    {0x226, 5, 138.0f, 0x85828c},   /* 0x858038 -> 0x858050 .. 0x85825c (frame s18 = 138 from 0x858030, 0x8580a8) */
    {0x225, 6, 138.0f, 0x8580e8},   /* 0x85804c -> 0x858050 .. 0x8580bc */
};

/* 4U 0x855fe4(this, k): quest rank >= 5 only; case k = a record pair of the vt77 table (kind 2): 0 (2, 3), 1 (0, 1),
 * 2 (4, 5), 3 (6, 7), 4 (8, 9), 5 = 0, 6 = 1; A.y += 300 (0x856148); the angle triple copied to work+68 now
 * (0x85617c); charged: both as subtype 4, else the first; origin = the position now (C) */
static void orb_event(void *self, uint32_t k, uint32_t site)
{
    static const uint8_t first[7] = {2, 0, 4, 6, 8, 2, 0};
    static uint32_t s_lines;
    uint8_t *rec = REC(self);
    uint32_t *ang = (uint32_t *)(WORK(self) + WK_ANGLES), charged;
    int32_t rank = questRank(QUEST_GLOBAL);
    const sz_orb_rec *p0, *p1;
    sz_orb_rec r0, r1;
    if (rank < 5 || k >= 7) return;
    p0 = orb_record(2, first[k]);
    p1 = orb_record(2, first[k] + 1u);
    if (!p0 || !p1) return;
    for (uint32_t i = 0; i < sizeof(sz_orb_rec) / 4; i++) {   /* no struct copy: it would call memcpy */
        ((uint32_t *)&r0)[i] = ((const uint32_t *)p0)[i];
        ((uint32_t *)&r1)[i] = ((const uint32_t *)p1)[i];
    }
    r0.a[1] += 300.0f;
    r1.a[1] += 300.0f;
    for (int i = 0; i < 3; i++) ang[i] = RU(rec, REC_ANGLES + 4 * i);
    charged = isCharged(self) != 0;
    if (++s_lines <= 30)
        logf("szport: orb event k %u (4U %x) %u/%u motion %x: rank %d charged %u records (2, %u)%s", k, site,
             FIELD(uint8_t, self, EN_ACT_CAT), FIELD(uint8_t, self, EN_ACT_NUM), curMotion(self), rank, charged,
             first[k], charged ? " + next" : "");
    sz_shell046(self, 4, &r0, &RF(rec, REC_POS_X), ang, 0xffff, 0, site);
    if (charged) sz_shell046(self, 4, &r1, &RF(rec, REC_POS_X), ang, 0xffff, 0, site);
}

void em057_01_orb_event_frame(void *self)
{
    uint32_t mot = curMotion(self);
    for (uint32_t i = 0; i < SZ_N(k_orb_events); i++)
        if (mot == k_orb_events[i].mot) {
            if (atFrame(self, k_orb_events[i].frame)) orb_event(self, k_orb_events[i].k, k_orb_events[i].site);
            return;
        }
}
