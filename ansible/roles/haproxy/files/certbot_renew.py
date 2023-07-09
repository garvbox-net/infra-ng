#!/usr/bin/env python3
"""Quick hack to update certbot cert and prep it for use in haproxy

Also bounce haproxy to pick up new cert
"""
import configparser
import logging
import os
import subprocess
import sys


class CertRenewalFail(Exception):
    """Basic Cert Renewal Exception Used for error capture and emailing"""

    DEFAULT_RESPCODE = 1

    def __init__(self, msg, respcode=None):
        self.respcode = respcode if respcode is not None else self.DEFAULT_RESPCODE
        super().__init__(msg)


class CertLoadFail(CertRenewalFail):
    """Problem Loading Cert to HAproxy"""

    DEFAULT_RESPCODE = 2


def main():
    # Set up stdout basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)-15s %(levelname)8s] [%(filename)20.20s:%(lineno)4s] %(message)s",
    )

    cfg = configparser.ConfigParser()
    if cfg.read("/etc/certbot_renew.cfg") == 0:
        raise CertRenewalFail(msg="Missing config file certbot_renew.cfg", respcode=-1)
    config = cfg["DEFAULT"]

    # Default Response code OK
    resp_code = 0

    # Run Cert renewal process, encapsulated in error catcher for notifications
    # TODO: Add discord or some notifications
    try:
        run_cert_update()
        load_cert_haproxy(config)
    except CertRenewalFail as e:
        logging.error(str(e))
        resp_code = e.respcode

    return resp_code


def run_cert_update():
    """Certificate Update Procedure"""
    if os.getenv("NO_RENEW") == "1":
        logging.info("NO_RENEW env var set - Skipping Cert renewal")
        return
    logging.info("Running Certificate Renewal")
    # Update cert
    cmd_renew = "certbot renew --force-renew --preferred-challenges http --http-01-port=8888"
    if subprocess.call(cmd_renew.split()) != 0:
        raise CertRenewalFail("Failed to renew cert...", respcode=1)


def load_cert_haproxy(config):
    """Attempt to Load HAproxy Cert

    Args:
        config (configparser.SectionProxy): Config loaded from file
    """

    CERT_NAME = config["CERT_NAME"]
    PROD_CERT = os.path.join(
        config.get("CERT_PATH", fallback="/etc/ssl/private"), CERT_NAME + ".pem"
    )

    # LetsEncrypt Certs
    LE_CERT_DIR = os.path.join(config.get("LE_PATH", fallback="/etc/letsencrypt/live"), CERT_NAME)
    LE_FULLCHAIN = LE_CERT_DIR + "/fullchain.pem"  # fullchain
    LE_PRIVKEY = LE_CERT_DIR + "/privkey.pem"  # private key

    # Check if we renewed
    if os.path.getmtime(LE_FULLCHAIN) <= os.path.getmtime(PROD_CERT):
        logging.info("No cert updated - quitting as there is no need to reload haproxy")
        return

    logging.info("Cert renewed - continue with building chain for HAproxy")
    # Build concatenated cert
    cat_c = f"cat {LE_FULLCHAIN} {LE_PRIVKEY} > {PROD_CERT}.tmp"
    if subprocess.call(cat_c, shell=True) != 0:
        raise CertLoadFail("Failed to build cert for HAproxy")

    # Backup prod cert, move in new one and bounce HAproxy
    if not os.path.isfile(PROD_CERT):
        # touch prod cert if doesnt exist
        open(PROD_CERT, "w").close()

    c_backup = f"cp -fp {PROD_CERT} {PROD_CERT}.bkp"
    if subprocess.call(c_backup.split()) != 0:
        raise CertLoadFail("Failed to back up cert")

    c_mv = f"mv -f {PROD_CERT}.tmp {PROD_CERT}"
    if subprocess.call(c_mv.split()) != 0:
        raise CertLoadFail("Failed to replace prod cert")

    logging.info("Restarting HAproxy...")
    if subprocess.call("systemctl reload haproxy".split()) != 0:
        raise CertLoadFail("Failed to reload HAProxy!")


if __name__ == "__main__":
    sys.exit(main())
