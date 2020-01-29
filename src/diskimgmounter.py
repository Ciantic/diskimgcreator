"""
Disk Image Mounter

:author: Jari Pennanen
:license: MIT
:version: 2020-01-29
"""

DESCRIPTION = """
Disk Image Mounter (.img) - Mounts the partitions in the img and executes a given script
Source code: https://github.com/Ciantic/diskimgcreator

"""
from diskimgcreator import Partfs, Losetup, Mount, print_error, _set_verbose
import uuid
from typing import List, Optional
from contextlib import ExitStack, contextmanager
import argparse
import glob
import sys
import os
import re
import io
import datetime
import textwrap
import subprocess


@contextmanager
def try_mount_image(
    imagefilename: str,
    partitions=[],  # partitions as numbers, e.g. [1, 2] means partitions 1 and 2
    mount_root_dir="/mnt",
    use_partfs=False,
    partfs_mount_dir="/mnt/_temp_partfs",
):
    if not os.path.exists(mount_root_dir):
        os.mkdir(mount_root_dir)
    with ExitStack() as cm:
        if use_partfs:
            partfs = cm.enter_context(Partfs(imagefilename, partfs_mount_dir))
        else:
            partfs = cm.enter_context(Losetup(imagefilename))

        if len(partitions) == 0:
            partitions = range(0, len(partfs))
        for pindex in partitions:
            try:
                part = partfs[pindex - 1]
            except IndexError:
                continue
            mntdir = "{}/p{}".format(mount_root_dir, pindex)
            if not os.path.exists(mntdir):
                os.mkdir(mntdir)

            cm.enter_context(Mount(part, mntdir))
        yield


def parse_cli_arguments():
    # https://docs.python.org/3/library/argparse.html
    # https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter, description=DESCRIPTION
    )
    parser.add_argument("imagefile", action="store")
    parser.add_argument("cmd", action="store", nargs="+")
    parser.add_argument(
        "-p",
        "--partitions",
        help="Comma separated list of partitions to mount (index starting from 1)",
        type=lambda s: [int(item) for item in s.split(",")],
        required=True,
    )
    parser.add_argument(
        "--use-partfs",
        help="Uses FUSE based partfs instead of losetup for mounting partitions, defaults to true in docker environment",
        action="store_true",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    return (parser, parser.parse_args())


def main():
    _, args = parse_cli_arguments()

    _set_verbose(args.verbose)

    # TODO: Something fun?
    # if sys.stdout.isatty():
    #     print_notice("You are running interactively")

    # Call the main creator
    try:
        mount_root_dir = "/mnt"
        with try_mount_image(
            args.imagefile,
            partitions=args.partitions,
            use_partfs=args.use_partfs,
            mount_root_dir=mount_root_dir,
            partfs_mount_dir="/mnt/_tmp_partfs{}".format(uuid.uuid4().hex),
        ):
            try:
                subprocess.run(args.cmd, check=True, cwd=mount_root_dir)
            except subprocess.CalledProcessError as err:
                print_error("Execution of your script failed.")
                raise err
    except subprocess.CalledProcessError as err:
        # print_error(
        #     f"Return code: {err.returncode}, Command: {subprocess.list2cmdline(err.cmd)}"
        # )
        exit(1)


if __name__ == "__main__":
    main()
