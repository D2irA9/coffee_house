from colors import *
from globals import *
from .base import Station
from ..tiled import Map
from ..node import CircleButton, Button, ImageButton
import globals, math

class BrewStation(Station):
    def __init__(self, sound_manager):
        self.sound_manager = sound_manager
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

        # Звук
        self.pour_sound = py.mixer.Sound("assets/sounds/sound/gotovka/Заливка_молока.mp3")
        # Канал для звука заливки
        self.pour_channel = py.mixer.Channel(1) if py.mixer.get_init() else None
        # флаг, чтобы не перезапускать звук повторно
        self.is_sound_playing = False

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
                "id": i, "x": x, "y": y, "image": self.image,

                "active_ingredient": None,
                "menu_level": 0,

                "button_milk": ImageButton("assets/sprites/buttons/milk.png", (x + 96, y + 65), 3),
                "button_temp_milk": {
                    "hot": ImageButton("assets/sprites/buttons/hot.png", (x + 96, y + 65), 3),
                    "cold": ImageButton("assets/sprites/buttons/cold.png", (x + 96, y + 320), 3)
                },
                "button_portion_milk": ImageButton("assets/sprites/buttons/milk extraction.png", (x + 23, y + 400), 3),
                "button_espresso": ImageButton("assets/sprites/buttons/espresso.png", (x + 96, y + 320), 3),
                "undo_btn": ImageButton("assets/sprites/buttons/undo.png", (center_x, center_y), 3),

                "milk_ingredient_buttons": milk_ingredient_buttons,
                "espresso_ingredient_buttons": espresso_ingredient_buttons,
                "cap": ImageButton("assets/sprites/buttons/cap.png", (x + 40, y + 150), 3),

                # Заливка
                "is_pouring": False,
                "pour_start_time": 0,
                "pour_progress": 0.0,
                "show_pour_button": True,
            }
            self.cells.append(cell)

    def update_sound_volume(self):
        """Обновляет громкость звука заливки в соответствии с настройками"""
        if self.pour_sound and self.sound_manager:
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.pour_sound.set_volume(vol)

    def start_pour_sound(self):
        """Запускает звук заливки с текущей громкостью"""
        if not self.pour_channel or not self.pour_sound:
            return
        if not self.sound_manager.sfx_enabled:
            return
        self.update_sound_volume()
        self.pour_channel.play(self.pour_sound, loops=-1)
        self.is_sound_playing = True

    def stop_pour_sound(self):
        """Останавливает звук заливки"""
        if self.pour_channel:
            self.pour_channel.stop()
        self.is_sound_playing = False

    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True

        self.map.draw_all(screen)

        for cell in self.cells:
            screen.blit(cell["image"], (cell["x"], cell["y"]))
            py.draw.rect(screen, CONTOUR, (cell["x"] - 3, cell["y"] - 3, 305, 501), 3)

            # Главное меню
            if cell["active_ingredient"] is None:
                cell["button_milk"].draw(screen)
                cell["button_espresso"].draw(screen)

            # Подменю молока
            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 1:
                cell["undo_btn"].draw(screen)
                for btn in cell["milk_ingredient_buttons"]:
                    btn.draw(screen)

            # Второй уровень молока
            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 2:
                self.milk_lvl2_draw(screen, cell)

            # Третий уровень молока
            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 3:
                self.milk_lvl3_draw(screen, cell)

            # Подменю эспрессо
            elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 1:
                cell["undo_btn"].draw(screen)
                for btn in cell["espresso_ingredient_buttons"]:
                    btn.draw(screen)

    def milk_lvl2_draw(self, screen, cell):
        """Отрисовка выбора температуры молока"""
        for btn in cell["button_temp_milk"].values():
            btn.draw(screen)

    def update_pouring(self, cell, current_time):
        """Плавное увеличение прогрессом заливки"""
        if not cell["is_pouring"]:
            return

        # Обновляем громкость звука в реальном времени
        if self.is_sound_playing and self.pour_channel and self.pour_channel.get_busy():
            self.update_sound_volume()

        elapsed = (current_time - cell["pour_start_time"]) / 1000.0
        max_time = 5.0
        new_progress = min(1.0, elapsed / max_time)
        cell["pour_progress"] = new_progress

        # Если достигли максимума, останавливаемся и скрываем кнопку
        if new_progress >= 1.0:
            cell["is_pouring"] = False
            cell["show_pour_button"] = False
            self.stop_pour_sound()
            print("Заливка завершена, стакан полон")

    def milk_lvl3_draw(self, screen, cell):
        """Отображение уровня Наливки"""
        x, y = cell["x"], cell["y"]

        py.draw.rect(screen, FON, (x + 25, y + 80, 250, 300))
        py.draw.rect(screen, CONTOUR, (x + 25, y + 80, 250, 300), 3)

        py.draw.rect(screen, PIPE, (x + 125, y + 80, 50, 50))
        py.draw.rect(screen, CONTOUR, (x + 125, y + 80, 50, 50), 3)

        # Прямоугольник-контур стакана
        glass_x = x + 40
        glass_y = y + 150
        glass_width = 219
        glass_height = 219
        py.draw.rect(screen, WHITE, (glass_x, glass_y, glass_width, glass_height), 3)

        # Заливка в зависимости от прогресса
        if cell["pour_progress"] > 0:
            fill_height = int(cell["pour_progress"] * glass_height)
            if fill_height > 0:
                fill_rect = py.Rect(glass_x, glass_y + glass_height - fill_height, glass_width, fill_height)
                py.draw.rect(screen, WHITE, fill_rect)

        # Кнопка наливки
        if cell["show_pour_button"]:
            cell["button_portion_milk"].draw(screen)

        cell["cap"].draw(screen)

    def events(self, events):
        current_time = py.time.get_ticks()

        # Обновление прогресса заливки
        for cell in self.cells:
            if cell.get("is_pouring", False):
                self.update_pouring(cell, current_time)

        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                for cell in self.cells:
                    # Главное меню
                    if cell["active_ingredient"] is None:
                        if cell["button_milk"].signal(event.pos):
                            print("Уровень 1: Молоко")
                            cell["active_ingredient"] = "milk"
                            cell["menu_level"] = 1
                        if cell["button_espresso"].signal(event.pos):
                            print("Уровень 1: Эспрессо")
                            cell["active_ingredient"] = "espresso"
                            cell["menu_level"] = 1

                    # Молоко lvl 1
                    elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 1:
                        if cell["undo_btn"].signal(event.pos):
                            cell["active_ingredient"] = None
                            cell["menu_level"] = 0
                        for btn in cell["milk_ingredient_buttons"]:
                            if btn.signal(event.pos):
                                print(f"Выбран ингредиент молока")
                                cell["menu_level"] = 2
                    # Молоко lvl 2
                    elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 2:
                        if cell["undo_btn"].signal(event.pos):
                            cell["menu_level"] = 1
                        for btn in cell["button_temp_milk"].values():
                            if btn.signal(event.pos):
                                cell["menu_level"] = 3
                                print("Температура выбрана")
                                cell["show_pour_button"] = True

                    # Молоко lvl 3
                    elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 3:
                        if cell["undo_btn"].signal(event.pos):
                            cell["menu_level"] = 2
                            cell["is_pouring"] = False
                            cell["show_pour_button"] = True
                            self.stop_pour_sound()
                        if cell["show_pour_button"] and cell["button_portion_milk"].signal(event.pos):
                            # Начинаем заливку
                            cell["is_pouring"] = True
                            cell["pour_start_time"] = current_time
                            self.start_pour_sound()

                    # Подменю эспрессо
                    elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 1:
                        if cell["undo_btn"].signal(event.pos):
                            cell["active_ingredient"] = None
                            cell["menu_level"] = 0
                        for btn in cell["espresso_ingredient_buttons"]:
                            if btn.signal(event.pos):
                                print(f"Выбран ингредиент эспрессо")

            # Отпускание кнопки мыши
            elif event.type == py.MOUSEBUTTONUP and event.button == 1:
                for cell in self.cells:
                    if cell.get("is_pouring", False):
                        cell["is_pouring"] = False
                        cell["show_pour_button"] = False
                        self.stop_pour_sound()
                        print(f"Заливка остановлена, прогресс сохранён: {cell['pour_progress']:.2f}")