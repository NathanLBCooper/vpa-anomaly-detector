# !/usr/bin/env python
# -*- coding:utf-8 -*-
import datetime
import pprint
import time

import numpy as np
import pandas as pd

from vpaad.constants import (
    CANDLE_RES_TO_TIMEDELTA, CANDLE_RES_TO_HISTORICAL_RES, DATETIME_STR_FORMAT,
    START_TIME_MULIPLIER)
from vpaad.candle import Candle


def condense_historic_data(df):
    sub_df = df.iloc[:, df.columns.get_level_values(0) == "bid"]
    volume_df = df.iloc[:, df.columns.get_level_values(1) == 'Volume']
    candle_df = sub_df["bid"]
    candle_df["Volume"] = volume_df["last"]["Volume"]
    candle_df["AbsSpread"] = (
        pd.Series.abs(candle_df["Open"] - candle_df["Close"]))
    print(candle_df)
    return candle_df


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

    def add_candle(self, candle_data, notify_on_condition=False):
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
