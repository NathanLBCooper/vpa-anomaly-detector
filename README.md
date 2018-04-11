VPA Anomaly Detector
====================

`vpaad` is a simple tool that detects anomalies in any trading market on
ig.com, using basic principles of Volume Price Analysis.

It can be used to find strong signals of reversals in market trends. For
example: a hammer candle with high volume at the bottom of a bearish trend.

Installation
------------

Run the `setup.py` file directly or using `pip`.

Usage
-----

You can use this tool with a free DEMO account on ig.com. Instructions on how
to set up an account can be found here: https://labs.ig.com/gettingstarted.

Be sure to edit the `config.json` file to use your credentials and select the
markets that you wish to track.

Then run:

`vpaad`

You can call `vpaad --help` for more info.

Tests
-----

Unit tests can be run by running pytests at the top level directory:

`pytest`
