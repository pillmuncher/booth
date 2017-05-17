#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals, division

import contextlib
import multiprocessing

from concurrent.futures import ProcessPoolExecutor
from PIL import Image


class Bunch(object):
    def __init__(self, **k):
        self.__dict__.update(k)


def _paste(bg_file_name, img_file_name, queue, n, size):
    image = Image.open(bg_file_name)
    for _ in xrange(n):
        pos, file_name = queue.get()
        image.paste(Image.open(file_name).resize(size, Image.ANTIALIAS), pos)
    image.save(img_file_name)
    return


@contextlib.contextmanager
def paster(bg_file_name, img_file_name, photo_size):
    with ProcessPoolExecutor(max_workers=1) as executor:
        queue = multiprocessing.Queue()
        future = executor.submit(
            _paste, bg_file_name, img_file_name, queue, 4, photo_size)
        yield Bunch(paste=queue.put, wait=future.result)
