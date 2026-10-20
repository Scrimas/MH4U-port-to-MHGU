/* subsdk1 layout: R-X text (crt0 first: rtld reads the MOD0 offset at base+4),
   R-- rodata + dynamic linking tables, RW- data + bss. Linked at 0, relocated by rtld. */
PHDRS
{
    text    PT_LOAD FLAGS(5);
    rodata  PT_LOAD FLAGS(4);
    data    PT_LOAD FLAGS(6);
    dynamic PT_DYNAMIC;
}

SECTIONS
{
    . = 0;
    .text : { KEEP(*(.text.crt0)) *(.text .text.*) } :text

    . = ALIGN(0x1000);
    .rodata  : { *(.rodata .rodata.*) } :rodata
    .dynsym  : { *(.dynsym) } :rodata
    .dynstr  : { *(.dynstr) } :rodata
    .hash    : { *(.hash) } :rodata
    .rel.dyn : { *(.rel.dyn) } :rodata
    .rel.plt : { *(.rel.plt) } :rodata

    . = ALIGN(0x1000);
    .data    : { *(.data .data.*) } :data
    .got     : { *(.got .got.plt) } :data
    .dynamic : { *(.dynamic) } :data :dynamic
    . = ALIGN(8);
    HIDDEN(__bss_start = .);
    .bss (NOLOAD) : {
        *(.bss .bss.*) *(COMMON)
        . = ALIGN(8);
        HIDDEN(__module_object = .);
        . += 0x100;
    } :data
    HIDDEN(__bss_end = .);

    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) *(.note*) *(.interp) }
}
