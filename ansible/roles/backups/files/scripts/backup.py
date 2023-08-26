#!/usr/bin/env python3
import logging
import os
import re
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from datetime import datetime
from typing import Any, ClassVar, List, Protocol, Type

_truthy_strs = ["true", "1", "y", "yes"]
DEBUG = os.getenv("DEBUG", "").lower() in _truthy_strs
DRY_RUN = os.getenv("DRY_RUN", "").lower() in _truthy_strs


def main():
    snapshotter, options = _get_snapshotter_from_args([ZfsSnapshotter])
    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format="[%(asctime)s] [%(levelname)8s] [%(funcName)12.12s()] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=options.log_file,
    )

    # Check root perms
    if not DRY_RUN and os.geteuid() != 0:
        print("ERROR: Root permissions needed for Snapshots")
        return 1

    try:
        snap_name = snapshotter.create_snapshot()
        snapshotter.backup_snapshot(snap_name)
        snapshotter.prune()
    except BackupError as e:
        logging.error(str(e))
        return e.return_code


def _get_snapshotter_from_args(supported_snapshotters: List[Type["Snapshotter"]]):
    p = ArgumentParser()
    p.add_argument("--log-file", type=str, help="Log File location")
    p.add_argument(
        "--type",
        dest="snapshotter_type",
        required=True,
        choices=[st.name for st in supported_snapshotters],
        help="Snapshotter Type",
    )
    for snapshotter_type in supported_snapshotters:
        grp = p.add_argument_group(snapshotter_type.name)
        for arg, kwargs in snapshotter_type.args.items():
            grp.add_argument(arg, **kwargs)
    options = p.parse_args()
    snapshotter_type = options.__dict__.pop("snapshotter_type")
    snapshotter = next(st for st in supported_snapshotters if st.name == snapshotter_type)(options)
    return snapshotter, options


class BackupError(RuntimeError):
    """Generic Backup Failure"""

    return_code: int

    def __init__(self, msg, return_code: int = 1, *args, **kwargs) -> None:
        super().__init__(msg, *args, **kwargs)
        self.return_code = return_code


class Snapshotter(Protocol):
    name: ClassVar[str]
    args: ClassVar[dict[str, dict[str, Any]]]

    options: Namespace

    def __init__(self, options: Namespace) -> None:
        ...

    def create_snapshot(self) -> str:
        ...

    def backup_snapshot(self, snap_name: str):
        ...

    def prune(self):
        ...


class ZfsSnapshotter:
    name: ClassVar = "zfs"
    args: ClassVar = {
        "--src-dataset": {"help": "Source ZFS Dataset for Snapshot", "required": True},
        "--dest-dataset": {"help": "Destination Backup Dataset"},
        "--dest-directory": {"help": "Destination Backup Directory"},
        "--snap-prefix": {"help": "Snapshot Name Prefix", "default": "backup"},
    }

    snap_prefix: str
    source_dataset: str
    dest_dataset: str
    dest_dir: str
    _snap_cache: dict[str, list[str]]

    def __init__(self, options: Namespace) -> None:
        self.options = options
        self._snap_cache = defaultdict(list)
        # Convenience helpers from class options
        self.snap_prefix = options.snap_prefix
        self.source_dataset = options.src_dataset
        self.dest_dataset = options.dest_dataset
        self.dest_dir = options.dest_directory

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:
        parser.add_argument("--src-dataset", help="Source ZFS Dataset for Snapshot", required=True)
        parser.add_argument("--snap-prefix", help="Snapshot Name Prefix", default="backup")
        parser.add_argument("--dest-dataset", help="Destination ZFS Dataset (snapshot replication)")
        parser.add_argument("--dest-directory", help="Destination Directory (tar backup)")
        parser.add_argument(
            "--ssh-user-host", help="SSH user@host for remote backups (Requires ssh trust)"
        )

    def create_snapshot(self) -> str:
        """Create a Snapshot for Backup on the defined source dataset"""
        res = _run_cmd(f"zfs list -H {self.source_dataset}", check=False)
        if res.returncode != 0:
            raise BackupError(f"Error: {res.stderr.decode().strip()}", return_code=res.returncode)
        date_str = datetime.now().strftime("%y%m%d_%H%M%S")
        snap_name = f"{self.source_dataset}@{self.snap_prefix}_{date_str}"
        logging.info("Taking zfs snapshot: " + snap_name)
        _run_cmd(f"zfs snap -r {snap_name}")
        self._snap_cache.pop(self.source_dataset, None)  # force cache refresh
        return snap_name

    def backup_snapshot(self, snap_name: str):
        """Send Snapshot to the designated targets"""
        # ZFS-specific behaviour: we can locate a source snap for incremental replication
        incremental_src = self.get_incremental_source_snap(snap_name)
        if incremental_src and incremental_src in self._get_snaps(self.dest_dataset):
            logging.info(
                f"Found incremental source snapshot {incremental_src} and matching replica on "
                "destination - using incremental snapshot"
            )
            # FIXME: Add incremental replication cmd
            raise NotImplementedError("Incremental replication not done yet")
        else:
            logging.info("No source snapshots for Incremental Replication - making full copy")
            # FIXME: Add full replication cmd and options
            # _run_cmd(f"zfs send -R {src} | zfs recv {}", shell=True)

    def prune(self):
        """Prune Source snaps not needed (and Destination if using snapshot replication)"""
        ...

    def get_incremental_source_snap(self, new_snap_exclude: str) -> str | None:
        """Get the Last snapshot for incremental replication"""
        snapshots = self._get_snaps(self.source_dataset)
        if new_snap_exclude in snapshots:
            snapshots.remove(new_snap_exclude)
        return sorted(snapshots)[0] if snapshots else None

    def get_dest_snapshots(self) -> list[str]:
        ...

    def remove_src_snapshot(self, snapshot_name: str):
        """Remove Snapshot after Backup completed"""
        ...

    def _get_snaps(self, dataset_name: str) -> list[str]:
        """Gets a list of snapshot names, filtered by the backup prefix and date regex"""
        if dataset_name not in self._snap_cache:
            logging.debug(f"Getting snapshots for {dataset_name}")
            snap_pattern = rf"{dataset_name}@({self.snap_prefix}\w+_\d+_\d+)"
            res = _run_cmd(f"zfs list -H -t snap {dataset_name}")
            snap_names = []
            for line in res.stdout.splitlines():
                stripped_line = line.decode().split()[0]
                logging.debug(f"Parsing snapshot output: {stripped_line}")
                match = re.match(snap_pattern, stripped_line)
                if not match:
                    logging.debug(
                        f"No match for snapshot: {stripped_line} with pattern {snap_pattern}"
                    )
                    continue
                snap_names.append(match.group(1))
            self._snap_cache[dataset_name] = snap_names
        return self._snap_cache[dataset_name]


def _run_cmd(command: str, check=True, shell=False) -> subprocess.CompletedProcess:
    cmd = command if shell else command.split(" ")
    if DRY_RUN:
        logging.info(f"Dry Run - would have run: {command}")
        res = subprocess.CompletedProcess(cmd, 0, "", "")
    else:
        res = subprocess.run(cmd, check=check, shell=shell, capture_output=True)
    return res


if __name__ == "__main__":
    sys.exit(main())
