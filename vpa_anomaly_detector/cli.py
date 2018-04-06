# !/usr/bin/env python
# -*- coding:utf-8 -*-
import collections
import logging
import time

from trading_ig import (IGService, IGStreamService)
from trading_ig.lightstreamer import Subscription

from constants import INTERESTING_ITEMS, INTERESTING_FIELDS
from volume_tracker import VolumeTracker

Config = collections.namedtuple(
    "Config",
    ['username', 'password', 'api_key', 'acc_number'])

CONFIG = Config(
    "mikeymo",
    "titlt9i2w:IG",
    "2b295a137bf7156ab56762bece9601aa49cc0a7a",
    "ZDKPF")


def create_ig_service(cfg):
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
    volume_trackers = {}
    for name, item in INTERESTING_ITEMS.items():
        vt = VolumeTracker(name, item, ig_service)
        vt.initiate()
        volume_trackers[item] = vt

    def add_candle_to_vt(event):
        values = event["values"]
        name = event["name"]
        if values["CONS_END"] == u"1":
            # Only add completed candles
            return volume_trackers[name].add_candle(
                values, notify_on_condition=True)

    # Making a new Subscription in MERGE mode
    subscription_prices = Subscription(
        mode="MERGE",
        items=INTERESTING_ITEMS.values(),
        fields=INTERESTING_FIELDS,
    )

    # Adding the "on_price_update" function to Subscription
    subscription_prices.addlistener(add_candle_to_vt)

    # Registering the Subscription
    ig_stream_service.ls_client.subscribe(subscription_prices)


def main():
    logging.basicConfig(level=logging.INFO)

    ig_service = create_ig_service(CONFIG)
    ig_stream_service = IGStreamService(ig_service)
    account_id = verify_stream_service_account(ig_stream_service, CONFIG)

    try:
        # Connect to account
        ig_stream_service.connect(account_id)
        subscribe_to_interesting_items(ig_service, ig_stream_service)

        print("Press Ctrl-C to exit.\n")

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("Ctrl-C received.")
    finally:
        # Disconnecting
        ig_stream_service.disconnect()


if __name__ == '__main__':
    main()
