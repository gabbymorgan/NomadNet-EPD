import copy
from PIL import Image, ImageFont
import threading
from nomadnet.vendor.waveshare import epd2in13_V4

import os
import RNS
import time
import readchar

fontdir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))), 'epaperui/assets/fonts')
picdir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))), 'epaperui/assets')


class EPaperInterface():
    # hardware and library constants
    MAX_PARTIAL_REFRESHES = 30
    MAX_REFRESH_INTERVAL = 24 * 60 * 60
    TIMEOUT_INTERVAL = 120
    FONT_15 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 15)
    FONT_12 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 12)

    # Routes

    PAGE_INDEX_NETWORK = 0
    PAGE_INDEX_CONVERSATIONS = 1
    PAGE_INDEX_CONVERSATION = 2
    PAGE_INDEX_COMPOSE = 3

    def __init__(self):
        try:
            self.display = epd2in13_V4.EPD()
            self.width = self.display.width
            self.height = self.display.height
            self.canvas = None
            self.display_thread_flag = True
            self.keyboard_thread_flag = True
            self.app_is_running = True
            self.screen_is_active = True
            self.should_render = False
            self.partial_refresh_counter = 0
            self.last_full_refresh = time.time()

            self._incoming_char = None
            self.last_keypress = time.time()

            self.keyboard_thread = threading.Thread(
                daemon=True, target=self.keyboard_loop
            )

            self.display_thread = threading.Thread(
                daemon=False, target=self.display_loop)

            self.reset_canvas()
            self.display.init()
            self.display.displayPartBaseImage(
                self.display.getbuffer(self.canvas))

            self.display_thread.start()
            self.keyboard_thread.start()

        except KeyboardInterrupt:
            self.shutdown()

        except Exception as e:
            RNS.log(
                "An error occured in the EPaperInterface. Exception was:" + str(e), RNS.LOG_ERROR)

    @property
    def incoming_char(self):
        incoming_char = self._incoming_char
        self._incoming_char = None
        return incoming_char

    @incoming_char.setter
    def incoming_char(self, new_value):
        self._incoming_char = new_value
        self.last_keypress = time.time()

    def display_loop(self):
        while self.display_thread_flag:
            now = time.time()
            if self.should_render:
                self.render()
            elif self.screen_is_active and (now - self.last_keypress > self.TIMEOUT_INTERVAL):
                self.sleep()
            elif not self.screen_is_active and (now - self.last_keypress < self.TIMEOUT_INTERVAL):
                self.awaken()
            elif now - self.last_full_refresh > self.MAX_REFRESH_INTERVAL:
                self.clear_screen()
            time.sleep(1)

    def keyboard_loop(self):
        while self.keyboard_thread_flag == True:
            self.incoming_char = readchar.readkey()

    def shutdown(self):
        self.display_thread_flag = False
        self.keyboard_thread_flag = False
        self.screen_is_active = False
        self.app_is_running = False
        self.sleep()
        self.display_thread.join()
        self.keyboard_thread.join()

    def sleep(self):
        self.screen_is_active = False
        self.clear_screen()
        time.sleep(2)
        self.display.sleep()

    def awaken(self):
        self.screen_is_active = True
        self.display.init()
        self.render(self.canvas)

    def clear_screen(self):
        self.display.init()
        self.display.Clear()

    def reset_canvas(self):
        self.canvas = Image.new('1', (self.height, self.width), 255)

    def render(self, isFrame=False):
        self.should_render = False
        if not self.screen_is_active:
            return
        canvas = copy.deepcopy(self.canvas)
        canvas = canvas.rotate(180)
        if self.partial_refresh_counter >= EPaperInterface.MAX_PARTIAL_REFRESHES or isFrame:
            self.display.init()
            self.display.displayPartBaseImage(
                self.display.getbuffer(canvas))
            self.partial_refresh_counter = 0
        else:
            self.display.displayPartial(self.display.getbuffer(canvas))
            self.partial_refresh_counter += 1

    def request_render(self):
        self.should_render = True

    def get_alignment(self, text, font):
        left, top, right, bottom = font.getbbox(text)
        text_width = right - left
        text_height = bottom - top

        return {
            'text_width': text_width,
            'text_height': text_height,
            'left_align': 0,
            'right_align': self.height-text_width,
            'center_align': (self.height-text_width)//2
        }
