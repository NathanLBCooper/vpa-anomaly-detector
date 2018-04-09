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


def create_emailer(notification_config, send_emails):
    if send_emails:
        print("Please enter your e-mail account's password.")
        password = getpass()
        return Emailer(notification_config, password)
    else:
        return None


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
    "--rhistory/--ihistory",
    default=False,
    help="When set --rhistory, set to use real historical data to "
         "determine thresholds. Otherwise, use user-defined parameters "
         "to interpolate initial thresholds.")
@click.option(
    "--send-emails/--no-emails",
    default=False,
    help="When True, send e-mails when anomalies are detected in markets.")
@click.option(
    "--pre/--no-pre",
    default=True,
    help="When True, pre-calculate thresholds before looking at new candles. "
         "Otherwise, do it on the fly.")
def monitor(config, rhistory, send_emails, pre):
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

    emailer = create_emailer(notification_config, send_emails)
    try:
        # Connect to account
        ig_stream_service.connect(account_id)
        historical_data_fetcher = create_historical_data_fetcher(
            interpolated_hd_params, ig_service, rhistory)
        callbacks = () if emailer is None else (emailer.add_email_to_queue,)
        add_volume_trackers(
            ig_service,
            ig_stream_service,
            markets,
            historical_data_fetcher,
            callbacks,
            pre)

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
