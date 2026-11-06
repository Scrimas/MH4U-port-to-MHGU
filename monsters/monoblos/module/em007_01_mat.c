/* em007_01_mat.c: Monoblos, his look: which mesh groups are drawn, and the rage material.
 *
 * Mesh groups (C, 0.4.6; user's screenshot 2026-11-06: red eye and pink veins from the start of the fight, in 0.4.5 too). Every
 * group starts drawn (0xba258) and only a monster's own code switches them. GU's uEm007_00 does that in slot 132 0xd39fc8, whose
 * first test leaves variants other than 0 and 4 at once, so for him (variant 1) nothing ever switched the breaks, and his parts
 * states named no eye. That left the frenzy look (groups 50 red eye, 51 pink veins: 4U rows show them only under cond 10, S)
 * on top of his amber eye (2), the horn stump (3) inside the horn, and the tail stump (4) with the tail. States from his 4U
 * rows (tools/build_em007_01_arc.py PART_STATES), applied here every frame:
 *   eyes: rec+0x5d02 -> closed, else open: GU's own rule (0x6f5a4, which runs behind a flag of the enemy manager: repeated here
 *   so that the frenzy look can never stay on); 102 / 3: part 6 rank >= 2; 103 (5 has no mesh): part 0 rank >= 1;
 *   101 / 4: tail severed (cond 1, W+0x42c = rec+0x3b4).
 * Rank = 0x9d428 [4U 0x94741c], as dalamadur dala_parts.c. Hook on slot 132's entry: it runs when GU's would for his Diablos,
 * every frame on every machine (0xae858, 0xaf2c4; what it reads is the state GU keeps in sync for its own monsters).
 *
 * His rage material: port of 4U uEm101's material code (C, literal). The material 'XfBA1__m02_angry' (type 2) lies on his face
 * and only shows in rage: 'Normal' alpha 0, 'Angry_Start' alpha 0 -> 1 in 60 frames, 'Angry_End' back in 60. It samples the
 * dark red part of his texture, not the pink one (tools: its UV range), so 0.4.5's reading of the pink glow was wrong.
 *
 * Spawn, 4U slot 39 0x8d9930..0x8d99ac: finds the type-2 material and the three names (table in that order). Per frame,
 * 4U slot 50 0x8e06cc (state byte class work+8, timer class work+80):
 *   rage: state 2 -> 3, plays 'Angry_Start'
 *   no rage: state 3 -> 4, timer 60, plays 'Angry_End'; state 4: at the timer's end -> 2;
 *            any other state (spawn, 2): at the timer's end -> 2, plays 'Normal'
 * GU: helpers as monsters/dalamadur/module/dala_mat.c (material = 0x890adc(this, i), i < this+0xfc; type = (obj+0x18 >>
 * 22) & 0xff; set obj+0x74; find 0xb0bb0c; play 0xb0cab0, which clears the frame, as 4U's store to obj+76 after its
 * play). The material is looked up per play and not kept, so a monster built later at the same address cannot leave a
 * stale pointer. Runs on every machine (rage reaches all of them, as Dalamadur's): every frame from em007_01_moves_run. */
#include "em007_01.h"
#include "alloc.h"

enum { R0, R1, R2, R3, R4, R5, R12, LR };

#define partRank FN(uint32_t (*)(void *, uint32_t), 0x9d428)    /* [4U 0x94741c] */
#define XFS_EYES_CLOSED 1   /* tools/build_em007_01_arc.py PART_STATES */
#define XFS_EYES_OPEN   2
#define XFS_HORN 5          /* + 1 = broken */
#define XFS_BACK 7
#define XFS_TAIL 9

/* hook on GU's slot 132 entry; 0 = GU's function runs on (for variant 1 it returns at its first test) */
int em007_01_parts_c(uint32_t *regs)
{
    void *self = (void *)regs[R0];
    struct mb_state *st;
    uint32_t horn, back, tail, bits;
    if (FIELD(uint16_t, self, EN_ID) != MONOBLOS_EM_ID) return 0;
    horn = partRank(self, 6) >= 2;
    back = partRank(self, 0) >= 1;
    tail = (FIELD(uint16_t, REC(self), REC_FLAGS) & 1) != 0;
    applyPartsState(self, FIELD(uint8_t, REC(self), 0x5d02) ? XFS_EYES_CLOSED : XFS_EYES_OPEN);
    applyPartsState(self, XFS_HORN + (int32_t)horn);
    applyPartsState(self, XFS_BACK + (int32_t)back);
    applyPartsState(self, XFS_TAIL + (int32_t)tail);
    st = mb_state(self);
    bits = horn | back << 1 | tail << 2;
    if (st->parts != bits + 1) {
        st->parts = (uint8_t)(bits + 1);
        logf("mbport: parts horn broken %u back broken %u tail cut %u (ranks part 6 %u, part 0 %u)", horn, back, tail,
             partRank(self, 6), partRank(self, 0));
    }
    return 0;
}

#define rageOn   FN(int (*)(void *), 0x8172c)   /* [4U 0x954e48: W+0x530 == 1] (dala_mat.c) */
typedef void *(*matGet_t)(void *self, uint32_t i);
#define matGet   FN(matGet_t, 0x890adc)
typedef int (*animFind_t)(void *set, const char *name);
#define animFind FN(animFind_t, 0xb0bb0c)
typedef void (*animPlay_t)(void *mat, uint32_t slot, uint32_t index);
#define animPlay FN(animPlay_t, 0xb0cab0)

#define ANGRY_TYPE 2                            /* 'XfBA1__m02_angry': the 'mNN' of the name, MRL w6 bits 21-28 */
#define ST_IDLE    2                            /* 4U's state numbers */
#define ST_RAGE    3
#define ST_FADE    4

static void play(void *self, const char *name)
{
    uint32_t n = FIELD(uint32_t, self, 0xfc);
    for (uint32_t i = 0; i < n; i++) {
        void *m = matGet(self, i);
        void *set;
        int k;
        if (!m || ((FIELD(uint32_t, m, 0x18) >> 22) & 0xff) != ANGRY_TYPE) continue;
        set = FIELD(void *, m, 0x74);
        k = set ? animFind(set, name) : -1;
        logf("mbport: rage veins %s -> %d", name, k);
        if (k >= 0) animPlay(m, 0, (uint32_t)k);
    }
}

void mb_angry_frame(void *self)
{
    struct mb_state *st = mb_state(self);
    if (rageOn(self)) {
        if (st->angry == ST_IDLE) {
            st->angry = ST_RAGE;
            play(self, "Angry_Start");
        }
    } else if (st->angry == ST_RAGE) {
        st->angry = ST_FADE;
        st->angry_t = 60.0f;
        play(self, "Angry_End");
    } else if (timerDown(self, &st->angry_t, 1.0f)) {
        if (st->angry != ST_IDLE) play(self, "Normal");     /* 4U restarts it every frame in state 2: the same alpha */
        st->angry = ST_IDLE;
    }
}
