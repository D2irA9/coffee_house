from colors import *
from globals import *
from .base import Station

class BuildStation(Station):
    def __init__(self):
        super().__init__("Сборка")

    def draw(self, screen):
        screen.fill(BLUE)

    def events(self, events):
        pass