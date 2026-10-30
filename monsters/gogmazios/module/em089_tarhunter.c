/* em089_tarhunter.c: Gogmazios' tar on hunters (4U status "tar", bit 25 of the player status word).
 *
 * 4U (C, tar helpers 2026-10-23; notes/port-checklist.md "Tar on hunters"): a tar shell hit is attack type 63 ->
 * damage 0xb18618 (skill 0x10d blocks it, as web) -> reaction 0xb3cfe4: timer pw+580 = 210, action 110 (motions 15,
 * 19) -> 108 (struggle 0xb4a384(5)); a second path 0xb19ec4 goes to 109 (landing) -> 106. The struggle: 5 presses per
 * step, timer -60 per step, frame delta per frame, at <= 0 release to action 6; remote hunters start at 210 (web
 * 240). Tar = 4U's web with other numbers: actions 110 / 106..108 / 109 = 0xb4b1a8 / 0xb4a384 / 0xb4ad30 with the tar
 * variant, web 72 / 66, 68, 73 / 70, 71 with the web variant (6 presses, timer 240).
 * Look (0x3284ac, per hunter in the displayed area, every machine): state 3 while bit 25 (pending flag or action
 * 106..110): qe008_026 looping on the hunter + effect model qe000_004 at joint 1; back to 0: qe008_025 once.
 *
 * GU has the web half only (Capcom's port, C): reaction 0x2f47cc (types 48 / 56 / 60 / 61) -> action 72 (motion 15,
 * 19) -> 73 = 0x2bb990(2); 71 -> 66 = 0x2bb990(0); timer player+0x2938 (240 / 360, 60 with skill 35; remote 240 at
 * 0x2bba70); 6 presses per step (byte player+6, 0x2bbb00), -60 per step (0x1629aa8); look = the player's effect
 * shell [player+0x2630] post 0x2826f4(player, slot 19, shell 159 = cm101_002 web texture on joint 0) at 0x2bc3bc
 * (71), 0x2bcb54 (72 landing), 0x2bbac8 (73 start). Type 63 falls to the default of GU's switches (no status).
 * Port (while an em089 exists in the quest, em089_efx_present(); nothing else in its quests webs a hunter):
 *   em089_tar_dmg @0x2f1c60 (player reaction(player, _, type, type2, ...)): types 63 -> 48: GU's web rules (skills,
 *       actions, release, other hits clearing it) carry the tar.
 *   em089_tar_struggle @0x2bba74 (0x2bb990 start, after GU's remote 240, r4 = player): timer = 210, local and remote
 *       (GU's fall does not count it down; 4U's local 210 is set at the reaction).
 *   em089_tar_mash @0x2bbb00 (r1 = word + 0x10000, count in bits 16..23): 5 presses make a step.
 *   em089_tar_webpost @0x2826f4: GU's web look (slot 19, shell 159) and its web wrap (slot 4, shell 101, posted at
 *       0x2baef0 and 0x2bbe8c) not posted.
 *   em089_tar_shellpost @0x44cdd0 (the shell post 0x2826f4 wraps): GU's status look unit 0x44d260 posts the white
 *       wrap (web status bit 0x100000 -> slot 4 shell 135) every frame from 0x44d4f8; not posted.
 *   em089_tar_hunters_tick (from the em089 effect tick): a hunter in GU's web actions (66, 68, 70..73 = 4U 106..110)
 *       after a tar hit (em089_tar_dmg, this machine's hunter) or a struggle start (em089_tar_struggle, any hunter:
 *       a remote hunter's hit is resolved on its own machine) gets PEL 7000 (qe008_026) on its effect shell's attach
 *       model and the coat; leaving them: 7000 stopped, the coat killed, 7001 (qe008_025). GU's action 72 alone is
 *       not tar: it is also GU's knock-up (test 2026-10-23).
 * Coat: 4U's effect-model object (sMhEffect 0xc0a360 -> uMhEftModel, a uBaseModel: path table 0xef8c4c[1][4] =
 * effect\base\qe\qe000\qe000_004, parent = the hunter at joint 1 via vt+0x48, scale 1, hunter +0x8 copied) has no GU
 * class; GU makes the same thing in code (uShellSt008 0x498c28): uBaseModel alloc 0x88e6dc(1136, 16) + ctor
 * 0x88e71c, sUnit add 0xc067ec(mgr, line 19, model, mask 0x200000), setModel vt+0x58, resource release 0x887660,
 * vt+0x4c / +0x50 matrix update, flags +0xc bit 10 cleared. Parent: vt+0x48 = 0x45884 (+0x30 parent, +0x34 joint
 * number, mapped by the hunter's vt+0x54 through its +0x498 id table). Kill: vt+0x40 (state 3, sUnit frees it). The
 * model ships in em089's arc (tools/efl4u2gu.py TAR_COAT_MODEL) and is fetched by path hash + type like port.c.
 * GU has no kill-with-parent (4U +0x206): the coat is killed here whenever the hunter's tar ends or changes.
 * Deviations: 4U's release call 0x2fff1c(.., 500 / 60, player, 1) (sound?) not ported; the effects follow joint 0
 * of the attach model (GU web's joint; 4U's loop attach joint not traced); 4U posts only for hunters in the displayed
 * area, here every hunter (others are not drawn); the coat's per-player visibility sub-object (4U +0x1fc) is absent;
 * coat line / mask = st008's (GU's own effect models use another line, not traced to the end). */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "em089.h"
