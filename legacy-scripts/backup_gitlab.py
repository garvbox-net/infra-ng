#!/usr/bin/python3
"""
Backup_gitlab.py

Back up /etc/gitlab and gitlab database to provided location
Enforce file retention from input arguments

"""
import os
import subprocess
import sys
from argparse import ArgumentParser
from datetime import date, datetime
from glob import glob


def main():
    p = ArgumentParser()
    p.add_argument("--tgt", default="/var/backups/gitlab", help="Target backup directory")
    p.add_argument("--num_backups", default=6, type=int, help="Number of backups to keep")
    p.add_argument("--backup_tgt", help="External backup target, rsync format")
    opts = p.parse_args()

    date_str = date.today().strftime("%y_%m_%d")
    print("Running gitlab backups - " + str(datetime.utcnow()))

    # Check root perms
    if os.geteuid() != 0:
        print("ERROR: Root permissions needed for Backups")
        return 1

    if not os.path.isdir(opts.tgt):
        print("Creating backup dir: " + opts.tgt)
        os.mkdir(opts.tgt)

    print("Creating backup of /etc/gitlab")
    etc_name = opts.tgt + "/etc_gitlab_" + date_str + ".tar.gz"
    subprocess.check_call(["tar", "-czf", etc_name, "/etc/gitlab"])

    bk_files = sorted(glob(opts.tgt + "/etc_gitlab*.tar.gz"), reverse=True)
    while len(bk_files) > opts.num_backups:
        f_remove = bk_files.pop()
        print("Removing old backup of /etc/gitlab: " + f_remove)
        os.remove(f_remove)

    print("Running gitlab backup procedure...")
    subprocess.check_call(["gitlab-rake", "gitlab:backup:create", "CRON=1"])
    # gitlab prunes its old backups automatically - nothing else to do here

    if opts.backup_tgt:
        print("Rsync backups folder to targets")
        subprocess.call(["rsync", "--delete", "-avh", opts.tgt, opts.backup_tgt])
    return 0


if __name__ == "__main__":
    sys.exit(main())
