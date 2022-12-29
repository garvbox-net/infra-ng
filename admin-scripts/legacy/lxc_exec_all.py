#!/usr/bin/env python3
""" Run command on all running containers """
import sys
import argparse

from util import lxc_cli


def main():
    pr = argparse.ArgumentParser()
    pr.add_argument(
        "--container",
        help="Container name to run command in, or 'all' to run in all (default=all)",
        default="all",
    )
    pr.add_argument(
        "--remote",
        help="Remote machine to connect to, default runs on the local machine",
    )
    pr.add_argument("--cmd", help="Command to run on containers", required=True)
    options = pr.parse_args()

    containers = lxc_cli.get_running_containers(options.remote)
    if options.container != "all":
        if options.container not in containers:
            print(
                f"ERROR: Container does not exist or is not running: {options.container}"
            )
            return 1
        containers = [options.container]

    for container in containers:
        print(f"Running command on container: {container}")
        res = lxc_cli.lxc_exec(container, options.cmd, options.remote)
        print(res.stdout.decode("UTF-8"))


if __name__ == "__main__":
    sys.exit(main())
