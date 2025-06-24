#!/usr/bin/env python3
#
# Module to parse and modify Win registry files, using reged (chnetpw)
#
# (c) Kurt Garloff <kurt@garloff.de>, 6/2025
#
# SPDX-License-Identifier: Apache-2.0

"""Module to parse and modify Win registry files (using reged executable).
   It reads the registry into a python dictionary.
   The class RegDict is a subclass of python class dict
   and offers a custom constructor, read(), write() and __repr__() methods.
"""


import os
import sys
import subprocess
import tempfile
import shutil


if not shutil.which("reged"):
    raise RuntimeError("You need reged (chntpw) installed")


def dump_reg(bcdnm, prefix="\\"):
    "Read BCD registry into a temporary text file (which is returned"
    tmp = tempfile.mkstemp()[1]
    subprocess.check_call(("reged", "-x", bcdnm, prefix, "\\", tmp),
                          stdout=subprocess.DEVNULL)
    return tmp


def write_reg(bcdnm, tmpnm, prefix="\\"):
    "Write into (existing!) BCD registry from reg text file"
    try:
        subprocess.check_call(("reged", "-N", "-C", "-I", bcdnm, prefix, tmpnm),
                              stdout=subprocess.DEVNULL)
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"{exc}", file=sys.stderr)
        return exc.returncode


def add_to_dict(dct, key):
    """Add new key to dictionary structure
       key may be hierarchical, split by '\\'
    """
    subdct = dct
    for k in key.split('\\'):
        if k in subdct:
            subdct = subdct[k]
            # print(f"Chose existing subdct {k}")
        else:
            subdct[k] = {}
            subdct = subdct[k]
            # print(f"New empty subdct {k}")
    return subdct


def reg_to_dict(tmpnm):
    "Read dumped registry file and transform into python dictionary"
    header = None
    regdict = {}
    key = None
    elem = None
    for ln in open(tmpnm, "r", encoding='utf-8'):
        if ln[0] != "[" and key is None:
            if not header:
                header = ln.rstrip('\n')
            continue
        ln = ln.rstrip("\n")
        # print(f"Parsing: \"{ln}\"")
        # New branch
        if not ln:
            key = None
            elem = None
            continue
        if ln[0] == "[":
            assert ln[-1] == "]"
            ln = ln[1:-1]
            if ln == "\\":
                continue
            while ln[0] == "\\":
                ln = ln[1:]
            key = add_to_dict(regdict, ln)
            continue
        # New leaf
        if ln[0] == '"':
            assert key is not None
            (k, val) = ln.split('=')
            if val[-1] == "\\":
                val = val[:-1]
            k = k.replace('"', '')
            key[k] = val
            elem = k
            continue
        # Continuation
        if ln[:2] == "  ":
            assert elem
            ln = ln[2:]
            if ln[-1] == "\\":
                ln = ln[:-1]
            key[elem] += ln
    return (regdict, header)


def arr_from_hexstr(hexstr):
    "Create array from hex data field in registry"
    if hexstr[:7] == "hex(7):":
        hexstr = hexstr[7:]
    elif hexstr[:4] == "hex:":
        hexstr = hexstr[4:]
    else:
        raise ValueError(hexstr)
    return [int(x, 16) for x in hexstr.split(",")]


def output_elem(val, f):
    "write leaf element into reg dump file"
    wrap = 66
    while val:
        if len(val) <= wrap:
            print(val, file=f)
            return
        idx = val.find(",", wrap-2)
        wrap = 76
        print(val[:idx+1] + "\\\n  ", file=f, end='')
        val = val[idx+1:]


def output_regsub(regd, f, pre):
    "write sub dict into reg dump file"
    for key in regd.keys():
        if isinstance(regd[key], dict):
            print(f"\n[{pre}\\{key}]", file=f)
            output_regsub(regd[key], f, pre+"\\"+key)
        else:
            print(f"\"{key}\"=", file=f, end='')
            output_elem(regd[key], f)


def output_reg(regd, fnm, header):
    "write dict into reg dump file"
    with open(fnm, "w", newline = "\r\n", encoding='utf-8') as f:
        if header:
            print(header + "\n", file=f)
        print("[\\]", file=f)
        output_regsub(regd, f, "\\")
        print('', file=f)


class RegDict(dict):
    """A python dictionary that is read from and written to a Win registry file,
       using the read() and write() methods (filename is passed in c'tor
    """
    def __init__(self, regname, prefix="\\"):
        "Constructor"
        self.regname = regname
        self.prefix = prefix
        self.header = None
        super().__init__()
        self.read()

    def read(self, nm=None, pre=None):
        "Read and parse registry file"
        if nm:
            self.regname = nm
        if pre:
            self.prefix = pre
        tmpnm = dump_reg(self.regname, self.prefix)
        dct, self.header = reg_to_dict(tmpnm)
        super().__init__(dct)
        os.remove(tmpnm)
        return self

    def write(self, backup=False):
        "Write changed registry file"
        if backup:
            shutil.copy2(self.regname, self.regname + ".bak")
        tmpnm = tempfile.mkstemp()[1]
        output_reg(self, tmpnm, self.header)
        ret = write_reg(self.regname, tmpnm, self.prefix)
        os.remove(tmpnm)
        return ret

    def __repr__(self):
        return f"Registry {self.regname}, {self.prefix}: " + super().__repr__()

