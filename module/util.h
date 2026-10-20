/* Freestanding helpers: debug log through svcOutputDebugString (Ryujinx prints it as a Guest log line). */
#pragma once
#include <stdint.h>
#include <stddef.h>

static inline void svc_output_debug_string(const char *s, size_t n)
{
    register const char *r0 __asm__("r0") = s;
    register size_t r1 __asm__("r1") = n;
    __asm__ volatile("svc #0x27" : "+r"(r0), "+r"(r1) : : "memory");
}

/* logf: %x (hex), %u (unsigned), %d, %s, %c; no width/flags. */
void logf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
