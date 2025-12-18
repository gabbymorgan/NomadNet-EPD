import os
import time
import nomadnet
import readchar
import RNS
import threading
import arrow

from PIL import ImageDraw
from .EPaper import *
from .BaseClasses import Component
from .EPaper import EPaperInterface


class NetworkDisplay(Component):
    def __init__(self, parent):
        super().__init__(parent)
        self.title = "Directory"
        self.peers = []
        self.current_peer_index = 0
        self.prev_peer_index = 0
        self.show_delete_announce_widget = False

        self.network_keyboard_thread = threading.Thread(
            daemon=True, target=self.network_keyboard_listener)

        self.refresh_thread = threading.Thread(
            daemon=True, target=self.refresh_loop)

    def start(self):
        self.network_keyboard_thread.start()
        self.refresh_thread.start()
        self.update()

    def update(self):
        try:
            if self.router.current_page_index != EPaperInterface.PAGE_INDEX_NETWORK:
                return

            if self.current_peer_index != self.prev_peer_index:
                self.parent.update()
            self.prev_peer_index = self.current_peer_index

            self.ui.reset_canvas()
            background = Image.open(os.path.join(
                picdir, 'network-display.bmp'))
            self.ui.canvas.paste(background, (0, 0))
            draw = ImageDraw.Draw(self.ui.canvas)
            draw.text((0, 0), self.title,
                      font=EPaperInterface.FONT_12)
            self.peers = [
                x for x in self.app.directory.announce_stream if x[3] == "peer"]
            if self.peers and len(self.peers) > 0:
                current_peer = self.peers[self.current_peer_index]
                peer_last_announce = current_peer[0]
                peer_hash = current_peer[1].hex()
                peer_alias = current_peer[2]
                timestamp = arrow.get(peer_last_announce)
                draw.text(
                    (25, 30), peer_alias, font=self.ui.FONT_15)
                draw.text((25, 52), peer_hash, font=self.ui.FONT_12)
                draw.text((25, 70), timestamp.humanize(), font=self.ui.FONT_12)
                if self.app.conversation_is_unread(peer_hash):
                    mail_icon = Image.open(os.path.join(
                        picdir, 'mail.bmp'))
                    self.ui.canvas.paste(mail_icon, (220, 0))
                else:
                    draw.rectangle((220, 0, 250, 30), fill=255)
                if self.show_delete_announce_widget == True:
                    draw.rectangle((20, 20, 220, 100), outline=0, fill=255)
                    alignment_data = self.ui.get_alignment(
                        "Delete Announce?", self.ui.FONT_15)
                    draw.text(
                        (alignment_data["center_align"], 40), "Delete Announce?", font=self.ui.FONT_15)
                    draw.rectangle((70, 70, 180, 95), outline=0, fill=255)
                    alignment_data = self.ui.get_alignment(
                        "YES", self.ui.FONT_12)
                    draw.text(
                        (alignment_data["center_align"], 80), "YES", font=self.ui.FONT_12)

            else:
                draw.text((25, 25), "aww no friends?")

            self.ui.request_render()

        except Exception as e:
            RNS.log(
                "Error in update method of NetworkDisplay component. Exception is: " + str(e), RNS.LOG_ERROR)

    def confirm_announce_deletion(self):
        self.app.directory.announce_stream.remove(
            self.peers[self.current_peer_index])
        self.current_peer_index = 0
        self.show_delete_announce_widget = False
        self.update()

    def select_peer_for_conversation(self):
        selected_peer = self.peers[self.current_peer_index]
        self.router.conversation_display.source_hash = selected_peer[1].hex()
        self.router.conversation_display.display_name = selected_peer[0]
        self.router.navigate(EPaperInterface.PAGE_INDEX_CONVERSATION)

    def network_keyboard_listener(self):
        while self.ui.app_is_running:
            if self.router.current_page_index == EPaperInterface.PAGE_INDEX_NETWORK:
                incoming_char = self.ui.incoming_char
                match incoming_char:
                    case "c":
                        self.router.navigate(
                            EPaperInterface.PAGE_INDEX_CONVERSATIONS)
                    case readchar.key.BACKSPACE:
                        self.show_delete_announce_widsget = not self.show_delete_announce_widget
                        self.update()
                    case readchar.key.RIGHT:
                        self.current_peer_index = min(
                            len(self.peers)-1, self.current_peer_index + 1)
                        self.update()
                    case readchar.key.LEFT:
                        self.current_peer_index = max(
                            0, self.current_peer_index - 1)
                        self.update()
                    case readchar.key.ENTER:
                        if self.show_delete_announce_widget == True:
                            self.confirm_announce_deletion()
                        else:
                            if self.peers and self.peers[self.current_peer_index]:
                                self.select_peer_for_conversation()
            time.sleep(0.02)

    def refresh_loop(self):
        while self.ui.app_is_running:
            if self.router.current_page_index == EPaperInterface.PAGE_INDEX_NETWORK:
                self.update()
            time.sleep(5)
