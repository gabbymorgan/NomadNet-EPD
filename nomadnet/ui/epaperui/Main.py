import RNS
import os

from .Conversation import *
from .Conversations import *
from .Network import *
from .BaseClasses import Component
from .EPaper import *

fontdir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))), 'epaperui/assets/fonts')
picdir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))), 'epaperui/assets')


class MainDisplay(Component):
    def __init__(self):
        try:
            super().__init__()
            self.ui = EPaperInterface()
            self.height = self.ui.display.height
            self.width = self.ui.display.width
            self.app_is_running = True
            self.should_update_render = False

            self.router = Router(self)

        except Exception as e:
            self.ui.shutdown()
            RNS.log("Error in Main Display. Exception was: " + str(e), RNS.LOG_ERROR)

    def update(self):
        return

class Router(Component):
    
    def __init__(self, parent):
        super().__init__(parent)
        self.router = self
        self.height = round(self.ui.height * .9)
        self.width = self.ui.width
        self.current_page_index = EPaperInterface.PAGE_INDEX_NETWORK
        self.prev_page_index = EPaperInterface.PAGE_INDEX_NETWORK
        self.conversations_display = ConversationsDisplay(self)
        self.conversation_display = ConversationDisplay(self)
        self.network_display = NetworkDisplay(self)
        self.compose_display = ComposeDisplay(self)
        self.pages = [self.network_display, self.conversations_display, self.conversation_display, self.compose_display]

        self.start()

    def start(self):
        for page in self.pages:
            page.start()
        self.update()


    def navigate(self, page_index):
        self.prev_page_index = self.current_page_index
        self.current_page_index = page_index
        current_page = self.pages[self.current_page_index]
        current_page.update()
