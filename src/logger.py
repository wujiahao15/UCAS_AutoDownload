# -*- encoding: utf-8 -*-
'''
@Filename   : logger.py
@Description: Customized logger class for printing info and error.
@Date       : 2020/03/22 18:57:27
@Author     : Wu Jiahao
@contact    : https://github.com/flamywhale
'''
import logging


class DispatchingFormatter:
    def __init__(self, formatters, default_formatter):
        self._formatters = formatters
        self._default_formatter = default_formatter

    def format(self, record):
        formatter = self._formatters.get(record.name, self._default_formatter)
        return formatter.format(record)


handler = logging.StreamHandler()
handler.setFormatter(
    DispatchingFormatter(
        {
            'error': logging.Formatter(fmt='%(asctime)s [%(levelname)s] File \"%(filename)s\" in %(funcName)s, line %(lineno)d: %(message)s', datefmt="%Y-%m-%d %H:%M:%S"),
            'info': logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S"),
        },
        logging.Formatter('%(message)s')
    )
)
logging.getLogger().addHandler(handler)
logging.getLogger('error').setLevel(logging.DEBUG)
logging.getLogger('info').setLevel(logging.INFO)

errorLogger = logging.getLogger('error')
infoLogger = logging.getLogger('info')

def logError(msg):
    errorLogger.error(msg)

def logInfo(msg):
    infoLogger.info(msg)

def logDebug(msg):
    errorLogger.debug(msg)
