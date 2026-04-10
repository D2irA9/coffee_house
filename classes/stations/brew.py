from colors import *
from globals import *
from .base import Station

class BrewStation(Station):
    def __init__(self):
        super().__init__("Приготовление")

    def draw(self, screen):
        screen.fill(ORANGE)

    def events(self, events):
        pass