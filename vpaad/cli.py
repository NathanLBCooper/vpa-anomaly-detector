# !/usr/bin/env python
# -*- coding:utf-8 -*-
import json
import logging
import time
import traceback

import click
from trading_ig.lightstreamer import Subscription

from vpaad.constants import INTERESTING_FIELDS
from vpaad.configuration import set_up_logging
from vpaad.volume_tracker import VolumeTracker
from vpaad.historical_data_fetcher import (
    RealHistoricalDataFetcher, InterpolatedHistoricalDataFetcher)
from vpaad import ig

set_up_logging()
LOGGER = logging.getLogger("vpaad")


def add_volume_trackers(
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


@click.group()
def cli():
    pass


@click.command()
@click.option(
    "--config",
    default="config.json",
    help="The location of the vpaad config JSON file.")
@click.argument("term")
def search(config, term):
    """
    Search market database for given term
    """
    cfg_json = {}
    with open(config, "r") as cfg_file:
        cfg_json = json.load(cfg_file)

    credentials = cfg_json["credentials"]
    ig_service = ig.create_ig_service(credentials)

    ig.create_ig_session(ig_service)
    print(ig_service.search_markets(term))


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
def monitor(config, real_history):
    """
    Run the main VPA anomaly detection procedure.
    """
    cfg_json = {}
    with open(config, "r") as cfg_file:
        cfg_json = json.load(cfg_file)

    credentials = cfg_json["credentials"]
    markets = cfg_json["markets"]
    interpolated_hd_params = cfg_json.get("interpolated_hd_params")

    ig_service = ig.create_ig_service(credentials)
    ig_stream_service = ig.create_ig_stream_service(ig_service)

    account_id = ig.verify_stream_service_account(
        ig_stream_service, credentials)

    try:
        # Connect to account
        ig_stream_service.connect(account_id)
        historical_data_fetcher = historical_data_fetcher_factory(
            interpolated_hd_params, ig_service, real_history)
        add_volume_trackers(
            ig_service, ig_stream_service, markets, historical_data_fetcher)

        print("Press Ctrl-C to exit.\n")

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("Ctrl-C received.")
    except Exception:
        LOGGER.error("An unexpected error occurred.")
        LOGGER.error(traceback.format_exc())
    finally:
        # Disconnecting
        ig_stream_service.disconnect()


cli.add_command(search)
cli.add_command(monitor)


if __name__ == '__main__':
    cli()
