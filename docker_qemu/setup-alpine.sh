#!/bin/sh

# On failure print error message
set -e


echo "auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
        hostname localhost" > /etc/network/interfaces

/etc/init.d/networking --quiet restart

echo "http://dl-cdn.alpinelinux.org/alpine/v3.10/main
http://dl-cdn.alpinelinux.org/alpine/v3.10/community" >> /etc/apk/repositories

apk update
apk add python3 py3-pip parted dosfstools e2fsprogs ntfs-3g-progs xfsprogs jfsutils mkinitfs fuse util-linux

echo "setup-alpine.sh: OK"