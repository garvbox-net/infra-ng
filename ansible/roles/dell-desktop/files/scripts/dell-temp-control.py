#!/usr/bin/env python3
"""Temp Control Script for Jankedy Jank Dell Fan speed control

Inspired by
https://github.com/vitorafsr/i8kutils/issues/25#issuecomment-1097806307
"""
import logging
import os
import re
import subprocess
import sys
from argparse import ArgumentParser
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from statistics import mean
from time import sleep
from typing import Optional, Sequence

HWMON_BASE = "/sys/class/hwmon"
I8KFAN = "/usr/bin/i8kfan"
UNSET_TEMP = -100
TEMP_HIST = 5
TEMP_WEIGHT_FACTOR = 5
DRY_RUN = False


@dataclass
class TempSensor:
    label: str
    idx: str
    max: int
    input: Path

    def read_temp(self) -> int:
        return int(self.input.read_text().strip())


@dataclass
class Thresholds:
    lower: int
    upper: int
    buffer: int

    @staticmethod
    def from_input(lower, upper, buffer) -> "Thresholds":
        return Thresholds(*(int(inp * 1000) for inp in (lower, upper, buffer)))


class FanState(Enum):
    UNKNOWN = -1
    OFF = 0
    LOW = 1
    HIGH = 2
    SYSTEM = 3


def main():
    p = ArgumentParser()
    p.add_argument("--module", required=True, help="hwmon module name (e.g. coretemp)")
    p.add_argument(
        "--interval",
        type=float,
        default=1,
        help="Interval between fan speed checks (in seconds) (Default: %(default)s)",
    )
    p.add_argument(
        "--sensor",
        required=True,
        help="Temp sensor Name regex (e.g. 'Package id \\d+')",
    )
    p.add_argument(
        "--threshold-lower",
        "-l",
        dest="lower",
        type=int,
        default=40,
        help="Set fan speed lower threshold (Default: %(default)s)",
    )
    p.add_argument(
        "--threshold-upper",
        "-u",
        dest="upper",
        type=int,
        default=60,
        help="Set fan speed upper threshold (Default: %(default)s)",
    )
    p.add_argument(
        "--threshold-buffer",
        "-b",
        dest="buffer",
        type=int,
        default=5,
        help="Threshold buffer (for debouncing) (Default: %(default)s)",
    )
    p.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Dry Run - do not change fan speeds (reccomend debug logging)",
    )
    opts = p.parse_args()

    # Set up logger, stripped well back for systemd unit which has timestamps in it
    if os.getenv("DEBUG"):
        log_lvl = logging.DEBUG
        log_fmt = "[%(asctime)s] [%(levelname)8s] [%(funcName)24.24s()] %(message)s"
    else:
        log_lvl = logging.INFO
        log_fmt = "[%(levelname)8s] %(message)s"
    logging.basicConfig(level=log_lvl, format=log_fmt, datefmt="%Y-%m-%d %H:%M:%S")

    if opts.dry_run:
        global DRY_RUN
        DRY_RUN = opts.dry_run

    module_path = get_hwmon_module(opts.module)
    logging.info(f"Monitor Module path: {module_path}")
    sensor = get_temp_sensor(module_path, "Package id 0")
    logging.info(
        f"Found Temp sensor: '{sensor.label}' -> reading: {sensor.read_temp() / 1000}C"
    )
    thresholds = Thresholds.from_input(
        lower=opts.lower, upper=opts.upper, buffer=opts.buffer
    )
    logging.info(f"Using temp thresholds: {thresholds}")
    weights = range(TEMP_HIST * TEMP_WEIGHT_FACTOR, 1, -TEMP_WEIGHT_FACTOR)
    logging.info(f"Computed weights for rolling average: {list(weights)}")
    last_state_requested = None
    temp_readings = deque(maxlen=TEMP_HIST)
    while True:
        try:
            last_state_requested = fancontrol(
                sensor, thresholds, last_state_requested, temp_readings, weights
            )
        except Exception as e:
            # Catch any exceptions reading files etc, allowing to run forever
            if isinstance(e, KeyboardInterrupt):
                logging.info("Stopping with ctrl+c")
                break
            logging.exception(e)
        sleep(opts.interval)
    return 0


