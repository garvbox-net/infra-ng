#!/usr/bin/env python3
"""
Quick hack to update certbot cert and
prep it for use in haproxy
Also bounce haproxy to pick up new cert

Idea for this was got here:
https://serversforhackers.com/c/letsencrypt-with-haproxy

"""
import logging
import os
import subprocess
import sys

from util.misc import config_logger, send_mail

# General Settings
MAIL_TO = "support@garvbox.net"

# HAproxy Certs
HAPR_PROD_CERT = "/etc/haproxy/ssl/private/secure.garvbox.net.pem"

# LetsEncrypt Certs
LE_CERT_PATH = "/etc/letsencrypt/live/secure.garvbox.net"
LE_FULLCHAIN = LE_CERT_PATH + "/fullchain.pem"  # fullchain
LE_PRIVKEY = LE_CERT_PATH + "/privkey.pem"  # private key


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
    # Configure the logger
    config_logger(logging.INFO)

    # Default Response code OK
    resp_code = 0

    # Run Cert renewal process, encapsulated in error catcher for mailing
    try:
        run_cert_update()
        load_cert_haproxy()
    except CertRenewalFail as e:
        logging.error(str(e))
        send_mail(
            MAIL_TO,
            "HAproxy LE Cert Renewal Failed",
            "Cert renewal process failed, error:\n{e}",
        )
        resp_code = e.respcode

    return resp_code


def run_cert_update():
    """Certificate Update Procedure"""
    logging.info("Running Certificate Renewal")
    # Update cert
    cmd_renew = "certbot renew --force-renew --preferred-challenges http --http-01-port=8888"
    if subprocess.call(cmd_renew.split()) != 0:
        raise CertRenewalFail("Failed to renew cert...", respcode=1)


def load_cert_haproxy():
    # Check if we renewed
    if os.path.getmtime(LE_FULLCHAIN) <= os.path.getmtime(HAPR_PROD_CERT):
        logging.info("No cert updated - quitting as there is no need to reload haproxy")
        return

    logging.info("Cert renewed - continue with building chain for HAproxy")
    # Build concatenated cert
    cat_c = f"cat {LE_FULLCHAIN} {LE_PRIVKEY} > {HAPR_PROD_CERT}.tmp"
    if subprocess.call(cat_c, shell=True) != 0:
        raise CertLoadFail("Failed to build cert for HAproxy")

    # Backup prod cert, move in new one and bounce HAproxy
    if not os.path.isfile(HAPR_PROD_CERT):
        # touch prod cert if doesnt exist
        open(HAPR_PROD_CERT, "w").close()

    c_backup = f"cp -fp {HAPR_PROD_CERT} {HAPR_PROD_CERT}.bkp"
    if subprocess.call(c_backup.split()) != 0:
        raise CertLoadFail("Failed to back up cert")

    c_mv = f"mv -f {HAPR_PROD_CERT}.tmp {HAPR_PROD_CERT}"
    if subprocess.call(c_mv.split()) != 0:
        raise CertLoadFail("Failed to replace prod cert")

    logging.info("Restarting HAproxy...")
    if subprocess.call("systemctl reload haproxy".split()) != 0:
        raise CertLoadFail("Failed to reload HAProxy!")


if __name__ == "__main__":
    sys.exit(main())
