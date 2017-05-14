#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals, division

import contextlib
import datetime
import glob
import itertools
import json
import os.path
import re
import Queue
import random
import subprocess
import threading
import time

from PIL import Image
import pygame
import RPi.GPIO as GPIO
import picamera

from paster import paster


def identity(x):
    return x


GPHOTO2_CMD = ['gphoto2', '--capture-image-and-download', '--filename']


class Config(object):

    def __init__(self, conf):
        for k, v in conf.iteritems():
            if isinstance(v, dict):
                setattr(self, k, Config(v))
            elif isinstance(v, list):
                setattr(self, k, tuple(v))
            else:
                setattr(self, k, v)


def get_first_collage_number(glob_mask, pattern):
    file_names = glob.glob(glob_mask)
    if not file_names:
        return 0
    matcher = re.compile(pattern=pattern)
    return 1 + max(int(matcher.match(each).group(1))
                   for each in file_names)


def _get_conf():

    with open('booth.json', 'r') as config_file:
        c = Config(json.load(config_file))
    c.photo.size = c.photo.width, c.photo.height
    c.screen.size = c.screen.width, c.screen.height
    c.screen.rect = 0, 0, c.montage.width, c.montage.height
    c.montage.photo.size = c.montage.photo.width, c.montage.photo.height
    c.montage.photo.positions = [
        (c.montage.x1, c.montage.y1),
        (c.montage.x2, c.montage.y1),
        (c.montage.x1, c.montage.y2),
        (c.montage.x2, c.montage.y2),
    ]
    c.montage.image = Image.open(c.montage.file)
    c.montage.full_mask = os.path.join(
        c.montage.path,
        c.montage.mask,
    )
    c.montage.full_glob_mask = os.path.join(
        c.montage.path,
        c.montage.glob_mask,
    )
    c.collage.full_mask = os.path.join(
        c.collage.path,
        c.collage.mask,
    )
    c.collage.image = Image.open(c.collage.file)
    c.collage.photo.size = c.collage.photo.width, c.collage.photo.height
    c.collage.photo.positions = [
        (c.collage.x1, c.montage.y1),
        (c.collage.x2, c.montage.y1),
        (c.collage.x1, c.montage.y2),
        (c.collage.x2, c.montage.y2),
    ]
    c.collage.counter = itertools.count(
        get_first_collage_number(
            c.collage.full_mask.format('*', '*'), c.collage.pattern))
    c.photo.file_mask = os.path.join(
        c.photo.path,
        c.photo.mask,
    )
    c.etc.prepare.full_image_mask = os.path.join(
        c.etc.path,
        c.etc.prepare.image_mask,
    )
    c.etc.countdown.full_sound_mask = os.path.join(
        c.etc.path,
        c.etc.countdown.sound_mask,
    )
    c.etc.countdown.full_image_mask = os.path.join(
        c.etc.path,
        c.etc.countdown.image_mask,
    )
    c.etc.smile.full_image_file = os.path.join(
        c.etc.path,
        c.etc.smile.image_file,
    )
    c.etc.black.full_image_file = os.path.join(
        c.etc.path,
        c.etc.black.image_file,
    )
    c.etc.songs.mask = os.path.join(c.etc.songs.dir, c.etc.songs.sound_mask)
    return c


CONF = _get_conf()


class Hatch(object):

    def __init__(self, timeout, default):
        self._timeout = timeout
        self._default = default
        self._queue = Queue.Queue(maxsize=1)
        self._task_pending = threading.Event()

    def put(self, item):
        if not self._task_pending.is_set():
            try:
                self._queue.put_nowait(item)
            except RuntimeError:
                pass
            else:
                self._task_pending.set()

    @contextlib.contextmanager
    def get(self):
        if self._task_pending.wait(self._timeout):
            yield self._queue.get()
            self._task_pending.clear()
        else:
            yield self._default


def switch_on(pin):
    GPIO.output(pin, True)


def switch_off(pin):
    GPIO.output(pin, False)


