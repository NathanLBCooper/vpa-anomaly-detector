# !/usr/bin/env python
# -*- coding:utf-8 -*-
import json
import logging
import time
import traceback
from getpass import getpass

import click

from vpaad.configuration import set_up_logging
from vpaad.historical_data_fetcher import create_historical_data_fetcher
from vpaad.volume_tracker import add_volume_trackers
from vpaad import ig
from vpaad.emailer import Emailer

set_up_logging()
LOGGER = logging.getLogger("vpaad")


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
    "--real-history/--fake-history",
    default=True,
    help="When True, set to use real historical data to determine thresholds. "
         "Otherwise, use user-defined parameters to interpolate thresholds.")
@click.option(
    "--send-emails/--no-emails",
    default=False,
    help="When True, send e-mails when anomalies are detected in markets.")
def monitor(config, real_history, send_emails):
    """
    Run the main VPA anomaly detection procedure.
    """
    cfg_json = {}
    with open(config, "r") as cfg_file:
        cfg_json = json.load(cfg_file)

    credentials = cfg_json["credentials"]
    markets = cfg_json["markets"]
    interpolated_hd_params = cfg_json.get("interpolated_hd_params")
    notification_config = cfg_json.get("notification_config")

    ig_service = ig.create_ig_service(credentials)
    ig_stream_service = ig.create_ig_stream_service(ig_service)

    account_id = ig.verify_stream_service_account(
        ig_stream_service, credentials)

    if send_emails:
        print("Please enter your e-mail account's password.")
        password = getpass()
        emailer = Emailer(notification_config, password)
    else:
        emailer = None

    try:
        # Connect to account
        ig_stream_service.connect(account_id)
        historical_data_fetcher = create_historical_data_fetcher(
            interpolated_hd_params, ig_service, real_history)
        add_volume_trackers(
            ig_service, ig_stream_service, markets, historical_data_fetcher)

        if emailer:
            emailer.start()

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
        if emailer:
            emailer.stop()


cli.add_command(search)
cli.add_command(monitor)


if __name__ == '__main__':
    cli()