#!/usr/bin/env python3
import os
import sys
import time
import json
import logging
from argparse import ArgumentParser
from urllib.request import urlopen

# Global Settings
cache_ip_file = "/tmp/ip.cache"
nm_server = "dynamicdns.park-your-domain.com"


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--debug", action="store_true", help="Debug mode - increased logging"
    )
    parser.add_argument(
        "--fqdn",
        help="Fully Qualified domain name to update - "
        + "will be split into host + domain",
    )
    parser.add_argument("--password", help="API Password (namecheap)")
    opts = parser.parse_args()

    loglevel = logging.INFO
    if opts.debug:
        loglevel = logging.DEBUG

    FORMAT = "[%(asctime)s] [%(levelname)7s]\
[%(filename)-10s:%(lineno)3s - %(funcName)10s()] %(message)s"
    DATEFMT = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=loglevel, format=FORMAT, datefmt=DATEFMT)

    logging.info("DNS Update Script Run - " + time.strftime("%Y-%m-%d %H:%M"))
    # Try to load cached IP file
    if os.path.isfile(cache_ip_file):
        logging.debug("Loading IP from cache")
        with open(cache_ip_file) as f_ip:
            cached_ip = json.load(f_ip).get("ip")
    else:
        logging.info("No Cached IP Found - just update current IP")
        cached_ip = None

    ip_url = "https://api.ipify.org/?format=json"
    curr_ip = json.loads(urlopen(ip_url).read().decode("utf-8")).get("ip")
    if not curr_ip:
        logging.error("Error Parsing Current IP Address!")

    if curr_ip == cached_ip:
        logging.info("Current IP matches cached version - no update needed")
        return 0
    logging.info(
        "IP addresses have changed - need update. (Old: {ol}, New: {nw})".format(
            ol=cached_ip, nw=curr_ip
        )
    )

    # Get Domain and host names
    arr_fqdn = opts.fqdn.split(".")
    host = arr_fqdn[0]
    dom = arr_fqdn[1] + "." + arr_fqdn[2]

    st_upd_url = "http://{tgt}/update?host={host}&domain={dm}&password={pw}"
    upd_url = st_upd_url.format(tgt=nm_server, host=host, dm=dom, pw=opts.password)
    logging.debug("Call URL: " + upd_url)

    logging.info("Updating DNS Record: " + host + "." + dom)
    resp_nm = urlopen(upd_url)
    resp_data = resp_nm.read().decode("utf-8")

    # check return code
    if resp_nm.getcode() != 200:
        logging.error("Update response code not OK: " + str(resp_nm.getcode()))
        print("Response Data:\n" + resp_data + "\n")
        return 1

    # Check for errors in response
    if "<ErrCount>0</ErrCount>" not in resp_data:
        logging.error("Errors found in response data:\n" + resp_data + "\n")
        return 2

    logging.info("Update OK - store IP address in cache")
    with open(cache_ip_file, "w") as f_cache:
        logging.debug("Storing IP to cache file: " + f_cache.name)
        json.dump({"ip": curr_ip}, f_cache)

    return 0  # Return OK if no errors


if __name__ == "__main__":
    sys.exit(main())
