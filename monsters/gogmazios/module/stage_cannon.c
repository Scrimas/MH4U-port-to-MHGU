/* Battlequarters alias: 4U floor cannons s03 / s04 (arena-4 agent, notes/stage.md section 14).
 *
 * 4U (traced, C; quest object = stage logic `this`, +0x803c = REMAINING-time countdown "rem"):
 *  - quest setup 0x6aa2d0 (m19, a monster of em 89 in the quest): +0xdd25 = 1 (cannons enabled), used bits +0xdd24
 *    |= 6 (cannons 1 / 2), use time +0xdca0 + 4k = rem + fps * 420; bonus time words +0xdd00 / +0xdd14 = -1.
 *  - per frame 0x6b0ce0: used cannon k re-arms when use time - rem >= fps * 60 * 10 (table 0xe08114 {3, 10, 10});
 *    enabled + not used: kobj (area 3, mId 3 + k) action in {52, 54, 255} -> command 34 = action 51 (barrel up 25
 *    deg), action 51 and word >= 0 and word - rem >= fps * 180 -> command 41 = action 55 (25 -> 55 deg).
 *  - KowareObj action-51 end (0x1cdc88): word = rem.
 *  - interaction kind 35 records (0x5b921c): (2050, 0, 1230) yaw 49152 / (-1575, 0, 1230) yaw 16384, pitch 0xee39
 *    (-25 deg), radius 100. Ready 0x6b1a58: enabled, not used, shots +0xdd26 + k-1 <= 0, kobj idle, its action not
 *    in {52, 54, 255}. Player switch action 0xb5b2a0 type 6 -> 0x6b91b4 -> 0x6aafec (request, bonus = word >= 0 and
 *    word - rem >= fps * 180) -> 0x6adb20 (shots > 0: drop; action in {52, 54, 255}: command bonus ? 39 (53) : 34
 *    (51)) -> 0x6ab7f8: used bit, use time = rem, bonus: shots += 1 + uShell023 (bonus 1); then shots += 1, word = -1,
 *    uShell023 (bonus 0).
 *  - uShell023 kind 1 (ctor 0xc77834, init 0xc77068): start = record pos + rotY(record yaw) * (0, 40, 190), or
 *    (0, 95, 155) for the bonus shell; pitch = record pitch (-25 deg) or 0xd8e4 (-55 deg) for the bonus shell;
 *    speed 125 / frame along it (0xc7678c); life 120 / 60 (bonus). End 0xc776a0: shots -= 1; cannons disabled or k
 *    used: last shell -> action 51 ? command 35 (action 52) : command 40 (action 54); otherwise word = action 51 ?
 *    rem : rem + fps * 180.
 * GU port:
 *  - models + animation: the converted s03 / s04 KowareObj schedulers (tools/stage4u2gu.py CANNONS_KOWARE; s04 is
 *    created here by stage_kobj_extra @0x4fdf7c with 0x500bb4(mgr, area 2, slot 5, file 0xc133)); actions are played
 *    with GU's play-action 0x515328(kobj, id, 0, 0, 0) (= 4U 0x1d2a10; commands 34/35/39/40/41 = actions
 *    51/52/53/54/55, 4U 0x1d2964..0x1d29d0).
 *  - prompt: two GU interaction records (mgr [0x1889ec0], 0x31aa6c / 0x31abac, as st006 0x495924) of kind 11 (the
 *    Dragonator switch: player action 143 = GU's switch action, 4U uses the same switch action body for both);
 *    stage_cannon_ready @0x503b88 answers the 4U ready check when the call comes from the kind-11 interaction
 *    (lr 0x2ed448) and the local hunter stands at a cannon record; the switch action's Dragonator fire 0x503bb0
 *    (hook owned by stage_gimmick.c, which calls stage_cannon_fire first) fires the cannon instead, and
 *    stage_dragonator_post @0x503a5c skips the Dragonator follow-up for that press.
 *  - projectile: GU's cannonball shell uShellPlcom_009 (shell type 29, the GU Fortress cannon st008's shot, life 120
 *    like uShell023), posted as st008 does (0x2d967c: setup param 0x4632ec(20, 16), mode 1, owner = the player,
 *    shell manager [0x1892550] 0x48c4f0); stage_cannon_shot @0x46365c (end of its mode-1 init, r4 = shell, before
 *    the start call vt+0x170) overwrites the start position / pitch / yaw with 4U's; stage_shell_dtor @0x4a18b4
 *    (uShell base dtor) runs the 4U shell-end logic for our shells.
 *  - stage_cleanup @0x4ff074 (stage manager cleanup at quest end): frees the interaction records.
 * uShellPlcom_009 IS Capcom's port of uShell023 (checked): its HDS entries 0 / 1 are 4U records 0x102cc60 + 40 * kind
 * (kind 0 / 1: same window 0..99 and layout; GU power 0 for 4U 1, attack type 14 = 14 and 75 for 4U 64 = Capcom's
 * renumbering), its HTS = 4U volume 0 (bone 1001, radius 50), FUP floats 120 (life) / 600 (stick time) / -15 (pitch),
 * the shared flight code holds 4U's 125 / frame (0x4692d0), and the stick-on-monster logic (+0x15e8 / +0x15a8) is
 * 4U's state 3. Mode 1 = variant 1 (hit001 / ef001 / snd001, like st003's sub-type byte +8) = 4U kind 1, the floor
 * cannon. So flight, damage, effects and sound are 4U's as converted by Capcom.
 * Online: no request of our own goes over the network. The switch press is replayed for every player on every machine,
 * so every machine runs the same fire (barrel action, state, one shell per shell slot); only the machine controlling
 * the monster turns the hit into damage (GU 0x97ddc), as with GU's own st008 cannon -> it counts once. 4U instead
 * sent its cannon request (0x6aafec) over the network; the per-machine state can drift by a frame (cooldowns), so a
 * replayed remote press is accepted whenever no shell is in flight.
 * Deviations: the bonus shell keeps life 120 (4U 0xc76eb4: 60; GU's life field not located); the prompt is GU's
 * kind-11 (Dragonator switch) prompt.
 * Define STAGE_CANNONS_OFF: no records / no driver (cannon kobjs stay in their rest pose). */
