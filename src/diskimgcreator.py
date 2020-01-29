"""
Disk Image Creator

:author: Jari Pennanen
:license: MIT
:version: 2019-07-28
"""

DESCRIPTION = """
Disk Image Creator (.img) - Partitions and copies files to img file
Source code: https://github.com/Ciantic/diskimgcreator

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

"""

import uuid
from typing import List, Optional
import argparse
import glob
import sys
import os
import re
import io
import datetime
import textwrap
import subprocess
import logging


VERBOSE = False


def _set_verbose(val: bool):
    global VERBOSE
    VERBOSE = val


def _is_verbose():
    global VERBOSE
    return VERBOSE


def print_error(err: str):
    CRED = "\033[91m"
    CEND = "\033[0m"
    print(CRED + "Error: " + err + CEND, file=sys.stderr)


def print_ok(ok: str):
    global VERBOSE
    CGREEN = "\33[32m"
    CEND = "\033[0m"
    if VERBOSE:
        print(CGREEN + ok + CEND)


def print_notice(notice: str):
    global VERBOSE
    CBLUE2 = "\33[94m"
    CEND = "\033[0m"
    if VERBOSE:
        print(CBLUE2 + notice + CEND)


class UnknownFilesystemException(Exception):
    def __init__(self, fstype: str):
        self.fstype = fstype


class ImageFileExistsException(Exception):
    def __init__(self, imagefile: str):
        self.imagefile = imagefile


class PartitionSizeParseException(Exception):
    def __init__(self, size: Optional[str] = None):
        self.size = size


class PartitionsNotFoundException(Exception):
    pass


class PartitionParseException(Exception):
    def __init__(self, filename: str):
        self.filename = filename


class PartfsMountInUseException(Exception):
    def __init__(self, mountdir: str):
        self.mountdir = mountdir


class Partfs:
    """
    Mounts diskimage partitions as FUSE mounts
    """

    def __init__(self, diskimage: str, mountdir: str):
        self.diskimage = diskimage
        self.mountdir = mountdir
        if not os.path.exists(mountdir):
            os.mkdir(mountdir)
        if os.listdir(mountdir):
            raise PartfsMountInUseException(mountdir)

    def __enter__(self):
        if not os.path.isdir(self.mountdir):
            os.mkdir(self.mountdir)

        try:
            subprocess.run(
                ["partfs", "-o", f"dev={self.diskimage}", self.mountdir], check=True
            )
        except subprocess.CalledProcessError as err:
            print_error("Partfs failed.")
            raise err
        print_ok(f"Partfs {self.mountdir} mounted.")
        return sorted(glob.glob(os.path.join(self.mountdir, r"p[0-9]*")))

    def __exit__(self, type, value, traceback):
        try:
            subprocess.run(["fusermount", "-u", self.mountdir], check=True)
        except subprocess.CalledProcessError as err:
            print_error("Unmount failed.")
            raise err
        os.rmdir(self.mountdir)
        print_ok(f"Partfs {self.mountdir} unmounted.")


class Losetup:
    """
    Mounts diskimage partitions as loop devices

    This requires permissions to create or loop devices.

    This tries to use free loop device if available. If not then it tries to
    create one with mknod. On exit it will free the losetup but does not try to
    delete the created mknod.
    """

    def __init__(self, diskimage: str):
        self.diskimage = diskimage

    def __enter__(self):
        self.device = None

        # Get or create losetup device
        losetup_f = subprocess.run(["losetup", "-f"], text=True, capture_output=True)
        if losetup_f.returncode == 0:
            self.device = losetup_f.stdout.strip()
        elif losetup_f.stderr.startswith(
            "losetup: cannot find an unused loop device: No such device"
        ):
            subprocess.run(["mknod", "/dev/loop0", "b", "7", "0"], check=True)
            self.device = "/dev/loop0"
        else:
            losetup_f.check_returncode()

        try:
            subprocess.run(["losetup", "-P", self.device, self.diskimage], check=True)
        except subprocess.CalledProcessError as err:
            print_error(f"Losetup {self.device} failed.")
            raise err
        print_ok(f"Losetup {self.device} created.")
        return glob.glob(os.path.join(self.device, r"p[0-9]*"))

    def __exit__(self, type, value, traceback):
        if self.device:
            try:
                subprocess.run(["losetup", "-d", self.device], check=True)
            except subprocess.CalledProcessError as err:
                print_error(f"Losetup failed to free device: {self.device}")
                raise err
        print_ok(f"Losetup {self.device} freed.")


