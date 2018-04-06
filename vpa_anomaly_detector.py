# !/usr/bin/env python
# -*- coding:utf-8 -*-
import collections
import logging
import pprint
import datetime
import math
import time

import numpy as np
import pandas as pd

from trading_ig import (IGService, IGStreamService)
from trading_ig.lightstreamer import Subscription

Config = collections.namedtuple(
    "Config",
    ['username', 'password', 'api_key', 'acc_number'])

START_TIME_MULIPLIER = 96
CONFIG = Config(
    "mikeymo",
    "titlt9i2w:IG",
    "2b295a137bf7156ab56762bece9601aa49cc0a7a",
    "ZDKPF")
INTERESTING_ITEMS = {
    "Spot Gold (5M)": 'CHART:CS.D.CFDGOLD.CFDGC.IP:5MINUTE',
    "Spot Silver (5M)": 'CHART:CS.D.CFDSILVER.CFDSI.IP:5MINUTE',
    "Spot Gold (15M)": 'CHART:CS.D.CFDGOLD.CFDGC.IP:15MINUTE',
    "Spot Silver (15M)": 'CHART:CS.D.CFDSILVER.CFDSI.IP:15MINUTE',
    "Spot Gold (30M)": 'CHART:CS.D.CFDGOLD.CFDGC.IP:30MINUTE',
    "Spot Silver (30M)": 'CHART:CS.D.CFDSILVER.CFDSI.IP:30MINUTE',
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
}
CANDLE_RES_TO_TIMEDELTA = {
    "5MINUTE": datetime.timedelta(minutes=5),
    "1MINUTE": datetime.timedelta(minutes=1),
    "15MINUTE": datetime.timedelta(minutes=15),
    "30MINUTE": datetime.timedelta(minutes=30),
}
DATETIME_STR_FORMAT = "%Y-%m-%d %H:%M:%S"


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
            return volume_trackers[name].add_candle(values)

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


def condense_historic_data(df):
    sub_df = df.iloc[:, df.columns.get_level_values(0) == "bid"]
    volume_df = df.iloc[:, df.columns.get_level_values(1) == 'Volume']
    candle_df = sub_df["bid"]
    candle_df["Volume"] = volume_df["last"]["Volume"]
    candle_df["AbsSpread"] = (
        pd.Series.abs(candle_df["Open"] - candle_df["Close"]))
    print(candle_df)
    return candle_df


class Candle(object):
    def __init__(self, candle_data):
        self._bid_high = float(candle_data["BID_HIGH"])
        self._bid_low = float(candle_data["BID_LOW"])
        self._bid_open = float(candle_data["BID_OPEN"])
        self._bid_close = float(candle_data["BID_CLOSE"])
        self._volume = float(candle_data["CONS_TICK_COUNT"])
        self._spread = self._bid_close - self._bid_open
        self._spread_size = math.fabs(self._spread)
        self._time = datetime.datetime.fromtimestamp(
            int(candle_data["UTM"]) / 1000)

        if self._spread > 0:
            self._type = "BULLISH"
        elif self._spread < 0:
            self._type = "BEARISH"
        else:
            self._type = "NO_PRICE_CHANGE"

        self._shape = None
        self._calculate_shape()

    def _calculate_shape(self):
        """
        Calculate the shape of the candle. We want to know if it's a hammer
        or a shooting star - these are the most important shapes.
        """
        if self._type == "BULLISH":
            upper_wick_length = self._bid_high - self._bid_close
            lower_wick_length = self._bid_open - self._bid_low
        else:
            upper_wick_length = self._bid_high - self._bid_open
            lower_wick_length = self._bid_close - self._bid_low

        LARGE_WICK_TO_SPREAD_SIZE_MULT = 1.5
        SMALL_WICK_TO_LARGE_WICK_MULT = 2.5

        # A wick is considered large if it's a factor of
        # LARGE_WICK_TO_SPREAD_SIZE_MULT larger than the spread size
        large_upper_wick = (
            upper_wick_length >
            self._spread_size * LARGE_WICK_TO_SPREAD_SIZE_MULT
        )
        large_lower_wick = (
            lower_wick_length >
            self._spread_size * LARGE_WICK_TO_SPREAD_SIZE_MULT
        )

        # A wick is considered small if it is less than half the size of the
        # opposing one
        small_upper_wick = (
            upper_wick_length * SMALL_WICK_TO_LARGE_WICK_MULT <
            lower_wick_length
        )
        small_lower_wick = (
            lower_wick_length * SMALL_WICK_TO_LARGE_WICK_MULT <
            upper_wick_length
        )

        candle_height = self._bid_high - self._bid_low
        upper_wick_percentage = upper_wick_length / candle_height
        lower_wick_percentage = lower_wick_length / candle_height

        if large_upper_wick and small_lower_wick:
            shape_name = "SHOOTING_STAR"
        elif large_lower_wick and small_upper_wick:
            shape_name = "HAMMER"
        elif large_upper_wick and large_lower_wick:
            shape_name = "LONG_LEGGED_DOJI"
        else:
            shape_name = "AVERAGE_SHAPE"

        self._shape = {
            "shape_type": shape_name,
            "upper_wick_percentage": upper_wick_percentage,
            "lower_wick_percentage": lower_wick_percentage
        }

        # print("*" * 50)
        # print(
        #     "upper", upper_wick_length,
        #     "lower", lower_wick_length,
        #     "spread", self._spread_size,
        #     "large_upper", large_upper_wick,
        #     "small_upper", small_upper_wick,
        #     "large_lower", large_lower_wick,
        #     "small_lower", small_lower_wick,
        # )

    def get_spread_volume_weight(self, volume_stats, spread_stats):
        volume_mean, volume_std = volume_stats
        spread_mean, spread_std = spread_stats

        volume = "AVERAGE_VOLUME"
        if self._volume > volume_mean + volume_std:
            volume = "HIGH_VOLUME"
        elif self._volume <= volume_mean - volume_std:
            volume = "LOW_VOLUME"

        spread = "AVERAGE_SPREAD"
        if self._spread_size > spread_mean + spread_std:
            spread = "WIDE_SPREAD"
        elif self._spread_size <= spread_mean - spread_std:
            spread = "NARROW_SPREAD"

        return (volume, spread, self._type)

    @property
    def shape(self):
        return self._shape

    @property
    def spread_size(self):
        return self._spread_size

    @property
    def volume(self):
        return self._volume

    @property
    def time(self):
        return self._time


