from PIL import ImageDraw, Image
from .EPaper import EPaperInterface
from .BaseClasses import Component
import time
import os
import nomadnet
import textwrap
import threading
import RNS
import LXMF
import arrow
import readchar

picdir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))), 'epaperui/assets')


class ConversationDisplay(Component):
    def __init__(self, parent):
        super().__init__(parent)
        self.title = "Conversation"
        self.source_hash = None
        self.display_name = None
        
        self.current_message_index = 0
        self.messages = []
        self.show_delete_conversation_widget = False
        self.refresh_thread = threading.Thread(
            daemon=True, target=self.refresh_loop)
        self.keyboard_thread = threading.Thread(
            daemon=True, target=self.keyboard_listener)

    def start(self):
        self.refresh_thread.start()
        self.keyboard_thread.start()
        self.update()

    def update(self):
        try:
            if self.router.current_page_index == EPaperInterface.PAGE_INDEX_CONVERSATION:
                self.conversation = nomadnet.Conversation(self.source_hash, self.app)
                self.app.mark_conversation_read(self.source_hash)
                
                self.messages = []
                for message in self.conversation.messages:
                    message.is_current_message = False
                    message.load()
                    self.messages.append(
                        MessageDisplay(self, message))
                self.messages.sort(
                    key=lambda m: m.message.timestamp, reverse=True)
                self.messages[self.current_message_index].is_current_message = True

                self.ui.reset_canvas()
                background = Image.open(os.path.join(
                    picdir, 'conversation-display.bmp'))
                self.ui.canvas.paste(background, (0, 0))
                draw = ImageDraw.Draw(self.ui.canvas)
                draw.text((0, 0), self.title, font=EPaperInterface.FONT_12)
                peer_name = f"{self.display_name} ({self.source_hash[-6:]})"
                alignment_data = self.ui.get_alignment(
                    peer_name, EPaperInterface.FONT_12)
                draw.text((alignment_data["right_align"], 0), peer_name,
                          font=EPaperInterface.FONT_12)
                
                if len(self.messages) > 0:
                    self.messages[self.current_message_index].update()
                    if self.show_delete_conversation_widget:
                        draw.rectangle((20, 20, 220, 100), outline=0, fill=255)
                        alignment_data = self.ui.get_alignment(
                            "Delete Conversation?", self.ui.FONT_15)
                        draw.text(
                            (alignment_data["center_align"], 40), "Delete Conversation?", font=self.ui.FONT_15)
                        draw.rectangle((70, 70, 180, 95), outline=0, fill=255)
                        alignment_data = self.ui.get_alignment(
                            "YES", self.ui.FONT_12)
                        draw.text(
                            (alignment_data["center_align"], 80), "YES", font=self.ui.FONT_12)
                else:
                    draw.text((50, 50), "No messages?",
                              font=EPaperInterface.FONT_15, fill=0)
                self.ui.request_render()

        except Exception as e:
            RNS.log("Error in update method of ConversationDisplay. Exception was: " +
                    str(e), RNS.LOG_ERROR)

    def confirm_conversation_deletion(self):
        nomadnet.Conversation.delete_conversation(
            self.source_hash, nomadnet.NomadNetworkApp.get_shared_instance())
        self.conversation = None
        self.current_message_index = 0
        self.show_delete_conversation_widget = False
        self.update()

    def keyboard_listener(self):
        while self.ui.app_is_running:
            if self.router.current_page_index == EPaperInterface.PAGE_INDEX_CONVERSATION:
                incoming_char = self.ui.incoming_char
                if self.ui.screen_is_active:
                    match incoming_char:
                        case "c":
                            self.router.navigate(EPaperInterface.PAGE_INDEX_CONVERSATIONS)
                        case "n":
                            self.router.navigate(EPaperInterface.PAGE_INDEX_NETWORK)
                        case readchar.key.LEFT:
                            self.current_message_index = min(
                                self.current_message_index+1, len(self.messages)-1)
                            self.update()
                        case readchar.key.RIGHT:
                            self.current_message_index = max(
                                self.current_message_index-1, 0)
                            self.update()
                        case readchar.key.ENTER:
                            if self.show_delete_conversation_widget:
                                self.confirm_conversation_deletion()
                            else:
                                self.router.navigate(EPaperInterface.PAGE_INDEX_COMPOSE)
                        case readchar.key.DELETE:
                            if hasattr(self, "conversation"):
                                self.show_delete_conversation_widget = True
                                self.update()
            time.sleep(0.02)

    def refresh_loop(self):
        while self.ui.app_is_running:
            if self.router.current_page_index == EPaperInterface.PAGE_INDEX_CONVERSATION:
                self.update()
            time.sleep(5)

    def get_state_string(self, message: LXMF.LXMessage):
        if self.app.lxmf_destination.hash == message.lxm.source_hash:
            state = message.get_state()
            state_string = ""
            if state == LXMF.LXMessage.DELIVERED:
                state_string = "delivered"
            elif state == LXMF.LXMessage.FAILED:
                state_string = "failed"
            elif state == LXMF.LXMessage.SENDING:
                state_string = "sending"
            elif state == LXMF.LXMessage.OUTBOUND:
                state_string = "outbound"
            elif message.lxm.method == LXMF.LXMessage.PROPAGATED and state == LXMF.LXMessage.SENT:
                state_string = "on propagation"
            elif message.lxm.method == LXMF.LXMessage.PAPER and state == LXMF.LXMessage.PAPER:
                state_string = "paper"
            elif state == LXMF.LXMessage.SENT:
                state_string = "sent"
            else:
                state_string = "sent"
        else:
            state_string = "received"

        return state_string