#include <stdint.h>
#include "util.h"
#include "game.h"
#include "em089_pile.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

int stage_alias_active(void);        /* stage.c */
uint32_t stage_setup_serial(void);   /* stage.c */
int stage_demolisher_ready(void *local);           /* stage_demolisher.c */
int stage_demolisher_fire(void *player, int local);
void stage_demolisher_create(void *mgr);
void stage_demolisher_cleanup(void);
void stage_demolisher_shell_gone(void *sh);

#define STAGE_GIMMICK_MGR 0x18977a0u
#define MGR_KOBJ          0x21cu
#define KOBJ_AREA         0x182u
#define KOBJ_STATUS       0x184u
#define KOBJ_ACT          0x185u
#define KOBJ_ID           0x188u
#define ARENA_AREA        2u
typedef void (*kobj_play_t)(void *kobj, uint32_t id, uint32_t a, uint32_t b, uint32_t c);
#define kobj_play FN(kobj_play_t, 0x515328)
typedef void *(*sched_create_t)(void *mgr, uint32_t area, uint32_t slot, uint32_t file_id, uint32_t play, uint32_t z);
#define sched_create FN(sched_create_t, 0x500bb4)
#define S04_FILE_ID       0xc133u     /* stage\m26d\m26a03d\sdl\m26a03d-k01 = converted 4U m19a03d-s04 */
#define S04_SLOT          5u          /* mgr+0x1bc + 4 * slot (0x4fe9c0 uses 1..4), freed by 0x4ff074 */

#define INTER_MGR         0x1889ec0u
typedef uint8_t *(*rec_alloc_t)(void *mgr);
#define rec_alloc FN(rec_alloc_t, 0x31aa6c)
typedef void (*rec_area_t)(void *rec, uint32_t area);
#define rec_area FN(rec_area_t, 0x3191a0)
typedef void (*rec_flag_t)(void *rec, uint32_t v);
#define rec_flag FN(rec_flag_t, 0x3191d8)
typedef void (*rec_reg_t)(void *mgr, void *rec, uint32_t z);
#define rec_register FN(rec_reg_t, 0x31abac)
typedef void (*rec_free_t)(void *mgr, void *rec);
#define rec_free FN(rec_free_t, 0x31aaf4)
#define KIND_SWITCH       11u         /* GU Dragonator switch (0x2ed1c4 case 11 -> 0x503b88, action 143) */

