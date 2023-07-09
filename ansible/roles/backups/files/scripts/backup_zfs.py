#!/usr/bin/python3
import os
import subprocess
import sys
from argparse import ArgumentParser
from datetime import date


def main():
    p = ArgumentParser()
    p.add_argument("--dataset", required=True, help="ZFS Dataset to backup")
    p.add_argument("--tgt", required=True, help="Target backup directory")
    opts = p.parse_args()

    date_str = date.today().strftime("%y_%m_%d")
    snap_name = opts.dataset + "@backup_" + date_str
    backup_file_name = f"{opts.tgt} /zfsbackup_{opts.dataset.replace('/', '_')}_{date_str}.gz"

    # Check root perms
    if os.geteuid() != 0:
        print("ERROR: Root permissions needed for ZFS Snapshots")
        return 1

    if not os.path.isdir(opts.tgt):
        print("Creating backup dir: " + opts.tgt)
        os.mkdir(opts.tgt)

    print("Taking zfs snapshot: " + snap_name)
    cmd_est_snap = ["zfs", "snap", "-r", snap_name]
    subprocess.check_call(cmd_est_snap)

    print("Backing up snap to: " + backup_file_name)
    cmd_backup_snap = f"zfs send -R {snap_name} | pv | gzip > {backup_file_name}"
    try:
        subprocess.check_call(cmd_backup_snap, shell=True)
    finally:
        print("Removing snapshot")
        cmd_rem_snap = ["zfs", "destroy", "-r", snap_name]
        subprocess.check_call(cmd_rem_snap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
