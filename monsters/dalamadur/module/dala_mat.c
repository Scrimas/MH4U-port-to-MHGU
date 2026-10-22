/* Head material animations (4U uEm024, both variants; tools/mrl_anim.py header for the GU runtime, C).
 * Spawn (slot 39, 0x76d668..0x76d730): for each material of the model (0x1a4814(this, i), i < this+0xf8) of type 1
 * (= m01, the eyes) work+0x44 = it, animation "breath"; type 2 (= m02, the inner glow) work+0x48 = it, "usually"
 * (0xcfba14(set +0x6c, name) -> index, 0x636b64(obj, slot 0, index)). Per frame 0x7746f0 (state byte work+0x4c):
 * dead (0x94d7a8: category 11 / 14 or 12/255) -> "death" / "usually" (2); enraged (0x954e48) -> "anger" / "anger"
 * (1); else "breath" / "usually" (0); the type-2 material is only switched into or out of state 1. The other
 * materials' animations are never started by the class (the converted MRLs set no autoplay, build_dalamadur_arc.py).
 * GU: material i = 0x890adc(this, i), i < this+0xfc; type = (obj+0x18 >> 22) & 0xff; set obj+0x74; find 0xb0bb0c;
 * play 0xb0cab0 (C, mrl_anim.py). The caller of 0x7746f0 sits outside the head vtable's slots (word 0xe66ce8, S):
 * run from GU slot 119 every frame on every machine (rage and death reach all machines, MP). */
#include "game.h"
#include "util.h"
#include "em090.h"

#define W_MAT1   0x44     /* void *: the type-1 material [4U work+0x44] */
#define W_MAT2   0x48     /* void *: the type-2 material [4U work+0x48] */
#define W_MATST  0x4c     /* u8: state + 1 (0 = never set) [4U work+0x4c] */
#define rageOn   FN(int (*)(void *), 0x8172c)   /* [4U 0x954e48: W+0x530 == 1] (dala_parts.c) */
typedef void *(*matGet_t)(void *self, uint32_t i);
#define matGet   FN(matGet_t, 0x890adc)
typedef int (*animFind_t)(void *set, const char *name);
#define animFind FN(animFind_t, 0xb0bb0c)
typedef void (*animPlay_t)(void *mat, uint32_t slot, uint32_t index);
#define animPlay FN(animPlay_t, 0xb0cab0)

static void play(void *mat, const char *name)
{
    void *set = mat ? FIELD(void *, mat, 0x74) : 0;
    int k = set ? animFind(set, name) : -1;
    static uint32_t s_n;
    if (++s_n <= 30) logf("dalaport: material %x animation %s -> %d", (uint32_t)mat, name, k);
    if (k >= 0) animPlay(mat, 0, (uint32_t)k);
}

void dala_mat_spawn(void *self)
{
    uint32_t n = FIELD(uint32_t, self, 0xfc);
    DALA_WORK(void *, self, W_MAT1) = DALA_WORK(void *, self, W_MAT2) = 0;
    for (uint32_t i = 0; i < n; i++) {
        void *m = matGet(self, i);
        uint32_t type = m ? (FIELD(uint32_t, m, 0x18) >> 22) & 0xff : 0;
        if (type == 1) { DALA_WORK(void *, self, W_MAT1) = m; play(m, "breath"); }
        else if (type == 2) { DALA_WORK(void *, self, W_MAT2) = m; play(m, "usually"); }
    }
    DALA_WORK(uint8_t, self, W_MATST) = 1;
    logf("dalaport: materials %u: type 1 %x, type 2 %x", n, (uint32_t)DALA_WORK(void *, self, W_MAT1),
         (uint32_t)DALA_WORK(void *, self, W_MAT2));
}

void dala_mat_frame(void *self)
{
    void *m1 = DALA_WORK(void *, self, W_MAT1), *m2 = DALA_WORK(void *, self, W_MAT2);
    uint8_t *st = &DALA_WORK(uint8_t, self, W_MATST);
    if (!m1 || !m2 || !*st) return;
    uint32_t cat = FIELD(uint8_t, self, EN_ACT_CAT), old = *st - 1u, s;
    if (cat == 11 || cat == 14 || (cat == 12 && FIELD(uint8_t, self, EN_ACT_NUM) == 255)) s = 2;
    else s = rageOn(self) != 0;
    if (s == old) return;
    play(m1, s == 2 ? "death" : s == 1 ? "anger" : "breath");
    if (s == 1 || old == 1) play(m2, s == 1 ? "anger" : "usually");
    *st = (uint8_t)(s + 1);
}