#define SHELL_MGR         0x1892550u
typedef uint8_t *(*param_alloc_t)(uint32_t size, uint32_t align);
#define param_alloc FN(param_alloc_t, 0x4632ec)
typedef void (*shell_post_t)(void *mgr, void *param);
#define shell_post FN(shell_post_t, 0x48c4f0)
#define VT_SETUP_PARAM    0x175f7b0u  /* +8 = vtable (0x2d96c4) */
#define SHELL_PL_COM_009  29u
#define SH_POS            0x40u
#define SH_PITCH          0xfe8u
#define SH_YAW            0xfecu

#define GAME_PTR          0x2126764u
#define SQUEST_PTR        0x188ad90u
#define LR_READY_KIND11   0x2ed448u
#define LR_FIRE_SWITCH    0x2d9514u
/* the other switch action calling the fire (0x120f6d8, from 0x1207e6c: a second player class, presumably the Prowler):
 * same shape as 0x2d9504, r4 = the acting player, then the local check 0x27bcd0 and the tail call of 0x503a5c */
#define LR_FIRE_SWITCH2   0x120f808u
/* isLocal(player) [0x27bcd0]: 1 for this machine's own hunter. The switch actions run for every player on every
 * machine (remote players' actions are replayed), so the fire hook sees other players' presses too. */
typedef int (*is_local_t)(void *player);
#define is_local FN(is_local_t, 0x27bcd0)

/* 4U records (0x5b921c) and shell offsets (0xc77210 / 0xc7726c / 0xc77288) */
static const float k_rec_pos[2][3] = {{2050.0f, 0.0f, 1230.0f}, {-1575.0f, 0.0f, 1230.0f}};
static const uint16_t k_rec_yaw[2] = {49152, 16384};
static const float k_yaw_sin[2] = {-1.0f, 1.0f}, k_yaw_cos[2] = {0.0f, 0.0f};   /* exact for 270 / 90 deg */
#define REC_PITCH   0xee39u           /* -25 deg */
#define BONUS_PITCH 0xd8e4u           /* -55 deg (0xc773c0) */
static const float k_off[2][3] = {{0.0f, 40.0f, 190.0f}, {0.0f, 95.0f, 155.0f}};   /* [bonus] */
#define REC_RADIUS  100.0f
#define REC_HEIGHT  200.0f            /* GU st006 lever records */
/* local match margin over REC_RADIUS (hunter joint 0 vs GU's prompt point): wide, so a prompt shown by a cannon
 * record is always answered as that cannon and never falls through to GU's Dragonator (nothing else of kind 11
 * stands within 500 of the floor cannons; hunter_cannon also needs y < 500, below the Dragonator ledge) */
#define LOCAL_MARGIN 150.0f

static struct {
    uint32_t serial;
    uint8_t inited, enabled, used[2], end51[2];
    int8_t shots[2];
    int32_t use_time[2], word[2];
    uint8_t *rec[2];
    void *shell[4]; uint8_t shell_k[4];
    struct { uint8_t k, bonus, live; int32_t rem0; } pend[4];   /* rem0 = quest countdown at the post */
    uint8_t skip_post;
    uint32_t logs;
} s_c;

static int fps(void)
{
    uint8_t *g = *(uint8_t **)MAIN(GAME_PTR);
    return g ? (int)FIELD(float, g, 56) : 30;
}

static int32_t rem(void)
{
    uint8_t *q = *(uint8_t **)MAIN(SQUEST_PTR);
    return q ? (int32_t)FIELD(uint32_t, q, 0x1c) : 0;
}

static uint8_t *cannon_kobj(uint32_t k)
{
    uint8_t *mgr = *(uint8_t **)MAIN(STAGE_GIMMICK_MGR);
    if (!mgr) return 0;
    for (uint32_t i = 0; i < 24; i++) {
        uint8_t *o = FIELD(uint8_t *, mgr, MGR_KOBJ + 4 * i);
        if (o && o[KOBJ_AREA] == ARENA_AREA && o[KOBJ_ID] == 4 + k) return o;
    }
    return 0;
}

