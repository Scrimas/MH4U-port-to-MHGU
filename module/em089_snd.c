/* em089_snd.c: code-triggered sound effects (see em089_snd.h for the 4U -> GU mapping and evidence). */
#include <stdint.h>
#include "game.h"
#include "util.h"
#include "em089_snd.h"

/* GU sSoundControl (main offsets): the singleton the shells / monsters pass as r0, read through GOT 0x1838be0 */
#define SND_MGR_PTR   0x1896f5cu
#define UNIT_AREA     0x1054u          /* u8 unit area (GU callers: ldrb [this, #0x1054]) */

typedef void *(*snd_joint_t)(void *mgr, uint32_t id, void *owner, uint32_t joint, uint32_t area, int32_t m2);
typedef void *(*snd_obj_t)(void *mgr, uint32_t id, void *obj, int32_t joint, void *owner, uint32_t area, void *obj2);
typedef void *(*snd_pos_t)(void *mgr, uint32_t id, void *owner, const float *pos, uint32_t area, int32_t m2);
#define snd_req_joint FN(snd_joint_t, 0x4efd74)   /* = 4U 0x2fcc50 */
#define snd_req_obj   FN(snd_obj_t, 0x4efe58)     /* = 4U 0x304d3c */
#define snd_req_pos   FN(snd_pos_t, 0x4efb98)     /* = 4U 0x312484 */
typedef void (*snd_move_t)(void *mgr, uint32_t id, void *owner, void *owner2, const float *pos);
#define snd_req_move  FN(snd_move_t, 0x4eff24)    /* = 4U 0x301074 */

static void *mgr(void) { return *(void **)MAIN(SND_MGR_PTR); }

static void note(const char *what, uint32_t id, uint32_t a)
{
    static uint32_t s_n;
    if (++s_n <= 40) logf("gogport: em089 snd %s id %u (%u)", what, id, a);
}

void em089_snd_joint(void *owner, uint32_t id, uint32_t joint)
{
    void *m = mgr();
    if (!m || !owner) return;
    snd_req_joint(m, id, owner, joint, FIELD(uint8_t, owner, UNIT_AREA), -2);
    note("joint", id, joint);
}

void em089_snd_obj(void *owner, uint32_t id, void *obj, uint32_t area)
{
    void *m = mgr();
    if (!m || !owner || !obj) return;
    snd_req_obj(m, id, obj, -1, owner, area & 0xff, obj);
    note("obj", id, area);
}

void em089_snd_pos(void *owner, uint32_t id, const float *pos, uint32_t area)
{
    void *m = mgr();
    if (!m || !owner || !pos) return;
    snd_req_pos(m, id, owner, pos, area & 0xff, -2);
    note("pos", id, area);
}

/* no note: called every frame */
void em089_snd_move(void *owner, uint32_t id, const float *pos)
{
    void *m = mgr();
    if (!m || !owner || !pos) return;
    snd_req_move(m, id, owner, owner, pos);
}

void em089_snd_tar_chest(void *self) { em089_snd_joint(self, 203, 2); }
void em089_snd_tail_break(void *self) { em089_snd_joint(self, 0, 143); }

void em089_snd_shell_spawn(void *shell, void *owner, uint32_t kind, uint32_t area)
{
    if (kind >= 2 && kind <= 5) em089_snd_obj(owner, 215, shell, area);
}

void em089_snd_shell_land(void *shell, void *owner, uint32_t kind, const float *pos, uint32_t area)
{
    (void)shell;
    if (kind > 9) return;
    em089_snd_pos(owner, (kind >= 2 && kind <= 5) ? 217 : 216, pos, area);
}

/* uShell051 init sound table 0x1031bfc (type 2 entries; -1 = none), subtypes 0..20 */
static const int16_t k_splash_id[21] = {-1, -1, 207, 207, 208, 208, -1, 207, 208, 207, 207, 207, 207, 207, 207, 207,
                                        -1, -1, 208, -1, -1};

/* delayed splash sounds (uShell051 shell+652 timer), advanced by em089_snd_tick */
#define SND_QUEUE 16
static struct { void *owner; float t, pos[3]; uint32_t area; } s_q[SND_QUEUE];

void em089_snd_splash(void *owner, uint32_t subtype, const float *pos, uint32_t area)
{
    if (!owner || !pos || subtype > 20) return;
    int id = k_splash_id[subtype];
    if (id >= 0) {
        /* 0xc8ff70 jump table: subtypes 2,3,7,9..15 -> 0x304d3c(207) following the splash (no splash object in
         * the port: positional at the same point), 4,5,8,18 -> 0x312484(table id) at the splash position */
        em089_snd_pos(owner, (uint32_t)id, pos, area);
    }
    if (subtype == 6 || subtype == 17 || subtype == 19 || subtype == 20) {   /* 0xc8fe38: shell+652 = 58.0 */
        for (int i = 0; i < SND_QUEUE; i++) {
            if (s_q[i].owner) continue;
            s_q[i].owner = owner; s_q[i].t = 58.0f; s_q[i].area = area;
            s_q[i].pos[0] = pos[0]; s_q[i].pos[1] = pos[1]; s_q[i].pos[2] = pos[2];
            return;
        }
        note("splash queue full", 220, subtype);
    }
}

void em089_snd_tick(void *owner, float dt)
{
    for (int i = 0; i < SND_QUEUE; i++) {
        if (s_q[i].owner != owner) continue;
        s_q[i].t -= dt;                              /* 4U 0x9aad4c: count down, fire at <= 0 */
        if (s_q[i].t > 0.0f) continue;
        s_q[i].owner = 0;
        em089_snd_pos(owner, 220, s_q[i].pos, s_q[i].area);
    }
}
