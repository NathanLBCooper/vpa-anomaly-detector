# -*- coding:utf-8 -*-
import datetime

import logging
import numpy as np
import pandas as pd

from vpaad.constants import (
    START_TIME_MULIPLIER, DATETIME_STR_FORMAT, DF_DATETIME_FORMAT,
    HISTORICAL_RES_TO_TIMEDELTA)

LOGGER = logging.getLogger(__name__)


def create_historical_data_fetcher(
        interpolated_hd_params, ig_service, real_history):
    if real_history:
        return RealHistoricalDataFetcher(ig_service)
    else:
        return InterpolatedHistoricalDataFetcher(interpolated_hd_params)


def condense_historic_data(df):
    sub_df = df.iloc[:, df.columns.get_level_values(0) == "bid"]
    volume_df = df.iloc[:, df.columns.get_level_values(1) == 'Volume']
    candle_df = sub_df["bid"]
    candle_df["Volume"] = volume_df["last"]["Volume"]
    candle_df["AbsSpread"] = (
        pd.Series.abs(candle_df["Open"] - candle_df["Close"]))
    # print(candle_df)
    return candle_df


class IHistoricalDataFetcher(object):
    def fetch(self, epic, resolution, start_time, end_time):
        raise NotImplementedError()


class RealHistoricalDataFetcher(IHistoricalDataFetcher):
    def __init__(self, ig_service):
        self._ig_service = ig_service

    def fetch(self, epic, resolution, start_time, end_time):
        """
        Fetch actual historical data from IG
        """
        historical_info = (
            self._ig_service.fetch_historical_prices_by_epic_and_date_range(
                epic, resolution, start_time, end_time)
        )
        return condense_historic_data(historical_info["prices"])


class InterpolatedHistoricalDataFetcher(IHistoricalDataFetcher):
    def __init__(self, interpolated_hd_params):
        self._interpolated_hd_params = interpolated_hd_params

    def fetch(self, epic, resolution, start_time, end_time):
        """
        Return mocked up data based on given mean and standard deviation
        """
        epic_params = self._interpolated_hd_params[epic][resolution]
        volume_params = epic_params["volume"]
        spread_params = epic_params["spread"]

        volume_a = np.random.normal(
            volume_params["mean"], volume_params["std"], START_TIME_MULIPLIER)
        spread_a = np.random.normal(
            spread_params["mean"], spread_params["std"], START_TIME_MULIPLIER)

        df = pd.DataFrame()

        td = HISTORICAL_RES_TO_TIMEDELTA[resolution]
        mock_times = [
            datetime.datetime.strptime(start_time, DATETIME_STR_FORMAT) +
            td * i for i in range(START_TIME_MULIPLIER)
        ]

        mock_times = [
            dt.strftime(DF_DATETIME_FORMAT) for dt in mock_times
        ]

        df["Time"] = mock_times
        df.set_index("Time", inplace=True)

        df["AbsSpread"] = spread_a.tolist()
        df["Volume"] = volume_a.tolist()

        # These are irrelevant
        df["Open"] = [0 for _ in range(START_TIME_MULIPLIER)]
        df["Close"] = [0 for _ in range(START_TIME_MULIPLIER)]
        df["High"] = [0 for _ in range(START_TIME_MULIPLIER)]
        df["Low"] = [0 for _ in range(START_TIME_MULIPLIER)]
        return df