def lights_on(pins):
    for pin in pins:
        GPIO.output(pin, False)


def lights_off(pins):
    for pin in pins:
        GPIO.output(pin, True)


def lightshow(seconds):
    switch_off(CONF.led.green)
    switch_off(CONF.led.yellow)
    switch_off(CONF.led.red)
    time.sleep(seconds)
    switch_on(CONF.led.green)
    time.sleep(seconds)
    switch_on(CONF.led.yellow)
    time.sleep(seconds)
    switch_on(CONF.led.red)
    time.sleep(seconds)
    switch_off(CONF.led.green)
    switch_off(CONF.led.yellow)
    switch_off(CONF.led.red)


class PhotoBooth(object):

    def __init__(self):
        self._events = None
        self._camera = None

    def __enter__(self):
        self._status_led = CONF.led.yellow
        self._events = Hatch(CONF.etc.interval, self.show_random_montage)
        self._camera = picamera.PiCamera()
        self._camera.capture('/dev/null', 'png')
        pygame.init()
        self._screen = pygame.display.set_mode(
            CONF.screen.size,
            pygame.FULLSCREEN,
        )
        pygame.display.set_caption('Photo Booth Pics')
        pygame.mouse.set_visible(False)
        pygame.mixer.pre_init(44100, -16, 1, 1024 * 3)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(CONF.led.green, GPIO.OUT)
        GPIO.setup(CONF.led.yellow, GPIO.OUT)
        GPIO.setup(CONF.led.red, GPIO.OUT)
        GPIO.setup(CONF.led.red, GPIO.OUT)
        for light in CONF.photo.lights:
            GPIO.setup(light, GPIO.OUT)
        GPIO.setup(CONF.event.click.port, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(CONF.event.quit.port, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(CONF.event.shutdown.port, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(CONF.event.reboot.port, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            CONF.event.click.port,
            GPIO.FALLING,
            callback=self.click,
            bouncetime=CONF.etc.bounce_time,
        )
        GPIO.add_event_detect(
            CONF.event.quit.port,
            GPIO.FALLING,
            callback=self.quit_program,
            bouncetime=CONF.etc.bounce_time,
        )
        GPIO.add_event_detect(
            CONF.event.shutdown.port,
            GPIO.FALLING,
            callback=self.shutdown_system,
            bouncetime=CONF.etc.bounce_time,
        )
        GPIO.add_event_detect(
            CONF.event.reboot.port,
            GPIO.FALLING,
            callback=self.reboot_system,
            bouncetime=CONF.etc.bounce_time,
        )
        switch_on(CONF.led.green)
        blinker = threading.Thread(target=self.blink)
        blinker.daemon = True
        blinker.start()
        return self

    def __exit__(self, *args):
        self._status_led = None
        lightshow(1)
        time.sleep(3)
        GPIO.remove_event_detect(CONF.event.reboot.port)
        GPIO.remove_event_detect(CONF.event.shutdown.port)
        GPIO.remove_event_detect(CONF.event.quit.port)
        GPIO.remove_event_detect(CONF.event.click.port)
        GPIO.cleanup()
        pygame.mouse.set_visible(True)
        pygame.quit()
        self._camera.close()
        self._camera = None
        self._events = None

    def event_loop(self):
        while True:
            with self._events.get() as event:
                if callable(event):
                    event()
                else:
                    return event

    def blink(self):
        while self._status_led is not None:
            led = self._status_led
            switch_on(led)
            time.sleep(1)
            switch_off(led)
            time.sleep(1)

    def show_image(self, image):
        self._screen.blit(image, CONF.screen.offset)
        pygame.display.flip()

    def show_random_montage(self):
        file_mask = CONF.montage.full_glob_mask
        file_names = glob.glob(file_mask)
        file_name = random.choice(file_names)
        image = pygame.image.load(file_name)
        self.show_image(pygame.transform.scale(image, CONF.screen.size))

    def send(self, channel, event, waits, message):
        time.sleep(.4)
        for _ in xrange(waits):
            time.sleep(.1)
            if GPIO.input(channel) != GPIO.LOW:
                print(message)
                return
        else:
            self._events.put(event)

    def quit_program(self, channel):
        self.send(
            channel=channel,
            event=CONF.event.quit.code,
            waits=2,
            message='Press longer to quit program!',
        )

    def shutdown_system(self, channel):
        self.send(
            channel=channel,
            event=CONF.event.shutdown.code,
            waits=8,
            message='Press longer to shut down!',
        )

    def reboot_system(self, channel):
        self.send(
            channel=channel,
            event=CONF.event.reboot.code,
            waits=8,
            message='Press longer to reboot!',
        )

    def click(self, channel):
        for _ in xrange(2):
            time.sleep(.01)
            if GPIO.input(channel) != GPIO.LOW:
                return
        self._events.put(getattr(self, CONF.event.click.action))

    def play_sound(self, file_name):
        pygame.mixer.music.load(file_name)
        pygame.mixer.music.play(0)

    def stop_sound(self):
        pygame.mixer.music.stop()

    def show_overlay(self, file_name, position, seconds):
        img = Image.open(os.path.join(CONF.etc.path, file_name))
        pad = Image.new('RGB', (
            ((img.size[0] + 31) // 32) * 32,
            ((img.size[1] + 15) // 16) * 16,
        ))
        pad.paste(img, position)
        overlay = self._camera.add_overlay(pad.tostring(), size=img.size)
        overlay.alpha = 64
        overlay.layer = 3
        time.sleep(seconds)
        self._camera.remove_overlay(overlay)

    def count_down(self, n):
        self.show_overlay(
            CONF.etc.prepare.full_image_mask.format(n),
            CONF.etc.prepare.image_position,
            1.2,
        )
        for i in [3, 2, 1]:
            self.play_sound(CONF.etc.countdown.full_sound_mask.format(i))
            self.show_overlay(
                CONF.etc.countdown.full_image_mask.format(i),
                CONF.etc.countdown.image_position,
                .7,
            )
        if CONF.etc.songs.enabled:
            file_names = glob.glob(CONF.etc.songs.mask)
            file_name = random.choice(file_names)
            self.play_sound(file_name)
        self.show_overlay(
            CONF.etc.smile.full_image_file,
            CONF.etc.smile.image_position,
            .5,
        )

    @contextlib.contextmanager
    def click_mode(self):
        self._status_led = CONF.led.red
        lights_on(CONF.photo.lights)
        self._camera.start_preview()
        self._camera.vflip = True
        yield
        self._camera.stop_preview()
        lights_off(CONF.photo.lights)
        self._status_led = CONF.led.yellow

    def click_event(self):
        timestamp = datetime.datetime.now()
        montage_file_name = CONF.montage.full_mask.format(timestamp)
        collage_file_name = CONF.collage.full_mask.format(
            timestamp, next(CONF.collage.counter))
        with paster(CONF.montage.image, CONF.montage.photo.size) as montp:
            with paster(CONF.collage.image, CONF.collage.photo.size) as collp:
                with self.click_mode():
                    for i in xrange(4):
                        self.count_down(i + 1)
                        photo_file_name = CONF.photo.file_mask.format(
                            timestamp, i + 1)
                        if subprocess.call(GPHOTO2_CMD + [photo_file_name]):
                            raise RuntimeError(
                                "gphoto2 couldn't capture image!")
                        montp.paste(
                            (CONF.montage.photo.positions[i], photo_file_name))
                        collp.paste(
                            (CONF.collage.photo.positions[i], photo_file_name))
                    self.show_image(
                        pygame.image.load(CONF.etc.black.full_image_file))
                montp.result().save(montage_file_name)
                self.show_image(pygame.image.load(montage_file_name))
                collp.result().save(collage_file_name)
        time.sleep(CONF.montage.interval)


def main():
    with PhotoBooth() as booth:
        return booth.event_loop()


if __name__ == '__main__':
    import sys
    sys.exit(main())
