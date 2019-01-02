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

def MkLogdir():
    cdir = os.path.dirname(os.path.abspath(__file__))
    logdir = os.path.join(cdir,"./logs/")
    if not os.path.isdir(logdir) == True:
        os.makedirs(logdir)
    return logdir

def SetFilepath(filename=None):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if not filename == None:
        logname = filename
    else:
        logname = "bash.txt"
    return os.path.join(logdir,now + "_" + logname)

def SelectShell(shell):
    if not shell == None:
        command = shell
    else:
        command = "bash"
    return command

def ChkChar(s):
    flag = True
    for c in s:
        ord_num = ord(c)
        if(ord_num <= 31):
            flag = False
    return flag

def Chktail(tail):
    if not re.match(regex[0],tail) or not re.match(regex_reps[0],tail):
        return True
    else:
        return False

def DelCtlCode(output):
    o = output
    for reg in regex:
        o = re.sub(reg,b"",o)
    for b in reps:
        o = o.replace(b,b"")
    return o

def DelDispValue(output):
    o = output
    #for reg in regex_read:
    #    o = re.sub(reg,b"",o)
    for regexd in regex_disp:
        o = re.sub(regexd,b"",o)
    return o

## parameters
blog = []
debug = []
pops = []
prechars = []
chars = []
regpattern = [
    rb"\x1b\x5d[^(\x07)]*\x07", #Bell when prompt displayed
    rb"\x08+\x1b\x5b\x31\x34\x50",  #continuous BS
    rb"(\x9b|\x1B\[)[0-?]*[ -/]*[@-~]", #ansi_escape
    rb"\x08*", #history BS
    rb"\x1b(\x3d|\x3e)",    # zsh prompt 
    rb"(\x1b\x5b\x43)+",    # histback
    rb"(\x1b\x5b\x4b)+",    # ^[[K
]
regex = []
reps = [
    rb"\x1b\x5b\x3f\x31\x30\x33\x34\x68",    #[?1034h
    rb"\x1b\x5b\x31\x41\x1b\x5b\x31\x4b\x1b\x5b\x4b\x0d",
    rb"\x1b\x5b\x31\x42",
    rb"\x1b\x5b\x4b",
    rb"\x1b\x5b\x30\x6d",
    rb"\x1b\x5b\x39\x31\x6d"
    rb"\x07"
    rb"\x0d"
]
regex_reps = []
reps_disp = [
    rb"\x20\x0d",    # auto CR
    rb"\x1b\x5b\x31\x6d\x1b\x5b\x37\x6d\x25\x1b\x5b\x32\x37\x6d\x1b\x5b\x31\x6d\x1b\x5b\x30\x6d(\x20)+", # zsh prompt %
]
regex_disp = []
hist = [
    re.compile(rb"(\x08)+"),
    re.compile(rb"\x1b\x5b\x4b"),
    re.compile(rb"\x1b\x5b(\x30|\x31|\x32|\x33|\x34|\x35|\x36|\x37|\x38|\x39)*\x50"),
]
histback = re.compile(rb"\x0d(\x1b\x5b\x43)+")
crlf = re.compile(rb"\x0d\x0a")
hlf = re.compile(rb"^(\x0d|\x0a)")
sig = re.compile(rb".\x20\x0d")
## MainProccess
args = EnOption()
logdir = MkLogdir()
path = SetFilepath(args.filename)
command = SelectShell(args.shell)

if args.timestamp == True:
    now = "[" + datetime.datetime.now().strftime("%a %b %d %H:%M:%S.%f %Y") + "] "
    blog.append(now.encode("utf-8"))
for reg in regpattern:
    regex.append(re.compile(reg))
for rep in reps:
    regex_reps.append(re.compile(rep))
for regd in reps_disp:
    regex_disp.append(re.compile(regd))
# save original tty setting then set it to raw mode
old_tty = termios.tcgetattr(sys.stdin)
tty.setraw(sys.stdin.fileno())

# open pseudo-terminal to interact with subprocess
master_fd, slave_fd = pty.openpty()

# use os.setsid() make it run in a new process group, or bash job control will not be enabled
try:
    p = Popen(command,
              preexec_fn=os.setsid,
              stdin=slave_fd,
              stdout=slave_fd,
              stderr=slave_fd,
              universal_newlines=True)
except:
    print("error : check if arguments are correct")
    sys.exit()
with open(logdir + "raw.txt",mode='w') as raw:
    while p.poll() is None:
        r, w, e = select.select([sys.stdin, master_fd], [], [])
        if sys.stdin in r:
            d = os.read(sys.stdin.fileno(),10000000)
            #debug.append("read value: " + d.decode("utf-8"))
            os.write(master_fd, d)
        elif master_fd in r:
            o = os.read(master_fd,10000000)
            if o:
                if re.match(sig,o):
                    o = DelDispValue(o)
                os.write(sys.stdout.fileno(), o)
                if o == b"\x07":
                    continue
                #debug.append(str(binascii.hexlify(o), 'utf-8'))
                #outputstr = (o.decode('utf-8'))
                #raw.write(outputstr)
                #prechars = list(outputstr)
                #debug.append("".join(prechars))
                if not re.search(hist[0],o) == None:
                    if o == b'\x08\x1b\x5b\x4b':
                        if len(blog[-1]) == 1:
                            blog.pop()
                            continue
                    if Chktail(blog[-1]) == True:
                        lastkey = blog.pop()
                        #debug.append("before last key:" + lastkey.decode("utf-8"))
                        num = o.count(b"\x08") * -1
                        DelCtlCode(lastkey)
                        lastkey = lastkey.decode("utf-8")[:num]
                        #debug.append("after last key:" + lastkey)
                        o = lastkey.encode("utf-8") + o
                        #debug.append("after o:" + o.decode("utf-8"))
                    for h in hist:
                        o = re.sub(h,b"",o)
                    blog.append(o)
                    continue
                if not re.search(histback,o) ==None:
                    if Chktail(blog[-1]) == True:
                        blog.pop()
                    o = re.sub(histback,b"",o)
                    blog.append(o)
                    continue
                if args.timestamp == True:
                    now = "[" + datetime.datetime.now().strftime("%a %b %d %H:%M:%S.%f %Y") + "] "
                    o = o.replace(b"\x0d\x0a",b"\x0a")
                    o = o.replace(b"\x0d",b"\x0a")
                    o = o.replace(b"\x0a",b"\x0a" + now.encode("utf-8"))
                else:
                    o = o.replace(b"\x0d\x0a",b"\x0a")
                    o = o.replace(b"\x0d",b"\x0a")
                o = o.replace(b"\x0d",b"\x0a")
                blog.append(o)

blogtxt = b"".join(blog)
blogtxt = DelCtlCode(blogtxt)
strblog = blogtxt.decode("utf-8")
with open(path,mode='w') as b:
    b.write(strblog)
## for debug
#with open(logdir + "debug.txt",mode='w') as d:
#    d.write("\n".join(debug))
#with open("/Users/tak/work/logs/binary.txt",mode='w') as b:
#    b.write("\n".join(binary))
#restore tty settings back
termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