class Mount:
    """
    Normal Linux mount operation
    """

    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target

    def __enter__(self):
        if not os.path.isdir(self.target):
            os.mkdir(self.target)

        try:
            subprocess.run(["mount", self.source, self.target], check=True)
        except subprocess.CalledProcessError as err:
            print_error("Mount failed.")
            raise err
        print_ok(f"Mount {self.target} created.")
        return self.target

    def __exit__(self, type, value, traceback):
        try:
            subprocess.run(["umount", self.target], check=True)
        except subprocess.CalledProcessError as err:
            print_error(f"Unmount failed to free target: {self.target}")
            raise err
        os.rmdir(self.target)
        print_ok(f"Mount {self.target} freed.")


class Partition:
    def __init__(self, filename: str, parted: str, fstype: str = ""):
        self.filename = filename
        self.parted = parted
        self.fstype = fstype

    def is_mountable(self):
        if self.fstype == "linux-swap":
            return False
        return True

    def try_copy_to(self, to_dir: str):
        if os.path.isdir(self.filename):
            # Directory
            print_notice(f"Copy -rp files from '{self.filename}' to '{to_dir}'...")
            try:
                subprocess.run(["cp", "-rp", self.filename, to_dir], check=True)
            except subprocess.CalledProcessError as err:
                print_error("Copying files failed.")
                raise err
            print_ok(f"Copying from '{self.filename}' succeeded.")

        elif self.filename.endswith(".tar"):
            # .tar files
            print_notice(f"Untar files from '{self.filename}' to '{to_dir}'...")
            try:
                subprocess.run(
                    ["tar", "--same-owner", "-xf", self.filename, "-C", to_dir],
                    check=True,
                )
            except subprocess.CalledProcessError as err:
                print_error("Untar failed.")
                raise err
            print_ok(f"Untar from '{self.filename}' succeeded.")

        elif self.filename.endswith(".tar.gz"):
            # .tar.gz files
            print_notice(f"Untar gzip files from '{self.filename}' to '{to_dir}'...")
            try:
                subprocess.run(
                    ["tar", "--same-owner", "-xzf", self.filename, "-C", to_dir],
                    check=True,
                )
            except subprocess.CalledProcessError as err:
                print_error("Untar failed.")
                raise err
            print_ok(f"Untar from '{self.filename}' succeeded.")


class PartitionCollection:
    def __init__(self, partitions: List[Partition]):
        self._partitions = partitions

    def get_total_size(self):
        """
        Tries to get the total size of the image

        In long format it's defined in first file for example: `-- dd 1GiB` In short
        format it's defined in the last file.
        """
        long_format = re.compile(r".* -- dd (?P<size_all>[^ $]+)")
        short_format = re.compile(r".*partition(\d\d?)[_ ](?P<partition_end>[^_ ]+)")

        # In long format the size is on first file
        m = long_format.match(self._partitions[0].filename)
        if m:
            return _parse_size(m.group("size_all"))

        # In short format the size is the last partition end
        m = short_format.match(self._partitions[-1].filename)
        if m:
            return _parse_size(m.group("partition_end"))

        raise PartitionSizeParseException()

    def get_parted(self):
        return list(map(lambda k: k.parted, self._partitions))

    def get_fstypes(self):
        return list(map(lambda k: k.fstype, self._partitions))

    def __iter__(self):
        return iter(self._partitions)

    @classmethod
    def from_directory(cls, from_dir: str):
        partition_filenames = sorted(
            glob.glob(os.path.join(from_dir, "partition[0-9][0-9]?*"))
        )

        partitions = _try_get_partitions_long_format(
            partition_filenames
        ) or _try_get_partitions_short_format(partition_filenames)

        if len(partitions) == 0:
            raise PartitionsNotFoundException()

        return PartitionCollection(partitions)


class Imagefile:
    def __init__(self, filename: str):
        self.filename = filename

    def make_empty(self, total_size: int, overwrite: bool = False):
        _try_dd(self.filename, total_size, overwrite)

    def partition(self, partitions: PartitionCollection):
        _try_parted(self.filename, partitions.get_parted())

    def mount(
        self,
        partitions: PartitionCollection,
        use_partfs=False,
        partfs_mount_dir="/mnt/_temp_partfs",
    ):
        return ImagefileMounted(
            self, partitions, use_partfs=use_partfs, partfs_mount_dir=partfs_mount_dir
        )


