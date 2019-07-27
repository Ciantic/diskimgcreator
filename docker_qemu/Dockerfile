FROM alpine
RUN apk add qemu-system-x86_64 qemu-img expect
RUN wget http://dl-cdn.alpinelinux.org/alpine/v3.10/releases/x86/alpine-virt-3.10.1-x86.iso -O /alpine.iso
RUN qemu-img convert -f raw -O qcow2 /alpine.iso /alpine.qcow2
COPY qemu-create-image.tcl /src/
COPY setup-alpine.sh /src/
COPY diskimgcreator.py /src/
RUN cd /src && chmod +x * && ./qemu-create-image.tcl
COPY . /src

WORKDIR /disk

# FROM alpine 
# RUN apk update && apk add qemu-system-x86_64 qemu-img expect
# COPY --from=create-qcow2 /alpine.qcow2 /alpine.qcow2
# COPY . /mnt
# RUN chmod +x /mnt/*
# RUN qemu-system-x86_64 -m 512 /alpine.qcow2 -nographic

# https://fadeevab.com/how-to-setup-qemu-output-to-console-and-automate-using-shell-script/

# RUN dd if=/dev/null of=empty.img bs=1 seek=512M
# RUN qemu-system-x86_64 -m 512 /alpine.qcow2 -loadvm snappy01 -nographic \
#     -drive if=none,file=/empty.img,format=raw,id=disk1,snapshot=off \
#     -device virtio-blk-pci,drive=disk1,id=virtiodisk1 \
#     -nographic


# setup-interfaces 
# /etc/init.d/networking --quiet restart
# echo "http://nl.alpinelinux.org/alpine/v3.10/main" >> /etc/apk/repositories

# HOT PLUG A VIRTUAL DISK using (qemu)
# drive_add 0 if=none,file=/empty.img,format=raw,id=disk1
# device_add virtio-blk-pci,drive=disk1,id=virtiodisk1

# UNHOT PLUG A VIRTUAL DISK (qemu)
# device_del virtiodisk1

# RUN qemu-system-x86_64 -m 512 /alpine.iso -drive file=empty.img,if=virtio -nographic
# mkfs.fat32 /dev/vd1
# mount /dev

# Create clean image with just partfs
# FROM debian:buster-slim

# RUN apt-get update -qq -y && apt-get -y install \
#     libfdisk1 libfuse2 parted dosfstools fuse wget

# RUN apt-get -y install \
#     python3 python3-pip

# RUN update-alternatives --install /usr/bin/python python /usr/bin/python3  2

# # COPY --from=partfs   /build/partfs/build/bin/partfs   /usr/local/bin/partfs

# COPY src/ /diskimgcreator.py
# COPY src/ /diskimgcreator.py


# WORKDIR /disk

# ENTRYPOINT [ "/diskimgcreator.sh" ]