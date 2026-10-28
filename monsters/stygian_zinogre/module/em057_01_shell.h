/* em057_01_shell.h: Stygian Zinogre's shell framework on GU uShellEnemy (em057_01_shell.c), shared by the shell
 * classes (em057_01_shell.c: blast, pillar; em057_01_shell046.c: orb) and the posts (em057_01_posts.c). [4U field]
 * after each GU one; the evidence is in em057_01_shell.c's header. C = confirmed in code, S = strong, G = guess. */
#ifndef EM057_01_SHELL_H
#define EM057_01_SHELL_H

#include "em057_01.h"

/* ---- GU uShellEnemy */
#define DTI_uShellEnemy    ((MtDTI *)MAIN(0x188ee88))
#define VT_uShellEnemy     MAIN(0x175b268)      /* object vtable address point (0x175b260 + 8) */
#define DTIVT_uShellEnemy  MAIN(0x175b3bc)      /* DTI vtable address point (0x175b3b4 + 8) */
#define VT_SLOTS           83
#define SIZE_uShellEnemy   0x15d0u
#define uShellEnemy_ctor   FN(ctor_t, 0x43b3f8)
#define uShellEnemy_dtor   FN(ctor_t, 0x43b488)
typedef int (*shell_setup_t)(void *self, void *param);
#define uShellEnemy_setup  FN(shell_setup_t, 0x43b4bc)
typedef void (*shell_fn_t)(void *self);
#define uShell_move        FN(shell_fn_t, 0x4a2304)
#define uShell_kill        FN(shell_fn_t, 0x4a247c)
typedef void (*shell_res_t)(void *self, void *res);
#define uShell_setResource FN(shell_res_t, 0x4a1c84)
#define uShell_hasHitData  FN(selfInt_t, 0x4a2744)
typedef void *(*file_res_t)(void *unused, uint32_t file_id);
#define fileResource       FN(file_res_t, 0x152960)
typedef void (*unit_add_t)(void *mgr, uint32_t line, void *unit, uint32_t a, uint32_t b);
#define unitAdd            FN(unit_add_t, 0xc067ec)
typedef void (*shell_mgr_add_t)(void *mgr, void *shell);
#define shellMgrAdd        FN(shell_mgr_add_t, 0x48c6c8)
#define SHELL_MGR          (*(uint8_t **)MAIN(0x1892550))
#define UNIT_MGR           (*(void **)MAIN(0x2126f48))
#define DTI_PARAM          ((MtDTI *)MAIN(0x188cb88))   /* cSetupParamEmBase01 */
#define VT_PARAM           MAIN(0x17556a0)
#define SHELL_MAX_LIVE     144
#define SHELL_LIVE_LIST    0x6d8c
enum { SLOT_DEL = 1, SLOT_DTI = 5, SLOT_MOVE = 9, SLOT_KILL = 16, SLOT_SETUP = 79, SLOT_ARM = 80 };
#define SH_STATE    0xc         /* u32 unit state (& 7: 1 / 2 = alive) */
#define SH_DT       28          /* float frames this tick [4U +20] */
#define SH_POS      0x40        /* float[3] [4U +0x100] */
#define SH_ANGLES   0xfe8       /* u32[3] [4U +0x110] */
#define SH_POS2     0x1000      /* bone-1001 capsule end [4U +0x120] */
#define SH_AREA     0x1054      /* u8 area [4U +0x130] */
#define SH_PARAM    0x136c      /* the param the base set-up stored (0x4a2508), owner at +0xc [4U +0x134] */
#define SH_ATK0     0x13a8      /* attack slot 0 [4U +360] */
#define ATK_ACTIVE  0x5         /* u8 [4U +0x16d - 360] */
#define ATK_HIT     0x6         /* u8 255 until the attack connects [4U +0x16e - 360] (slot ctors 0x1685cc / 4U
                                 * 0xb70428 set 255, kills 0x4a247c / 0x9ab16c too; GU's hit code writes it, S) */
#define ATK_F14     0x14        /* float passed to slot 80 */
#define ATK_START   0x5c        /* float start delay, the record's s16 +0 [4U +444 - 360] (arm 0x168ee0 / 4U
                                 * 0xb7014c; counted down by GU 0x169260 / 4U 0xb70024, then the length) */
#define ATK_TIME    0x60        /* float window length, the record's s16 +2 [4U +448 - 360] (arm 0x168ef0 / 4U
                                 * 0xb7015c) */
#define ROW_ID      0xcafc      /* owner u32: GU's shell row for the variant (f00978) */

/* our family shell\em\em057_01_shell01\em057_01_01: def file ID and HDS order (build_em057_01_arc.py
 * SHELL_FILE_ID / SHELL_HDS_NAMES, both asserted there) */
#define SZ_SHELL_FILE  0x108dbu
enum { SZ_HDS_PILLAR = 0, SZ_HDS_BLAST135 = 1, SZ_HDS_BLAST236 = 2, SZ_HDS_ORB = 3 };
/* PEL u list-2 records of our code posts (build_em057_01_arc.py SHELL_FX) */
#define SZ_EFX_BLAST   3222u    /* em049_022, k -1, placed once */
#define SZ_EFX_BURST   3219u    /* em049_019, k -1, placed once */
#define SZ_EFX_GATHER  3220u    /* em049_020, k -1, placed once */
#define SZ_EFX_FLIGHT  3215u    /* em049_015, k 0, follows its unit */
#define SZ_EFX_IMPACT  3217u    /* em049_017, k 0, placed once */
#define SZ_EFX_EXPIRE  3267u    /* em049_017, k 1, placed once */

typedef struct {
    MtDTI dti;
    uint32_t dti_vt[2 + 3];
    uint32_t vt[2 + VT_SLOTS];
    uint32_t size;
    uint8_t registered;
} szcls_t;

/* the class: uShellEnemy's vtable with our slots, our DTI (parent uShellEnemy) */
void sz_cls_register(szcls_t *c, const char *name, uint32_t size, void *(*new_fn)(MtDTI *), void (*del)(void *),
                     MtDTI *(*get_dti)(void *), void (*move)(void *), int (*setup)(void *, void *),
                     void (*kill)(void *));
void *sz_cls_new(szcls_t *c);                   /* alloc + uShellEnemy ctor + our vtable, own fields zeroed */
void sz_cls_free(szcls_t *c, void *self);       /* uShellEnemy dtor + release */
/* the param of GU's request 0x48c4f0 as GU's own slam fills it; 0 when the post is dropped (logged) */
void *sz_shell_param(void *owner, uint32_t kind, const float *pos, uint32_t group, const char *what);
/* resource, slot 79, unit line 18, live list (0x48c4f0's tail); 0 when the set-up failed (the shell is deleted) */
void *sz_shell_start(void *shell, void *param, const char *what);
/* 4U 0x9ab120(shell, records, volumes, record, a, b) + the request group = GU slot 80; 1 = armed */
int sz_shell_arm(void *self, uint32_t hds, uint32_t a, uint32_t b, uint32_t group);
int sz_shell_live(void *self);
/* 4U 0x304d3c(mgr, id, shell, -1, owner, area, -2): a sound that follows the shell (GU 0x4efe58) */
void sz_snd_obj(void *owner, uint32_t id, void *obj);

#endif
