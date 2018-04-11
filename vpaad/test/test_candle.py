# -*- coding:utf-8 -*-
import datetime
import time
import pytest

from vpaad.candle import CompositeCandle


def test_composite_candle_simple_sub_candles():
    candle_time = time.time() * 1000
    composite_candle = CompositeCandle(datetime.timedelta(minutes=15))
    composite_candle.add_5min_candle(
        {
            "BID_HIGH": 100,
            "BID_LOW": 50,
            "BID_CLOSE": 80,
            "BID_OPEN": 70,
            "CONS_TICK_COUNT": 50,
            "UTM": candle_time,
        }
    )
    assert composite_candle.complete is False
    composite_candle.add_5min_candle(
        {
            "BID_HIGH": 100,
            "BID_LOW": 50,
            "BID_CLOSE": 90,
            "BID_OPEN": 80,
            "CONS_TICK_COUNT": 50,
            "UTM": candle_time,
        }
    )
    assert composite_candle.complete is False
    composite_candle.add_5min_candle(
        {
            "BID_HIGH": 100,
            "BID_LOW": 50,
            "BID_CLOSE": 80,
            "BID_OPEN": 90,
            "CONS_TICK_COUNT": 50,
            "UTM": candle_time,
        }
    )
    assert composite_candle.complete is True
    data = composite_candle.data
    assert data["high"] == 100
    assert data["low"] == 50
    assert data["open"] == 70
    assert data["close"] == 80
    assert data["volume"] == 150
    assert data["spread"] == 10
    assert data["spread_size"] == 10
    assert data["spread_type"] == "BULLISH"
    assert composite_candle.shape["shape_type"] == "AVERAGE_SHAPE"


def test_composite_candle_last_sub_candle_dramatic_fall():
    candle_time = time.time() * 1000
    composite_candle = CompositeCandle(datetime.timedelta(minutes=15))
    composite_candle.add_5min_candle(
        {
            "BID_HIGH": 100,
            "BID_LOW": 50,
            "BID_CLOSE": 80,
            "BID_OPEN": 70,
            "CONS_TICK_COUNT": 50,
            "UTM": candle_time,
        }
    )
    assert composite_candle.complete is False
    composite_candle.add_5min_candle(
        {
            "BID_HIGH": 100,
            "BID_LOW": 50,
            "BID_CLOSE": 80,
            "BID_OPEN": 70,
            "CONS_TICK_COUNT": 50,
            "UTM": candle_time,
        }
    )
    assert composite_candle.complete is False
    composite_candle.add_5min_candle(
        {
            "BID_HIGH": 100,
            "BID_LOW": 20,
            "BID_CLOSE": 30,
            "BID_OPEN": 70,
            "CONS_TICK_COUNT": 100,
            "UTM": candle_time,
        }
    )
    assert composite_candle.complete is True
    data = composite_candle.data
    assert data["high"] == 100
    assert data["low"] == 20
    assert data["open"] == 70
    assert data["close"] == 30
    assert data["volume"] == 200
    assert data["spread"] == -40
    assert data["spread_size"] == 40
    assert data["spread_type"] == "BEARISH"
    assert composite_candle.shape["shape_type"] == "AVERAGE_SHAPE"


def test_composite_candle_completed_exception():
    candle_time = time.time() * 1000
    composite_candle = CompositeCandle(datetime.timedelta(minutes=15))
    composite_candle.add_5min_candle(
        {
            "BID_HIGH": 100,
            "BID_LOW": 50,
            "BID_CLOSE": 80,
            "BID_OPEN": 70,
            "CONS_TICK_COUNT": 50,
            "UTM": candle_time,
        }
    )
    assert composite_candle.complete is False
    composite_candle.add_5min_candle(
        {
            "BID_HIGH": 100,
            "BID_LOW": 50,
            "BID_CLOSE": 90,
            "BID_OPEN": 80,
            "CONS_TICK_COUNT": 50,
            "UTM": candle_time,
        }
    )
    assert composite_candle.complete is False
    composite_candle.add_5min_candle(
        {
            "BID_HIGH": 100,
            "BID_LOW": 50,
            "BID_CLOSE": 80,
            "BID_OPEN": 90,
            "CONS_TICK_COUNT": 50,
            "UTM": candle_time,
        }
    )
    assert composite_candle.complete is True
    with pytest.raises(ValueError):
        composite_candle.add_5min_candle(
            {
                "BID_HIGH": 100,
                "BID_LOW": 50,
                "BID_CLOSE": 80,
                "BID_OPEN": 80,
                "CONS_TICK_COUNT": 50,
                "UTM": candle_time,
            }
        )
