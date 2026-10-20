import sys, os, collections
sys.path.insert(0,'py')
from arc import arc_entries
want = {0x00e0bb1c:'Link',0x61cf79af:'Group',0x1bbfd18e:'Data',0x26bec21c:'Plus',0x02929600:'Daily'}
for root,_,fs in os.walk('rom'):
    for f in fs:
        p=os.path.join(root,f); d=open(p,'rb').read(0x50*3000)
        if d[:4]!=b'ARC\0': continue
        try: es=arc_entries(open(p,'rb').read())
        except Exception: continue
        for e in es:
            if e[1] in want: print(want[e[1]], p, e[0], e[2], e[3])
