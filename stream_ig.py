# !/usr/bin/env python
# -*- coding:utf-8 -*-
import collections
import logging
import pprint
import datetime

import numpy as np

from trading_ig import (IGService, IGStreamService)
from trading_ig.lightstreamer import Subscription

Config = collections.namedtuple(
    "Config",
    ['username', 'password', 'api_key', 'acc_number'])

CONFIG = Config(
    "mikeymo",
    "titlt9i2w:IG",
    "2b295a137bf7156ab56762bece9601aa49cc0a7a",
    "ZDKPF")
INTERESTING_ITEMS = [
    'CHART:CS.D.CFDGOLD.CFDGC.IP:1MINUTE'
]
INTERESTING_FIELDS = [
    "OFR_OPEN", "OFR_CLOSE", "OFR_LOW", "OFR_HIGH", "BID_OPEN",
    "BID_CLOSE", "BID_LOW", "BID_HIGH", "CONS_END", "CONS_TICK_COUNT",
]
CANDLE_RES_TO_HISTORICAL_RES = {
    "5MINUTE": "5Min",
    "1MINUTE": "1Min",
}
CANDLE_RES_TO_TIMEDELTA = {
    "5MINUTE": datetime.timedelta(minutes=5),
    "1MINUTE": datetime.timedelta(minutes=1)
}


# A simple function acting as a Subscription listener
# TODO: change this to the volume tracker class
def on_prices_update(item_update):
    """
    Print when a full candle is complete
    """
    if item_update["values"].get("CONS_END") == u'1':
        pprint.pprint(item_update)


def create_ig_session(cfg):
    return IGService(cfg.username, cfg.password, cfg.api_key)


def create_ig_stream_service(ig_service):
    return IGStreamService(ig_service)


def verify_stream_service_account(ig_stream_service, cfg):
    ig_session = ig_stream_service.create_session()
    # Ensure configured account is selected
    accounts = ig_session[u'accounts']
    accountId = None

    for account in accounts:
        if account[u'accountId'] == cfg.acc_number:
            return account[u'accountId']

    if accountId is None:
        raise ValueError(
           'Account not found: {0} in {1}'.format(
               cfg.acc_number, accounts))


def subscribe_to_interesting_items(ig_service, ig_stream_service):
    for item in INTERESTING_ITEMS:
        vt = VolumeTracker(item, ig_service)
        vt.initiate()

    # # Making a new Subscription in MERGE mode
    # subscription_prices = Subscription(
    #     mode="MERGE",
    #     items=INTERESTING_ITEMS,
    #     fields=INTERESTING_FIELDS,
    # )

    # # Adding the "on_price_update" function to Subscription
    # subscription_prices.addlistener(on_prices_update)

    # # Registering the Subscription
    # ig_stream_service.ls_client.subscribe(subscription_prices)


class VolumeTracker(object):
    """
    Class tracks volume for a given item.
    """
    def __init__(self, item, ig_service):
        _, epic, resolution = item.split(":")

        self._epic = epic
        self._candle_res = resolution
        self._historical_res = CANDLE_RES_TO_HISTORICAL_RES[resolution]
        self._timedelta = CANDLE_RES_TO_TIMEDELTA[resolution]

        self._ig_service = ig_service

        self._average_volume = None
        self._volume_std = None
        self._volume_threshold = None

    def initiate(self):
        """
        Populate average volume from historical price data
        """
        START_TIME_MULIPLIER = 96
        now = datetime.datetime.now()
        start_time = now - self._timedelta * START_TIME_MULIPLIER
        print("Start time:", start_time, ". End time:", now)
        historical_info = (
            self._ig_service.fetch_historical_prices_by_epic_and_date_range(
                    self._epic,
                    self._historical_res,
                    start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    now.strftime("%Y-%m-%d %H:%M:%S"))
        )
        df = historical_info["prices"]
        sub_df = df.iloc[:, df.columns.get_level_values(1) == 'Volume']
        vol_series = sub_df["last"]["Volume"]
        mean = np.mean(vol_series)
        std = np.std(vol_series)

        print("Mean Volume:", mean)
        print("Volume Standard Deviation:", std)
        print("Anomaly Volume Threshold:", mean + std)


def main():
    logging.basicConfig(level=logging.INFO)

    ig_service = create_ig_session(CONFIG)
    ig_stream_service = IGStreamService(ig_service)
    account_id = verify_stream_service_account(ig_stream_service, CONFIG)

    try:
        # Connect to account
        ig_stream_service.connect(account_id)
        subscribe_to_interesting_items(ig_service, ig_stream_service)

        raw_input("Press any key to exit.\n")
    except KeyboardInterrupt:
        print("Ctrl-C received.")
    finally:
        # Disconnecting
        ig_stream_service.disconnect()


if __name__ == '__main__':
    main()
