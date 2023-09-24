#!/usr/bin/env python3
import logging
import os
import platform
import re
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, List, Protocol, Type

import requests

_truthy_strs = ["true", "1", "y", "yes"]
DEBUG = os.getenv("DEBUG", "").lower() in _truthy_strs
DRY_RUN = os.getenv("DRY_RUN", "").lower() in _truthy_strs
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


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
        snap_name = snapshotter.create_source_snapshot()
        snapshotter.backup_snapshot(snap_name)
        snapshotter.prune()
    except BackupError as e:
        logging.error(str(e))
        send_discord_notification(e)
        return e.return_code
    except Exception as e:
        send_discord_notification(e)
        raise


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


class SnapShotVolume(Protocol):
    name: ClassVar[str]

    def exists(self) -> bool:
        ...

    def create_snapshot(self, snapshot_prefix: str) -> str:
        ...

    def destroy_snapshot(self, snapshot: str) -> None:
        ...

    def get_snapshots(self, snapshot_prefix: str) -> list[str]:
        ...

    def prune_snapshots(self):
        ...


class Snapshotter(Protocol):
    name: ClassVar[str]
    args: ClassVar[dict[str, dict[str, Any]]]

    options: Namespace

    def __init__(self, options: Namespace) -> None:
        ...

    def create_source_snapshot(self) -> str:
        ...

    def backup_snapshot(self, snapshot: str):
        ...

    def prune(self):
        ...


@dataclass
class ZfsDataSet:
    name: str
    remote_host: str | None = None

    def exists(self):
        return _run_cmd(f"zfs list -H {self.name}", check=False).returncode == 0

    def create_snapshot(self, snapshot_prefix: str) -> str:
        date_str = datetime.now().strftime("%y%m%d_%H%M%S")
        snapshot_name = f"{snapshot_prefix}_{date_str}"
        logging.info("Taking zfs snapshot: " + snapshot_name)
        _run_cmd(f"zfs snap -r {self.name}@{snapshot_name}")
        return snapshot_name

    def get_snapshots(self, snapshot_prefix: str) -> list[str]:
        logging.debug(f"Getting snapshots for {self.name}")
        snap_pattern = rf"{self.name}@({snapshot_prefix}_\d+_\d+)"
        res = _run_cmd(f"zfs list -H -t snap {self.name}")
        snap_names = []
        for line in res.stdout.splitlines():
            stripped_line = line.decode().split()[0]
            logging.debug(f"Parsing snapshot output: {stripped_line}")
            match = re.match(snap_pattern, stripped_line)
            if not match:
                logging.debug(f"No match for snapshot: {stripped_line} with pattern {snap_pattern}")
                continue
            snap_names.append(match.group(1))
        return sorted(snap_names)

    def delete_snapshot(self, snapshot: str):
        logging.info(f"Deleting Snapshot: {snapshot}")
        _run_cmd(f"zfs destroy -R {self.name}@{snapshot}")


class ZfsSnapshotter:
    name: ClassVar = "zfs"
    args: ClassVar = {
        "--src-dataset": {"help": "Source ZFS Dataset for Snapshot", "required": True},
        "--dest-dataset": {"help": "Destination Backup Dataset"},
        "--dest-directory": {"help": "Destination Backup Directory"},
        "--snap-prefix": {"help": "Snapshot Name Prefix", "default": "backup"},
        "--num-snaps": {
            "help": "Number of Snapshots to keep (Local and Remote)",
            "type": int,
            "default": 3,
        },
    }

    snap_prefix: str
    source_dataset: ZfsDataSet
    dest_dataset: ZfsDataSet | None = None

    def __init__(self, options: Namespace) -> None:
        self.options = options
        # Convenience helpers from class options
        self.snap_prefix = options.snap_prefix
        self.source_dataset = ZfsDataSet(options.src_dataset)
        self.dest_dataset = ZfsDataSet(options.dest_dataset) if options.dest_dataset else None

    def create_source_snapshot(self) -> str:
        """Create a Snapshot for Backup on the defined source dataset"""
        if not self.source_dataset.exists():
            raise BackupError(f"Dataset does not exist: {self.source_dataset.name}")
        return self.source_dataset.create_snapshot(self.snap_prefix)

    def backup_snapshot(self, snapshot: str):
        """Send Snapshot to the designated targets"""
        if not self.dest_dataset:
            raise BackupError("Error: Destination Dataset for backups not provided")
        # ZFS-specific behaviour: we can locate a source snap for incremental replication
        incremental_src = self._get_incremental_source(self.source_dataset, snapshot)
        src_ds_name = self.source_dataset.name
        if incremental_src and incremental_src in self.dest_dataset.get_snapshots(self.snap_prefix):
            logging.info(
                f"Found incremental source snapshot {incremental_src} and matching replica on "
                "destination - using incremental snapshot"
            )
            src_path = f"-i {src_ds_name}@{incremental_src} {src_ds_name}@{snapshot}"
        else:
            logging.info("No source snapshots for Incremental Replication - making full copy")
            src_path = f"{src_ds_name}@{snapshot}"
        _run_cmd(
            f"zfs send -R {src_path} | zfs recv -F {self.dest_dataset.name}",
            shell=True,
        )

    def prune(self):
        """Prune Source snaps not needed (and Destination if using snapshot replication)"""
        datasets = [self.source_dataset]
        if self.dest_dataset is not None:
            datasets.append(self.dest_dataset)
        for dataset in datasets:
            snap_names = dataset.get_snapshots(self.snap_prefix)
            if self.options.num_snaps > len(snap_names):
                logging.info(f"No snapshots to prune on {dataset.name}")
                continue
            snaps_to_delete = snap_names[self.options.num_snaps :]
            for snap_name in snaps_to_delete:
                dataset.delete_snapshot(snap_name)

    def _get_incremental_source(self, dataset: ZfsDataSet, exclude_snap: str) -> str | None:
        """Get the Last snapshot for incremental replication"""
        snapshots = dataset.get_snapshots(self.snap_prefix)
        if exclude_snap in snapshots:
            snapshots.remove(exclude_snap)
        return snapshots[0] if snapshots else None


def send_discord_notification(message):
    if WEBHOOK_URL is None:
        logging.info("Webhook not set - skipping notification")
        return
    logging.info("Sending Discord Notification")
    requests.post(
        WEBHOOK_URL,
        json={"username": platform.node(), "content": f"Backup Error:\n{message}"},
    )


def _run_cmd(command: str, check=True, shell=False) -> subprocess.CompletedProcess:
    if "destroy" in command and "@" not in command:
        raise BackupError(f"Destroy protection prevented running command: {command}")
    cmd = command if shell else command.split(" ")
    if DRY_RUN:
        logging.info(f"Dry Run - would have run: {command}")
        res = subprocess.CompletedProcess(cmd, 0, "", "")
    else:
        logging.debug(f"Running Command: {cmd}")
        try:
            res = subprocess.run(cmd, check=check, shell=shell, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise BackupError(f"Error: {e.stderr.decode().strip()}", return_code=e.returncode)
    return res


if __name__ == "__main__":
    sys.exit(main())
