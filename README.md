# Fix_BCD
Fix Windows BCD registry for common boot problems.

When you move your Windows installation to another partition or another
hard disk (or SSD or NVMe), it is amazingly hard to get Windows booting
again from the new disk or partition.

The reason is the byzantine construct with a BCD registry where Windows
stores partition and disk UUIDs to identify the locations to read files
to be booted from.
This makes moving really harder than it needs to be:
- By using partition and disk UUIDs rather the filesystem UUIDs (which
  grub normally does), a 1:1 copy of a partition is not good enough to
  make Windows find it. You need to adjust the BCD.
- As BCD is a binary registry format, adjusting it is hard.

`fix_boot_bcd.py BCDFILE` analyzes the BCD file and searches for the
partition and disk UUIDs and checks whether these are consistent and
existing on your system. Otherwise it offers you a selection of
the existing partitions and adjusts the BCD according to your choices.
With option `-n`, it does not do any changes but just lists the boot
entries and reports problems.

You would typically run this as root on Linux with `/boot/efi/Boot/BCD`
for the Windows Boot Manager and with `/boot/efi/EFI/Microsoft/Boot/BCD`
for Windows Boot and `/boot/efi/EFI/Microsoft/Recovery/BCD` for
Windows Recovery Boot. (The path assumes that your EFI boot partition
is mounted at `/boot/efi` which is typically the case on Linux machines.)

Note that it requires the `reged` binary (from the `chntpw` package)
to read and change the Windows registry entries.
To access registries, there is a little ORM-like translation tool in
`class registry_dict.RegDict` which behaves like a dictionary with
additional `read()` and `write()` methods that do the registry reading,
writing and translation into python data structures.
Feel free to reuse it.

Notes: The `registry_dict.py` helper is under Apache-2.0 license, while
the fix script `fix_boot_bcd.py` uses the `CC-BY-SA-4.0` license. So do
not create proprietary tools nor remove credits to me from the latter.

This tool was inspired by [lupoDharkael](https://gist.github.com/lupoDharkael)
with his
[instructions](https://gist.github.com/lupoDharkael/f0054016e2dbdddc0293871af3eb6189).
Huge thanks for figuring this all out!
