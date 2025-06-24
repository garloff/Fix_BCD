#!/usr/bin/env python3
#
# Fixing Windows boot manager entries (BCD registry)
# Uses reged and fdisk.
# You typically need to run this as root.
# Follows https://gist.github.com/lupoDharkael/f0054016e2dbdddc0293871af3eb6189
# (c) Kurt Garloff <kurt@garloff.de>, 6/2025
# SPDX-License-Identifier: CC-BY-SA-4.0
"Fix Windows Boot BCD files"

import os
import sys
import shutil
import registry_dict


if not shutil.which("fdisk"):
    raise RuntimeError("You need fdisk installed")
if os.geteuid() != 0:
    print("WARNING: Not running as root, can't see disk information.", file=sys.stderr)


# Globals
PartUUIDs = {}
DiskUUIDs = {}
PartDisks = {}
PartDskNm = {}
PartDescr = {}
DiskOutput = {}


def multiws_split(stg):
    "Split string fields delimited with multiple whitespace"
    el = []
    ln = len(stg)
    previx = 0
    ix = stg.find(' ', previx)
    if ix == -1:
        ix = stg.find('\t', previx)
    while ix != -1:
        el.append(stg[previx:ix])
        previx = ix+1
        while ln > previx and stg[previx].isspace():
            previx += 1
        ix = stg.find(' ', previx)
        if ix == -1:
            ix = stg.find('\t', previx)
    if previx < ln:
        el.append(stg[previx:])
    return el


def disk_uuid(disk):
    "Use fdisk to get DISK UUID"
    # global DiskOutput
    uuid = None
    for ln in os.popen(f"fdisk -l /dev/{disk}"):
        ln = ln.rstrip('\n')
        if ln[:17] == "Disk identifier: ":
            uuid = ln[17:].lower()
        if not ln.startswith(f"/dev/{disk}"):
            continue
        arr = multiws_split(ln)
        DiskOutput[arr[0][5:]] = f"{arr[4]:6} " + " ".join(arr[5:])
    return uuid


def find_loop(nm):
    "Find whole disk loop device for dm- partitions (kpartx)"
    loops = filter(lambda x: x.startswith("loop"), os.listdir("/dev/mapper"))
    for lp in loops:
        if os.path.basename(os.readlink(f"/dev/mapper/{lp}")) == nm:
            return lp
    return None


def strip_part(nm):
    "Find whole disk name by stripping partition suffix"
    if not nm[-1].isdigit():
        return None
    if nm[:2] == "dm":
        nm = find_loop(nm)
        if not nm:
            return None
    dnm = nm[:-1]
    while dnm[-1].isdigit():
        dnm = dnm[:-1]
    if dnm[-1] == 'p':
        dnm = dnm[:-1]
    return dnm


def collect_partuuids():
    """Create dicts by looking at part_uuid_path:
    * PartUUIDs has all Partition UUIDs with device names
    * PartDisks holds Disk UUID belonging to Partition UUIDs
    * PartDskNm holds Disk DevName belonging to Partition UUIDs
    * PartDescr holds descriptions from fdisk -l
    * DiskOutput is the same table indexed by device names
    * DiskUUIDs is a table we build to avoid repeating fdisk -l all the time
    """
    part_uuid_path = "/dev/disk/by-partuuid/"
    # global PartUUIDs, DiskUUIDs, PartDisks, PartDskNm, PartDescr
    with os.scandir(part_uuid_path) as pdir:
        for entry in pdir:
            if entry.name.startswith('.') or not entry.is_symlink():
                continue
            part = os.path.basename(os.readlink(entry))
            PartUUIDs[entry.name] = part
            disknm = strip_part(part)
            if disknm:
                if disknm not in DiskUUIDs:
                    DiskUUIDs[disknm] = disk_uuid(disknm)
                PartDisks[entry.name] = DiskUUIDs[disknm]
                PartDskNm[entry.name] = disknm
                if part in DiskOutput:
                    PartDescr[entry.name] = DiskOutput[part]
                else:
                    PartDescr[entry.name] = ""


def counts(arr):
    "Count zeros and ASCII chars in byte array"
    cntz = 0
    cnta = 0
    for val in arr:
        if val == 0:
            cntz += 1
        if 32 <= val <= 122:
            cnta += 1
    return (cntz, cnta)


def uuidstr(hex16):
    "Create UUID string from byte array"
    return f"{hex16[3]:02x}{hex16[2]:02x}{hex16[1]:02x}{hex16[0]:02x}-{hex16[5]:02x}{hex16[4]:02x}-" \
           f"{hex16[7]:02x}{hex16[6]:02x}-{hex16[8]:02x}{hex16[9]:02x}-" \
           f"{hex16[10]:02x}{hex16[11]:02x}{hex16[12]:02x}{hex16[13]:02x}{hex16[14]:02x}{hex16[15]:02x}"


