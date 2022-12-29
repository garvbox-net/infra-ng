""" Miscellaneous Utilities: Logging, emails etc """

import copy
import logging
from smtplib import SMTP
from email.mime.text import MIMEText

# Email Settings
FROM_MAIL = "support@garvbox.net"
SMTP_RELAY = "smtp.upcmail.ie"


def config_logger(loglevel=logging.INFO, logfile=None):
    """ Standardised Logging configurer

    Args:
        loglevel (int): Logging level - standardised logger levels
        logfile (str): Path to a log file to automatically create a rotating log file
    """
    # Clear any existing root logging handlers
    while len(logging.root.handlers) > 0:
        logging.root.removeHandler(logging.root.handlers[-1])
    logging.root.setLevel(loglevel)

    log_time = "%(asctime)-15s %(levelname)8s"
    basic_func_info = "%(filename)20.20s:%(lineno)4s"
    ext_func_info = "%(filename)20s:%(lineno)4s - %(funcName)20.20s()"
    logformat = f"[{log_time}] "
    if loglevel == logging.DEBUG:
        # debug log gets extra info in log format - add function name
        logformat += f"[{ext_func_info}]"
    else:
        logformat += f"[{basic_func_info}]"
    logformat += " %(message)s"

    console_handler = logging.StreamHandler()
    console_handler.setLevel(loglevel)
    console_handler.setFormatter(ColouredLogFormatter(logformat))

    if logfile:
        file_handler = logging.handlers.RotatingFileHandler(
            logfile, maxBytes=1024 ** 2, backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(logformat))
        logging.root.addHandler(file_handler)


class ColouredLogFormatter(logging.Formatter):
    """ Coloured Log Formatter """

    COLOURS = {
        "CRITICAL": "\x1b[31m",  # red
        "ERROR": "\x1b[31m",  # red
        "WARNING": "\x1b[33m",  # yellow
        "INFO": "\x1b[32m",  # green
        "DEBUG": "\x1b[35m",  # pink
    }
    RESET_SEQ = "\x1b[0m"

    def format(self, record):
        # Copy the log message and return coloured one
        # We dont want to modify for any other handlers
        coloured_record = copy.copy(record)
        if coloured_record.levelname in ColouredLogFormatter.COLOURS:
            coloured_record.msg = (
                ColouredLogFormatter.COLOURS[coloured_record.levelname]
                + str(coloured_record.msg)
                + ColouredLogFormatter.RESET_SEQ
            )
        return logging.Formatter.format(self, coloured_record)


def send_mail(to_addr, subject, content):
    """ Send simple email to recipient """
    server = SMTP(SMTP_RELAY)
    msg = MIMEText(content)
    msg["Subject"] = subject
    msg["From"] = FROM_MAIL
    msg["To"] = to_addr
    server.send_message(msg)
    server.quit()