static int kobj_busy(const uint8_t *o) { return o[KOBJ_STATUS] >= 3 && o[KOBJ_STATUS] <= 7; }
static int lowered(uint8_t act) { return act == 52 || act == 54 || act == 255; }

static void play(uint8_t *o, uint32_t k, uint32_t id, const char *why)
{
    if (!o || o[KOBJ_ACT] == id) return;
    kobj_play(o, id, 0, 0, 0);
    if (++s_c.logs <= 80) logf("gogport: stage cannon %u: action %u (%s)", k + 1, id, why);
}

static void *local_hunter(void)
{
    void *root = *(void **)PLAYER_ROOT;
    void *pl = root ? *(void **)((uint8_t *)root + 0x58) : 0;
    return (pl && *(void **)((uint8_t *)pl + 0x498) && *(void **)((uint8_t *)pl + 0x494)) ? pl : 0;
}

/* cannon index (0 / 1) whose record the hunter stands at, -1 if none; LOCAL_MARGIN for the local hunter, wider for a
 * replayed remote press (that hunter's position here is the synced copy) */
static int hunter_cannon(void *pl, float margin)
{
    float p[4];
    if (!pl || !*(void **)((uint8_t *)pl + 0x498) || !*(void **)((uint8_t *)pl + 0x494)) return -1;
    jointPos(pl, 0, p);
    for (int k = 0; k < 2; k++) {
        float dx = p[0] - k_rec_pos[k][0], dz = p[2] - k_rec_pos[k][2];
        if (dx * dx + dz * dz <= (REC_RADIUS + margin) * (REC_RADIUS + margin) && p[1] < 500.0f) return k;
    }
    return -1;
}

static void make_records(void)
{
    void *im = *(void **)MAIN(INTER_MGR);
    if (!im) return;
    for (int k = 0; k < 2; k++) {
        uint8_t *r = rec_alloc(im);
        if (!r) { if (++s_c.logs <= 80) logf("gogport: stage cannon: no free interaction record"); return; }
        FIELD(uint32_t, r, 0x60) = 4;
        rec_area(r, ARENA_AREA);
        FIELD(uint16_t, r, 0x4e) = 0xffff;
        FIELD(uint16_t, r, 0x50) = 0xffff;
        /* in-range test 0x319278 (C): +0x44 = horizontal radius, +0x48 = height (|dy| < h / 2). Swapped until
         * 2026-10-24: the prompt reached 200 while hunter_cannon matched 160, and a press in between fired GU's
         * Dragonator (test 09:49 05:01, user: "the restraint triggers the Dragonator") */
        FIELD(float, r, 0x48) = REC_HEIGHT;
        rec_flag(r, 0);
        FIELD(uint8_t, r, 0x56) = 0;
        FIELD(float, r, 0x44) = REC_RADIUS;
        FIELD(uint32_t, r, 0x64) = KIND_SWITCH;
        FIELD(uint8_t, r, 0x58) = ARENA_AREA;
        for (int i = 0; i < 3; i++) FIELD(float, r, 4 + 4 * i) = k_rec_pos[k][i];
        rec_register(im, r, 0);
        s_c.rec[k] = r;
    }
    logf("gogport: stage cannon: interaction records (kind 11) at (2050, 0, 1230) %x and (-1575, 0, 1230) %x",
         (uint32_t)s_c.rec[0], (uint32_t)s_c.rec[1]);
}

static void free_records(void)
{
    void *im = *(void **)MAIN(INTER_MGR);
    for (int k = 0; k < 2; k++) {
        uint8_t *r = s_c.rec[k];
        if (im && r && FIELD(uint32_t, r, 0x64) == KIND_SWITCH && FIELD(float, r, 4) == k_rec_pos[k][0])
            rec_free(im, r);
        s_c.rec[k] = 0;
    }
}

static void reset(void)
{
    uint32_t serial = stage_setup_serial(), logs = s_c.logs;
    for (uint32_t i = 0; i < sizeof s_c; i++) ((uint8_t *)&s_c)[i] = 0;
    s_c.serial = serial; s_c.logs = logs;
    s_c.word[0] = s_c.word[1] = -1;
}

