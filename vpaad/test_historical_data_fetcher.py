import datetime

from vpaad.historical_data_fetcher import InterpolatedHistoricalDataFetcher
from vpaad.constants import DATETIME_STR_FORMAT, START_TIME_MULIPLIER


def test_interpolated_hdf():
    volume_mean = 10.0
    volume_std = 3.0
    spread_mean = 15.0
    spread_std = 5.0

    ihdf_params = {
        "CS.D.CFDGOLD.CFDGC.IP": {
            "5Min": {
                "volume": {"mean": 10.0, "std": 3.0},
                "spread": {"mean": 15.0, "std": 5.0}
            }
        }
    }
    ihdf = InterpolatedHistoricalDataFetcher(ihdf_params)

    now = datetime.datetime.now()
    start_time = now - datetime.timedelta(minutes=5) * START_TIME_MULIPLIER

    df = ihdf.fetch(
        "CS.D.CFDGOLD.CFDGC.IP",
        "5Min",
        start_time.strftime(DATETIME_STR_FORMAT),
        now.strftime(DATETIME_STR_FORMAT)
    )
    assert len(df[df["Volume"] > 0]) > 0
    assert len(df[df["AbsSpread"] > 0]) > 0

    described_df = df.describe()

    assert described_df["AbsSpread"]["mean"] < spread_mean + 1.0
    assert described_df["AbsSpread"]["mean"] > spread_mean - 1.0

    assert described_df["Volume"]["mean"] < volume_mean + 1.0
    assert described_df["Volume"]["mean"] > volume_mean - 1.0

    assert described_df["Volume"]["std"] < volume_std + 1.0
    assert described_df["Volume"]["std"] > volume_std - 1.0

    assert described_df["AbsSpread"]["std"] < spread_std + 1.0
    assert described_df["AbsSpread"]["std"] > spread_std - 1.0
