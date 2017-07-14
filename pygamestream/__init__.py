import os
import asyncio
import pygame
from threading import Event
from atlasbuggy.datastream import AsyncStream
from atlasbuggy import get_platform


class PygameStream(AsyncStream):
    pygame_initialized = False
    pygame_exit_event = Event()

    def __init__(self, enabled, log_level=None, width=None, height=None, fps=None, name=None, display_flags=0, display_depth=0):
        super(PygameStream, self).__init__(enabled, name, log_level)

        self.fps = fps
        self.width = width
        self.height = height
        if self.fps is None:
            self.delay = 0.0
        else:
            self.delay = 1 / fps

        self.display_size = (width, height)

        if self.width is None or self.height is None or self.fps is None:
            # turn off the pygame display. Required if using opencv with QT
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            self.display = "dummy"
        else:
            self.display = pygame.display.set_mode(self.display_size, display_flags, display_depth)

    def start(self):
        self.init_pygame()
        self.pygame_stream_start()

    def pygame_stream_start(self):
        pass

    @staticmethod
    def init_pygame():
        if not PygameStream.pygame_initialized:
            pygame.init()

    def event(self, event):
        pass

    async def run(self):
        while self.is_running():
            pygame.event.pump()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.exit()
                    break

                self.event(event)
            self.update()

            pygame.display.flip()

            await asyncio.sleep(self.delay)
        self.quit_pygame()

    def quit_pygame(self):
        if not PygameStream.pygame_exit_event.is_set():
            PygameStream.pygame_exit_event.set()
            pygame.quit()
