#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author:yuc
# @Date:2018-01-02
# python 2.7.15
import logging
import logging.handlers  
import copy
from colors import*

ROOT = os.path.dirname(os.path.realpath(__file__))

LOG_PATH = os.path.join(ROOT,'log/log.txt')


class ConsoleHandler(logging.StreamHandler):
    def emit(self, record):
        colored = copy.copy(record)

        if record.levelname == "WARNING":
            colored.msg = yellow(record.msg)
        elif record.levelname == "ERROR" or record.levelname == "CRITICAL":
            colored.msg = red(record.msg)
        else:
            if "analysis procedure completed" in record.msg:
                colored.msg = cyan(record.msg)
            else:
                colored.msg = record.msg

        logging.StreamHandler.emit(self, colored)

#初始化时候调用
def init_logging(str_logger_name):
    log = logging.getLogger(str_logger_name)
    formatter = logging.Formatter("%(asctime)s [%(name)s %(lineno)d] %(levelname)s: %(message)s")
    log_path = LOG_PATH
    _path = os.path.dirname(log_path)
    if not os.path.exists(_path):
        os.makedirs(_path)
        
    fh = logging.handlers.RotatingFileHandler(log_path, maxBytes = 10485760, backupCount = 1)
    fh.setFormatter(formatter)
    log.addHandler(fh)

    #控制台输出
    ch = ConsoleHandler()
    ch.setFormatter(formatter)
    log.addHandler(ch)
    log.setLevel(logging.INFO)
    return log