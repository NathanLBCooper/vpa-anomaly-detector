# -*- coding:utf-8 -*-
import datetime
import logging
import pprint
import time

import numpy as np
from trading_ig.lightstreamer import Subscription

from vpaad.constants import (
    CANDLE_RES_TO_TIMEDELTA, CANDLE_RES_TO_HISTORICAL_RES, DATETIME_STR_FORMAT,
    START_TIME_MULIPLIER, DF_DATETIME_FORMAT, INTERESTING_FIELDS)
from vpaad.candle import Candle

LOGGER = logging.getLogger(__name__)


class VolumeTracker(object):
    """
    Class tracks volume for a given item.
    """
    def __init__(
            self, name, item, ig_service,
            historical_data_fetcher, notification_callbacks=()):
        self._name = name
        _stream_type, epic, resolution = item.split(":")

        self._epic = epic
        self._candle_res = resolution
        self._historical_res = CANDLE_RES_TO_HISTORICAL_RES[resolution]
        self._timedelta = CANDLE_RES_TO_TIMEDELTA[resolution]

        self._ig_service = ig_service
        self._historical_data_fetcher = historical_data_fetcher

        self._candles = []

        self._volumes = None
        self._volume_stats = None

        self._candle_spreads = None
        self._candle_spread_stats = None

        self._log_prefix = "VT:{}".format(self._name)
        self._notification_callbacks = notification_callbacks

    def log(self, msg, *args):
        LOGGER.info(" ".join((self._log_prefix, msg)), *args)

    def log_debug(self, msg, *args):
        LOGGER.debug(" ".join((self._log_prefix, msg)), *args)

    def _initiate_volume_stats(self, vol_series):
        """
        Calculate volume data from a Series of volumes
        """
        desc = vol_series.describe()
        mean = desc.loc["mean"]
        std = desc.loc["std"]

        self._volume_stats = (mean, std)
        self._volumes = vol_series.tolist()

        self.log("Mean Volume: %s", mean)
        self.log("Volume Standard Deviation: %s", std)
        self.log("Anomaly Volume Threshold: %s", mean + std)

    def _initiate_candle_spread_stats(self, spread_series):
        desc = spread_series.describe()
        mean = desc.loc["mean"]
        std = desc.loc["std"]

        self._candle_spread_stats = (mean, std)
        self._candle_spreads = spread_series.tolist()

        self.log("Mean Spread: %s", mean)
        self.log("Spread Standard Deviation: %s", std)
        self.log("Anomaly Spread Threshold: %s", mean + std)

    def initiate(self):
        """
        Populate average volume from historical price data
        """
        self.log("Initiating")

        now = datetime.datetime.now()
        start_time = now - self._timedelta * START_TIME_MULIPLIER

        self.log("Start time: %s, End time: %s", start_time, now)

        df = self._historical_data_fetcher.fetch(
            self._epic,
            self._historical_res,
            start_time.strftime(DATETIME_STR_FORMAT),
            now.strftime(DATETIME_STR_FORMAT)
        )
        self.log_debug(str(df))
        self._initiate_volume_stats(df["Volume"])
        self._initiate_candle_spread_stats(df["AbsSpread"])
        self._add_candles_from_historic_data(df)

    def _add_candles_from_historic_data(self, df):
        for i, row in df.iterrows():
            candle_date = datetime.datetime.strptime(
                row.name, DF_DATETIME_FORMAT)
            utm_time = time.mktime(candle_date.timetuple()) * 1000
            candle_data = {
                "BID_OPEN": row["Open"],
                "BID_CLOSE": row["Close"],
                "BID_HIGH": row["High"],
                "BID_LOW": row["Low"],
                "CONS_TICK_COUNT": row["Volume"],
                "UTM": utm_time,
            }
            self.add_candle(candle_data)

    def _update_stats(self, new_candle):
        """
        Update the mean and standard deviation of volume and candle spread
        sizes
        """
        # Add new data, remove oldest
        self._volumes.append(new_candle.volume)
        self._candle_spreads.append(new_candle.spread_size)
        self._volumes.pop(0)
        self._candle_spreads.pop(0)

        v_npa = np.array(self._volumes)
        s_npa = np.array(self._candle_spreads)
        self._volume_stats = (np.mean(v_npa), np.std(v_npa))
        self._candle_spread_stats = (np.mean(s_npa), np.std(s_npa))

    def _notify_callbacks(self, candle, relative_data, full_details):
        """
        Notify callbacks with candle data
        """
        if not self._notification_callbacks:
            return

        summary = ", ".join((
            self._name,
            candle.shape["shape_type"],
            str(relative_data)
        ))
        content = (
            "VPAAD has detected an anomaly candle in: {}.\n\n"
            "{}"
        ).format(self._name, full_details)
        for cb in self._notification_callbacks:
            cb(summary, content)

    def add_candle(self, candle_data, notify_on_anomaly=False):
        """Add a candle to this volume tracker"""
        new_candle = Candle(candle_data)
        self._update_stats(new_candle)

        relative_data = new_candle.get_spread_volume_weight(
            self._volume_stats, self._candle_spread_stats)
        volume, spread, sentiment = relative_data

        self._candles.append(new_candle)

        if len(self._candles) > START_TIME_MULIPLIER:
            self._candles.pop(0)

        notable_shapes = ("STRONG_HAMMER", "STRONG_SHOOTING_STAR")
        full_details = pprint.pformat({
            "time": new_candle.time.strftime(DATETIME_STR_FORMAT),
            "name": self._name,
            "epic": self._epic,
            "resolution": self._candle_res,
            "relative_data": (volume, spread, sentiment),
            "data": new_candle.data,
        })

        is_anomaly = False

        if (volume == "HIGH_VOLUME"
                and new_candle.shape["shape_type"] in notable_shapes):
            # High volume hammers and shooting stars are the most
            # useful VPA signals.
            is_anomaly = True
        # elif volume != "HIGH_VOLUME" and spread == "WIDE_SPREAD":
        #     # If the volume isn't high, but the spread is wide,
        #     # it is possibly not a legitimate price action.
        #     is_anomaly = True

        if is_anomaly:
            self.log(full_details)

            if notify_on_anomaly:
                self._notify_callbacks(
                    new_candle, relative_data, full_details)
        else:
            self.log_debug(full_details)


def add_volume_trackers(
        ig_service, ig_stream_service, markets, historical_data_fetcher,
        notification_callbacks):
    """
    Add Volume trackers to an IG stream session.
    """
    volume_trackers = {}
    for name, item in markets.items():
        vt = VolumeTracker(
            name, item, ig_service, historical_data_fetcher,
            notification_callbacks)
        vt.initiate()
        volume_trackers[item] = vt

    def add_candle_to_vt(event):
        values = event["values"]
        name = event["name"]
        if values["CONS_END"] == u"1":
            # Only add completed candles
            return volume_trackers[name].add_candle(
                values, notify_on_anomaly=True)

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
