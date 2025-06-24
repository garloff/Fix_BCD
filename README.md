# Fix_BCD
Fix Windows BCD registry for common boot problems.

When you move your Windows installation to another partition or another
hard disk (or SSD or NVMe), it is amazingly hard to get Windows booting
again from that new disk or partition.

The reason is the byzantine construct with a BCD registry where Windows
stores partition and disk UUIDs to identify the locations to read files
to be booted from.
This makes moving hard:
- By using partition and disk UUIDs rather the filesystem UUIDS (which
  grub normally does), a 1:1 copy of a partition is not good enough to
  make Windows find it. You need to adjust the BCD.
- As BCD is a binary registry format, adjusting it is hard.

`fix_boot_bcd.py BCDFILE` analyzes the BCD file and searches for the
partition and disk UUIDs and checks whether those are consistent and
existing on your system. Otherwise it offers you a selection of
the existing partitions and adjusts the BCD according to your choices.

You would typically run this on Linux with `/boot/efi/Boot/BCD` for
the Windows Boot Manager and with `/boot/efi/EFI/Microsoft/Boot/BCD`
for the Windows Boot and `/boot/efi/EFI/Microsoft/Recovery/BCD`
for Windows Recovery Boot.

Note that it requires the `reged` binary (from the `chntpw` package)
to read and change the Windows registry entries.

This tool was inspired by [lupoDharkael](https://gist.github.com/lupoDharkael)
with his
[instructions](https://gist.github.com/lupoDharkael/f0054016e2dbdddc0293871af3eb6189).
