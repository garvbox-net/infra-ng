#!/usr/bin/env python3
import os
from argparse import ArgumentParser
from typing import ClassVar, Dict, List, Protocol, Tuple, Type


class BackupError(RuntimeError):
    """Generic Backup Failure"""


class Snapshotter(Protocol):
    name: ClassVar[str]
    args: ClassVar[Tuple[str, Dict]]

    def create_snapshot(self):
        pass

    def get_snapshots(self):
        pass

    def prune(self):
        pass


class ZfsSnapshotter:
    name: ClassVar = "zfs"
    args: ClassVar = ("--src_dataset", dict(action="store_true"))


class LvmSnapshotter:
    name: ClassVar = "lvm"
    args: ClassVar = ("--src_lv", dict(action="store_true"))


class BackupController:
    def __init__(self, snapshotter: Snapshotter) -> None:
        self.snapshotter = snapshotter

    def run(self):
        self.snapshotter.create_snapshot()


def main():
    supported_snapshotters: List[Type[Snapshotter]] = [ZfsSnapshotter, LvmSnapshotter]

    p = ArgumentParser()
    p.add_argument("--type", required=True, options=[], help="Snapshotter Type")
    subparsers = p.add_subparsers()
    for snapshotter in supported_snapshotters:
        sp = subparsers.add_parser(snapshotter.name)
        for args, kwargs in snapshotter.args:
            sp.add_argument(*args, **kwargs)
