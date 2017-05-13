#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals, division

import contextlib
import Queue

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from PIL import Image


def _paste(background, size, position, photo_file_name):
    photo = Image.open(photo_file_name).resize(size, Image.ANTIALIAS)
    return background.paste(photo, position)


@contextlib.contextmanager
def paster(background, size):
    class Thing:
        pass
    in_queue = Queue.Queue()
    with ThreadPoolExecutor(max_workers=1) as thread_executor:
        with ProcessPoolExecutor(max_workers=1) as process_executor:
            def run(image=background):
                for _ in xrange(4):
                    position, photo_file_name = in_queue.get()
                    image = process_executor.submit(_paste,
                                                    image,
                                                    size,
                                                    position,
                                                    photo_file_name).result()
                return image
            thing = Thing()
            thing.paste = in_queue.put
            thing.result = thread_executor.submit(run).result
            yield thing
