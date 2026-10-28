/* em057_01_shell.c: Stygian Zinogre's shells on GU uShellEnemy (B5, notes/b5-shells.md). The paw slam blast: a
 * literal translation of 4U uShell003 (DTI 0x10bb32c, 696 B, vtable 0xe6d3dc) for the subtypes 135 / 236 that 4U
 * 0x6639a0 posts from the slams 0x84f900 / 0x850164 / 0x8508fc / 0x852968 (em057_01_mv_d.c slam_shell). The dragon
 * pillar: 4U uShell044 subtype 3 and its three frame-table posts (section below).
 * Written from the 4U and GU code, not from Dalamadur's shells (user 2026-10-28, issue #6; notes/b5-shells.md 8).
 * C = read in code, S = strong, G = guess. 4U = MH4U v1.1, GU = MHGU 1.4.
 *
 * 4U uShell003 for 129 / 135 / 235 / 236 (C):
 * - message 3 (0x6639a0 -> 0x661c5c): {owner, 1, subtype, 0, &position, &zero vector, area, hit bits, group, flags
 *   0, scale 1.0, &rotation, ground kind}; ctor 0xc55b10: +0xfd subtype, +0x100 position, +0x110 angles = the zero
 *   vector, +0x130 area, +0x26c hit bits, +0x26e group, +0x270 flags, +0x290 scale, a rotation pointer -> +0x278
 *   and +0xf3 = 1, +0x274 ground kind, +0x29c effect = 0.
 * - init 0xc544d0, default path (0xc54ad4): state +0xf1 = 1, age +316 = 0, capsule end +0x120 = position; attack
 *   0x9ab120(records 0x101f230, volumes 0x101efbc, subtype, 31, 2) (table 0x101ddcc); group +0x26e != 0xffff -> the
 *   slot's group; effect 0xc5540c: request {area +0x130, (58, 27) = em049_022 (table 0x101dfcc, mask -1), flags 256
 *   = no player-area gate, ground kind +0x274, position +0x100, rotation +0x278 (+0xf3 set), scale 1.0 (0x1021a08)}
 *   -> 0xc08628 at the point, handle +0x29c; sound 0xc54f48: table 0x101e7c4 kind 2 id 226 -> 0x312484(mgr, 226,
 *   owner, position, area, -2); 0xc55034: flags 0 -> nothing.
 * - per frame 0xc54b04 (default case): age += dt; state 2 when the attack slot's active byte (+0x16d) is 0 or age >=
 *   200.0 (0xc54e20); 0xc54e44 holds only other subtypes' timed sounds; a dead effect handle is dropped (0xc54dd0).
 * - kill 0xc5598c: base kill, then 0xc470dc(effect): a one-shot effect (mode 0 / 2) is asked to finish (vt+0x70 /
 *   vt+0x7c), only a mode-1 effect is cut (vt+0x40).
 * - records 135 / 236 (build_em057_01_arc.py HDS 1 / 2): window 0 + 10, power 100, type 2, element 0x21; volume 110
 *   (bone 255 r180) / 153 (r200).
 * GU (C unless marked):
 * - uShellEnemy calls and fields: Gogmazios' em089_shell.c / port-checklist.md "GU findings" (DTI 0x188ee88, vtable
 *   0x175b268 83 slots, ctor 0x43b3f8, dtor 0x43b488, slots 1 delete, 5 DTI, 9 move 0x4a2304, 16 kill 0x4a247c, 79
 *   set-up, 80 arm 0x43b51c -> 0x4a2790(this, slot, HDS, -1, 31, 2, group)); the request tail of 0x48c4f0 (resource
 *   0x4a1c84(fileResource(def)), slot 79, unit line 18 0xc067ec, live list 0x48c6c8). Re-read here: the base set-up
 *   0x43b4bc -> 0x4a24f8 takes only the owner (alive), its area and the def's effect lists from the param, so the
 *   class places itself, as GU's own EmBase01 set-up 0x3fb104 does from its param.
 * - GU's own Zinogre slam (f00684 / efd9ac) posts its blast shell at the ground point with param {+4 row this+0xcafc
 *   (247 for v0 / v1), +8 kind 12 / 13, +0xc owner, +0x10 position, +0x30 the monster's angles, +0x3c hit group
 *   rec+0xb0a}: the same param here (kind 12 for 135, 13 for 236 = GU's blast kinds; GU base code reads the row id
 *   only for ids 22 / 26 / 41 / 42 / 48-51 and kind only with ids 22 / 42; our class has no per-kind code).
 * - the effect: a world post at the point through the monster's PEL (sz_efx_world, em057_01_efx.c: 0x53b500 without
 *   the owner attach of 0x6ff74, so no model scale of the monster), 4U's rotation and ground flags as request
 *   overrides; stopped with 0x32a400 mode 0 (asks it to finish) at the kill, as 4U's release.
 * - the end: GU's arm sets the slot's active byte at once (0x168ec0) and its attack-slot update (base slot 11) clears
 *   it at the record's window end (S: the clearing not traced here); a guard ends the shell 2 frames after the window
 *   if it did not, logged (no 4U counterpart: a stuck slot would keep the blast's hit volume for 200 frames).
 * Multiplayer: no net test in 4U's poster or class; every machine runs the slam handler (synced action) and posts its
 * own shell, as GU's own Zinogre slams (C: f00684 has no controller test). */