/* the stage logic's per-frame part (4U 0x6b0ce0 + the 0x6aa2d0 setup), from stage_doors.c's stage_frame hook */
void stage_cannon_tick(void *mgr)
{
#ifdef STAGE_CANNONS_OFF
    (void)mgr;
    return;
#else
    (void)mgr;
    if (s_c.serial != stage_setup_serial()) reset();
    s_c.skip_post = 0;          /* fire (0x503bb0) and its follow-up (0x503a5c) happen inside one player update */
    int f = fps();
    int32_t r = rem();
    if (!s_c.inited) {
        if (r <= 0) return;
        s_c.inited = 1;
        s_c.enabled = 1;                              /* 0x6aa550: em 89 in the quest */
        for (int k = 0; k < 2; k++) { s_c.used[k] = 1; s_c.use_time[k] = r + f * 420; }
        logf("gogport: stage cannon: enabled, both used until %u s of quest time (4U 0x6aa550)", 600u - 420u);
    }
    if (!s_c.rec[0] && !s_c.rec[1] && *(void **)MAIN(INTER_MGR)) make_records();
    for (int i = 0; i < 4; i++)   /* a posted shot whose shell never initialised (90 quest frames: FPS-patch proof) */
        if (s_c.pend[i].live && s_c.pend[i].rem0 - r > 90) {
            s_c.pend[i].live = 0;
            if (s_c.shots[s_c.pend[i].k] > 0) s_c.shots[s_c.pend[i].k]--;
            logf("gogport: stage cannon %u: shot never initialised (pl_com_009 mode 1), dropped", s_c.pend[i].k + 1u);
        }
    for (int k = 0; k < 2; k++) {
        uint8_t *o = cannon_kobj(k);
        if (s_c.used[k] && s_c.use_time[k] - r >= f * 600) {   /* 0x6b0f08: re-arm after 10 min */
            s_c.used[k] = 0;
            if (++s_c.logs <= 80) logf("gogport: stage cannon %u: re-armed", k + 1u);
        }
        if (!o) continue;
        uint8_t act = o[KOBJ_ACT];
        if (act == 51 && !kobj_busy(o)) {             /* 0x1cdc88: end of action 51 */
            if (!s_c.end51[k]) { s_c.end51[k] = 1; s_c.word[k] = r; }
        } else if (act != 51) s_c.end51[k] = 0;
        if (s_c.enabled && !s_c.used[k]) {            /* 0x6b1044 */
            if (lowered(act)) play(o, k, 51, "ready: barrel up 25 deg");
            else if (act == 51 && !kobj_busy(o) && s_c.word[k] >= 0 && s_c.word[k] - r >= f * 180)
                play(o, k, 55, "3 min at 25 deg: up to 55 deg");
        }
    }
#endif
}

static int cannon_ready(int k)
{
    uint8_t *o = cannon_kobj((uint32_t)k);
    return s_c.enabled && !s_c.used[k] && s_c.shots[k] <= 0 && o && !kobj_busy(o) && !lowered(o[KOBJ_ACT]);
}

static void post_shot(void *player, int k, int bonus)
{
    uint8_t *p = param_alloc(20, 16);
    if (!p) return;
    FIELD(uint32_t, p, 0) = MAIN(VT_SETUP_PARAM) + 8;
    FIELD(uint32_t, p, 4) = SHELL_PL_COM_009;
    FIELD(uint32_t, p, 8) = 1;                        /* mode 1 (st008 cannon shot) */
    FIELD(void *, p, 0xc) = player;
    FIELD(uint8_t, p, 0x10) = 0;
    for (int i = 0; i < 4; i++)
        if (!s_c.pend[i].live) { s_c.pend[i].k = (uint8_t)k; s_c.pend[i].bonus = (uint8_t)bonus; s_c.pend[i].live = 1;
                                 s_c.pend[i].rem0 = rem(); break; }
    s_c.shots[k]++;
    shell_post(*(void **)MAIN(SHELL_MGR), p);
}