class VolumeTracker(object):
    """
    Class tracks volume for a given item.
    """
    def __init__(self, name, item, ig_service):
        self._name = name
        _stream_type, epic, resolution = item.split(":")

        self._epic = epic
        self._candle_res = resolution
        self._historical_res = CANDLE_RES_TO_HISTORICAL_RES[resolution]
        self._timedelta = CANDLE_RES_TO_TIMEDELTA[resolution]

        self._ig_service = ig_service

        self._candles = []

        self._volumes = None
        self._volume_stats = None

        self._candle_spreads = None
        self._candle_spread_stats = None

    def _initiate_volume_stats(self, vol_series):
        """
        Calculate volume data from a Series of volumes
        """
        desc = vol_series.describe()
        mean = desc.loc["mean"]
        std = desc.loc["std"]

        self._volume_stats = (mean, std)
        self._volumes = vol_series.tolist()

        print("*" * 50)
        print("Mean Volume:", mean)
        print("Volume Standard Deviation:", std)
        print("Anomaly Volume Threshold:", mean + std)

    def _initiate_candle_spread_stats(self, spread_series):
        desc = spread_series.describe()
        mean = desc.loc["mean"]
        std = desc.loc["std"]

        self._candle_spread_stats = (mean, std)
        self._candle_spreads = spread_series.tolist()

        print("*" * 50)
        print("Mean Spread:", mean)
        print("Spread Standard Deviation:", std)
        print("Anomaly Spread Threshold:", mean + std)

    def initiate(self):
        """
        Populate average volume from historical price data
        """
        print("*" * 50)
        print("Initiating:", self._epic, self._candle_res)

        now = datetime.datetime.now()
        start_time = now - self._timedelta * START_TIME_MULIPLIER

        print("Start time:", start_time, ". End time:", now)

        historical_info = (
            self._ig_service.fetch_historical_prices_by_epic_and_date_range(
                self._epic,
                self._historical_res,
                start_time.strftime(DATETIME_STR_FORMAT),
                now.strftime(DATETIME_STR_FORMAT))
        )

        df = condense_historic_data(historical_info["prices"])
        self._initiate_volume_stats(df["Volume"])
        self._initiate_candle_spread_stats(df["AbsSpread"])
        self._add_candles_from_historic_data(df)

    def _add_candles_from_historic_data(self, df):
        for i, row in df.iterrows():
            candle_date = datetime.datetime.strptime(
                row.name, "%Y:%m:%d-%H:%M:%S")
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

    def add_candle(self, candle_data):
        """Add a candle to this volume tracker"""
        new_candle = Candle(candle_data)
        self._update_stats(new_candle)

        volume, spread, sentiment = new_candle.get_spread_volume_weight(
            self._volume_stats, self._candle_spread_stats)

        if volume == "HIGH_VOLUME":
            print(50 * "*")
            pprint.pprint({
                "time": new_candle.time.strftime(DATETIME_STR_FORMAT),
                "name": self._name,
                "epic": self._epic,
                "resolution": self._candle_res,
                "shape": new_candle.shape,
                "data": (volume, spread, sentiment)
            })

        self._candles.append(new_candle)

        if len(self._candles) > START_TIME_MULIPLIER:
            self._candles.pop(0)


def main():
    logging.basicConfig(level=logging.INFO)

    ig_service = create_ig_session(CONFIG)
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