def fancontrol(
    sensor: TempSensor,
    thresholds: Thresholds,
    last_state_requested: Optional[FanState],
    temp_readings: deque[int],
    weights: Sequence[int],
) -> Optional[FanState]:
    """Simple threshold based temp controller

    Provided lower,upper threshold can set the fan speed to one of 3 levels
    if temp < lower threshold - set to minimum
    if lower < temp < upper - set to mid
    if temp > upper - set to max
    """
    fan_state = get_fan_state()
    temp = sensor.read_temp()
    if not temp_readings:
        # Set initial values so that ramp-up isnt too slow starting
        temp_readings.extendleft([temp] * TEMP_HIST)
    temp_readings.appendleft(temp)

    weighted_average = int(
        sum(weight * val for weight, val in zip(weights, temp_readings)) / sum(weights)
    )
    logging.debug(
        f"Running Fan control: {fan_state=}, {temp=}, {weighted_average=}, {temp_readings=}"
    )
    # NOTE: i8kfan reports weird fan states, the checks below are experimentally evaluated,
    # but the target fan states should be correctly named
    if min(weighted_average, temp) < thresholds.lower and fan_state != FanState.LOW:
        state_requested = set_fan_state(FanState.OFF, last_state_requested)
    elif (
        thresholds.upper > mean((temp, weighted_average)) > thresholds.lower
        and fan_state != FanState.UNKNOWN
    ):
        state_requested = set_fan_state(FanState.LOW, last_state_requested)
    elif max(weighted_average, temp) > thresholds.upper and fan_state != FanState.HIGH:
        state_requested = set_fan_state(FanState.HIGH, last_state_requested)
    else:
        logging.debug("No Fan speed changes needed")
        state_requested = last_state_requested
    return state_requested


def get_hwmon_module(module_name: str) -> Path:
    """Read hwmon module names and find the path for desired one

    since these could change on reboot if loaded in a different order
    """
    hwmon_base = Path(HWMON_BASE)
    for path in hwmon_base.iterdir():
        logging.debug(f"Checking path: {path}")
        mod_name_file = path / "name"
        try:
            mod_name = mod_name_file.read_text().strip()
            logging.debug(f"Got module name from {mod_name_file}: {mod_name}")
        except IOError as e:
            logging.error(f"Failed to read {mod_name_file}: {e}")
            continue
        if mod_name == module_name:
            logging.info(f"Found module name: {mod_name}")
            return path
    raise IOError("HwMon Module Not found")


def get_temp_sensor(module_path: Path, sensor_name_re: str) -> TempSensor:
    """Given Hwmon module and desired sensor regex, get the sensor metadata"""
    matcher = re.compile(sensor_name_re)
    for s_name_path in module_path.glob("temp*_label"):
        sensor_label = s_name_path.read_text().strip()
        logging.debug(f"Checking sensor label from: {s_name_path}")
        if matcher.match(sensor_label):
            sensor_index = s_name_path.name.replace("_label", "")
            logging.debug(f"Found Temp sensor label match: {sensor_label}")
            break
    else:
        raise IOError("Temp Sensor Not found")
    max_temp = int((module_path / f"{sensor_index}_max").read_text().strip())
    return TempSensor(
        label=sensor_label,
        idx=sensor_index,
        max=max_temp,
        input=module_path / f"{sensor_index}_input",
    )


def get_fan_state() -> int:
    logging.debug("Getting i8kfan state")
    res = subprocess.run([I8KFAN], check=True, capture_output=True, text=True)
    output = res.stdout.strip()
    logging.debug(f"i8kfan output: {output}")
    fan_status = output.split(" ")[-1]
    return int(fan_status)


def set_fan_state(
    requested_fan_state: FanState, last_fan_state: Optional[FanState]
) -> FanState:
    if last_fan_state == requested_fan_state and last_fan_state is not None:
        logging.debug(
            f"Last Fan state = Requested Fan State ({requested_fan_state}), "
            "not requesting duplicate change"
        )
        return last_fan_state
    logging.debug(f"Setting Fan speed to {requested_fan_state.name}")
    cmd = [I8KFAN, "-", str(requested_fan_state.value)]
    logging.debug(f"Running command: {' '.join(cmd)}")
    if DRY_RUN:
        logging.info(f"DRY_RUN Mode, would have executed: '{cmd}'")
    else:
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.debug(f"i8kfan output: {res.stdout.strip()}")
    return requested_fan_state


if __name__ == "__main__":
    sys.exit(main())
