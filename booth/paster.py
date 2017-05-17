#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals, division

import contextlib
import Queue

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from PIL import Image


class Thing:
    pass


def _paste(background, size, position, photo_file_name):
    photo = Image.open(photo_file_name).resize(size, Image.ANTIALIAS)
    background.paste(photo, position)
    return background


@contextlib.contextmanager
def paster(background, size):
    queue = Queue.Queue()
    with ThreadPoolExecutor(max_workers=1) as thread_executor:
        with ProcessPoolExecutor(max_workers=1) as process_executor:
            def run(image=background):
                for _ in xrange(4):
                    position, photo_file_name = queue.get()
                    image = process_executor.submit(_paste,
                                                    image,
                                                    size,
                                                    position,
                                                    photo_file_name).result()
                return image
            thing = Thing()
            thing.paste = queue.put
            thing.result = thread_executor.submit(run).result
            yield thing
