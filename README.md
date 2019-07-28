

# DiskImgCreator - Disk Image Creator

Partitions and copies files to img file.

## Usage with Python 3.7 or newer in Linux

Requires dd, parted, mount, umount, losetup or partfs.

`diskimgcreatory.py`

## Usage with docker

This works from Windows as well as Linux, and does not require installing.

`docker run --rm -v $(pwd):/disk --privileged ciantic/diskimgcreator`

FUSE rights are required for the container, and unfortunately the SYS_ADMIN is
required still for the FUSE rights to container. Therefore it's pretty much same
as running with privileged rights.

## Defining partitions

Define partitions as directories, .tar or .tar.gz files. Then run this command
with disk image file you want to create. You can define partitions in *short
format* or *long format*.

### Short format

`partitionNN[_msdos]_ENDPOS_TYPE[ .tar | .tar.gz ]`

e.g.: 
* `partition01_8MiB_fat32`
* `partition02_16GiB_ext4`

Would define partition table as gpt (the default), create a 16GiB sized image
file, where first partition ending at 8MiB and second partition ending at 16GiB.
Beware with the permissions, especially if you use plain directory. In short
format the first partition always is bootable and starts at 1MiB for optimal
alignment of smaller images.

*Notice*: Underscores in short format are optional, you may also use spaces.

### Long format

You can also define partitions in *long format*, if you want to partition like
it's 1947:

`partitionNN [-- dd FULLSIZE] -- parted PARTEDCMD[ .tar | .tar.gz ]`

e.g.:
* `partition01 -- dd 256MiB -- parted mklabel msdos mkpart primary fat32 1 8MiB`
* `partition02 -- parted mkpart primary ext4 8MiB 100%`

Would create 256MiB sized image, with 7MiB fat32 partition and 248MiB ext4
partition. Consult parted manual for the scripting syntax. Full size used in
initial dd is parsed only from the first partition.
