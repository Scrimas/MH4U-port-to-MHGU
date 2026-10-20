#include <stdarg.h>
#include "util.h"

static char *put_u(char *p, char *end, uint32_t v, unsigned base)
{
    char tmp[12]; int n = 0;
    do { tmp[n++] = "0123456789abcdef"[v % base]; v /= base; } while (v);
    while (n && p < end) *p++ = tmp[--n];
    return p;
}

void logf(const char *fmt, ...)
{
    char buf[256], *p = buf, *end = buf + sizeof buf - 1;
    va_list ap;
    va_start(ap, fmt);
    for (; *fmt && p < end; fmt++) {
        if (*fmt != '%') { *p++ = *fmt; continue; }
        switch (*++fmt) {
        case 'x': p = put_u(p, end, va_arg(ap, uint32_t), 16); break;
        case 'u': p = put_u(p, end, va_arg(ap, uint32_t), 10); break;
        case 'd': { int32_t v = va_arg(ap, int32_t);
                    if (v < 0 && p < end) { *p++ = '-'; v = -v; }
                    p = put_u(p, end, (uint32_t)v, 10); break; }
        case 's': { const char *s = va_arg(ap, const char *);
                    while (*s && p < end) *p++ = *s++; break; }
        case 'c': *p++ = (char)va_arg(ap, int); break;
        case '%': *p++ = '%'; break;
        default: if (!*fmt) fmt--; break;
        }
    }
    va_end(ap);
    svc_output_debug_string(buf, (size_t)(p - buf));
}