class ImagefileMounted:
    def __init__(
        self,
        imagefile: Imagefile,
        partitions: PartitionCollection,
        use_partfs=False,
        partfs_mount_dir="/mnt/_temp_partfs",
    ):
        self.imagefile = imagefile
        self.use_partfs = use_partfs
        self.partitions = partitions
        self.partfs_mount_dir = partfs_mount_dir

    def __enter__(self):
        if self.use_partfs:
            self._mount = Partfs(self.imagefile.filename, self.partfs_mount_dir)
        else:
            self._mount = Losetup(self.imagefile.filename)
        self._partition_dirs = self._mount.__enter__()
        return zip(self.partitions, self._partition_dirs)

    def __exit__(self, type, value, traceback):
        self._mount.__exit__(type, value, traceback)


def try_create_image(
    rootdir: str,
    imagefilename: str,
    overwrite: bool = False,
    use_partfs=False,
    partfs_mount_dir="/mnt/_temp_partfs",
    mount_root_dir="/mnt/_temp_fs",
):
    print(f"Partitions directory: {rootdir}")
    print(f"Image file to create: {imagefilename}")
    partitions = PartitionCollection.from_directory(rootdir)
    total_size = partitions.get_total_size()
    imagefile = Imagefile(imagefilename)
    imagefile.make_empty(total_size, overwrite)
    imagefile.partition(partitions)

    with imagefile.mount(
        partitions, use_partfs=use_partfs, partfs_mount_dir=partfs_mount_dir
    ) as partition_dirs:
        for partition, partition_dir in partition_dirs:
            _try_mkfs(partition_dir, partition.fstype)
            if partition.is_mountable():
                with Mount(partition_dir, mount_root_dir) as mntdir:
                    partition.try_copy_to(mntdir)