class MessageDisplay(Component):
    def __init__(self, parent, message: LXMF.LXMessage):
        super().__init__(parent)
        self.message = message
        self.is_current_message = False

    def update(self):
        try:
            if self.is_current_message:
                draw = ImageDraw.Draw(self.ui.canvas)
                lines = textwrap.wrap(self.message.get_content(), width=32)
                text_y_position = 20
                for line in lines:
                    left, top, right, bottom = EPaperInterface.FONT_15.getbbox(
                        line)
                    text_width = right - left
                    text_height = bottom - top
                    draw.text(
                        ((self.ui.height-text_width)//2, text_y_position), line, font=EPaperInterface.FONT_15, fill=0)
                    text_y_position += text_height
                state = self.parent.get_state_string(self.message)
                timestamp = arrow.get(self.message.timestamp)
                bottom_text = f'{state} {timestamp.humanize()} at {timestamp.to("local").format(fmt="h:mma", locale="en-us")}'
                centered = self.ui.get_alignment(
                    bottom_text, EPaperInterface.FONT_12)["center_align"]
                draw.text((centered, 100), bottom_text,
                          font=EPaperInterface.FONT_12, fill=0)
                self.ui.request_render()

        except Exception as e:
            RNS.log("Error in update method of MessageDisplay. Exception was: " +
                    str(e), RNS.LOG_ERROR)


class ComposeDisplay(Component):
    def __init__(self, parent):
        super().__init__(parent)
        self.char_buffer = ""
        self.keyboard_thread = threading.Thread(
            daemon=True, target=self.keyboard_listener)

    def start(self):
        self.keyboard_thread.start()
        self.update()

    def update(self):
        if self.router.current_page_index != EPaperInterface.PAGE_INDEX_COMPOSE:
            return
        self.ui.reset_canvas()
        background = Image.open(os.path.join(
            picdir, 'compose-display.bmp'))
        self.ui.canvas.paste(background, (0, 0))
        draw = ImageDraw.Draw(self.ui.canvas)
        lines = textwrap.wrap(self.char_buffer, width=32)[-5:]
        text_y_position = 10
        for line in lines:
            left, top, right, bottom = EPaperInterface.FONT_15.getbbox(
                line)
            text_height = bottom - top
            draw.text((10, text_y_position), line,
                      font=EPaperInterface.FONT_15, fill=0)
            text_y_position += text_height
        self.ui.request_render()

    def keyboard_listener(self):
        while self.ui.app_is_running:
            if self.router.current_page_index == EPaperInterface.PAGE_INDEX_COMPOSE:
                incoming_char = self.ui.incoming_char
                if incoming_char:
                    if incoming_char == readchar.key.CTRL_B:
                        self.router.current_page_index = EPaperInterface.PAGE_INDEX_CONVERSATION
                        self.current_message_index = 0
                        self.parent.update()
                    elif incoming_char == readchar.key.ENTER:
                        if self.router.conversation_display.conversation:
                            self.router.conversation_display.conversation.send(
                                self.char_buffer)
                        else:
                            source_hash = self.router.conversation_display.conversation.source_hash
                            new_conversation = nomadnet.Conversation(
                                source_hash, nomadnet.NomadNetworkApp.get_shared_instance(), initiator=True)
                            new_conversation.send(self.char_buffer)
                        self.router.current_page_index = EPaperInterface.PAGE_INDEX_CONVERSATION
                        self.char_buffer = ""
                        self.parent.update()
                    if incoming_char == readchar.key.BACKSPACE:
                        self.char_buffer = self.char_buffer[0:-1]
                    else:
                        self.char_buffer += incoming_char
                    self.update()
            time.sleep(0.02)