#include "em057_01_shell.h"
#include "alloc.h"

static void *alloc_dti(MtDTI *dti, uint32_t size)
{
    void *a = get_allocator(dti);
    void *(*alloc)(void *, uint32_t, uint32_t, uint32_t) = (*(void ***)a)[0x20 / 4];
    return alloc(a, size, 16, dti->w[7]);
}

/* ---- the framework (em057_01_shell.h) */
void sz_cls_register(szcls_t *c, const char *name, uint32_t size, void *(*new_fn)(MtDTI *), void (*del)(void *),
                     MtDTI *(*get_dti)(void *), void (*move)(void *), int (*setup)(void *, void *),
                     void (*kill)(void *))
{
    const uint32_t *bv = (const uint32_t *)VT_uShellEnemy, *bd = (const uint32_t *)DTIVT_uShellEnemy;
    for (int i = 0; i < 2 + VT_SLOTS; i++) c->vt[i] = bv[i - 2];
    c->vt[2 + SLOT_DEL] = (uint32_t)del;
    c->vt[2 + SLOT_DTI] = (uint32_t)get_dti;
    c->vt[2 + SLOT_MOVE] = (uint32_t)move;
    c->vt[2 + SLOT_SETUP] = (uint32_t)setup;
    c->vt[2 + SLOT_KILL] = (uint32_t)kill;
    for (int i = 0; i < 2 + 3; i++) c->dti_vt[i] = bd[i - 2];
    c->dti_vt[2 + 2] = (uint32_t)new_fn;
    c->size = size;
    MtDTI_ctor(&c->dti, name, DTI_uShellEnemy, size, 0, 0, 0);
    c->dti.w[0] = (uint32_t)&c->dti_vt[2];
    c->registered = 1;
    logf("szport: %s DTI %x id %x size %x, resource file %x", name, (uint32_t)&c->dti, c->dti.w[7], size,
         SZ_SHELL_FILE);
}

void *sz_cls_new(szcls_t *c)
{
    void *mem = alloc_dti(&c->dti, c->size);
    if (!mem) return 0;
    uShellEnemy_ctor(mem);
    FIELD(uint32_t, mem, 0) = (uint32_t)&c->vt[2];
    for (uint32_t o = SIZE_uShellEnemy; o < c->size; o++) FIELD(uint8_t, mem, o) = 0;
    return mem;
}

void sz_cls_free(szcls_t *c, void *self)
{
    uShellEnemy_dtor(self);
    void *a = get_allocator(&c->dti);
    ((void (*)(void *, void *))(*(void ***)a)[0x34 / 4])(a, self);
}