#include "em089_efx.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define TYPE_TAR          63u
#define TYPE_WEB          48u
#define PL_ACTION         0x250au     /* u16 (0x2b9a58) */
#define PL_TIMER          0x2938u     /* f32 struggle timer */
#define PL_EFX_SHELL      0x2630u     /* uShellPlEffectCom (0x2826f4) */
#define PL_AREA           0x1054u
#define TAR_TIMER         210.0f      /* 4U 0xb3cfe4 / 0xb4a384 */
#define TAR_PRESSES       5u
#define WEB_SLOT          19u
#define WEB_SHELL         159u
/* GU's second web look: shell 101 in slot 4 on the attach model (the white wrap of tests 20:06 .. 20:59, still shown
 * while 159 was skipped), posted only at 0x2baef0 (the action-70 path the tar hits take) and 0x2bbe8c (the struggle
 * start 0x2bb990): the only two of GU's 23 calls to 0x2826f4 with shell 101 */
#define WRAP_SLOT         4u
#define WRAP_SHELL        101u
#define LR_WRAP_POST_A    0x2baef4u
#define LR_WRAP_POST_B    0x2bbe90u
#define VT_ATTACH         0x130u      /* unit slot 76: attach model getter */

static int web_action(uint32_t a) { return a == 66 || a == 68 || (a >= 70 && a <= 73); }

/* hunters a tar hit (this machine's) or a struggle start (any hunter: nothing else in em089's quests webs one)
 * was seen for; em089_tar_hunters_tick moves them to its per-hunter flag. GU also uses action 72 for ordinary
 * knock-ups (test 2026-10-23: "tarred" at 00:18:13 / 00:22:58 without a tar hit), so the action alone is not tar. */
static void *s_mark[4];

/* test 2026-10-24 08:43: the white wrap still shown, but neither shell-101 site posted (no skip logged) while our
 * 7000 was posted on every hit -> every player effect post (0x2826f4) on the tarred hunter is logged after a hit */
static void *s_diag_pl;
static uint32_t s_diag_left;

static void mark_tarred(void *pl)
{
    s_diag_pl = pl;
    s_diag_left = 24;
    for (uint32_t i = 0; i < 4; i++) if (s_mark[i] == pl) return;
    for (uint32_t i = 0; i < 4; i++) if (!s_mark[i]) { s_mark[i] = pl; return; }
}

