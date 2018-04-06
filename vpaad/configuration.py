# -*- coding:utf-8 -*-
from datetime import datetime
import logging
import os
from vpaad.constants import LOG_FILE_DATETIME_FORMAT


def set_up_logging():
    logging.basicConfig()
    logger = logging.getLogger('vpaad')
    logger.setLevel(logging.DEBUG)

    now = datetime.now()
    filename = 'vpaad-{}.log'.format(
        now.strftime(LOG_FILE_DATETIME_FORMAT))
    fh = logging.FileHandler(os.path.join("log", filename))
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
