# -*- encoding: utf-8 -*-
'''
@Filename   : logger.py
@Description: Customized logger class for printing info and error.
@Date       : 2020/03/22 18:57:27
@Author     : Wu Jiahao
@contact    : https://github.com/flamywhale
'''
import logging

# Custom formatter

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    FORMATS = {
        logging.ERROR: "%(asctime)s [ERROR] %(filename)s:%(lineno)d, in %(funcName)s(), %(msg)s",
        logging.INFO: "%(asctime)s [INFO] %(msg)s",
        logging.DEBUG: "%(asctime)s [DEBUG] %(filename)s:%(lineno)d, in %(funcName)s(), %(msg)s",
        "DEFAULT": "%(asctime)s [TEXT] %(msg)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_ch = logging.StreamHandler()
logger_ch.setLevel(logging.DEBUG)
logger_ch.setFormatter(CustomFormatter())
logger.addHandler(logger_ch)
