/* em089 sound effects played from CODE (everything else plays from data: the converted 4U sound call
 * "sound\call\em\em089" = manifest field 12 keys requests to motion frames, and the engine's generic reactions
 * use the standard request IDs of the converted request = field 13). Evidence: notes/port-checklist.md
 * "Sound + BGM (sound agent)".
 *
 * Every 4U em089 / uShell050 site that queues a sound goes through one of three 4U sSoundControl calls; GU has the
 * same three (same queue, same request slot 0 of the owner's sound component, same area check; the GU shells and
 * monsters call them exactly like 4U did):
 *   4U 0x2fcc50(mgr, id, owner, joint, area, -2)      -> GU 0x4efd74   type 8, at an owner joint
 *   4U 0x304d3c(mgr, id, obj, -1, owner, area, -2)    -> GU 0x4efe58   type 11, follows an object (a shell)
 *   4U 0x312484(mgr, id, owner, pos, area, -2)        -> GU 0x4efb98   type 8, at a fixed position
 * plus the move of a playing request (uShell016's beam sounds):
 *   4U 0x301074(mgr, id, owner, owner, pos)           -> GU 0x4eff24   owner's sound object (4U +0xd90, GU +0x111c)
 *     -> queue command 6 sub 0 (4U 0xbcaecc -> 0xbc78a4, GU 0xbf0a84 -> 0xbf07c4) with the position (C; GU shells
 *     call it the same way, e.g. 0x3fde7c)
 * mgr = 4U *0xfccd6c = GU *(main + 0x1896f5c); area = the unit's area byte (GU unit +0x1054, 4U W+0x14c / shell
 * +0x130); the request = owner's request slot 0 (GU owner+0x111c+0x170 = manifest field 13). */
#pragma once
#include <stdint.h>

/* raw calls (id = request ID of em089's request) */
void em089_snd_joint(void *owner, uint32_t id, uint32_t joint);
void em089_snd_obj(void *owner, uint32_t id, void *obj, uint32_t area);
void em089_snd_pos(void *owner, uint32_t id, const float *pos, uint32_t area);
void em089_snd_move(void *owner, uint32_t id, const float *pos);

/* 4U em089 sites */
/* 0x8c352c (per-frame tar helper of slot 40): chest Liquid timer work+0xd4 past 210 -> id 203 at joint 2
 * (bank group 20 key 3 = em089_se_oil_flow) */
void em089_snd_tar_chest(void *self);
/* slot 64 0x8c67c0, tail part first break (after the 4U effect shell 138): id 0 at joint 143 (as 4U passes it;
 * request 0 is the empty entry of the bank's group 0 = em089_blank) */
void em089_snd_tail_break(void *self);

/* 4U uShell050 (em089 tar blob) sites; kind = blob kind 0..9, area = the shell's area byte (GU shell +0x1054) */
/* slot 22 init 0xc8e938 (table 0x1031784): kinds 2-5 -> id 215 following the shell (em089_se_oil_appear) */
void em089_snd_shell_spawn(void *shell, void *owner, uint32_t kind, uint32_t area);
/* slot 23 0xc8f1dc -> 0xc8f580 (table 0x1031734 + 160): map impact at pos -> kinds 0,1,6-9 id 216 (drips),
 * kinds 2-5 id 217 (shots), positional, the same for ground and wall */
void em089_snd_shell_land(void *shell, void *owner, uint32_t kind, const float *pos, uint32_t area);
/* CORRECTION (2026-10-18): the code at 0xc8fda4 / 0xc90048 is NOT uShell050 slots 50/51. The uShell050 vtable
 * 0xe6e86c holds two 28-slot tables; its slots 50/51/52/57 = slots 22/23/24/29 of the NEXT class, uShell051 (the
 * generic ground splash that uShell050 posts on a ground impact, subtype = 4U 0xc8f200 table: blob kinds 0,2,4 -> 1,
 * 1,3,5 -> 6, 6 -> 16, 7 -> 17, 8 -> 19, 9 -> 20). uShell051 init 0xc8fda4: table 0x1031bfc[subtype] = id -1 for
 * subtypes 0, 1, 6, 16, 17, 19, 20 (so no init sound for any em089 splash; 207/208 belong to other subtypes);
 * subtypes 6, 17, 19, 20 arm shell+652 = 58.0; uShell051 per frame 0xc90048: subtypes 6/17/19/20, timer counted down
 * by dt while >= 0 (0x9aad4c), at <= 0 -> id 220 at shell+0xe0 (position), timer -1.
 * em089_snd_splash = that behaviour without the splash object (not ported): call it at the ground impact with the
 * subtype and the impact point; it plays the init sound (table, faithful though empty for em089) and queues 220
 * 58 frames later. The queue is advanced by em089_snd_tick(owner, dt), which the monster's per-frame update must
 * call (em089.c owner). Deviation: 4U plays 220 only if the splash still lives at frame 58 (its lifetime is not
 * ported). */
void em089_snd_splash(void *owner, uint32_t subtype, const float *pos, uint32_t area);
void em089_snd_tick(void *owner, float dt);
