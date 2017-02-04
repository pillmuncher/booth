#!/usr/bin/env python3
# coding: utf-8

from setuptools import setup, find_packages

setup(
    name="booth",
    version="0.1a0",
    packages=find_packages(),
    install_requires=[
        'picamera>=1.12',
        'Pillow>=3.4.2',
        'Pygame>=1.9.3',
        'RPi.GPIO',
    ]
)
