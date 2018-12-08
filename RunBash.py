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
import binascii
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
debug = []
#binary = []
prechars = []
chars = []
regex = []
regex.append(re.compile(b"\x1b.*\x07"))
regex.append(re.compile(rb"\x08+\x1b\x5b\x31\x34\x50"))
hist = re.compile(b"(\x08\x08\x08\x08)+")
#bsw = re.compile(b"\x1b\x5b\x4b")
log.append("[" + datetime.datetime.now().strftime("%a %b %d %H:%M:%S.%f %Y") + "] ")
def ChkChar(s):
    flag = True
    for c in s:
        ord_num = ord(c)
        if(ord_num <= 31):
            flag = False
    return flag
    

while p.poll() is None:
    r, w, e = select.select([sys.stdin, master_fd], [], [])
    if sys.stdin in r:
        d = os.read(sys.stdin.fileno(), 10240)
        os.write(master_fd, d)
    elif master_fd in r:
        o = os.read(master_fd, 10240)
        if o:
            os.write(sys.stdout.fileno(), o)
            debug.append(str(binascii.hexlify(o), 'utf-8'))
            outputstr = (o.decode('utf-8'))
            prechars = list(outputstr)
            if ChkChar(outputstr) == True:
                log.append(outputstr)
                continue
            debug.append("".join(prechars))
            if o == b'\x08\x1b\x5b\x4b':
                log.pop()
                continue
            for b in (b"\x1b\x5b\x31\x41\x1b\x5b\x31\x4b\x1b\x5b\x4b",b"\x1b\x5b\x31\x42"):
                o = o.replace(b,b"")
            for reg in regex:
                o = re.sub(reg,b"",o)
            if re.search(hist,o):
                log.pop()
                o = re.sub(hist,b"",o)
            chars = list(o.decode('utf-8'))
            for c in chars:
                ord_num = ord(c)
                if  ord_num == 13:
                    log.append("\n[" + datetime.datetime.now().strftime("%a %b %d %H:%M:%S.%f %Y") + "] ")
                elif ord_num <= 31:
                    pass
                else:
                    log.append(c)

with open(path,mode='w') as f:
    #f.write(re.sub(r'\[\?1034h|\]0;.*\?1034h|\]0;.*:~|\[0m|\[(\d+;)+\d+m',"","".join(log)))
    f.write("".join(log))
## for debug
with open("/Users/tak/work/logs/debug.txt",mode='w') as d:
    d.write("\n".join(debug))
#with open("/Users/tak/work/logs/binary.txt",mode='w') as b:
#    b.write("\n".join(binary))
#restore tty settings back
termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