/* 0x2f1c60(player, _, type, type2, ...): the reaction dispatcher */
int em089_tar_dmg_c(uint32_t *regs)
{
    static uint32_t s_n;
    if (regs[R2] != TYPE_TAR && regs[R3] != TYPE_TAR) return 0;
    if (!em089_efx_present()) return 0;
    if (regs[R2] == TYPE_TAR) regs[R2] = TYPE_WEB;
    if (regs[R3] == TYPE_TAR) regs[R3] = TYPE_WEB;
    mark_tarred((void *)(uintptr_t)regs[R0]);
    if (++s_n <= 40) logf("gogport: em089 tar: hunter %x hit by tar (type 63 -> GU web 48)", regs[R0]);
    return 0;
}

/* 0x2bba74 in 0x2bb990's start (r4 = player, r5 = variant 0 / 1 / 2) */
int em089_tar_struggle_c(uint32_t *regs)
{
    static uint32_t s_n;
    uint8_t *pl = (uint8_t *)(uintptr_t)regs[R4];
    if (!pl || !em089_efx_present()) return 0;
    float was = FIELD(float, pl, PL_TIMER);
    FIELD(float, pl, PL_TIMER) = TAR_TIMER;
    mark_tarred(pl);
    if (++s_n <= 40) logf("gogport: em089 tar: struggle %u start, hunter %x timer %d -> %d", regs[R5], (uint32_t)pl,
                          (int32_t)was, (int32_t)TAR_TIMER);
    return 0;
}

/* 0x2bbb00 (`and r1, r1, #0xfe0000; cmp r1, #0x50000`: a step when the new count >= 6) */
int em089_tar_mash_c(uint32_t *regs)
{
    static uint32_t s_n;
    if (((regs[R1] >> 16) & 0xff) != TAR_PRESSES || !em089_efx_present()) return 0;
    regs[R1] = (regs[R1] & ~0xff0000u) | 0x60000u;
    if (++s_n <= 20) logf("gogport: em089 tar: %u presses -> step", TAR_PRESSES);
    return 0;
}

/* 0x2826f4(player, slot, shell index, req, force): the player effect shell post */
int em089_tar_webpost_c(uint32_t *regs)
{
    static uint32_t s_n;
    int web = regs[R1] == WEB_SLOT && regs[R2] == WEB_SHELL;
    uint32_t lr = regs[LR] - MAIN_BASE;
    int wrap = regs[R1] == WRAP_SLOT && regs[R2] == WRAP_SHELL && (lr == LR_WRAP_POST_A || lr == LR_WRAP_POST_B);
    static uint32_t s_nd;
    if ((void *)(uintptr_t)regs[R0] == s_diag_pl && s_diag_left && ++s_nd <= 120) {
        s_diag_left--;
        logf("gogport: em089 tar: diag post on hunter %x: slot %u shell %u req %u (lr %x, action %u)%s", regs[R0],
             regs[R1], regs[R2], regs[R3], lr, FIELD(uint16_t, (void *)(uintptr_t)regs[R0], PL_ACTION),
             web || wrap ? " -> skipped" : "");
    }
    if (!(web || wrap) || !em089_efx_present()) return 0;
    if (++s_n <= 20) logf("gogport: em089 tar: GU web look (slot %u shell %u) on hunter %x skipped", regs[R1], regs[R2],
                          regs[R0]);
    regs[R0] = 0;
    return 1;
}

/* 0x44cdd0(shell, slot, shell index, req, force) = the player effect shell's post (vt+0x158), which 0x2826f4 wraps.
 * GU's white wrap = its status look unit 0x44d260 (twin of 4U 0x3284ac, per frame): web status bit 0x100000 ->
 * slot 4 shell 135, posted every frame from 0x44d4f8 (test 2026-10-30 18:3x, our wrap off: the wrap stayed, with no
 * web post through 0x2826f4). Skipped here for every hunter (the unit runs for players only; any web while an em089
 * exists is tar, as em089_tar_dmg). */
