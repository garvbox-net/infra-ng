#!/usr/bin/env python3
import os
import sys
from datetime import date
from argparse import ArgumentParser
import subprocess
import logging
import platform

import requests

_truthy_strs = ["true", "1", "y", "yes"]
DEBUG = os.getenv("DEBUG", "").lower() in _truthy_strs
DRY_RUN = os.getenv("DRY_RUN", "").lower() in _truthy_strs
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


class BackupError(RuntimeError):
    """Generic Backup Failure"""


def main():
    p = ArgumentParser()
    p.add_argument("-t", "--tgt", required=True, help="Target backup directory")
    p.add_argument(
        "-v", "--vg", required=True, help="Volume group containing LV to backup"
    )
    p.add_argument(
        "-l", "--lv", required=True, help="LV To back up, snap name will be <lv>-backup"
    )
    p.add_argument(
        "-p", "--src-path", default="*", help="Path(s) to back up within snapshot"
    )
    p.add_argument("-s", "--size", default="5G", help="LV Snap Size")
    p.add_argument(
        "-m",
        "--mount-base",
        default="/mnt",
        help="Base path for mounting snapshot. Actual mount point will be <mount-base>/<snap>",
    )
    p.add_argument("-c", "--cleanup", action="store_true", help="Run cleanup only")
    p.add_argument("-f", "--log-file", help="Output Log file")
    opts = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format="[%(asctime)s] [%(levelname)8s] [%(funcName)12.12s()] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=opts.log_file,
    )

    if not DRY_RUN and os.geteuid() != 0:
        raise PermissionError("Root permissions needed for LVM Snapshots")

    snap_lv = opts.lv + "-backup"
    date_str = date.today().strftime("%y_%m_%d")
    snap_mount_dir = os.path.join(opts.mount_base, snap_lv)
    backup_file_name = os.path.join(opts.tgt, f"backup_{opts.lv}_{date_str}.gz")

    if opts.cleanup:
        logging.info("Running Snapshot and MP Cleanup")
        unmount_snap(snap_mount_dir)
        remove_snap(opts.vg, snap_lv)
        return 0

    if not os.path.isdir(snap_mount_dir):
        logging.info("Creating backup mount dir: " + snap_mount_dir)
        os.mkdir(snap_mount_dir)

    check_snap_res = check_snap_lv(opts.vg, snap_lv)
    if check_snap_res.returncode == 5 or DRY_RUN:
        logging.info("No Existing Snapshot found - continuing with backup")
    elif check_snap_res.returncode == 0:
        raise BackupError(f"Snapshot {snap_lv} already exists - manual cleanup needed")
    else:
        raise BackupError(f"Error getting Snapshot: {check_snap_res.returncode}")

    create_snap(opts.vg, opts.lv, snap_lv, opts.size)
    try:
        mount_snap(opts.vg, snap_lv, snap_mount_dir)
        tar_backup(snap_mount_dir, opts.src_path, backup_file_name)
    finally:
        logging.info("Cleaning up mount point and snapshot")
        # Note unmount is idempotent, if the snap was never mounted it will not fail
        unmount_snap(snap_mount_dir)
        remove_snap(opts.vg, snap_lv)
    return 1


def check_snap_lv(vg, snap_name):
    logging.info("Checking for previous LV Snapshot")
    cmd_check_snap = ["lvdisplay", f"{vg}/{snap_name}"]
    res = _run_cmd(cmd_check_snap)

    return res


def create_snap(vg, lv, snap, size):
    return _run_cmd(
        [
            "lvcreate",
            "--yes",
            "--snapshot",
            "--name",
            snap,
            "--size",
            size,
            f"{vg}/{lv}",
        ],
        check=True,
    )


def tar_backup(mountpoint, sub_path, target):
    cmd_backup_snap = ["tar", "czf", target, "-C", mountpoint, sub_path]
    return _run_cmd(cmd_backup_snap, check=True)


def mount_snap(vg, snap_lv, mountpoint):
    if _get_mounted(mountpoint):
        raise BackupError(
            f"Something is already mounted at {mountpoint}, possible previous failed cleanup"
        )
    return _run_cmd(
        ["mount", os.path.join("/dev", vg, snap_lv), mountpoint], check=True
    )


def unmount_snap(mountpoint):
    if not _get_mounted(mountpoint):
        logging.warning(f"Snapshot is not mounted at {mountpoint}, skipping unmount")
        return None
    return _run_cmd(["umount", mountpoint], check=True)


def remove_snap(vg, snap_lv):
    return _run_cmd(["lvremove", "--yes", f"{vg}/{snap_lv}"], check=True)


def send_discord_notification(message):
    if WEBHOOK_URL is None:
        logging.info("Webhook not set - skipping notification")
        return
    logging.info("Sending Discord Notification")
    requests.post(
        WEBHOOK_URL,
        json={"username": platform.node(), "content": f"Backup Error:\n{message}"},
    )


def _get_mounted(mountpoint):
    logging.debug(f"Checking for mount point: {mountpoint}")
    with open("/proc/mounts", "r") as f:
        for line in f.readlines():
            if line.split()[1] == mountpoint:
                return True
    return False


def _run_cmd(cmd_args, **kwargs):
    if DRY_RUN:
        logging.info(f"DRY_RUN - Would have executed: '{' '.join(cmd_args)}'")
        return subprocess.CompletedProcess(cmd_args, returncode=0)
    logging.debug(f"Running command: '{' '.join(cmd_args)}'")
    return subprocess.run(cmd_args, **kwargs)


if __name__ == "__main__":
    res = 1
    try:
        res = main()
    except Exception as e:
        send_discord_notification(e)
        logging.exception(e)
    sys.exit(res)
