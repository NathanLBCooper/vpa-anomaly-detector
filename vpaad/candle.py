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
        self._time = datetime.datetime.fromtimestamp(
            int(candle_data["UTM"]) / 1000)

        self._spread = None
        self._spread_size = None
        self._type = None
        self._shape = None

        self._calculate_spread()
        self._calculate_shape()
        self._complete = True

    def _calculate_spread(self):
        self._spread = self._bid_close - self._bid_open
        self._spread_size = math.fabs(self._spread)

        if self._spread > 0:
            self._type = "BULLISH"
        elif self._spread < 0:
            self._type = "BEARISH"
        else:
            self._type = "NO_PRICE_CHANGE"

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

        candle_height = max(self._bid_high - self._bid_low, 0.0000001)
        upper_wick_percentage = upper_wick_length / candle_height
        lower_wick_percentage = lower_wick_length / candle_height

        if upper_wick_percentage > 0.75:
            shape_name = "STRONG_SHOOTING_STAR"
        elif upper_wick_percentage > 0.4 and lower_wick_percentage < 0.3:
            shape_name = "WEAK_SHOOTING_STAR"
        elif lower_wick_percentage > 0.75:
            shape_name = "STRONG_HAMMER"
        elif lower_wick_percentage > 0.4 and upper_wick_percentage < 0.3:
            shape_name = "WEAK_HAMMER"
        elif lower_wick_percentage > 0.4 and upper_wick_percentage > 0.4:
            shape_name = "LONG_LEGGED_DOJI"
        else:
            shape_name = "AVERAGE_SHAPE"

        self._shape = {
            "shape_type": shape_name,
            "upper_wick_percentage": upper_wick_percentage,
            "lower_wick_percentage": lower_wick_percentage
        }

    def get_spread_volume_weight(self, volume_stats, spread_stats):
        volume_mean, volume_std = volume_stats
        spread_mean, spread_std = spread_stats

        NUMBER_OF_STDS_AWAY_FROM_MEAN = 1.0
        volume = "AVERAGE_VOLUME"
        volume_epsilon = NUMBER_OF_STDS_AWAY_FROM_MEAN * volume_std
        if self._volume > volume_mean + volume_epsilon:
            volume = "HIGH_VOLUME"
        elif self._volume <= volume_mean - volume_epsilon:
            volume = "LOW_VOLUME"

        spread = "AVERAGE_SPREAD"
        if self._spread_size > spread_mean + spread_std:
            spread = "WIDE_SPREAD"
        elif self._spread_size <= spread_mean - 0.5 * spread_std:
            spread = "NARROW_SPREAD"

        return (volume, spread, self._type)

    @property
    def data(self):
        return {
            "high": self._bid_high,
            "low": self._bid_low,
            "open": self._bid_open,
            "close": self._bid_close,
            "volume": self._volume,
            "spread": self._spread,
            "spread_size": self._spread_size,
            "spread_type": self._type,
        }

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

    @property
    def complete(self):
        return self._complete


class CompositeCandle(Candle):
    """
    A candle made up of smaller 5 minute candles. For example, this could
    be a 15 minute candle containing 3 x 5 minute candles.
    """
    def __init__(self, timedelta):
        self._ratio = int(
            timedelta.total_seconds() /
            datetime.timedelta(minutes=5).total_seconds()
        )
        self._sub_candle_num = 0

        self._bid_high = None
        self._bid_low = None
        self._bid_open = None
        self._bid_close = None
        self._volume = None
        self._spread = None
        self._spread_size = None
        self._time = None
        self._type = None
        self._shape = None
        self._complete = False

    def add_5min_candle(self, candle_data):
        if self._complete:
            raise ValueError("Cannot add candle data to a complete candle.")

        sub_candle = Candle(candle_data)

        if self._sub_candle_num == 0:
            self._bid_high = sub_candle._bid_high
            self._bid_low = sub_candle._bid_low
            self._bid_open = sub_candle._bid_open
            self._bid_close = sub_candle._bid_close
            self._volume = sub_candle._volume
            self._time = sub_candle._time
        else:
            self._bid_high = max(self._bid_high, sub_candle._bid_high)
            self._bid_low = min(self._bid_low, sub_candle._bid_low)
            self._bid_close = sub_candle._bid_close
            self._volume += sub_candle._volume

        self._sub_candle_num += 1

        if self._sub_candle_num == self._ratio:
            # Complete the candle
            self._calculate_spread()
            self._calculate_shape()
            self._complete = True