/* the param of GU's request 0x48c4f0 as GU's own slam fills it (f00978..f00a84); 0 when the post is dropped */
void *sz_shell_param(void *owner, uint32_t kind, const float *pos, uint32_t group, const char *what)
{
    static uint32_t s_fail;
    uint8_t *mgr = SHELL_MGR, *param;
    uint32_t live = 0;
    if (!owner || !mgr) {
        if (++s_fail <= 20) logf("szport: %s post dropped (owner %x shell manager %x)", what, (uint32_t)owner,
                                 (uint32_t)mgr);
        return 0;
    }
    for (int i = 0; i < SHELL_MAX_LIVE; i++) {
        uint8_t *u = FIELD(uint8_t *, mgr, SHELL_LIVE_LIST + 4 * i);
        if (u && (FIELD(uint32_t, u, SH_STATE) & 7) - 1 < 2) live++;
    }
    if (live >= SHELL_MAX_LIVE) {
        if (++s_fail <= 20) logf("szport: %s post dropped: %u live shells", what, live);
        return 0;
    }
    param = alloc_dti(DTI_PARAM, 64);
    if (!param) return 0;
    for (int i = 0; i < 64; i += 4) FIELD(uint32_t, param, i) = 0;
    FIELD(uint32_t, param, 0) = VT_PARAM;
    FIELD(uint32_t, param, 4) = FIELD(uint32_t, owner, ROW_ID);
    FIELD(uint32_t, param, 8) = kind;
    FIELD(void *, param, 0xc) = owner;
    for (int i = 0; i < 3; i++) FIELD(float, param, 0x10 + 4 * i) = pos[i];
    for (int i = 0; i < 3; i++) FIELD(uint32_t, param, 0x30 + 4 * i) = FIELD(uint32_t, owner, SH_ANGLES + 4 * i);
    FIELD(uint16_t, param, 0x3c) = (uint16_t)group;
    return param;
}

/* resource, slot 79, unit line 18, live list (0x48c4f0's tail); on a failed set-up the shell is deleted (its dtor
 * frees the param the base set-up stored) */
void *sz_shell_start(void *shell, void *param, const char *what)
{
    static uint32_t s_fail;
    uShell_setResource(shell, fileResource(0, SZ_SHELL_FILE));
    if (((shell_setup_t)((*(uint32_t **)shell)[SLOT_SETUP]))(shell, param) != 1) {
        if (++s_fail <= 20) logf("szport: %s set-up failed", what);
        VCALL0(shell, SLOT_DEL);
        return 0;
    }
    unitAdd(UNIT_MGR, 18, shell, 0, 0);
    shellMgrAdd(SHELL_MGR, shell);
    return shell;
}

/* 4U 0x9ab120(shell, records, volumes, record, a, b) + the request group = GU slot 80(shell, 0, HDS, -1, a, b, group,
 * slot f14); 1 = armed */
int sz_shell_arm(void *self, uint32_t hds, uint32_t a, uint32_t b, uint32_t group)
{
    typedef void (*arm_t)(void *, uint32_t, int32_t, int32_t, uint32_t, uint32_t, uint32_t, float);
    if (uShell_hasHitData(self) != 1) {
        static uint32_t s_n;
        if (++s_n <= 5) logf("szport: shell %x: no hit data in resource %x (family %x not loaded?)", (uint32_t)self,
                             FIELD(uint32_t, self, 0x1384), SZ_SHELL_FILE);
        return 0;
    }
    ((arm_t)((*(uint32_t **)self)[SLOT_ARM]))(self, 0, (int32_t)hds, -1, a, b, group & 0xffff,
                                               FIELD(float, self, SH_ATK0 + ATK_F14));
    return 1;
}

int sz_shell_live(void *self) { return self && (FIELD(uint32_t, self, SH_STATE) & 7) - 1 < 2; }

typedef void *(*snd_obj_t)(void *mgr, uint32_t id, void *obj, int32_t joint, void *owner, uint32_t area, void *obj2);
#define sndObj    FN(snd_obj_t, 0x4efe58)     /* [0x304d3c(mgr *0xfccd6c, id, obj, -1, owner, area, -2)] */

void sz_snd_obj(void *owner, uint32_t id, void *obj)
{
    void *mgr = *(void **)MAIN(SND_MGR);
    if (mgr && owner && obj) sndObj(mgr, id, obj, -1, owner, FIELD(uint8_t, obj, SH_AREA), obj);
}

/* ================================================================== uShell003 135 / 236: the paw slam blast ====== */

