# !/usr/bin/env python
# -*- coding:utf-8 -*-
import json
import logging
import time

import click
from trading_ig import (IGService, IGStreamService)
from trading_ig.lightstreamer import Subscription

from vpaad.constants import INTERESTING_FIELDS
from vpaad.volume_tracker import VolumeTracker


def create_ig_service(credentials):
    print("Creating service with", credentials)
    return IGService(
        credentials["username"],
        credentials["password"],
        credentials["api_key"])


def create_ig_stream_service(ig_service):
    return IGStreamService(ig_service)


def verify_stream_service_account(ig_stream_service, credentials):
    ig_session = ig_stream_service.create_session()
    # Ensure configured account is selected
    accounts = ig_session[u'accounts']
    accountId = None

    for account in accounts:
        if account[u'accountId'] == credentials["acc_number"]:
            return account[u'accountId']

    if accountId is None:
        raise ValueError(
           'Account not found: {0} in {1}'.format(
               credentials["acc_number"], accounts))


def subscribe_to_interesting_items(ig_service, ig_stream_service, markets):
    volume_trackers = {}
    for name, item in markets.items():
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
        items=markets.values(),
        fields=INTERESTING_FIELDS,
    )

    # Adding the "on_price_update" function to Subscription
    subscription_prices.addlistener(add_candle_to_vt)

    # Registering the Subscription
    ig_stream_service.ls_client.subscribe(subscription_prices)


@click.command()
@click.option(
    "--config",
    default="config.json",
    help="The location of the vpaad config JSON file.")
def run(config):
    logging.basicConfig(level=logging.INFO)

    cfg_json = {}
    with open(config, "r") as cfg_file:
        cfg_json = json.load(cfg_file)

    credentials = cfg_json["credentials"]
    markets = cfg_json["markets"]

    ig_service = create_ig_service(credentials)
    ig_stream_service = IGStreamService(ig_service)
    account_id = verify_stream_service_account(ig_stream_service, credentials)

    try:
        # Connect to account
        ig_stream_service.connect(account_id)
        subscribe_to_interesting_items(ig_service, ig_stream_service, markets)

        print("Press Ctrl-C to exit.\n")

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("Ctrl-C received.")
    finally:
        # Disconnecting
        ig_stream_service.disconnect()


if __name__ == '__main__':
    run()
