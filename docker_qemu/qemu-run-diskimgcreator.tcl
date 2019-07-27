#!/usr/bin/expect -f 

# apk add iscsi-scst zfs-scripts zfs zfs-utils-py \
#     cciss_vol_status lvm2 mdadm mkinitfs mtools nfs-utils \
#     parted rsync sfdisk syslinux unrar util-linux xfsprogs \
#     dosfstools ntfs-3g
    
set timeout -1

spawn qemu-system-x86_64 -m 512 /alpine.qcow2 -loadvm snappy01 -nographic -virtfs local,path=/disk,mount_tag=host0,security_model=passthrough,id=host0 

send "\r"

expect -exact "localhost:~# "
send -- "mount -t 9p -o trans=virtio host0 /mnt -oversion=9p2000.L\r"

expect -exact "localhost:~# "
send -- "cd /mnt/\r"

expect -exact "localhost:~# "
send -- "python3 /diskimgcreator.py $argument1\r"

expect -exact "localhost:~# "
send -- "x"
puts ""