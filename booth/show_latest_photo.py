#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals, division

import contextlib
import subprocess

import pygame


SIZE = (1280, 1024)


def flip(f):
    def flipped(*args):
        return f(*reversed(args))
    return flipped


def apply(f, *args, **kwargs):
    return f(*args, **kwargs)


rapply = flip(apply)


def thread_thru(v, *fs):
    return reduce(rapply, fs, v)


def inject(f, *args, **kwargs):
    def inj(x):
        return f(x, *args, **kwargs)
    return inj


@contextlib.contextmanager
def pygame_context():
    pygame.init()
    screen = pygame.display.set_mode(SIZE, pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    yield screen
    pygame.mouse.set_visible(True)
    pygame.quit()


def wait_for_newest_file_name(directory):
    args = ['inotifywait', directory, '-e', 'moved_to', '--format',  '%f']
    return subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]


def main(directory):
    with pygame_context() as screen:
        while True:
            thread_thru(
                wait_for_newest_file_name(directory),
                pygame.image.load,
                inject(pygame.transform.scale, SIZE),
                inject(screen.blit, (0, 0))
            )


if __name__ == '__main__':
    import sys
    import argparse
    parser = argparse.ArgumentParser(description='FotoBox Collage Viewer.')
    parser.add_argument(
        'directory',
        default='.',
        metavar='d',
        type=str,
        help='directory of collage files'
    )
    thread_thru(parser.parse_args().directory, main, sys.exit)