#define STATUS_WEB_SHELL  135u
#define LR_STATUS_WEB     0x44d4fcu
int em089_tar_shellpost_c(uint32_t *regs)
{
    static uint32_t s_n;
    uint32_t lr = regs[LR] - MAIN_BASE;
    if (lr != LR_STATUS_WEB || regs[R1] != WRAP_SLOT || regs[R2] != STATUS_WEB_SHELL || !em089_efx_present())
        return 0;
    if (++s_n <= 20) logf("gogport: em089 tar: GU web shell (slot %u shell %u, lr %x) skipped", regs[R1], regs[R2], lr);
    regs[R0] = 0;
    return 1;
}

static struct {
    void *pl;
    uint8_t on;
    uint8_t hit;       /* tar hit / struggle seen, waiting for or in GU's web actions */
    uint8_t wait;      /* ticks left for a marked hunter to enter them (a blocked hit never does) */
    void *loop;
    uint8_t *coat;
} s_th[4];
#define HIT_WAIT          60u

#define COAT_HASH         0xcac4d30cu /* crc32('effect\base\qe\qe000\qe000_004') ^ ~0 */
#define TYPE_MOD          0x58a15856u
#define COAT_JOINT        1u          /* 4U [req+0x40] */
#define COAT_LINE         19u         /* uShellSt008 0x498c48 */
#define COAT_MASK         0x200000ull /* 0x162b8a0 */
#define RES_MGR           0x2126a64u
#define UNIT_MGR          (*(void **)MAIN(0x2126f48))
typedef void *(*res_find_t)(void *mgr, uint32_t fn, uint32_t hash, uint32_t type);
typedef void (*res_release_t)(void *res);
#define resRelease FN(res_release_t, 0x887660)
typedef void *(*model_alloc_t)(uint32_t size, uint32_t align);
#define modelAlloc FN(model_alloc_t, 0x88e6dc)
typedef void (*model_ctor_t)(void *m);
#define modelCtor  FN(model_ctor_t, 0x88e71c)
typedef void (*unit_add_t)(void *mgr, uint32_t line, void *unit, uint64_t mask);
#define unitAdd    FN(unit_add_t, 0xc067ec)
#define VT(o, off) ((*(uint32_t **)(o))[(off) / 4])

/* The coat is OFF unless built with EM089_TAR_COAT (test 2026-10-23 20:06): it stayed where it was made (a black blob
 * beside the knocked hunter: the uBaseModel's matrix is only updated at creation, vt+0x4c / +0x50), and Ryujinx's
 * Vulkan renderer crashed (DescriptorSetUpdater.SetUniformBuffers, index out of range) 0.37 s after the third coat
 * was made: the only effect material drawn through the model renderer. The tar look on the hunter is then 4U's
 * loop effect qe008_026 (the qe000_000 wrap) alone. */
#ifdef EM089_TAR_COAT
static uint8_t *coat_make(uint8_t *pl)
{
    void *mgr = *(void **)MAIN(RES_MGR);
    if (!mgr) return 0;
    res_find_t find = (res_find_t)VT(mgr, 0x38);
    void *res = find(mgr, (uint32_t)find, COAT_HASH, TYPE_MOD);
    if (!res) {
        static uint32_t s_n;
        if (++s_n <= 5) logf("gogport: em089 tar: coat model qe000_004 not loaded (hash %x)", COAT_HASH);
        return 0;
    }
    uint8_t *m = modelAlloc(1136, 16);
    if (!m) { resRelease(res); return 0; }
    modelCtor(m);
    unitAdd(UNIT_MGR, COAT_LINE, m, COAT_MASK);
    ((void (*)(void *, void *))VT(m, 0x58))(m, res);  /* setModel: takes its own reference */
    resRelease(res);
    for (int i = 0; i < 4; i++) FIELD(float, m, 0x40 + 4 * i) = 0.0f;   /* at the joint (4U request pos 0) */
    FIELD(uint32_t, m, 0x10) = FIELD(uint32_t, pl, 0x10);              /* 4U: hunter +0x8 copied */
    ((void (*)(void *, void *, uint32_t))VT(m, 0x48))(m, pl, COAT_JOINT);
    ((void (*)(void *))VT(m, 0x4c))(m);
    ((void (*)(void *))VT(m, 0x50))(m);
    FIELD(uint32_t, m, 0xc) &= ~(1u << 10);
    return m;
}
#endif

