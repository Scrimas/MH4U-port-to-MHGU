/* dala_shell.h: Dalamadur's attack shells (goal D5) as GU uShellEnemy subclasses, and the small framework they share
 * (dala_shell.c). Own copies of the GU calls (the package stays independent of Gogmazios' em089_shell*.c, which
 * found them; evidence there and in dala_meteor.c). C = read in code, S = strong, G = guess.
 *
 * 4U shell types posted by the classes uEm024 (head, 0x76c700..0x776290) and uEm083 (tail, 0x89fab8..0x8a3160) and by
 * their shells (scan of every bl into the shell manager 0x660000..0x664000, C):
 *   head 0x76dda8 -> 0x66242c type 29 (meteor, dala_meteor.c)
 *   head 0x772714 (in 0x77250c) -> 0x661bec type 1 uShell001 kinds 24 / 25 / 88 / 89 (fireball, dala_shell001.c)
 *   head 0x7711f8 / 0x775e70 -> 0x6620c4 type 16 uShell016 subtypes 21 / 39 (mouth beam, dala_shell016.c)
 *   tail 0x8a064c (7.0) -> 0x661d18 type 5 uShell005 subtype 4 (tremor column, dala_shell005.c)
 *   uShell029 0xc7d540.. -> 0x663220 -> 0x661c5c type 3 uShell003 113 / 126 / 160 / 162 (meteor blast) and 0x6626e8
 *   type 38 uShell038 (meteor scale, dala_shell038.c); uShell001 impacts -> uShell003 114 / 161 or 0x661ea0 type 9
 *   uShell009 1 / 2, which posts uShell003 112 / 159 (dala_shell003.c).
 * The tail range's other posts (0x89e4b4..0x89f984) belong to uEm081 (its ctor at 0x89fa2c stores vtable
 * 0xe69e28, C). Multiplayer: no W+0x1d9 (net owner) test in either class range except 0x77543c (Shah effect
 * reset 0x7753f4, not a shell site) and none in the shell classes (C); 4U's shell manager 0x660e88 creates the
 * shell locally (0x660fe0 unit add, no net send, as dala_meteor.c found). GU replays each action on every machine,
 * so every machine posts its own shells, as 4U. */
#pragma once
#include <stdint.h>
#include "game.h"

/* Dalamadur's shell family shell\em\em090_00_shell00\em090_00_00 (build_dalamadur_arc.py shell_family: a copy of
 * Kushala's family 00 with HDS / HTS from the 4U inline records). Def file ID = em090_00's extra 'shell00' (the
 * build asserts it); row id param+4 = 175 as Kushala's and Gogmazios' family. */
#define DALA_SHELL_FILE 0x107a6u
#define DALA_SHELL_ID   175u

/* HDS entries of the family (build_dalamadur_arc.py SHELL_HDS; 4U record in brackets; byte-identical 4U records
 * fold onto one entry, the build checks it) */
enum {
    DALA_HDS_METEOR = 0,     /* 0..5 = uShell029 records 0x102dff0 + 40 i; kinds 0..7 use u32 table 0x102e0e0 */
    DALA_HDS_S001_HI = 6,    /* uShell001 record 64 (kind 24; kind 89's record 82 is identical) */
    DALA_HDS_S001_LO = 7,    /* record 62 (kind 25; kind 88's 81 is identical) */
    DALA_HDS_S003_112 = 8,   /* uShell003 records = subtype: 112 (= 159) */
    DALA_HDS_S003_113 = 9,   /* 113 (= 160) */
    DALA_HDS_S003_114 = 10,  /* 114 (= 161) */
    DALA_HDS_S003_126 = 11,  /* 126 (= 162) */
    DALA_HDS_S016_14 = 12,   /* uShell016 record 14 (subtype 21; 39's record 34 is identical) */
    DALA_HDS_S016_18 = 13,   /* record 18 (21 from owner frame 380; 39's 35 is identical) */
    DALA_HDS_S005_4 = 14,    /* uShell005 record 4 */
};

/* ---- GU uShellEnemy (main offsets / fields; evidence in Gogmazios' em089_shell.c and dala_meteor.c) ---- */
#define VT_uShellEnemy_SLOTS 83
#define SIZE_uShellEnemy     0x15d0u
#define SH_STATE             0xc      /* u32 unit state (& 7: 1 / 2 = alive) */
#define SH_DT                28       /* float time scale [4U +20] */
#define SH_POS               0x40     /* float x, y, z [4U +0x100] */
#define SH_ANGLES            0xfe8    /* u32 x, y, z [4U +0x110 / +0x114 / +0x118] */
#define SH_POS2              0x1000   /* bone-1001 capsule second point [4U +0x120] (GU 0x16e46c) */
#define SH_AREA              0x1054   /* u8 area [4U +0x130] */
#define SH_PARAM             0x136c   /* param object, owner at +0xc */
#define SH_ATK0              0x13a8   /* attack slot 0 [4U +360] */
#define ATK_ACTIVE           0x5      /* u8 slot active [4U +0x16d - 360] */
#define ATK_F14              0x14     /* float passed to slot 80 */
#define ATK_GROUP            0x34     /* u16 hit group: global serial at arming, GU 0x168ed0 / 4U 0xb70134 (C) */
#define ATK_TIME             0x60     /* float window length from the record's s16 +2 [4U slot +88] (C) */
#define DALA_SH_FIELDS       SIZE_uShellEnemy   /* first byte of a class's own fields */

typedef struct {
    MtDTI dti;
    uint32_t dti_vt[2 + 3];
    uint32_t vt[2 + VT_uShellEnemy_SLOTS];
    uint32_t size;
    uint8_t registered;
} dala_shcls_t;

