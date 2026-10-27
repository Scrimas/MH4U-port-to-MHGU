/* icons.c: the ported monsters' icons, a third atlas after GU's HD_cmn_micon00 / 01 (tools/ui_icons.py,
 * notes/data.md "HUD icon").
 *
 * GU's setter 0x56ef50(ui, obj, kind, index, ids) binds texture ids[index / 98] (the caller's {micon00, micon01}
 * .gui texture IDs) only for index < 196, then sets the cell rect index % 98 (0x560918 kind 3, no bound). Hook
 * icon_set: for index 196 + k it lets GU skip the bind and set cell k's rect, and points the sprite at a copy of this
 * .gui's micon01 texture entry (same UVs) whose rTexture is our atlas (sResource load, cached): sprite +0x100 = a
 * texture ID no .gui uses (hook tex_entry resolves it to the copy). GU's next 0xa4faf0 bind replaces it, except a
 * rebind of the .gui's micon IDs outside the setter (hook tex_bind). Our atlas missing: cell 146 instead (empty in
 * GU's atlases).
 *
 * Quest board: GU's mapper 0x3a3178(_, byte) gives 0 (no icon) for bytes > 186; hook board_icon maps bytes from
 * BOARD_FIRST to our cells. The board loop 0x6132d0 shows the hyper badge for bytes >= 142 (0x613318), so hook
 * board_byte hands it byte 0 and the mapper call right after it our byte. */
#include <stdint.h>
#include "game.h"
#include "util.h"

enum { R0, R1, R2, R3 };

#define ICON_PAGE2    196u          /* tools/alloc.py ICON_PAGE2 */
#define ICON_CELLS    49u           /* tools/ui_icons.py CELLS */
#define ICON_FALLBACK 146u          /* micon01 cell 48: empty in GU's atlases */
#define BOARD_FIRST   200u          /* tools/alloc.py BOARD_FIRST */
#define OUR_TEX_ID    0x4d480000u   /* sprite +0x100 while it shows our atlas: | its entry copy's pool index */
#define OWN_MAX       32u
#define RES_MGR       0x2126a64     /* sResource (behind GOT 0x1839450) */
#define DTI_RTEXTURE  0x21255d0     /* rTexture (GOT 0x183f6e0), as the .gui loader 0xb808a4 asks for it */
#define POOL          16u

typedef void *(*res_get_t)(void *mgr, void *dti, const char *path, uint32_t mode);
#define gui_tex_entry FN(uint8_t *(*)(void *, uint32_t), 0xb80fd0)   /* (sprite +0x78, id) -> 64-byte entry */

static const struct { uint32_t w, h; const char *path; } s_atlas[] = {
    { 512, 512, "mh4uport\\micon_sd" },      /* GU's micon01 size */
    { 1024, 1024, "mh4uport\\micon_hd" },    /* HD UI v4's */
};
static void *s_tex[2];
static uint8_t s_tried[2];
static uint8_t s_pool[POOL][64];            /* entry copies: kept for good, sprites point at them */
static uint32_t s_pool_n;
static uint8_t s_board;

/* our atlas of micon01's size (rTexture +0xdc / +0xe0), loaded on first use; 0 until its GPU texture exists */
static void *atlas(const uint8_t *micon)
{
    uint32_t w = FIELD(uint32_t, micon, 0xdc), h = FIELD(uint32_t, micon, 0xe0);
    for (uint32_t k = 0; k < 2; k++) {
        if (s_atlas[k].w != w || s_atlas[k].h != h) continue;
        if (!s_tried[k]) {
            s_tried[k] = 1;
            void *mgr = *(void **)MAIN(RES_MGR);
            res_get_t get = (*(res_get_t **)mgr)[0x30 / 4];
            s_tex[k] = get(mgr, (void *)MAIN(DTI_RTEXTURE), s_atlas[k].path, 1);
            logf("mh4uport: icon atlas %s -> %x", s_atlas[k].path, (uint32_t)(uintptr_t)s_tex[k]);
        }
        uint8_t *t = s_tex[k];
        return t && FIELD(uint32_t, t, 0xdc) == w && FIELD(uint32_t, t, 0xe0) == h && FIELD(void *, t, 0xd0) ? t : 0;
    }
    static uint8_t s_logged;
    if (!s_logged++) logf("mh4uport: no icon atlas for a %ux%u micon01", w, h);
    return 0;
}

/* a copy of entry e drawing texture t; one per entry layout (flags +4, rect +8..+0xe: what the draw path reads
 * besides +0x28), refreshed from the latest .gui so its other words stay current */
static uint8_t *entry_copy(const uint8_t *e, void *t)
{
    uint32_t k = 0;
    for (; k < s_pool_n; k++) {
        uint32_t i = 4;
        while (i < 16 && s_pool[k][i] == e[i]) i++;
        if (i == 16) break;
    }
    if (k == POOL) return 0;
    if (k == s_pool_n) s_pool_n++;
    for (uint32_t i = 0; i < 64; i++) s_pool[k][i] = e[i];
    FIELD(void *, s_pool[k], 0x28) = t;
    return s_pool[k];
}

/* the sprites showing our atlas and the .gui's micon IDs they replaced: a later bind of one of those IDs that is not
 * the setter's (it drops the sprite first) is kept off, see tex_bind_c */