static void coat_kill(uint8_t *m)
{
    if (m && (FIELD(uint32_t, m, 0xc) & 7) - 1 <= 1) ((void (*)(void *))VT(m, 0x40))(m);
}

static void *attach_model(uint8_t *pl, uint32_t *area)
{
    void *sh = FIELD(void *, pl, PL_EFX_SHELL);
    *area = FIELD(uint8_t, pl, PL_AREA);
    if (!sh) return 0;
    return ((void *(*)(void *))((*(uint32_t **)sh)[VT_ATTACH / 4]))(sh);
}

void em089_tar_hunters_tick(void *self)
{
    static uint32_t s_n;
    for (uint32_t i = 0; i < 4; i++) {
        uint8_t *pl = em089_hunter_at(i);
        if (pl != s_th[i].pl) {             /* new / gone hunter: its coat's parent is no longer valid */
            coat_kill(s_th[i].coat);
            s_th[i].pl = pl; s_th[i].on = 0; s_th[i].hit = 0; s_th[i].loop = 0; s_th[i].coat = 0;
        }
        if (!pl) continue;
        for (uint32_t k = 0; k < 4; k++)
            if (s_mark[k] == pl) { s_mark[k] = 0; s_th[i].hit = 1; s_th[i].wait = HIT_WAIT; }
        uint32_t act = FIELD(uint16_t, pl, PL_ACTION), area;
        int web = web_action(act);
        if (s_th[i].hit && !web && !s_th[i].on && s_th[i].wait && !--s_th[i].wait) s_th[i].hit = 0;
        int tar = s_th[i].hit && web;
        if (s_th[i].on && !tar) s_th[i].hit = 0;   /* left the web actions: this tar is over */
        if (tar == s_th[i].on) continue;
        s_th[i].on = (uint8_t)tar;
        void *m = attach_model(pl, &area);
        if (tar) {
            s_th[i].loop = em089_efx_post_model(self, EM089_EFX_TAR_LOOP, m, area);
#ifdef EM089_TAR_COAT
            s_th[i].coat = coat_make(pl);
#endif
        } else {
            if (s_th[i].loop && em089_efx_alive(s_th[i].loop)) em089_efx_stop(s_th[i].loop);
            s_th[i].loop = 0;
            coat_kill(s_th[i].coat);
            s_th[i].coat = 0;
            em089_efx_post_model(self, EM089_EFX_TAR_END, m, area);
        }
        if (++s_n <= 40) logf("gogport: em089 tar: hunter %u %s (action %u, model %x, coat %x)", i,
                              tar ? "tarred" : "freed", act, (uint32_t)m, (uint32_t)s_th[i].coat);
    }
    for (uint32_t k = 0; k < 4; k++) s_mark[k] = 0;   /* marks of no current hunter */
}

/* the effect owner is being destroyed: stop the loops it posted */
void em089_tar_hunters_forget(void)
{
    for (uint32_t i = 0; i < 4; i++) {
        if (s_th[i].loop && em089_efx_alive(s_th[i].loop)) em089_efx_stop(s_th[i].loop);
        coat_kill(s_th[i].coat);
        s_th[i].pl = 0; s_th[i].on = 0; s_th[i].hit = 0; s_th[i].loop = 0; s_th[i].coat = 0;
        s_mark[i] = 0;
    }
}