#define B_SUB     (SIZE_uShellEnemy + 0x00)   /* u8 subtype [4U +0xfd] */
#define B_STATE   (SIZE_uShellEnemy + 0x01)   /* u8 0 new, 1 active, 2 done [+0xf1] */
#define B_ARMED   (SIZE_uShellEnemy + 0x02)
#define B_KIND    (SIZE_uShellEnemy + 0x03)   /* u8 ground kind [+0x274] */
#define B_GROUP   (SIZE_uShellEnemy + 0x04)   /* u16 hit group [+0x26e] */
#define B_HITBITS (SIZE_uShellEnemy + 0x06)   /* u8 hit attribute bits 16-19 [+0x26c] (read by other subtypes only) */
#define B_PLACED  (SIZE_uShellEnemy + 0x07)   /* u8 1: the effect's placement was logged */
#define B_SERIAL  (SIZE_uShellEnemy + 0x08)
#define B_AGE     (SIZE_uShellEnemy + 0x0c)   /* float [+316] */
#define B_EFX     (SIZE_uShellEnemy + 0x10)   /* void * [+0x29c] */
#define B_POS     (SIZE_uShellEnemy + 0x14)   /* float[3] request position [+0x100] */
#define B_ROT     (SIZE_uShellEnemy + 0x20)   /* float[3] request rotation, radians [+0x278] */
#define B_SIZE    (SIZE_uShellEnemy + 0x30)
#define B_WINDOW  10.0f                       /* records 135 / 236: start 0 + length 10 */
#define B_AGE_MAX 200.0f                      /* 0xc54e20 */
#define B_LINES   40u

static szcls_t s_blast;
static uint32_t s_blast_serial, s_blast_lines;

