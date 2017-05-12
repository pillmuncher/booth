#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals, division

import Queue
import threading

from concurrent.futures import ProcessPoolExecutor
from PIL import Image


def _paste(background, size, position, photo_file_name):
    photo = Image.open(photo_file_name).resize(size, Image.ANTIALIAS)
    return background.paste(photo, position)


def paste_images(background, size):
    def run(image=background):
        with ProcessPoolExecutor(max_workers=1) as executor:
            for _ in xrange(4):
                position, photo_file_name = in_queue.get()
                image = executor.submit(_paste,
                                        image,
                                        size,
                                        position,
                                        photo_file_name).result()
        out_queue.put(image)
    in_queue = Queue.Queue()
    out_queue = Queue.Queue()
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
    return in_queue.put, out_queue.get
