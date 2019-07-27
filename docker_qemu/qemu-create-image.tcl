#!/usr/bin/expect -f 

# apk add iscsi-scst zfs-scripts zfs zfs-utils-py \
#     cciss_vol_status lvm2 mdadm mkinitfs mtools nfs-utils \
#     parted rsync sfdisk syslinux unrar util-linux xfsprogs \
#     dosfstools ntfs-3g
    
set timeout -1

spawn qemu-system-x86_64 -m 512 /alpine.qcow2 -nographic -virtfs local,path=/src,mount_tag=host0,security_model=passthrough,id=host0

expect -exact "login: "
send "root\r"

expect -exact "localhost:~# "
send -- "mount -t 9p -o trans=virtio host0 /mnt -oversion=9p2000.L\r"

expect -exact "localhost:~# "
send -- "cp /mnt/diskimgcreator.py /\r"

expect -exact "localhost:~# "
send "/bin/sh /mnt/setup-alpine.sh || echo \"FATAL\" \"ERROR\"\r"

expect {
    "FATAL ERROR" { exit 1 }
    "setup-alpine.sh: OK" { }
}

expect -exact "localhost:~# "
send -- "umount /mnt\r"

expect -exact "localhost:~# "
# Ctrl+A C
send -- "c"

expect -exact "(qemu) "
send -- "savevm snappy01\r"

expect -exact "(qemu) "
# Ctrl+A X
send -- "x"

puts ""
puts "Qemu image is now complete."