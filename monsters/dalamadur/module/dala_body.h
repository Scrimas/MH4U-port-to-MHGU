/* dala_body.c: Dalamadur's hurt / push volumes (bodydata, manifest field 30) in GU, both halves. */
#pragma once
#include <stdint.h>

/* per frame, both halves (call it at the end of dala_parts_frame, GU slot 130): checks the sHit shape cache of
 * this half against the shapes rebuilt from the current joint matrices and logs part-damage changes (read only) */
void dala_body_frame(void *self);
