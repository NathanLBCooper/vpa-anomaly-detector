# !/usr/bin/env python
# -*- coding:utf-8 -*-
import datetime

START_TIME_MULIPLIER = 96
INTERESTING_ITEMS = {
    "Spot Gold (5M)": 'CHART:CS.D.CFDGOLD.CFDGC.IP:5MINUTE',
    "Spot Gold (15M)": 'CHART:CS.D.CFDGOLD.CFDGC.IP:15MINUTE',
    "Spot Gold (30M)": 'CHART:CS.D.CFDGOLD.CFDGC.IP:30MINUTE',
    "Spot Gold (1H)": 'CHART:CS.D.CFDGOLD.CFDGC.IP:HOUR',
    "Spot Silver (5M)": 'CHART:CS.D.CFDSILVER.CFDSI.IP:5MINUTE',
    "Spot Silver (15M)": 'CHART:CS.D.CFDSILVER.CFDSI.IP:15MINUTE',
    "Spot Silver (30M)": 'CHART:CS.D.CFDSILVER.CFDSI.IP:30MINUTE',
    "Spot Silver (1H)": 'CHART:CS.D.CFDSILVER.CFDSI.IP:HOUR',
}
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
CANDLE_RES_TO_TIMEDELTA = {
    "5MINUTE": datetime.timedelta(minutes=5),
    "1MINUTE": datetime.timedelta(minutes=1),
    "15MINUTE": datetime.timedelta(minutes=15),
    "30MINUTE": datetime.timedelta(minutes=30),
    "HOUR": datetime.timedelta(hours=1),
}
DATETIME_STR_FORMAT = "%Y-%m-%d %H:%M:%S"
