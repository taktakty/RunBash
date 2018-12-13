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
from argparse import ArgumentParser

def EnOption():
    argparser = ArgumentParser()
    argparser.add_argument('-t', '--timestamp', action='store_true',
                           help='Adding timestamp to head of each line.')
    argparser.add_argument('-f', '--filename', type=str,
                           help='Specify name of logfile.')
    argparser.add_argument('-s', '--shell', type=str,
                           help='Specify a shell you want to run./n(Default is bash).')
    return argparser.parse_args()

args = EnOption()

def MkLogdir():
    cdir = os.path.dirname(os.path.abspath(__file__))
    logdir = os.path.join(cdir,"./logs/")
    if not os.path.isdir(logdir) == True:
        os.makedirs(logdir)
    return logdir

logdir = MkLogdir()

def SetFilepath(filename=None):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if not filename == None:
        logname = filename
    else:
        logname = "bash.txt"
    return os.path.join(logdir,now + "_" + logname)

path = SetFilepath(args.filename)

def SelectShell(shell):
    if not shell == None:
        command = shell
    else:
        command = "bash"
    return command

command = SelectShell(args.shell)

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
log = []
blog = []
if args.timestamp == True:
    now = "[" + datetime.datetime.now().strftime("%a %b %d %H:%M:%S.%f %Y") + "] "
    log.append(now)
    blog.append(now.encode("utf-8"))
debug = []
pops = []
prechars = []
chars = []
regpattern = [
    rb"\x1b.*\x07", #Bell when prompt displayed
    rb"\x08+\x1b\x5b\x31\x34\x50",  #continuous BS
    rb"\x1B\[[0-?]*[ -/]*[@-~]", #ansi_escape
]
regex = []
for reg in regpattern:
    regex.append(re.compile(reg))
reps = [
    b"\x1b\x5b\x3f\x31\x30\x33\x34\x68",    #[?1034h
    b"\x1b\x5b\x31\x41\x1b\x5b\x31\x4b\x1b\x5b\x4b\x0d",
    b"\x1b\x5b\x31\x42",
    b"\x1b\x5b\x4b",
    b"\x1b\x5b\x30\x6d",
    b"\x1b\x5b\x39\x31\x6d"
]
#regex.append(re.compile(rb"\x1b\x5b([0-9A-Fa-f]+\x3b)+[0-9A-Fa-f]+\x6d"))
#regex.append(re.compile(rb"\x1b\x5b[0-9A-Fa-f]+\x50"))
hist = re.compile(rb"\x08(\x08)+")
histback = re.compile(rb"\x0d(\x1b\x5b\x43)+")
def ChkChar(s):
    flag = True
    for c in s:
        ord_num = ord(c)
        if(ord_num <= 31):
            flag = False
    return flag

def DelCtlCode(output):
    o = output
    for reg in regex:
        o = re.sub(reg,b"",o)
    for b in reps:
        o = o.replace(b,b"")
    return o

def Chktail(tail):
    if not re.match(rb"\x1b",tail):
        return True
    else:
        return False

with open(logdir + "raw.txt",mode='w') as raw:
    while p.poll() is None:
        r, w, e = select.select([sys.stdin, master_fd], [], [])
        if sys.stdin in r:
            d = os.read(sys.stdin.fileno(),10000000)
            os.write(master_fd, d)
        elif master_fd in r:
            o = os.read(master_fd,10000000)
            if o:
                os.write(sys.stdout.fileno(), o)
                debug.append(str(binascii.hexlify(o), 'utf-8'))
                outputstr = (o.decode('utf-8'))
                raw.write(outputstr)
                prechars = list(outputstr)
                #if ChkChar(outputstr) == True:
                #    log.append(outputstr)
                #    continue
                debug.append("".join(prechars))
                if not re.search(hist,o) == None:
                    log.pop()
                    if Chktail(blog[-1]) == True:
                        lastkey = blog.pop()
                        debug.append("before last key:" + lastkey.decode("utf-8"))
                        num = o.count(b"\x08") * -1
                        lastkey = lastkey.decode("utf-8")[:num]
                        debug.append("after last key:" + lastkey)
                        blog.append(lastkey.encode("utf-8"))
                    o = re.sub(hist,b"",o)
                    blog.append(o)
                    log.append(o.decode('utf-8'))
                    continue
                if not re.search(histback,o) ==None:
                    log.pop()
                    if Chktail(blog[-1]) == True:
                        blog.pop()
                    o = re.sub(histback,b"",o)
                    blog.append(o)
                    log.append(o.decode('utf-8'))
                    continue
                if o == b'\x08\x1b\x5b\x4b':
                    log.pop()
                    continue
                if args.timestamp == True:
                    now = "[" + datetime.datetime.now().strftime("%a %b %d %H:%M:%S.%f %Y") + "] "
                    o = o.replace(b"\x0d\x0a",b"\x0a" + now.encode("utf-8"))
                else:
                    o = o.replace(b"\x0d\x0a",b"\x0a")
                o = o.replace(b"\x0d",b"\x0a")
                blog.append(o)
                o = DelCtlCode(o)
                chars = list(o.decode('utf-8'))
                for c in chars:
                    ord_num = ord(c)
                    if  ord_num == 13:
                        if args.timestamp == True:
                            log.append("\n[" + datetime.datetime.now().strftime("%a %b %d %H:%M:%S.%f %Y") + "] ")
                        else:
                            log.append("\n")
                    elif ord_num <= 31:
                        pass
                    else:
                        log.append(c)

blogtxt = b"".join(blog)
blogtxt = DelCtlCode(blogtxt)
strblog = blogtxt.decode("utf-8")
with open(logdir + "blog.txt",mode='w') as b:
    b.write(strblog)
with open(path,mode='w') as f:
    f.write(re.sub(r'\[(\d+;)+\d+m',"","".join(log)))
    #f.write("".join(log))
## for debug
with open(logdir + "debug.txt",mode='w') as d:
    d.write("\n".join(debug))
#with open("/Users/tak/work/logs/binary.txt",mode='w') as b:
#    b.write("\n".join(binary))
#restore tty settings back
termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
