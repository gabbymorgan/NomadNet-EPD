import os
import time
import nomadnet
import readchar
import RNS
import threading

from PIL import ImageDraw
from .EPaper import *
from .BaseClasses import Component
from .EPaper import EPaperInterface


class ConversationsDisplay(Component):
    def __init__(self, parent):
        super().__init__(parent)
        self.title = "Conversations"
        self.current_conversation_index = 0
        self.prev_conversation_index = 0
        self.show_delete_conversation_widget = False

        self.network_keyboard_thread = threading.Thread(
            daemon=True, target=self.network_keyboard_listener)

        self.refresh_thread = threading.Thread(
            daemon=True, target=self.refresh_loop)

    def start(self):
        self.network_keyboard_thread.start()
        self.refresh_thread.start()
        self.update()

    def update(self):
        if self.router.current_page_index != EPaperInterface.PAGE_INDEX_CONVERSATIONS:
            return

        try:
            self.prev_conversation_index = self.current_conversation_index

            self.ui.reset_canvas()
            background = Image.open(os.path.join(
                picdir, 'network-display.bmp'))
            self.ui.canvas.paste(background, (0, 0))
            draw = ImageDraw.Draw(self.ui.canvas)
            draw.text((0, 0), self.title,
                      font=EPaperInterface.FONT_12)
            self.conversations = nomadnet.Conversation.conversation_list(
                self.app)
            if self.conversations and len(self.conversations) > 0:
                current_conversation = self.conversations[self.current_conversation_index]
                display_name = str(current_conversation[1])
                source_hash = current_conversation[0]
                unread = current_conversation[4]

                if unread:
                    mail_icon = Image.open(os.path.join(
                        picdir, 'mail.bmp'))
                    self.ui.canvas.paste(mail_icon, (220, 0))
                else:
                    draw.rectangle((220, 0, 250, 30), fill=255)
                draw.text(
                    (20, 30), display_name, font=self.ui.FONT_15)
                draw.text((20, 52), source_hash, font=self.ui.FONT_12)

            else:
                draw.text((25, 25), "aww no friends?")

            self.ui.request_render()

        except Exception as e:
            print(e)
            RNS.log(
                "Error in update method of ConversationsDisplay component. Exception is: " + str(e), RNS.LOG_ERROR)

    def network_keyboard_listener(self):
        while self.ui.app_is_running:
            if self.router.current_page_index == EPaperInterface.PAGE_INDEX_CONVERSATIONS:
                incoming_char = self.ui.incoming_char
                match incoming_char:
                    case "n":
                        self.router.navigate(
                            EPaperInterface.PAGE_INDEX_NETWORK)
                    case readchar.key.RIGHT:
                        self.current_conversation_index = min(
                            len(self.conversations)-1, self.current_conversation_index + 1)
                        self.update()
                    case readchar.key.LEFT:
                        self.current_conversation_index = max(
                            0, self.current_conversation_index - 1)
                        self.update()
                    case readchar.key.ENTER:
                        current_conversation = self.conversations[self.current_conversation_index]
                        if self.conversations and self.conversations[self.current_conversation_index]:
                            self.router.conversation_display.source_hash = current_conversation[0]
                            self.router.conversation_display.display_name = current_conversation[1]
                            self.router.navigate(
                                EPaperInterface.PAGE_INDEX_CONVERSATION)
            time.sleep(0.02)

    def refresh_loop(self):
        while self.ui.app_is_running:
            if self.router.current_page_index == EPaperInterface.PAGE_INDEX_CONVERSATIONS:
                self.update()
            time.sleep(5)
