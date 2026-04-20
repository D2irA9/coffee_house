from colors import *
from globals import *
from .base import Station
from ..tiled import Map
from ..node import CircleButton, Button, ImageButton

class BrewStation(Station):
    def __init__(self):
        super().__init__("Приготовление")
        self.map = Map('assets/tiled/tmx/stations1.tmx', 48)
        self.map_loaded = False

        scale = 3
        self.cells = []
        self.cells_pos = [(0, 75), (303, 75), (606, 75), (909, 75)]
        self.fon_img = py.image.load("assets/sprites/buttons/fon.png").convert_alpha()
        new_w = int(self.fon_img.get_width() * scale)
        new_h = int(self.fon_img.get_height() * scale)
        self.image = py.transform.scale(self.fon_img, (new_w, new_h))

        for i, (x, y) in enumerate(self.cells_pos):
            cell = {
                "id": i,
                "x": x,
                "y": y,
                "image": self.image,
                "button_milk": ImageButton("assets/sprites/buttons/milk.png", (x + 96, y + 65), 3),
                "button_espresso": ImageButton("assets/sprites/buttons/espresso.png", (x + 96, y + 320), 3),
                # Уровни меню (0-основное, 1-тип, 2-температура, 3-наливка, 4-взбивание)
                "milk_menu_level": 0,
                # Уровни эспрессо (0-нет, 1-тип эспрессо, 2-порция)
                "espresso_menu_level": 0,

                # Молоко
                "milk_level1_buttons": {
                    "undo": ImageButton("assets/sprites/buttons/undo.png", (x + 96, y + 190), 3),
                },

                # Эспрессо
                "espresso_level1_buttons": {
                    "undo": ImageButton("assets/sprites/buttons/undo.png", (x + 96, y + 190), 3),
                },
            }
            self.cells.append(cell)

    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True

        self.map.draw_all(screen)

        for cell in self.cells:
            screen.blit(cell["image"], (cell["x"], cell["y"]))
            py.draw.rect(screen, CONTOUR, (cell["x"]-3, cell["y"]-3, 305, 501), 3)
            if cell["milk_menu_level"] == 0 and cell["espresso_menu_level"] == 0:
                cell["button_milk"].draw(screen)
                cell["button_espresso"].draw(screen)

            if cell["milk_menu_level"] == 1:
                cell["milk_level1_buttons"]["undo"].draw(screen)

            if cell["espresso_menu_level"] == 1:
                cell["espresso_level1_buttons"]["undo"].draw(screen)

    def events(self, events):
        for event in events:
            if event.type == py.MOUSEBUTTONDOWN:
                for cell in self.cells:
                    if cell["button_milk"].signal(event.pos):
                        print("Уровень 1: Молоко")
                        cell["milk_menu_level"] = 1
                    if cell["button_espresso"].signal(event.pos):
                        print("Уровень 1: Эспрессо")
                        cell["espresso_menu_level"] = 1