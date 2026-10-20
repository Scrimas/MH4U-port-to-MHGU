set architecture arm
set pagination off
target remote localhost:55555
echo \n== module header\n
x/4wx 0x2e19000
echo == g_init_magic g_hook_count\n
x/2wx 0x2e1b038
echo == main hook site 0x73ee90 (expect e51ff004 02e19028)\n
x/2wx 0x73ee90
detach