static void blast_end(void *self, const char *why)
{
    if (s_blast_lines < B_LINES) {
        s_blast_lines++;
        logf("szport: blast %u end at age %d: %s", FIELD(uint32_t, self, B_SERIAL), (int32_t)FIELD(float, self, B_AGE),
             why);
    }
    FIELD(uint8_t, self, B_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

/* slot 16 = 4U slot 24 0xc5598c: base kill, the effect asked to finish (0xc470dc on a one-shot) */
static void blast_kill(void *self)
{
    void *h = FIELD(void *, self, B_EFX);
    uShell_kill(self);
    if (sz_efx_alive(h)) sz_efx_finish(h);
    FIELD(void *, self, B_EFX) = 0;
}

/* slot 79: base set-up, then 4U init 0xc544d0 (default path) */
static int blast_setup(void *self, void *param)
{
    void *owner;
    float *pos = &FIELD(float, self, B_POS), *rot = &FIELD(float, self, B_ROT);
    uint32_t sub = FIELD(uint8_t, self, B_SUB), kind = FIELD(uint8_t, self, B_KIND), area;
    if (uShellEnemy_setup(self, param) != 1) return 0;
    owner = FIELD(void *, param, 0xc);
    area = FIELD(uint8_t, self, SH_AREA);                   /* the base set-up copied the owner's [4U +0x130] */
    for (int i = 0; i < 3; i++) {
        FIELD(float, self, SH_POS + 4 * i) = pos[i];
        FIELD(float, self, SH_POS2 + 4 * i) = pos[i];      /* +0x120 = +0x100 */
        FIELD(uint32_t, self, SH_ANGLES + 4 * i) = 0;      /* +0x110 = the zero vector */
    }
    FIELD(uint8_t, self, B_STATE) = 1;
    FIELD(float, self, B_AGE) = 0.0f;
    FIELD(uint8_t, self, B_ARMED) = (uint8_t)sz_shell_arm(self, sub == 135 ? SZ_HDS_BLAST135 : SZ_HDS_BLAST236, 31, 2,
                                                       FIELD(uint16_t, self, B_GROUP));
    FIELD(void *, self, B_EFX) = sz_efx_world(owner, SZ_EFX_BLAST, pos, rot, sz_ground_flags(kind));
    sz_snd_at(owner, 226, pos, area);
    if (s_blast_lines < B_LINES) {
        s_blast_lines++;
        logf("szport: blast %u sub %u at %d %d %d rot %d %d %d mrad kind %u group %x area %u hit %u efx %x",
             FIELD(uint32_t, self, B_SERIAL), sub, (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2],
             (int32_t)(rot[0] * 1000.0f), (int32_t)(rot[1] * 1000.0f), (int32_t)(rot[2] * 1000.0f), kind,
             FIELD(uint16_t, self, B_GROUP), area, FIELD(uint8_t, self, B_ARMED),
             (uint32_t)FIELD(void *, self, B_EFX));
    }
    return 1;
}

/* slot 9 = 4U slot 23 0xc54b04 (default case) */
static void blast_move(void *self)
{
    void *h = FIELD(void *, self, B_EFX);
    float *age = &FIELD(float, self, B_AGE), p[3];
    if (h && !sz_efx_alive(h)) FIELD(void *, self, B_EFX) = h = 0;
    uShell_move(self);
    if (!sz_shell_live(self) || FIELD(uint8_t, self, B_STATE) != 1) return;
    if (!FIELD(uint8_t, self, B_PLACED) && *age >= 3.0f && sz_efx_pos(h, p)) {   /* units built after the post */
        const float *q = &FIELD(float, self, B_POS);
        FIELD(uint8_t, self, B_PLACED) = 1;
        if (s_blast_lines < B_LINES) {
            s_blast_lines++;
            logf("szport: blast %u effect placed at %d %d %d (asked %d %d %d)", FIELD(uint32_t, self, B_SERIAL),
                 (int32_t)p[0], (int32_t)p[1], (int32_t)p[2], (int32_t)q[0], (int32_t)q[1], (int32_t)q[2]);
        }
    }
    *age += FIELD(float, self, SH_DT);
    if (FIELD(uint8_t, self, B_ARMED) ? !FIELD(uint8_t, self, SH_ATK0 + ATK_ACTIVE) : *age >= B_WINDOW)
        blast_end(self, FIELD(uint8_t, self, B_ARMED) ? "attack window over" : "window (not armed)");
    else if (*age >= B_AGE_MAX) blast_end(self, "age 200");
    else if (*age >= B_WINDOW + 2.0f) blast_end(self, "guard: attack slot still active after the window");
}

static void *blast_new(MtDTI *dti) { (void)dti; return sz_cls_new(&s_blast); }
static MtDTI *blast_dti(void *self) { (void)self; return &s_blast.dti; }
static void blast_delete(void *self)
{
    void *h = FIELD(void *, self, B_EFX);
    if (sz_efx_alive(h)) sz_efx_finish(h);
    FIELD(void *, self, B_EFX) = 0;
    sz_cls_free(&s_blast, self);
}

/* 4U 0x6639a0(mgr, owner, subtype, pos, [sp] rot, kind, area, group, hit bits) (em057_01.h); site = the 4U call */
void sz_shell003(void *self, uint32_t shell_id, uint32_t site, const float *pos, const float *rot, uint32_t kind,
                 uint32_t area, uint32_t grp, uint32_t sub)
{
    void *param, *shell;
    (void)area;                                             /* the base set-up takes the owner's, the same area */
    if (shell_id != 135 && shell_id != 236) {
        if (s_blast_lines < B_LINES) {
            s_blast_lines++;
            logf("szport: blast subtype %u is not Stygian's (4U %x): dropped", shell_id, site);
        }
        return;
    }
    if (!s_blast.registered)
        sz_cls_register(&s_blast, "uShellEm057_01Blast", B_SIZE, blast_new, blast_delete, blast_dti, blast_move,
                     blast_setup, blast_kill);
    param = sz_shell_param(self, shell_id == 135 ? 12 : 13, pos, grp, "blast");
    if (!param) return;
    shell = sz_cls_new(&s_blast);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return;
    }
    FIELD(uint8_t, shell, B_SUB) = (uint8_t)shell_id;
    FIELD(uint8_t, shell, B_KIND) = (uint8_t)kind;
    FIELD(uint16_t, shell, B_GROUP) = (uint16_t)grp;
    FIELD(uint8_t, shell, B_HITBITS) = (uint8_t)sub;
    for (int i = 0; i < 3; i++) {
        FIELD(float, shell, B_POS + 4 * i) = pos[i];
        FIELD(float, shell, B_ROT + 4 * i) = rot ? rot[i] : 0.0f;
    }
    FIELD(uint32_t, shell, B_SERIAL) = ++s_blast_serial;
    sz_shell_start(shell, param, "blast");
}

/* ================================================================== uShell044 subtype 3: the dragon pillar ====== */
/* 4U uShell044 (DTI 0x10bc1d0, 0x2e0 B, vtable 0xe6e5cc; C unless marked); subtype 3 = Stygian's pillar, 1 =
 * Zinogre's (the same code, other effects and record):
 * - post 0x662904(mgr, owner, sub, &ofs, [sp] &rot, grp, b8, s0 f) -> message 44 -> ctor 0xc8835c: +0xfd subtype, the
 *   owner (0x9ab158), area W+0x14c, +0x26c b8, position +0x100 = ofs + owner +0xe0 (the uCoord world-matrix
 *   translation = the owner's position; base slot 15 0x6d3e5c moves it with mPos), capsule end +0x120 = position,
 *   angles +0x110 = 0, +0x280 = rot, +0x26e grp, +0x2a0 = (0, 100, 0); +0x280 / +0x2a0 and the target fields are
 *   read by other subtypes only.
 * - init 0xc87f10: subtype < 10 and an owner, else done; the gather effect 0xc880ec (table 0x1030260 row 3: (58, 25)
 *   = em049_020, mask -1) posted ON the shell (0xc08698, request +0x5c = shell, +0x18 = the owner's ground kind
 *   0xc09908); a failed post sets state 2, yet the init ends with state 1 (0xc88098); arm 0x9ab120(records 0x10300d0,
 *   volumes 0x10300c8, 3, 7, 2) (table 0x10302b0); grp != 0xffff -> the slot's group; sound 217 on the shell (case
 *   0xc88070); then the first per-frame (tail call 0xc880b4).
 * - per frame 0x9a9a3c: owner gone or leaving (0x917620) -> slot off, state 3; slot inactive (+0x16d == 0) or age +316
 *   >= 400 (table 0x10302c4) -> state 2; gather effect dead -> state 2; case 0x9aa458 (subtypes 1 / 3): capsule end
 *   +0x120 = position + (0, 2000, 0) (volume 1 = bone 1001 r200: a column 2000 high); once (+0xf4), when the slot's
 *   start delay +444 reaches 0 (record 3: start 50, length 10): the burst (58, 24) = em049_019 at the position
 *   (0xc08628, flags 256, ground kind left at the request ctor's 0, 0xc0cad0), the gather effect released
 *   (0xc470dc), sound 218 on the shell; then age += dt (0x9a95c0).
 * - kill 0xc88358 = the base kill 0x9ab16c (state 3, slot off): it does not release the gather effect, which is
 *   attached to the shell (S: it ends with it).
 * Port (GU, C unless marked): this file's framework; HDS 0 (window 50 + 10, power 80, element 0x21, HTS group 0 =
 * bone 1001 r200); GU's own pillar kind 0 in the param (GU's 7/113 post efb884 passes kind and grp 0xffff the same
 * way; our class reads no kind); position = ofs + the monster's position rec+0x40 (the uCoord translation of an
 * unparented unit = its position, S); the effects are world posts at the position (records 3220 / 3219: the pillar
 * never moves, no +0x100 write after the ctor in the subtype-1 / 3 paths): the gather one finished at the burst and at
 * the kill (S above); em049_020's three elements carry ground mask ffffffff, so the owner's ground kind picks nothing
 * and is not passed; em049_019's elements 3 / 4 carry 0x22, kept by the request's kind 0 (flags 3, passed). Sounds 217
 * / 218 follow the shell through GU 0x4efe58, called as GU's own shells call it (0x400e7c). GU's arm keeps its own hit
 * group for grp 0xffff (0x4a2884), as 4U; GU's slot update 0x169260 counts the start delay down, then the length,
 * then clears the active byte, as 4U 0xb70024. A guard ends a pillar whose slot is still active 10 frames after the
 * window (logged; no 4U counterpart).
 * Posts: em057_01_mv_f.c 7/113 115 (4U 0x84dff4) and the frame tables (em057_01_posts.c); every machine posts its
 * own pillars from the replayed action (4U has no controller test at any of the four sites). */

#define P_SUB     (SIZE_uShellEnemy + 0x00)   /* u8 subtype [4U +0xfd] */
#define P_STATE   (SIZE_uShellEnemy + 0x01)   /* u8 0 new, 1 active, 2 done [+0xf1] */
#define P_ARMED   (SIZE_uShellEnemy + 0x02)
#define P_BURST   (SIZE_uShellEnemy + 0x03)   /* u8 bursts done [+0xf4] */
#define P_GROUP   (SIZE_uShellEnemy + 0x04)   /* u16 hit group [+0x26e] */
#define P_SERIAL  (SIZE_uShellEnemy + 0x08)
#define P_SITE    (SIZE_uShellEnemy + 0x0c)   /* u32 the 4U post site (logs) */
#define P_AGE     (SIZE_uShellEnemy + 0x10)   /* float [+316] */
#define P_EFX     (SIZE_uShellEnemy + 0x14)   /* void * the gather effect [+0x27c] */
#define P_POS     (SIZE_uShellEnemy + 0x18)   /* float[3] position [+0x100] */
#define P_SIZE    (SIZE_uShellEnemy + 0x24)
#define P_START   50.0f                       /* record 3 = HDS 0: start 50, length 10 */
#define P_LENGTH  10.0f
#define P_AGE_MAX 400.0f                      /* table 0x10302c4, subtype 3 */
#define P_HEIGHT  2000.0f                     /* the capsule end above the position (0x9aa45c..0x9aa480) */
#define P_LINES   120u

static szcls_t s_pillar;
static uint32_t s_pillar_serial, s_pillar_lines;

static int pillar_line(void)
{
    if (s_pillar_lines >= P_LINES) return 0;
    s_pillar_lines++;
    return 1;
}

static void pillar_end(void *self, const char *why)
{
    if (pillar_line())
        logf("szport: pillar %u end at age %d: %s", FIELD(uint32_t, self, P_SERIAL), (int32_t)FIELD(float, self, P_AGE),
             why);
    FIELD(uint8_t, self, P_STATE) = 2;
    VCALL0(self, SLOT_KILL);
}

/* slot 16 = 4U slot 24 0xc88358 (the base kill); the gather effect ends with the shell it is attached to in 4U (S) */
static void pillar_kill(void *self)
{
    void *h = FIELD(void *, self, P_EFX);
    uShell_kill(self);
    if (sz_efx_alive(h)) sz_efx_finish(h);
    FIELD(void *, self, P_EFX) = 0;
}

/* 4U per frame 0x9a9a3c after its owner test (GU's base move makes that one, as 4U 0x917620) */
static void pillar_frame(void *self)
{
    void *owner = FIELD(void *, FIELD(uint8_t *, self, SH_PARAM), 0xc), *h = FIELD(void *, self, P_EFX);
    float *age = &FIELD(float, self, P_AGE), *pos = &FIELD(float, self, SH_POS);
    uint32_t armed = FIELD(uint8_t, self, P_ARMED);
    if (armed ? !FIELD(uint8_t, self, SH_ATK0 + ATK_ACTIVE) : *age >= P_START + P_LENGTH) {
        pillar_end(self, armed ? "attack window over" : "window (not armed)");
        return;
    }
    if (*age >= P_AGE_MAX) {
        pillar_end(self, "age 400");
        return;
    }
    if (armed && *age >= P_START + P_LENGTH + 10.0f) {
        pillar_end(self, "guard: attack slot still active after the window");
        return;
    }
    if (h && !sz_efx_alive(h)) {
        FIELD(void *, self, P_EFX) = 0;
        pillar_end(self, "gather effect gone");
        return;
    }
    for (int i = 0; i < 3; i++) FIELD(float, self, SH_POS2 + 4 * i) = pos[i] + (i == 1 ? P_HEIGHT : 0.0f);
    if (!FIELD(uint8_t, self, P_BURST) &&
        (armed ? FIELD(float, self, SH_ATK0 + ATK_START) <= 0.0f : *age >= P_START)) {
        void *b = sz_efx_world(owner, SZ_EFX_BURST, pos, 0, sz_ground_flags(0));
        if (h) sz_efx_finish(h);
        FIELD(void *, self, P_EFX) = 0;
        FIELD(uint8_t, self, P_BURST)++;
        sz_snd_obj(owner, 218, self);
        if (pillar_line())
            logf("szport: pillar %u burst at age %d: efx %x", FIELD(uint32_t, self, P_SERIAL), (int32_t)*age,
                 (uint32_t)b);
    }
    *age += FIELD(float, self, SH_DT);
}

/* slot 79: base set-up, then 4U init 0xc87f10 (subtype 3) */
static int pillar_setup(void *self, void *param)
{
    void *owner;
    float *pos = &FIELD(float, self, P_POS);
    if (uShellEnemy_setup(self, param) != 1) return 0;
    owner = FIELD(void *, param, 0xc);
    /* 4U's init ends with a first per-frame call (0xc880b4); before the window its only effects are the capsule end
     * and one dt of age (the age limit 400 is never reached: the window ends at 60), so the capsule end is set here
     * and the frame is left to GU's unit update (the shell's dt is set there, S) */
    for (int i = 0; i < 3; i++) {
        FIELD(float, self, SH_POS + 4 * i) = pos[i];
        FIELD(float, self, SH_POS2 + 4 * i) = pos[i] + (i == 1 ? P_HEIGHT : 0.0f);
        FIELD(uint32_t, self, SH_ANGLES + 4 * i) = 0;      /* +0x110 = 0 */
    }
    FIELD(void *, self, P_EFX) = sz_efx_world(owner, SZ_EFX_GATHER, pos, 0, 0);
    FIELD(uint8_t, self, P_ARMED) = (uint8_t)sz_shell_arm(self, SZ_HDS_PILLAR, 7, 2, FIELD(uint16_t, self, P_GROUP));
    FIELD(float, self, P_AGE) = 0.0f;
    sz_snd_obj(owner, 217, self);
    FIELD(uint8_t, self, P_STATE) = 1;                     /* 0xc88098, also after a failed effect post */
    if (pillar_line())
        logf("szport: pillar %u sub %u at %d %d %d (4U %x) area %u hit %u efx %x", FIELD(uint32_t, self, P_SERIAL),
             FIELD(uint8_t, self, P_SUB), (int32_t)pos[0], (int32_t)pos[1], (int32_t)pos[2],
             FIELD(uint32_t, self, P_SITE), FIELD(uint8_t, self, SH_AREA), FIELD(uint8_t, self, P_ARMED),
             (uint32_t)FIELD(void *, self, P_EFX));
    return 1;
}

/* slot 9 = 4U slot 23 */
static void pillar_move(void *self)
{
    uShell_move(self);
    if (sz_shell_live(self) && FIELD(uint8_t, self, P_STATE) == 1) pillar_frame(self);
}

static void *pillar_new(MtDTI *dti) { (void)dti; return sz_cls_new(&s_pillar); }
static MtDTI *pillar_dti(void *self) { (void)self; return &s_pillar.dti; }
static void pillar_delete(void *self)
{
    void *h = FIELD(void *, self, P_EFX);
    if (sz_efx_alive(h)) sz_efx_finish(h);
    FIELD(void *, self, P_EFX) = 0;
    sz_cls_free(&s_pillar, self);
}

/* 4U 0x662904(mgr *0xef3cf0, owner, subtype, ofs, [sp] rot, [sp+4] grp, [sp+8] b8, s0 f) (em057_01.h); rot, b8 and f
 * are read by other subtypes only (+0x280, +0x26c, +0x2c0) */
void sz_shell044(void *self, uint32_t subtype, const float *ofs, const uint32_t *rot, uint32_t grp, uint32_t b8,
                 float f, uint32_t site)
{
    uint8_t *rec = REC(self);
    float pos[3];
    void *param, *shell;
    (void)rot;
    (void)b8;
    (void)f;
    if (subtype != 3) {
        if (pillar_line()) logf("szport: pillar subtype %u is not Stygian's (4U %x): dropped", subtype, site);
        return;
    }
    if (!s_pillar.registered)
        sz_cls_register(&s_pillar, "uShellEm057_01Pillar", P_SIZE, pillar_new, pillar_delete, pillar_dti, pillar_move,
                     pillar_setup, pillar_kill);
    for (int i = 0; i < 3; i++) pos[i] = ofs[i] + RF(rec, REC_POS_X + 4 * i);
    param = sz_shell_param(self, 0, pos, grp, "pillar");
    if (!param) return;
    shell = sz_cls_new(&s_pillar);
    if (!shell) {
        ((void (*)(void *))((*(uint32_t **)param)[1]))(param);
        return;
    }
    FIELD(uint8_t, shell, P_SUB) = (uint8_t)subtype;
    FIELD(uint16_t, shell, P_GROUP) = (uint16_t)grp;
    FIELD(uint32_t, shell, P_SITE) = site;
    for (int i = 0; i < 3; i++) FIELD(float, shell, P_POS + 4 * i) = pos[i];
    FIELD(uint32_t, shell, P_SERIAL) = ++s_pillar_serial;
    sz_shell_start(shell, param, "pillar");
}