/* called by stage_gimmick.c's 0x503bb0 (Dragonator fire) hook first: 1 = handled (cannon fired, skip) */
int stage_cannon_fire(uint32_t *regs)
{
#ifdef STAGE_CANNONS_OFF
    (void)regs;
    return 0;
#else
    uint32_t lr = regs[LR] - MAIN_BASE;
    if (lr != LR_FIRE_SWITCH && lr != LR_FIRE_SWITCH2) return 0;
    /* the pressing player (r4 of the switch action), not the local hunter: with the local hunter, another player's
     * cannon press fired the Dragonator here whenever the local hunter stood elsewhere */
    void *player = (void *)(uintptr_t)regs[R4];
    if (!player) player = local_hunter();
    /* the fallen Dragonator spear's record (em089_pile.c, any stage). A replayed remote press is matched after the
     * cannons with a wider radius: each machine lands its own copy of the spear from its own monster position. */
    int local = is_local(player) == 1;
    if (local && em089_pile_fire(player, 0)) { s_c.skip_post = 1; return 1; }
    if (!stage_alias_active()) return !local && em089_pile_fire(player, 1);
    if (stage_demolisher_fire(player, local)) { if (local) s_c.skip_post = 1; return 1; }
    int k = hunter_cannon(player, local ? LOCAL_MARGIN : 300.0f);
    if (k < 0) return !local && em089_pile_fire(player, 1);
    if (local) s_c.skip_post = 1;                   /* 0x503a5c follows only for the local hunter */
    uint8_t *o = cannon_kobj((uint32_t)k);
    int f = fps();
    int32_t r = rem();
    int bonus = s_c.word[k] >= 0 && s_c.word[k] - r >= f * 180;
    /* Online (GU, C): only the machine controlling the monster turns hits into damage, and every machine posts its
     * own shell from the replayed press (as GU's st008 cannon) -> one shell per press per machine, never gated on
     * isLocal. A remote press was already checked by the presser's prompt: here only the shells in flight stop it
     * (this machine's cooldown timers may lag a frame behind, and the controller's shell is the one that counts). */
    int ready = local ? cannon_ready(k) : (s_c.enabled && o != 0);
    if (!ready || s_c.shots[k] > 0) {
        logf("gogport: stage cannon %u: switch pressed but not ready (used %u shots %d act %u)", k + 1u, s_c.used[k],
             s_c.shots[k], o ? o[KOBJ_ACT] : 0u);
        return 1;
    }
    if (o && lowered(o[KOBJ_ACT])) play(o, (uint32_t)k, bonus ? 53 : 51, "fire from rest");
    s_c.used[k] = 1; s_c.use_time[k] = r;            /* 0x6ab7f8 */
    if (bonus) post_shot(player, k, 1);
    s_c.word[k] = -1;
    post_shot(player, k, 0);
    logf("gogport: stage cannon %u: FIRE (%s, %d shell(s), barrel action %u)", k + 1u, bonus ? "bonus 55 deg" : "25 deg",
         bonus ? 2 : 1, o ? o[KOBJ_ACT] : 0u);
    return 1;
#endif
}

/* 0x503b88(mgr) Dragonator ready: the kind-11 interaction check of the player (lr 0x2ed448) at a cannon record */
int stage_cannon_ready_c(uint32_t *regs)
{
#ifdef STAGE_CANNONS_OFF
    (void)regs;
    return 0;
#else
    static uint32_t s_n;
    if (regs[LR] - MAIN_BASE != LR_READY_KIND11) return 0;
    int pr = em089_pile_ready(local_hunter());   /* the fallen Dragonator spear's record (em089_pile.c, any stage) */
    if (pr >= 0) { regs[R0] = (uint32_t)pr; return 1; }
    if (!stage_alias_active()) return 0;
    int dr = stage_demolisher_ready(local_hunter());   /* the Demolisher record at the cart's fire point at S */
    if (dr >= 0) { regs[R0] = (uint32_t)dr; return 1; }
    int k = hunter_cannon(local_hunter(), LOCAL_MARGIN);   /* the prompt check is the local hunter's */
    if (k < 0) return 0;
    regs[R0] = (uint32_t)cannon_ready(k);
    if (++s_n <= 6) logf("gogport: stage cannon %u: prompt check -> %u", k + 1u, regs[R0]);
    return 1;
#endif
}

int stage_dragonator_camera(uint32_t *regs);   /* stage_gimmick.c: 4U m19a03 camera for the alias, 1 = done */

/* 0x503a5c(mgr): Dragonator camera after 0x503bb0 in the switch action (local hunter only): skipped for a cannon,
 * else 4U's Battlequarters camera (stage_gimmick.c) instead of GU's Fortress record */
