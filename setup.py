# -*- coding: utf-8 -*-
"""
Setup vpa_anomaly_detector
"""
from setuptools import setup, find_packages

setup(
    name='vpa_anomaly_detector',
    author='Mikey Mo',
    author_email='fadeout7@gmail.com',
    url='https://github.com/mikeymo/vpa_anomaly_detector',
    version='0.1',
    packages=find_packages(),
    install_requires=('trading_ig', 'pandas', 'numpy'),
    description=(
        'Experimental tool for detect anomalies in markets using the '
        'ig.com API and volume price analysis'
    ),
    entry_points={
       'console_scripts': ['vpaad = vpaad.cli:main']
    }
)