/* class set-up: copies uShellEnemy's vtable, puts the given slots (0 = keep the base), registers the DTI */
void dala_shell_register(dala_shcls_t *c, const char *name, uint32_t size, void *(*new_fn)(MtDTI *),
                         void (*del)(void *), MtDTI *(*get_dti)(void *), void (*move)(void *),
                         int (*setup)(void *, void *), void (*kill)(void *));
void *dala_shell_new(dala_shcls_t *c);              /* alloc + uShellEnemy ctor + our vtable, own fields zeroed */
void dala_shell_free(dala_shcls_t *c, void *self);  /* uShellEnemy dtor + release (slot 1) */
/* our copy of the GU request 0x48c4f0 (em089_shell.c): live-shell bound, the 64-B param (row DALA_SHELL_ID, entry
 * 0, owner and its record fields); 0 when the post is dropped (logged under `what`) */
void *dala_shell_param(void *owner, const char *what);
void dala_shell_param_free(void *param);
/* resource DALA_SHELL_FILE, slot 79 set-up, unit line 18, shell manager; on failure the shell is deleted (slot 1)
 * and 0 returned */
void *dala_shell_start(void *shell, void *param, const char *what);
/* 4U 0x9ab120(shell, records, volumes, record, a, b) = GU slot 80(shell, 0, HDS entry, -1, a, b, group, f14); 4U
 * then writes a request group unless 0xffff, GU takes it as the group argument. 1 = armed */
int dala_shell_arm(void *self, uint32_t hds, uint32_t a, uint32_t b, uint32_t group);
void dala_shell_slots_off(void *self);              /* 4U +0x16e = 255, +0x16d = 0 (0x4a247c's attack slots 0..2) */
void *dala_shell_owner(void *self);
int dala_shell_live(void *self);                    /* unit state 1 / 2 */
int dala_shell_timer(void *self, float *t);         /* 4U 0x9aad4c: t -= dt, 1 once <= 0 (clamped) */
float dala_shell_dt(void *self);                    /* 4U frames this tick = the shell's +28 (user's 4U footage) */
uint32_t dala_shell_group(void *self);              /* 4U this+0x19c = slot 0 +0x34 */
float dala_shell_owner_step(void *owner);           /* 4U 0x94460c: owner +668 (motion speed) * dt */
int dala_listener_pos(float *out);                  /* the local hunter (4U 0xaf79a4 +0xe30 + 16 stand-in) */

/* sounds (ids = the 4U request ids of the owner's request, as em090_act7.c) */
void dala_snd_pos(void *owner, uint32_t id, const float *pos, uint32_t area);     /* 4U 0x312484 = GU 0x4efb98 */
void dala_snd_obj(void *owner, uint32_t id, void *obj, uint32_t area);            /* 4U 0x304d3c = GU 0x4efe58 */
void dala_snd_move(void *owner, uint32_t id, const float *pos);                   /* 4U 0x301074 = GU 0x4eff24 */
/* 4U 0x304c34(mgr, id, owner, joint, area, -2): the joint's position now (0xb054ac, else W+0x198), then a type-8
 * request there (0x312100), i.e. a point sound at the joint (C) -> GU jointPos + 0x4efb98 */
void dala_snd_joint_pos(void *owner, uint32_t id, uint32_t joint, uint32_t area);
/* 4U 0xbfd568(mgr *0x105729c, id, &pos) when the shell's area is the local player's (0xc4f188, C) = GU
 * 0x49eac(owner, id, pos, 0) with that test (Gogmazios' em089_shell016.c pairing of 0xbfe98c, S) */
void dala_cam_shake_pos(void *owner, uint32_t id, const float *pos, uint32_t area);

/* ---- the shells (one file each) ---- */
/* dala_shell001.c: 4U 0x77250c(this, kind, lim, ang, flag) = the head's aim (joint 5 toward target slot 0, clamped)
 * + 0x773e00's spawn data + the post; and the fireball itself (uShell001 kinds 24 / 25 / 88 / 89) */
void dala_head_fireball(void *self, uint32_t kind, uint32_t lim, uint32_t ang, uint32_t flag);
void *dala_shell001_post(void *owner, uint32_t kind, const float *pos, uint32_t pitch, uint32_t yaw);
/* dala_shell003.c: 4U 0x663220 (uShell003 blast: subtypes 112..114 / 126 / 159..162) and 0x661ea0 (uShell009
 * burn sequence: subtypes 1 / 2) */
void *dala_shell003_post(void *owner, uint32_t subtype, const float *pos, uint32_t area, uint32_t group);
void *dala_shell009_post(void *owner, uint32_t subtype, const float *pos, uint32_t area, uint32_t group,
                         const uint32_t *angles);
/* dala_shell016.c: 4U 0x6620c4 with {joint 5, (0, -273, 751), x 0xe39, y 0}, subtype 21 / Shah 39, length 12000 */
void *dala_shell016_post(void *owner, uint32_t subtype, uint32_t joint, const float *off, uint32_t xang,
                         uint32_t yang, float length);
/* dala_shell005.c: 4U 0x661d18(mgr, owner, &pos, subtype, 0xffff, scale) (tail 7.0: subtype 4) */
void *dala_shell005_post(void *owner, uint32_t subtype, const float *pos, float scale);
/* dala_shell038.c: 4U 0x6626e8(mgr, owner, kind 0 / Shah 1, area, &pos, yaw, ground byte): the meteor scale and its
 * mining point (the ground byte = the kobj the meteor hit: not passed, see the file) */
void *dala_shell038_post(void *owner, uint32_t kind, const float *pos, uint32_t area, uint32_t yaw);