static struct { uint8_t *spr; void *tab; uint32_t id[2]; } s_own[OWN_MAX];
static uint32_t s_own_next;

static int ours(uint32_t id) { return (id & ~0xffu) == OUR_TEX_ID && (id & 0xffu) < s_pool_n; }

static int own_find(const uint8_t *spr)
{
    for (uint32_t k = 0; k < OWN_MAX; k++)
        if (s_own[k].spr == spr) return (int)k;
    return -1;
}

/* sprite (obj, kind) of a .gui, looked up as 0x546f48 does */
static uint8_t *sprite(uint32_t ui, uint32_t obj, uint32_t kind)
{
    uint8_t *gui = FIELD(uint8_t *, ui, 0x24);
    uint32_t n = FIELD(uint32_t, gui, 0x298);
    uint8_t **list = obj < n ? FIELD(uint8_t **, gui, 0xf8) : FIELD(uint8_t **, gui, 0x294);
    if (obj >= n) obj -= n;
    uint8_t **kinds = FIELD(uint8_t **, list[obj], 0xd8);
    return kinds ? kinds[kind] : 0;
}

/* hook 0x56ef58 (setter after its push: r0 ui, r1 obj, r2 kind, r3 index; 5th argument above the frame) */
int icon_set_c(uint32_t *regs)
{
    uint32_t i = regs[R3];
    if (i >= ICON_PAGE2 + ICON_CELLS) return 0;
    uint8_t *spr = sprite(regs[R0], regs[R1], regs[R2]);
    int o = spr ? own_find(spr) : -1;
    if (i < ICON_PAGE2) {                     /* GU's own icon: its bind goes through */
        if (o >= 0) s_own[o].spr = 0;
        return 0;
    }
    const uint32_t *ids = (const uint32_t *)regs[8 + 10];    /* saved r0-r5, r12, lr; then 24 + 16 bytes of frame */
    uint8_t *e = spr && FIELD(void *, spr, 0x78) ? gui_tex_entry(FIELD(void *, spr, 0x78), ids[1]) : 0;
    void *t = e && FIELD(void *, e, 0x28) ? atlas(FIELD(uint8_t *, e, 0x28)) : 0;
    uint8_t *c = t ? entry_copy(e, t) : 0;
    if (!c) {
        static uint32_t s_n;
        if (++s_n <= 10) logf("mh4uport: icon %u: no atlas (sprite %x entry %x), cell %u", i,
                              (uint32_t)(uintptr_t)spr, (uint32_t)(uintptr_t)e, ICON_FALLBACK);
        regs[R3] = ICON_FALLBACK;
        return 0;
    }
    FIELD(uint32_t, spr, 0x100) = OUR_TEX_ID | (uint32_t)((c - s_pool[0]) / 64);
    FIELD(uint8_t *, spr, 0x104) = c;
    if (o < 0) {
        o = (int)(s_own_next++ % OWN_MAX);
        s_own[o].spr = spr;
    }
    s_own[o].tab = FIELD(void *, spr, 0x78);
    s_own[o].id[0] = ids[0];
    s_own[o].id[1] = ids[1];
    return 0;
}

/* hook 0xa4faf0 (sprite, texture ID): GU's bind. The quest board rebinds the micon01 ID after the setter (user
 * 2026-10-27: Tigerstripe's board icon = micon01 cell 2, Tidal Najarala), so a sprite of ours keeps our atlas
 * against its .gui's micon IDs; any other ID (or another .gui) goes through */
int tex_bind_c(uint32_t *regs)
{
    uint8_t *spr = (uint8_t *)(uintptr_t)regs[R0];
    uint32_t id = regs[R1];
    if (!ours(FIELD(uint32_t, spr, 0x100)) || ours(id)) return 0;
    int o = own_find(spr);
    if (o < 0 || s_own[o].tab != FIELD(void *, spr, 0x78) || (id != s_own[o].id[0] && id != s_own[o].id[1]))
        return 0;
    static uint32_t s_n;
    if (++s_n <= 20) logf("mh4uport: icon sprite %x: rebind of micon ID %x kept off", (uint32_t)(uintptr_t)spr, id);
    return 1;
}

/* hook 0xb80fd0 (.gui table, texture ID) -> 64-byte entry: our IDs (sprite +0x100) name their entry copy, as GU's
 * readers of +0x100 (0x547e5c) expect an entry for it */
int tex_entry_c(uint32_t *regs)
{
    if (!ours(regs[R1])) return 0;
    regs[R0] = (uint32_t)(uintptr_t)s_pool[regs[R1] & 0xffu];
    return 1;
}

/* hook 0x3a3178 (_, byte) -> UI index + 1, 0 = none */
int board_icon_c(uint32_t *regs)
{
    uint32_t b = regs[R1];
    if (s_board && b == 0) b = s_board;
    s_board = 0;
    if (b < BOARD_FIRST || b > 0xff) return 0;
    regs[R0] = b - BOARD_FIRST + ICON_PAGE2 + 1;
    return 1;
}

/* hook 0x6132e0 (board loop: uxtb r7, r1; mov r1, r7; bl 0x3a3178): r7 >= 142 shows the hyper badge */
int board_byte_c(uint32_t *regs)
{
    if ((regs[R1] & 0xff) < BOARD_FIRST) return 0;
    s_board = regs[R1] & 0xff;
    regs[R1] = 0;
    return 0;
}