def parse_cli_arguments():
    # https://docs.python.org/3/library/argparse.html
    # https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter, description=DESCRIPTION
    )
    parser.add_argument("imagefile", action="store")
    parser.add_argument(
        "-d",
        "--partitions-dir",
        help="Directory of the partitions, defaults to current directory",
        action="store",
        default=".",
    )
    parser.add_argument(
        "-f", "--force", help="Overwrites any existing image file", action="store_true"
    )
    parser.add_argument(
        "--use-partfs",
        help="Uses FUSE based partfs instead of losetup for mounting partitions, defaults to true in docker environment",
        action="store_true",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    return (parser, parser.parse_args())


def main():
    global VERBOSE
    _, args = parse_cli_arguments()

    _set_verbose(args.verbose)

    # TODO: Something fun?
    # if sys.stdout.isatty():
    #     print_notice("You are running interactively")

    # Fail if partitions directory does not exist
    if not os.path.isdir(args.partitions_dir):
        print_error(f"Directory '{args.partitions_dir}' does not exist")
        exit(1)

    # Call the main creator
    try:
        try_create_image(
            args.partitions_dir,
            args.imagefile,
            overwrite=args.force,
            use_partfs=args.use_partfs,
            partfs_mount_dir="/mnt/_tmp_partfs{}".format(uuid.uuid4().hex),
        )
    except ImageFileExistsException as err:
        print_error(
            f"Image file '{err.imagefile}' already exists, use `-f` to overwrite"
        )
    except PartitionsNotFoundException:
        print_error(f"Directory '{args.partitions_dir}' does not contain partitions.")
        exit(1)
    except PartitionSizeParseException as err:
        print_error(f"Unable to parse disk size {err.size}")
        exit(1)
    except PartitionParseException as err:
        print_error(f"Unable to parse partition file name: {err.filename}")
        exit(1)
    except subprocess.CalledProcessError as err:
        print_error(
            f"Return code: {err.returncode}, Command: {subprocess.list2cmdline(err.cmd)}"
        )
        exit(1)


def _parse_size(size: str):
    """
    Parse size for parted

    Note: This is not accurate reproduction of parted function `ped_unit_parse_custom`
    """
    units = {
        "": 1000 ** 2,  # Parted assumes MB if no unit is given
        "s": 512,  # Can this vary?
        "b": 1,
        "kb": 1000,
        "mb": 1000 ** 2,
        "gb": 1000 ** 3,
        "tb": 1000 ** 4,
        "kib": 1024,
        "mib": 1024 ** 2,
        "gib": 1024 ** 3,
        "tib": 1024 ** 4,
    }
    m = re.match(r"^([\d\.]+)(.*)$", size)
    if m:
        num = float(m.group(1))
        unit = m.group(2).lower()
        if unit in units:
            return int(num * units[unit])
    raise PartitionSizeParseException()


def _try_get_partitions_long_format(files: List[str]) -> List[Partition]:
    """
    Tries to get partitions in long format:

    `partition01 (-- dd 16GiB)? -- parted mklabel msdos mkpart ...(.tar|.tar.gz)`
    """
    long_format = re.compile(
        r".*partition(\d\d?).*-- parted (?P<parted>.*)(\.tar|\.tar\.gz)?$"
    )
    long_format_fstype = re.compile(
        r".* (?P<fstype>[^ ]+) (?P<partition_start>[^ ]+) (?P<partition_end>[^ ]+)$"
    )

    partitions = []
    if long_format.match(files[0]):
        for fname in files:
            # Parse parted script from the file name
            m = long_format.match(fname)
            if not m:
                raise PartitionParseException(fname)
            parted = m.group("parted")

            # Parse fs type from the parted script
            m = long_format_fstype.match(parted)
            if not m:
                raise PartitionParseException(fname)
            fstype = m.group("fstype")

            # Add a partition
            partitions.append(Partition(fname, parted, fstype))
    return partitions


def _try_get_partitions_short_format(files: List[str]) -> List[Partition]:
    """
    Tries to get partitions in short format:
    
    `partition01[_msdos]_128MiB_fat32(.tar|.tar.gz)`

    Notice that the bytes given is *end* of the partition, not the size!
    """
    short_format = re.compile(
        r".*partition(\d\d?)[_ ](?P<msdos>msdos[_ ])?(?P<partition_end>[^_ ]+)[_ ](?P<fstype>[^_\. ]+)(\.tar|\.tar\.gz)?$"
    )
    partitions = []

    # Default beginning of the first partition
    first_partition_start = "1MiB"

    if short_format.match(files[0]):
        partition_end = first_partition_start
        last_index = len(files) - 1

        for i, fname in enumerate(files):
            m = short_format.match(fname)
            if not m:
                raise PartitionParseException(fname)
            fstype = m.group("fstype")
            partition_start = partition_end
            partition_end = m.group("partition_end")

            # Extend the last partition to the end
            if last_index == i:
                partition_end = "100%"

            # First partition needs to define the table type `gpt` or `msdos`
            # default is the modern gpt.
            if i == 0:
                table_type = "gpt"
                if m.group("msdos"):
                    table_type = "msdos"
                parted = f"unit s mklabel {table_type} mkpart primary {fstype} {partition_start} {partition_end} set 1 boot on"
            else:
                parted = f"mkpart primary {fstype} {partition_start} {partition_end}"
            partitions.append(Partition(fname, parted, fstype))
    return partitions


def _try_dd(imagefile: str, size: int, ovewrite: bool):
    if os.path.exists(imagefile) and not ovewrite:
        raise ImageFileExistsException(imagefile)

    # TODO: Replace with a pure python zero file
    print_notice(f"Executing DD, allocating {size} bytes...")
    try:
        subprocess.run(
            [
                "dd",
                "if=/dev/null",
                f"of={imagefile}",
                "bs=1",
                "count=0",
                f"seek={size}",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as err:
        print_error("DD failed.")
        raise err
    print_ok("DD succeeded.")


def _try_parted(imagefile: str, parted: List[str]):
    print_notice(f"Executing parted script:")
    print_notice("\n".join(parted))
    try:
        subprocess.run(
            ["parted", "--script", imagefile, "--"] + parted + ["print"], check=True
        )
    except subprocess.CalledProcessError as err:
        print_error("Parted failed.")
        raise err
    print_ok("Parted succeeded.")


def _try_mkfs(dirname: str, fstype: str):
    cmds = {
        "fat32": ["mkfs.fat", "-F", "32", dirname],
        "ext4": ["mkfs.ext4", "-F", dirname],
        "ext2": ["mkfs.ext2", dirname],
        "linux-swap": ["mkswap", dirname],
    }

    if fstype not in cmds:
        raise UnknownFilesystemException(fstype)

    print_notice(f"Executing mkfs {fstype} for {dirname}...")
    try:
        subprocess.run(cmds[fstype], check=True)
    except subprocess.CalledProcessError as err:
        print_error("Mkfs failed.")
        raise err
    print_ok("Mkfs succeeded.")


if __name__ == "__main__":
    main()