def find_part_disk(hexstr):
    "Search for Part/Disk UUIDs"
    ids = []
    offs = []
    hexarr = registry_dict.arr_from_hexstr(hexstr)
    ln = len(hexarr)
    idx = 32
    while ln >= idx+16:
        while hexarr[idx] == 0:
            idx += 4
        if ln < idx+16:
            return (ids, offs)
        cntz, cnta = counts(hexarr[idx:idx+16])
        if cntz < 2 and cnta <= 10 and (ln == idx+16 or hexarr[idx+16] == 0):
            ids.append(uuidstr(hexarr[idx:idx+16]))
            offs.append(idx)
            idx += 16
        idx += 4
    return (ids, offs)


def partkey(st):
    "Insert 0 in sort key for partition number"
    if not st[-2].isdigit():
        return st[:-2] + '0' + st[-1]
    return st


def select_uuid():
    "Display list of partitions and ask user to select one"
    while True:
        print("  Select Partition:")
        for part in sorted(PartUUIDs, key = lambda x: partkey(PartUUIDs[x])):
            print(f"   {PartUUIDs[part]:10} : {PartDescr[part]:30} : {part}")
        ans = input("  Partition: ")
        if not ans:
            return None
        if ans in PartUUIDs:
            return ans
        for partid, partnm in PartUUIDs.items():
            if ans == partnm:
                return partid


def uuid_bytes(ustr):
    "Return reg dump file from bytes representing a UUID"
    return f"{ustr[6:8]},{ustr[4:6]},{ustr[2:4]},{ustr[0:2]},{ustr[11:13]},{ustr[9:11]}," \
           f"{ustr[16:18]},{ustr[14:16]},{ustr[19:21]},{ustr[21:23]}," \
           f"{ustr[24:26]},{ustr[26:28]},{ustr[28:30]},{ustr[30:32]},{ustr[32:34]},{ustr[34:36]}"


def correct_uuid(uuid, offs, dct):
    "Correct leaf assigment string with uuid at offset"
    dstr = dct['Element']
    # print(dstr)
    ix = dstr.find(':')
    assert ix >= 0
    ix += 3*offs+1
    dct['Element'] = dstr[:ix] + uuid_bytes(uuid) + dstr[ix+47:]
    # print(dct['Element'])


def list_and_correct_entries(regd):
    "List boot menu entries and correct wrong disk UUIDs"
    file_key = "12000002"
    fil2_key = "22000002"
    desc_key = "12000004"
    disk_key = "11000001"
    osdk_key = "21000001"

    unfixed = 0
    fixes = 0
    objs = regd["Objects"]
    for obk, ob in objs.items():
        elms = ob["Elements"]
        if desc_key not in elms:
            continue
        desc = elms[desc_key]["Element"]
        if file_key in elms:
            desc += " (" + elms[file_key]['Element'].replace("\\\\", "\\") + ")"
        if fil2_key in elms:
            desc += " (" + elms[fil2_key]['Element'].replace("\\\\", "\\") + ")"
        print(f"Entry {obk}: {desc}")
        resp = None
        for key, txt in (disk_key, "Disk "), (osdk_key, "OSDsk"):
            if key in elms:
                ids, offs = find_part_disk(elms[key]['Element'])
                print(f" {txt} IDs: {ids}")
                if len(ids) != 2:
                    print("  ERROR")
                    unfixed += 1
                    continue
                if ids[0] not in PartUUIDs:
                    print("  Partition UUID unknown!")
                    if not resp:
                        resp = select_uuid()
                    if not resp:
                        unfixed += 1
                        continue
                    correct_uuid(resp, offs[0], elms[key])
                    correct_uuid(PartDisks[resp], offs[1], elms[key])
                    fixes += 2
                    # Validate
                    ids, offs = find_part_disk(elms[key]['Element'])
                    assert ids[0] == resp
                    assert ids[1] == PartDisks[resp]
                else:
                    if ids[0] not in PartDisks or not PartDisks[ids[0]]:
                        print(f"  Partition {ids[0]} without known disk")
                        unfixed += 1
                        continue
                    if ids[1] != PartDisks[ids[0]]:
                        print(f"  Partition {PartUUIDs[ids[0]]} should be on {PartDisks[ids[0]]} not {ids[1]}, correct")
                        correct_uuid(PartDisks[ids[0]], offs[1], elms[key])
                        fixes += 1
                    else:
                        print(f"  Partition {PartUUIDs[ids[0]]} on {PartDskNm[ids[0]]} OK")
    return fixes, unfixed


def usage():
    "help"
    print("Usage: fix_boot_bcd.py /PATH/TO/BCD")
    print(" You typically need to run this as root")
    sys.exit(1)


def main(argv):
    "Main entry point"
    if len(argv) < 2:
        usage()
    collect_partuuids()
    # print(f"Partitions: {PartUUIDs}")
    # print(f"Disks: {DiskUUIDs}")
    # print(f"PartDisks: {PartDisks}")
    bcd = registry_dict.RegDict(argv[1])
    # print(bcd)
    fixes, unfixed = list_and_correct_entries(bcd)
    if fixes:
        bcd.write(True)
    return unfixed


if __name__ == "__main__":
    sys.exit(main(sys.argv))
