# !/usr/bin/env python
# -*- coding:utf-8 -*-
import datetime

START_TIME_MULIPLIER = 96
INTERESTING_FIELDS = [
    "OFR_OPEN", "OFR_CLOSE", "OFR_LOW", "OFR_HIGH", "BID_OPEN",
    "BID_CLOSE", "BID_LOW", "BID_HIGH", "CONS_END", "CONS_TICK_COUNT",
    "UTM"
]
CANDLE_RES_TO_HISTORICAL_RES = {
    "1MINUTE": "1Min",
    "5MINUTE": "5Min",
    "15MINUTE": "15Min",
    "30MINUTE": "30Min",
    "HOUR": "1H",
}
HISTORICAL_RES_TO_CANDLE_RES = {
    value: key for key, value in CANDLE_RES_TO_HISTORICAL_RES.items()
}
CANDLE_RES_TO_TIMEDELTA = {
    "5MINUTE": datetime.timedelta(minutes=5),
    "1MINUTE": datetime.timedelta(minutes=1),
    "15MINUTE": datetime.timedelta(minutes=15),
    "30MINUTE": datetime.timedelta(minutes=30),
    "HOUR": datetime.timedelta(hours=1),
}
HISTORICAL_RES_TO_TIMEDELTA = {
    key: CANDLE_RES_TO_TIMEDELTA[value]
    for key, value in HISTORICAL_RES_TO_CANDLE_RES.items()
}
DATETIME_STR_FORMAT = "%Y-%m-%d %H:%M:%S"
DF_DATETIME_FORMAT = "%Y:%m:%d-%H:%M:%S"
