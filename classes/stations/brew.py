from colors import *
from globals import *
from .base import Station
from ..tiled import Map
from ..node import CircleButton, Button, ImageButton
import globals, math

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

        self.type_ingredients = db.get_ingredients_level(globals.id_player)
        for i, (x, y) in enumerate(self.cells_pos):
            center_x = x + 114
            center_y = y + 210
            radius = 100

            milk_ingredient_buttons = []
            milk_ingredients = [ing for ing in self.type_ingredients if ing["type"] == "milk"]
            num_milk = len(milk_ingredients)

            for idx, ing in enumerate(milk_ingredients):
                angle = (2 * math.pi * idx) / num_milk
                btn_x = center_x + radius * math.cos(angle)
                btn_y = center_y + radius * math.sin(angle)
                btn = ImageButton(f'assets/sprites/ingredients/milk/{ing["name"]}.png', (int(btn_x), int(btn_y)), 3)
                milk_ingredient_buttons.append(btn)

            espresso_ingredient_buttons = []
            espresso_ingredients = [ing for ing in self.type_ingredients if ing["type"] == "espresso"]
            num_espresso = len(espresso_ingredients)

            for idx, ing in enumerate(espresso_ingredients):
                # Вычисляем угол для равномерного распределения по кругу
                angle = (2 * math.pi * idx) / num_espresso
                btn_x = center_x + radius * math.cos(angle)
                btn_y = center_y + radius * math.sin(angle)
                btn = ImageButton(f'assets/sprites/ingredients/espresso/{ing["name"]}.png', (int(btn_x), int(btn_y)), 3)
                espresso_ingredient_buttons.append(btn)

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
                "undo_btn": ImageButton("assets/sprites/buttons/undo.png", (center_x, center_y), 3),
                "milk_ingredient_buttons": milk_ingredient_buttons,
                "espresso_ingredient_buttons": espresso_ingredient_buttons,
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

            # Подменю молока
            if cell["milk_menu_level"] == 1:
                cell["undo_btn"].draw(screen)
                for btn in cell["milk_ingredient_buttons"]:
                    btn.draw(screen)

            # Подменю эспрессо
            if cell["espresso_menu_level"] == 1:
                cell["undo_btn"].draw(screen)
                for btn in cell["espresso_ingredient_buttons"]:
                    btn.draw(screen)

    def events(self, events):
        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                for cell in self.cells:
                    # Главное меню
                    if cell["milk_menu_level"] == 0 and cell["espresso_menu_level"] == 0:
                        if cell["button_milk"].signal(event.pos):
                            print("Уровень 1: Молоко")
                            cell["milk_menu_level"] = 1
                        if cell["button_espresso"].signal(event.pos):
                            print("Уровень 1: Эспрессо")
                            cell["espresso_menu_level"] = 1

                    # Подменю молока
                    if cell["milk_menu_level"] == 1:
                        if cell["undo_btn"].signal(event.pos):
                            cell["milk_menu_level"] = 0
                        for btn in cell["milk_ingredient_buttons"]:
                            if btn.signal(event.pos):
                                print(f"Выбран ингредиент молока")

                    # Подменю эспрессо
                    if cell["espresso_menu_level"] == 1:
                        if cell["undo_btn"].signal(event.pos):
                            cell["espresso_menu_level"] = 0
                        for btn in cell["espresso_ingredient_buttons"]:
                            if btn.signal(event.pos):
                                print(f"Выбран ингредиент эспрессо")
