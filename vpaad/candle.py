# -*- coding:utf-8 -*-
import datetime
import math
import logging

LOGGER = logging.getLogger(__name__)


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
