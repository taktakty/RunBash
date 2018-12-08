#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import select
import termios
import tty
import pty
import re
import datetime
from subprocess import Popen

command = 'bash'
# command = 'docker run -it --rm centos /bin/bash'.split()

# save original tty setting then set it to raw mode
old_tty = termios.tcgetattr(sys.stdin)
tty.setraw(sys.stdin.fileno())

# open pseudo-terminal to interact with subprocess
master_fd, slave_fd = pty.openpty()

# use os.setsid() make it run in a new process group, or bash job control will not be enabled
p = Popen(command,
          preexec_fn=os.setsid,
          stdin=slave_fd,
          stdout=slave_fd,
          stderr=slave_fd,
          universal_newlines=True)
path = '/Users/tak/work/logs/' + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_TeamKujira.txt"
log = []
## for debug
#bytelog = []
#debug = []
#pops = []
#chars = []
log.append("[" + datetime.datetime.now().strftime("%a %b %d %H:%M:%S.%f %Y") + "] ")
while p.poll() is None:
    r, w, e = select.select([sys.stdin, master_fd], [], [])
    if sys.stdin in r:
        d = os.read(sys.stdin.fileno(), 10240)
        os.write(master_fd, d)
    elif master_fd in r:
        o = os.read(master_fd, 10240)
        if o:
            os.write(sys.stdout.fileno(), o)
            if o == b'\x08\x1b\x5b\x4b':
                log.pop()
                continue
            chars = list(o.decode('utf-8'))
            if len(chars) == 1:
                flag = True
            else:
                flag = False
            for c in chars:
                ord_num = ord(c)
                if  ord_num == 13:
                    log.append("\n[" + datetime.datetime.now().strftime("%a %b %d %H:%M:%S.%f %Y") + "] ")
                elif ord_num <= 31:
                    pass
                else:
                    log.append(c)

with open(path,mode='w') as f:
    f.write(re.sub(r'\[\?1034h|\]0;.*\?1034h|\]0;.*:~|\[0m|\[(\d+;)+\d+m',"","".join(log)))
## for debug
#with open("/Users/tak/work/logs/debug.txt",mode='w') as d:
#    d.write(",".join(debug))
#with open("/Users/tak/work/logs/pops.txt",mode='w') as p:
#    p.write(",".join(pops))
# restore tty settings back
termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
