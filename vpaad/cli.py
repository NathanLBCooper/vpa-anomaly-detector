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
from vpaad.historical_data_fetcher import (
    RealHistoricalDataFetcher, InterpolatedHistoricalDataFetcher)


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


def subscribe_to_interesting_items(
        ig_service, ig_stream_service, markets, historical_data_fetcher):
    volume_trackers = {}
    for name, item in markets.items():
        vt = VolumeTracker(name, item, ig_service, historical_data_fetcher)
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


def historical_data_fetcher_factory(
        interpolated_hd_params, ig_service, real_history):
    if real_history:
        return RealHistoricalDataFetcher(ig_service)
    else:
        return InterpolatedHistoricalDataFetcher(interpolated_hd_params)


@click.command()
@click.option(
    "--config",
    default="config.json",
    help="The location of the vpaad config JSON file.")
@click.option(
    "--real-history",
    default=True,
    help="When True, set to use real historical data to determine thresholds. "
         "Otherwise, use user-defined parameters to interpolate thresholds.")
def run(config, real_history):
    logging.basicConfig(level=logging.INFO)

    cfg_json = {}
    with open(config, "r") as cfg_file:
        cfg_json = json.load(cfg_file)

    credentials = cfg_json["credentials"]
    markets = cfg_json["markets"]
    # Optional config
    interpolated_hd_params = cfg_json.get("interpolated_hd_params")

    ig_service = create_ig_service(credentials)
    ig_stream_service = IGStreamService(ig_service)
    account_id = verify_stream_service_account(ig_stream_service, credentials)

    try:
        # Connect to account
        ig_stream_service.connect(account_id)
        historical_data_fetcher = historical_data_fetcher_factory(
            interpolated_hd_params, ig_service, real_history)
        subscribe_to_interesting_items(
            ig_service, ig_stream_service, markets, historical_data_fetcher)

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