int stage_dragonator_post_c(uint32_t *regs)
{
    if (!s_c.skip_post) return stage_dragonator_camera(regs);
    s_c.skip_post = 0;
    return 1;
}

/* 0x46365c inside uShellPlcom_009 init, mode 1 (r4 = shell, position and angles set, start call next) */
int stage_cannon_shot_c(uint32_t *regs)
{
    uint8_t *sh = (uint8_t *)(uintptr_t)regs[R4];
    int i;
    for (i = 0; i < 4 && !s_c.pend[i].live; i++) ;
    if (i == 4 || !sh) return 0;
    int k = s_c.pend[i].k, b = s_c.pend[i].bonus;
    s_c.pend[i].live = 0;
    const float *o = k_off[b];
    float x = o[0] * k_yaw_cos[k] + o[2] * k_yaw_sin[k], z = o[2] * k_yaw_cos[k] - o[0] * k_yaw_sin[k];
    FIELD(float, sh, SH_POS) = k_rec_pos[k][0] + x;
    FIELD(float, sh, SH_POS + 4) = k_rec_pos[k][1] + o[1];
    FIELD(float, sh, SH_POS + 8) = k_rec_pos[k][2] + z;
    FIELD(uint32_t, sh, SH_PITCH) = b ? BONUS_PITCH : REC_PITCH;
    FIELD(uint32_t, sh, SH_YAW) = k_rec_yaw[k];
    for (int j = 0; j < 4; j++)
        if (!s_c.shell[j]) { s_c.shell[j] = sh; s_c.shell_k[j] = (uint8_t)k; break; }
    if (++s_c.logs <= 80)
        logf("gogport: stage cannon %u: shell %x start (%d, %d, %d) pitch %x yaw %x%s", k + 1, (uint32_t)sh,
             (int)FIELD(float, sh, SH_POS), (int)FIELD(float, sh, SH_POS + 4), (int)FIELD(float, sh, SH_POS + 8),
             FIELD(uint32_t, sh, SH_PITCH), k_rec_yaw[k], b ? " (bonus)" : "");
    return 0;
}

/* 0x4a18b4(shell): uShell base dtor -> 4U uShell023 end 0xc776a0 for our shells */
int stage_shell_dtor_c(uint32_t *regs)
{
    void *sh = (void *)(uintptr_t)regs[R0];
    int j;
    stage_demolisher_shell_gone(sh);
    for (j = 0; j < 4 && s_c.shell[j] != sh; j++) ;
    if (j == 4 || !sh) return 0;
    int k = s_c.shell_k[j];
    s_c.shell[j] = 0;
    if (s_c.shots[k] > 0) s_c.shots[k]--;
    uint8_t *o = cannon_kobj((uint32_t)k);
    int32_t r = rem();
    if (!o) return 0;
    uint8_t act = o[KOBJ_ACT];
    if ((!s_c.enabled || s_c.used[k]) && s_c.shots[k] <= 0)
        play(o, (uint32_t)k, act == 51 ? 52 : 54, "last shell gone: barrel down");
    else
        s_c.word[k] = act == 51 ? r : r + fps() * 180;
    return 0;
}

/* 0x4fdf7c (stage load, right after 0x4fe9c0 made the k01..k04 schedulers): the second cannon's scheduler */
int stage_kobj_extra_c(uint32_t *regs)
{
    (void)regs;
#ifndef STAGE_CANNONS_OFF
    void *mgr = *(void **)MAIN(STAGE_GIMMICK_MGR);
    if (!mgr || !stage_alias_active()) return 0;
    void *s = sched_create(mgr, ARENA_AREA, S04_SLOT, S04_FILE_ID, 1, 0);
    logf("gogport: stage cannon: s04 scheduler (file %x) -> %x", S04_FILE_ID, (uint32_t)s);
    stage_demolisher_create(mgr);
#endif
    return 0;
}

/* 0x4ff074(mgr): stage manager cleanup (quest end) */
int stage_cleanup_c(uint32_t *regs)
{
    (void)regs;
    em089_pile_cleanup();
    stage_demolisher_cleanup();
    if (s_c.rec[0] || s_c.rec[1]) {
        free_records();
        logf("gogport: stage cannon: interaction records freed (stage cleanup)");
    }
    reset();
    s_c.serial = 0xffffffffu;
    return 0;
}
