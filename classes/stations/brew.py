from colors import *
from globals import *
from .base import Station
from ..tiled import Map
from ..node import CircleButton, Button, ImageButton
import globals, math, random

class BrewStation(Station):
    """
    Станция приготовления молочной основы и эспрессо.
    """

    def __init__(self, sound_manager, milk_colors, espresso_colors, syrup_colors):
        self.sound_manager = sound_manager
        self.milk_colors = milk_colors
        self.espresso_colors = espresso_colors
        self.syrup_colors = syrup_colors
        super().__init__("Приготовление")

        #Загрузка карты и фона
        self.map = Map('assets/tiled/tmx/stations1.tmx', 48)
        self.map_loaded = False

        scale = 3
        self.cells = []
        self.cells_pos = [(0, 75), (303, 75), (606, 75), (909, 75)]
        self.fon_img = py.image.load("assets/sprites/buttons/fon.png").convert_alpha()
        new_w = int(self.fon_img.get_width() * scale)
        new_h = int(self.fon_img.get_height() * scale)
        self.image = py.transform.scale(self.fon_img, (new_w, new_h))

        # Звуки молока
        self.pour_sound = py.mixer.Sound("assets/sounds/sound/gotovka/Заливка_МолокаЭспрессо.mp3")
        self.pour_channel = py.mixer.Channel(1) if py.mixer.get_init() else None
        self.is_sound_playing = False

        self.whisk_sound = py.mixer.Sound("assets/sounds/sound/gotovka/Взбивание.mp3")
        self.whisk_channel = py.mixer.Channel(2) if py.mixer.get_init() else None
        self.whisk_was_playing = False

        # Звук налива эспрессо
        self.pour_espresso_sound = py.mixer.Sound("assets/sounds/sound/gotovka/Заливка_МолокаЭспрессо.mp3")
        self.pour_espresso_channel = py.mixer.Channel(3) if py.mixer.get_init() else None

        # Звук обжарки эспрессо
        self.roast_sound = py.mixer.Sound("assets/sounds/sound/gotovka/Звук_закипания_кофеварки.mp3")
        self.roast_channel = py.mixer.find_channel()
        self.roast_was_playing = False

        # Загрузка ингредиентов из БД
        self.type_ingredients = db.get_ingredients_level(globals.id_player)

        # Создание 4-х ячеек
        for i, (x, y) in enumerate(self.cells_pos):
            center_x = x + 114
            center_y = y + 210
            radius = 100

            # ---- Кнопки молока ----
            milk_ingredient_buttons = []
            milk_ingredients = [ing for ing in self.type_ingredients if ing["type"] == "milk"]
            num_milk = len(milk_ingredients)
            for idx, ing in enumerate(milk_ingredients):
                angle = (2 * math.pi * idx) / num_milk
                btn_x = center_x + radius * math.cos(angle)
                btn_y = center_y + radius * math.sin(angle)
                btn = ImageButton(f'assets/sprites/ingredients/milk/{ing["name"]}.png', (int(btn_x), int(btn_y)), scale)
                btn.ingredient_milk = ing["name"]
                milk_ingredient_buttons.append(btn)

            # ---- Кнопки эспрессо ----
            espresso_ingredient_buttons = []
            espresso_ingredients = [ing for ing in self.type_ingredients if ing["type"] == "espresso"]
            num_espresso = len(espresso_ingredients)
            for idx, ing in enumerate(espresso_ingredients):
                angle = (2 * math.pi * idx) / num_espresso
                btn_x = center_x + radius * math.cos(angle)
                btn_y = center_y + radius * math.sin(angle)
                btn = ImageButton(f'assets/sprites/ingredients/espresso/{ing["name"]}.png', (int(btn_x), int(btn_y)), scale)
                btn.ingredient_espresso = ing["name"]
                espresso_ingredient_buttons.append(btn)

            # ---- Ячейка ----
            cell = {
                "id": i,
                "x": x,
                "y": y,
                "image": self.image,

                "active_ingredient": None,
                "menu_level": 0,

                # Кнопки молока
                "button_milk": ImageButton("assets/sprites/buttons/milk.png", (x + 96, y + 65), scale),
                "button_temp_milk": {
                    "hot": ImageButton("assets/sprites/buttons/hot.png", (x + 96, y + 65), 3),
                    "cold": ImageButton("assets/sprites/buttons/cold.png", (x + 96, y + 320), 3)
                },
                "button_portion_milk": ImageButton("assets/sprites/buttons/milk extraction.png", (x + 23, y + 400), scale),
                "button_espresso": ImageButton("assets/sprites/buttons/espresso.png", (x + 96, y + 320), scale),
                "undo_btn": ImageButton("assets/sprites/buttons/undo.png", (center_x, center_y), scale),

                "milk_ingredient_buttons": milk_ingredient_buttons,
                "espresso_ingredient_buttons": espresso_ingredient_buttons,
                "button_portion_espresso": {
                    "1": ImageButton("assets/sprites/buttons/portions.png", (x + 112, y + 100), 3, "1"),
                    "2": ImageButton("assets/sprites/buttons/portions.png", (x + 112, y + 210), 3, "2"),
                    "3": ImageButton("assets/sprites/buttons/portions.png", (x + 112, y + 325), 3, "3")
                },
                "espresso_stop_button": ImageButton("assets/sprites/buttons/espresso stop.png", (x + 23, y + 400), 3),
                "cap": ImageButton("assets/sprites/buttons/cap.png", (x + 40, y + 150), 3),

                # --- Молоко ---
                "is_pouring": False,
                "pour_start_time": 0,
                "pour_progress": 0.0,
                "show_pour_button": True,
                "is_extending": False,
                "extend_start_time": 0,
                "extend_progress": 0.0,
                "pipe_height": 50,
                "is_whisking": False,
                "whisk_start_time": 0,
                "whisk_progress": 0.0,

                # --- Эспрессо (выбор и мини-игра) ---
                "selected_espresso_type": None,
                "selected_espresso_portion": 1,
                "roast_slider_progress": 0,
                "roast_slider_direction": 1,
                "roast_slider_speed": 1.2,
                "roast_slider_stopped": False,
                "roast_target_progress": 0,
                "is_roasting": False,
                "roast_progress": 0,
                "roast_start_time": 0,
                "ideal_zone_start": 0,
                "ideal_zone_end": 0,

                # --- Плавная заливка эспрессо ---
                "is_pouring_espresso": False,
                "pour_espresso_start_time": 0,
                "pour_espresso_progress": 0.0,
                "target_espresso_progress": 0.0,

                # Стакан
                "cap_draggable": False,
                "cap_drag": False,
                "cap_drag_offset_x": 0,
                "cap_drag_offset_y": 0,
                "cap_pos": None,

                "pipe_pos": None,

                "milk_cap_draggable": False,
                "milk_cap_drag": False,
                "milk_cap_drag_offset_x": 0,
                "milk_cap_drag_offset_y": 0,
                "milk_cap_pos": None,
                "milk_whisking_paused": False,
            }
            self.cells.append(cell)

    def start_drag_milk_cap(self, cell, mouse_x, mouse_y):
        if not cell.get("milk_cap_draggable", False):
            return
        if not cell["milk_cap_pos"]:
            return
        cap_x, cap_y = cell["milk_cap_pos"]
        glass_img = cell["cap"].image
        cap_rect = py.Rect(cap_x, cap_y, glass_img.get_width(), glass_img.get_height())
        if cap_rect.collidepoint(mouse_x, mouse_y):
            cell["milk_cap_drag"] = True
            cell["milk_cap_drag_offset_x"] = mouse_x - cap_x
            cell["milk_cap_drag_offset_y"] = mouse_y - cap_y

            # Если взбивание активно – ставим на паузу
            if cell.get("is_whisking", False):
                cell["milk_whisking_paused"] = True
                self.stop_whisk_sound()  # останавливаем звук
                self.retract_milk_pipe(cell)  # втягиваем трубу

    def update_drag_milk_cap(self, cell, mouse_x, mouse_y):
        if cell.get("milk_cap_drag", False):
            new_x = mouse_x - cell["milk_cap_drag_offset_x"]
            new_y = mouse_y - cell["milk_cap_drag_offset_y"]
            cell["milk_cap_pos"] = (new_x, new_y)

    def stop_drag_milk_cap(self, cell):
        if cell.get("milk_cap_drag", False):
            cell["milk_cap_drag"] = False
            # Возвращаем стакан в исходное положение
            glass_img = cell["cap"].image
            glass_w, glass_h = glass_img.get_width(), glass_img.get_height()
            original_glass_x = cell["x"] + (300 - glass_w) // 2
            original_glass_y = cell["y"] + 150
            cell["milk_cap_pos"] = (original_glass_x, original_glass_y)

            # Если взбивание было на паузе – возобновляем
            if cell.get("milk_whisking_paused", False):
                cell["milk_whisking_paused"] = False
                self.start_whisk_sound()  # возобновляем звук
                # Трубу не опускаем – остаётся короткой (уже retract_milk_pipe)

    def retract_milk_pipe(self, cell):
        """Втягивает трубу молока: укорачивает до 50 пикселей"""
        cell["pipe_height"] = 50

    def start_roast_sound(self):
        print("start_roast_sound called")
        if not self.roast_channel or not self.roast_sound:
            print("no channel or sound")
            return
        if not self.sound_manager.sfx_enabled:
            print("sfx disabled")
            return
        vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
        print(f"volume: {vol}")
        self.roast_sound.set_volume(vol)
        self.roast_channel.play(self.roast_sound, loops=-1)
        print("sound played")

    def stop_roast_sound(self):
        if self.roast_channel:
            self.roast_channel.stop()

    # ---------- ОБНОВЛЕНИЕ ПРОЦЕССОВ ЭСПРЕССО ----------
    def update_pouring_espresso(self, cell, current_time):
        """Плавное наполнение стакана эспрессо до целевого уровня"""
        if not cell.get("is_pouring_espresso", False):
            return

        # Запускаем звук, если не играет
        if self.pour_espresso_channel and not self.pour_espresso_channel.get_busy() and self.sound_manager.sfx_enabled:
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.pour_espresso_sound.set_volume(vol)
            self.pour_espresso_channel.play(self.pour_espresso_sound, loops=-1)

        elapsed = (current_time - cell["pour_espresso_start_time"]) / 1000.0
        max_time = 5.0   # полная заливка за 5 сек
        progress = min(1.0, elapsed / max_time)

        target = cell.get("target_espresso_progress", 1.0)
        if progress >= target:
            progress = target
            cell["is_pouring_espresso"] = False
            # Останавливаем звук
            if self.pour_espresso_channel:
                self.pour_espresso_channel.stop()
            # Запускаем анимацию опускания трубы
            cell["is_espresso_extending"] = True
            cell["espresso_extend_start_time"] = current_time
            print("Эспрессо налит, опускаем трубу")
        cell["pour_espresso_progress"] = progress

    def update_espresso_extending(self, cell, current_time):
        if not cell.get("is_espresso_extending", False):
            return
        elapsed = (current_time - cell["espresso_extend_start_time"]) / 1000.0
        if elapsed >= 1.0:
            cell["is_espresso_extending"] = False
            cell["espresso_pipe_height"] = 219
            cell["menu_level"] = 4
            cell["is_roasting"] = True
            self.start_roast_sound()
            cell["roast_progress"] = 0
            cell["roast_start_time"] = current_time

            if cell["pipe_pos"] is None:
                cell["pipe_pos"] = (cell["x"] + 125, cell["y"] + 80)

            # --- Инициализация позиции стакана ---
            if cell["cap_pos"] is None:
                glass_img = cell["cap"].image
                glass_w, glass_h = glass_img.get_width(), glass_img.get_height()
                cell["cap_pos"] = (cell["x"] + (300 - glass_w) // 2, cell["y"] + 150)

            # Удалите всё, что связано с pipe_pos и pipe_draggable
            print("Труба опущена, начинаем обжарку")
        else:
            progress = elapsed / 1.0
            cell["espresso_pipe_height"] = int(50 + (219 - 50) * progress)

    def update_roasting(self, cell, current_time):
        if not cell.get("is_roasting", False):
            return
        if "roast_start_time" not in cell:
            cell["roast_start_time"] = current_time
            self.start_roast_sound()
            return

        # Обновляем громкость в реальном времени (как в других звуках)
        if self.roast_channel and self.roast_channel.get_busy():
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.roast_channel.set_volume(vol)

        target_progress = cell.get("roast_target_progress", 0)
        stop_position = cell.get("roast_slider_stop_position", 0)
        zone_start = cell.get("ideal_zone_start", 40)
        zone_end = cell.get("ideal_zone_end", 60)

        portions = cell["selected_espresso_portion"]
        if portions == 1:
            base_time = 20.0
        elif portions == 2:
            base_time = 30.0
        else:
            base_time = 40.0

        # Ускорение при попадании в зелёную зону (по желанию)
        if zone_start <= stop_position <= zone_end:
            roast_time = base_time * 0.8  # быстрее на 20%
        else:
            roast_time = base_time

        elapsed = (current_time - cell["roast_start_time"]) / 1000.0
        progress = min(target_progress, (elapsed / roast_time) * 100)
        cell["roast_progress"] = progress

        if progress >= target_progress:
            quality = "отличное" if zone_start <= stop_position <= zone_end else "среднее"
            print(f"Эспрессо обжарен! Порций: {cell['selected_espresso_portion']}, качество: {quality}")
            cell["is_roasting"] = False
            self.stop_roast_sound()
            # Стакан становится перетаскиваемым
            cell["cap_draggable"] = True
            if cell["cap_pos"] is None:
                glass_img = cell["cap"].image
                glass_w, glass_h = glass_img.get_width(), glass_img.get_height()
                cell["cap_pos"] = (cell["x"] + (300 - glass_w) // 2, cell["y"] + 150)
            # Удалите всё, что связано с pipe_pos и pipe_draggable

    # ---------- МЕТОДЫ ОТРИСОВКИ ЭСПРЕССО ----------
    def draw_espresso_slider(self, screen, cell):
        """Отрисовка ползунка и зелёной зоны для эспрессо"""
        x, y = cell["x"], cell["y"]
        timer_y = y + 20
        timer_w, timer_h = 260, 40

        py.draw.rect(screen, (80, 80, 80), (x + 20, timer_y, timer_w, timer_h))

        portions = cell["selected_espresso_portion"]
        if portions == 1:

            zone_start, zone_end = 40, 50
        elif portions == 2:
            zone_start, zone_end = 60, 70
        else:
            zone_start, zone_end = 80, 90
        cell["ideal_zone_start"] = zone_start
        cell["ideal_zone_end"] = zone_end

        zone_w = int(timer_w * (zone_end - zone_start) / 100)
        zone_x = x + 20 + int(timer_w * zone_start / 100)
        py.draw.rect(screen, GREEN, (zone_x, timer_y, zone_w, timer_h))

        if not cell.get("roast_slider_stopped", False):
            cell["roast_slider_progress"] += cell["roast_slider_direction"] * cell["roast_slider_speed"]
            if cell["roast_slider_progress"] >= 95:
                cell["roast_slider_progress"] = 95
                cell["roast_slider_direction"] = -1
            elif cell["roast_slider_progress"] <= 0:
                cell["roast_slider_progress"] = 0
                cell["roast_slider_direction"] = 1

        slider_x = x + 20 + int(timer_w * cell["roast_slider_progress"] / 100)
        slider_w = 10
        if zone_start <= cell["roast_slider_progress"] <= zone_end:
            slider_color = GREEN
        else:
            slider_color = YELLOW
        py.draw.rect(screen, slider_color, (slider_x, timer_y, slider_w, timer_h))
        py.draw.rect(screen, (200, 180, 0), (slider_x, timer_y, slider_w, timer_h), 2)
        py.draw.rect(screen, (40, 40, 40), (x + 20, timer_y, timer_w, timer_h), 3)

    def espresso_lvl3_draw(self, screen, cell):
        """Уровень 3: ползунок + заливка + кнопка СТОП"""
        x, y = cell["x"], cell["y"]
        pipe_height = cell.get("espresso_pipe_height", 50)
        pipe_y = y + 80

        py.draw.rect(screen, FON, (x + 25, y + 80, 250, 300))
        py.draw.rect(screen, CONTOUR, (x + 25, y + 80, 250, 300), 3)

        # Труба (может быть короткой, пока не началась заливка)
        py.draw.rect(screen, PIPE, (x + 125, pipe_y, 50, pipe_height))
        py.draw.rect(screen, CONTOUR, (x + 125, pipe_y, 50, pipe_height), 3)
        if pipe_height > 50:
            tip_y = pipe_y + pipe_height - 10
            py.draw.rect(screen, (100, 100, 100), (x + 125, tip_y, 50, 10))

        self.draw_espresso_slider(screen, cell)

        # Стакан и заливка
        glass_img = cell["cap"].image
        glass_w, glass_h = glass_img.get_width(), glass_img.get_height()
        glass_x = x + (300 - glass_w) // 2
        glass_y = y + 150
        espresso_color = self.espresso_colors.get(cell["selected_espresso_type"], (110, 59, 9))

        progress = cell.get("pour_espresso_progress", 0.0)
        if progress > 0:
            fill_h = int(glass_h * progress)
            if fill_h > 0:
                fill_rect = py.Rect(glass_x, glass_y + glass_h - fill_h, glass_w, fill_h)
                py.draw.rect(screen, espresso_color, fill_rect)

        cell["cap"].draw(screen)

        # Кнопка СТОП – только если ползунок ещё не остановлен и не начат налив
        if not cell.get("roast_slider_stopped", False) and not cell.get("is_pouring_espresso", False):
            cell["espresso_stop_button"].draw(screen)

    def retract_pipe(self, cell):
        """Втягивает трубу: укорачивает и возвращает на исходную позицию"""
        cell["espresso_pipe_height"] = 50

    def start_drag_cap(self, cell, mouse_x, mouse_y):
        if not cell.get("cap_draggable", False):
            return
        if not cell["cap_pos"]:
            return
        cap_x, cap_y = cell["cap_pos"]
        glass_img = cell["cap"].image
        cap_rect = py.Rect(cap_x, cap_y, glass_img.get_width(), glass_img.get_height())
        if cap_rect.collidepoint(mouse_x, mouse_y):
            cell["cap_drag"] = True
            cell["cap_drag_offset_x"] = mouse_x - cap_x
            cell["cap_drag_offset_y"] = mouse_y - cap_y
            self.retract_pipe(cell)

    def update_drag_cap(self, cell, mouse_x, mouse_y):
        if cell.get("cap_drag", False):
            new_x = mouse_x - cell["cap_drag_offset_x"]
            new_y = mouse_y - cell["cap_drag_offset_y"]
            cell["cap_pos"] = (new_x, new_y)

    def stop_drag_cap(self, cell):
        if cell.get("cap_drag", False):
            cell["cap_drag"] = False
            # Возвращаем стакан в исходное положение
            glass_img = cell["cap"].image
            glass_w, glass_h = glass_img.get_width(), glass_img.get_height()
            original_glass_x = cell["x"] + (300 - glass_w) // 2
            original_glass_y = cell["y"] + 150
            cell["cap_pos"] = (original_glass_x, original_glass_y)

    def espresso_lvl4_draw(self, screen, cell):
        x, y = cell["x"], cell["y"]

        py.draw.rect(screen, FON, (x + 25, y + 80, 250, 300))
        py.draw.rect(screen, CONTOUR, (x + 25, y + 80, 250, 300), 3)

        self.draw_espresso_roast_timer(screen, cell)

        # Труба – по сохранённой позиции или по умолчанию
        if cell.get("pipe_pos"):
            pipe_x, pipe_y = cell["pipe_pos"]
        else:
            pipe_x, pipe_y = x + 125, y + 80
        pipe_height = cell.get("espresso_pipe_height", 219)
        py.draw.rect(screen, PIPE, (pipe_x, pipe_y, 50, pipe_height))
        py.draw.rect(screen, CONTOUR, (pipe_x, pipe_y, 50, pipe_height), 3)
        if pipe_height > 50:
            tip_y = pipe_y + pipe_height - 10
            py.draw.rect(screen, (100, 100, 100), (pipe_x, tip_y, 50, 10))

        # Стакан – перетаскиваемый
        glass_img = cell["cap"].image
        glass_w, glass_h = glass_img.get_width(), glass_img.get_height()
        if cell["cap_pos"]:
            glass_x, glass_y = cell["cap_pos"]
        else:
            glass_x, glass_y = x + (300 - glass_w) // 2, y + 150

        # Заливка эспрессо
        portions = cell["selected_espresso_portion"]
        espresso_color = self.espresso_colors.get(cell["selected_espresso_type"], (110, 59, 9))
        fill_h = int(glass_h * (portions / 4.0))
        if fill_h > 0:
            fill_rect = py.Rect(glass_x, glass_y + glass_h - fill_h, glass_w, fill_h)
            py.draw.rect(screen, espresso_color, fill_rect)

        # Отрисовка самого стакана поверх заливки
        screen.blit(glass_img, (glass_x, glass_y))

        # Если нужна декоративная крышка (cap) – она уже есть в cell["cap"], но мы её уже отрисовали

    def draw_espresso_roast_timer(self, screen, cell):
        """Отрисовка таймера обжарки"""
        x, y = cell["x"], cell["y"]
        timer_y = y + 20
        timer_w = 260

        py.draw.rect(screen, (80, 80, 80), (x + 20, timer_y, timer_w, 40))
        fill_w = int(timer_w * (cell["roast_progress"] / 100))
        py.draw.rect(screen, YELLOW, (x + 20, timer_y, fill_w, 40))

        target = cell.get("roast_target_progress", 0)
        if target > 0:
            target_x = x + 20 + int(timer_w * target / 100)
            py.draw.rect(screen, GREEN, (target_x, timer_y, 10, 40))

        py.draw.rect(screen, (40, 40, 40), (x + 20, timer_y, timer_w, 40), 3)

    # ---------- МЕТОДЫ МОЛОКА ----------
    def update_sound_volume(self):
        if self.pour_sound and self.sound_manager:
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.pour_sound.set_volume(vol)
        if self.whisk_sound and self.sound_manager:
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.whisk_sound.set_volume(vol)
        if self.roast_sound and self.sound_manager:  # добавить
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.roast_sound.set_volume(vol)

    def start_pour_sound(self):
        if not self.pour_channel or not self.pour_sound:
            return
        if not self.sound_manager.sfx_enabled:
            return
        self.update_sound_volume()
        self.pour_channel.play(self.pour_sound, loops=-1)
        self.is_sound_playing = True

    def stop_pour_sound(self):
        if self.pour_channel:
            self.pour_channel.stop()
        self.is_sound_playing = False

    def start_whisk_sound(self):
        if not self.whisk_channel or not self.whisk_sound:
            return
        if not self.sound_manager.sfx_enabled:
            return
        self.update_sound_volume()
        self.whisk_channel.play(self.whisk_sound, loops=-1)

    def stop_whisk_sound(self):
        if self.whisk_channel:
            self.whisk_channel.stop()

    def update_extending(self, cell, current_time):
        if not cell.get("is_extending", False):
            return
        elapsed = (current_time - cell["extend_start_time"]) / 1000.0
        if elapsed >= 1.0:
            cell["is_extending"] = False
            cell["pipe_height"] = 219
            cell["extend_progress"] = 1.0
            cell["is_whisking"] = True
            cell["whisk_start_time"] = current_time
            cell["whisk_progress"] = 0.0
            cell["menu_level"] = 4
            self.start_whisk_sound()
            # Разрешаем перетаскивание стакана
            cell["milk_cap_draggable"] = True
            # Инициализируем позицию стакана
            if cell["milk_cap_pos"] is None:
                glass_img = cell["cap"].image
                glass_w, glass_h = glass_img.get_width(), glass_img.get_height()
                cell["milk_cap_pos"] = (cell["x"] + 40, cell["y"] + 150)  # исходная позиция
            # Сбрасываем флаг паузы (на всякий случай)
            cell["milk_whisking_paused"] = False
        else:
            progress = elapsed / 1.0
            cell["extend_progress"] = progress
            cell["pipe_height"] = int(50 + (219 - 50) * progress)

    def update_whisking(self, cell, current_time):
        if not cell.get("is_whisking", False):
            return
        # Если взбивание на паузе – ничего не делаем
        if cell.get("milk_whisking_paused", False):
            return

        if self.whisk_channel and self.whisk_channel.get_busy():
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.whisk_channel.set_volume(vol)

        elapsed = (current_time - cell["whisk_start_time"]) / 1000.0
        portions = int(cell["pour_progress"] * 4)
        if portions < 1:
            portions = 1
        if portions == 1:
            target_time = 26.0
            cell["ideal_zone_start"] = 40
            cell["ideal_zone_end"] = 60
        elif portions == 2:
            target_time = 46.0
            cell["ideal_zone_start"] = 50
            cell["ideal_zone_end"] = 70
        elif portions == 3:
            target_time = 66.0
            cell["ideal_zone_start"] = 60
            cell["ideal_zone_end"] = 80
        else:
            target_time = 86.0
            cell["ideal_zone_start"] = 70
            cell["ideal_zone_end"] = 90
        progress = min(100.0, (elapsed / target_time) * 100)
        cell["whisk_progress"] = progress
        if progress >= 100.0:
            cell["is_whisking"] = False
            self.stop_whisk_sound()

    def update_pouring(self, cell, current_time):
        if not cell["is_pouring"]:
            return
        if self.is_sound_playing and self.pour_channel and self.pour_channel.get_busy():
            self.update_sound_volume()
        elapsed = (current_time - cell["pour_start_time"]) / 1000.0
        new_progress = min(1.0, elapsed / 20.0)
        cell["pour_progress"] = new_progress
        if new_progress >= 1.0:
            cell["is_pouring"] = False
            cell["show_pour_button"] = False
            self.stop_pour_sound()
            cell["is_extending"] = True
            cell["extend_start_time"] = current_time
            cell["extend_progress"] = 0.0
            cell["pipe_height"] = 50

    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True
        self.map.draw_all(screen)

        for cell in self.cells:
            screen.blit(cell["image"], (cell["x"], cell["y"]))
            py.draw.rect(screen, CONTOUR, (cell["x"] - 3, cell["y"] - 3, 305, 501), 3)

            if cell["active_ingredient"] is None:
                cell["button_milk"].draw(screen)
                cell["button_espresso"].draw(screen)

            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 1:
                cell["undo_btn"].draw(screen)
                for btn in cell["milk_ingredient_buttons"]:
                    btn.draw(screen)

            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 2:
                self.milk_lvl2_draw(screen, cell)

            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 3:
                self.milk_lvl3_draw(screen, cell)

            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 4:
                self.milk_whisk_draw(screen, cell)

            elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 1:
                cell["undo_btn"].draw(screen)
                for btn in cell["espresso_ingredient_buttons"]:
                    btn.draw(screen)

            elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 2:
                self.espresso_lvl2_draw(screen, cell)

            elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 3:
                self.espresso_lvl3_draw(screen, cell)

            elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 4:
                self.espresso_lvl4_draw(screen, cell)

        py.draw.rect(screen, RED, (350, 620, 70, 50), 3)
        py.draw.rect(screen, GREEN, (780, 620, 70, 50), 3)

    def milk_lvl2_draw(self, screen, cell):
        for btn in cell["button_temp_milk"].values():
            btn.draw(screen)

    def milk_lvl3_draw(self, screen, cell):
        x, y = cell["x"], cell["y"]
        pipe_height = cell.get("pipe_height", 50)
        pipe_y = y + 80
        py.draw.rect(screen, FON, (x + 25, y + 80, 250, 300))
        py.draw.rect(screen, CONTOUR, (x + 25, y + 80, 250, 300), 3)
        py.draw.rect(screen, PIPE, (x + 125, pipe_y, 50, pipe_height))
        py.draw.rect(screen, CONTOUR, (x + 125, pipe_y, 50, pipe_height), 3)
        if pipe_height > 50:
            tip_y = pipe_y + pipe_height - 10
            py.draw.rect(screen, (100, 100, 100), (x + 125, tip_y, 50, 10))
        if cell.get("is_extending", False):
            for i in range(5):
                drop_x = x + 125 + random.randint(-10, 60)
                drop_y = pipe_y + pipe_height + random.randint(0, 20)
                py.draw.circle(screen, (200, 200, 255), (drop_x, drop_y), random.randint(2, 4))

        glass_x, glass_y = x + 40, y + 150
        glass_w, glass_h = 219, 219
        py.draw.rect(screen, WHITE, (glass_x, glass_y, glass_w, glass_h), 3)
        if cell["pour_progress"] > 0:
            fill_h = int(cell["pour_progress"] * glass_h)
            fill_rect = py.Rect(glass_x, glass_y + glass_h - fill_h, glass_w, fill_h)
            milk_color = self.milk_colors.get(cell.get("selected_milk_type"), (255, 250, 240))
            py.draw.rect(screen, milk_color, fill_rect)

        if cell["show_pour_button"] and not cell.get("is_extending", False):
            cell["button_portion_milk"].draw(screen)
        cell["cap"].draw(screen)

    def milk_whisk_draw(self, screen, cell):
        x, y = cell["x"], cell["y"]
        py.draw.rect(screen, FON, (x + 25, y + 80, 250, 300))
        py.draw.rect(screen, CONTOUR, (x + 25, y + 80, 250, 300), 3)
        pipe_y = y + 80
        pipe_height = cell.get("pipe_height", 219)
        py.draw.rect(screen, PIPE, (x + 125, pipe_y, 50, pipe_height))
        py.draw.rect(screen, CONTOUR, (x + 125, pipe_y, 50, pipe_height), 3)
        if cell["is_whisking"]:
            for i in range(10):
                bubble_x = x + 40 + random.randint(0, 219)
                bubble_y = y + 150 + random.randint(0, 219)
                offset = (py.time.get_ticks() // 50) % 20
                bubble_y = bubble_y - offset
                if bubble_y > y + 150:
                    py.draw.circle(screen, (200, 200, 255, 150), (bubble_x, bubble_y), random.randint(2, 5))
        self.draw_whisk_timer(screen, cell)

        # Стакан – используем milk_cap_pos если есть
        glass_img = cell["cap"].image
        glass_w, glass_h = glass_img.get_width(), glass_img.get_height()
        if cell.get("milk_cap_pos"):
            glass_x, glass_y = cell["milk_cap_pos"]
        else:
            glass_x, glass_y = x + 40, y + 150

        # Заливка молоком
        if cell["pour_progress"] > 0:
            fill_h = int(cell["pour_progress"] * glass_h)
            fill_rect = py.Rect(glass_x, glass_y + glass_h - fill_h, glass_w, fill_h)
            milk_color = self.milk_colors.get(cell.get("selected_milk_type"), (255, 250, 240))
            py.draw.rect(screen, milk_color, fill_rect)

        # Отрисовка стакана поверх заливки
        screen.blit(glass_img, (glass_x, glass_y))

    def draw_whisk_timer(self, screen, cell):
        x, y = cell["x"], cell["y"]
        timer_y = y + 20
        timer_w = 260
        py.draw.rect(screen, (80, 80, 80), (x + 20, timer_y, timer_w, 40))
        fill_w = int(timer_w * (cell["whisk_progress"] / 100))
        py.draw.rect(screen, YELLOW, (x + 20, timer_y, fill_w, 40))
        zone_start = cell["ideal_zone_start"]
        zone_end = cell["ideal_zone_end"]
        zone_w = int(timer_w * (zone_end - zone_start) / 100)
        zone_x = x + 20 + int(timer_w * zone_start / 100)
        py.draw.rect(screen, GREEN, (zone_x, timer_y, zone_w, 40))
        py.draw.rect(screen, (40, 40, 40), (x + 20, timer_y, timer_w, 40), 3)

    def espresso_lvl2_draw(self, screen, cell):
        for btn in cell["button_portion_espresso"].values():
            btn.draw(screen)

    def events(self, events):
        current_time = py.time.get_ticks()

        for cell in self.cells:
            if cell.get("is_pouring", False):
                self.update_pouring(cell, current_time)
            if cell.get("is_extending", False):
                self.update_extending(cell, current_time)
            if cell.get("is_whisking", False):
                self.update_whisking(cell, current_time)
            if cell.get("is_pouring_espresso", False):
                self.update_pouring_espresso(cell, current_time)
            if cell.get("is_espresso_extending", False):
                self.update_espresso_extending(cell, current_time)
            if cell.get("is_roasting", False):
                self.update_roasting(cell, current_time)

        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                for cell in self.cells:
                    self.start_drag_cap(cell, event.pos[0], event.pos[1])
                    self.start_drag_milk_cap(cell, event.pos[0], event.pos[1])

                # Обработка кликов по кнопкам
                for cell in self.cells:
                    # --- Главное меню ---
                    if cell["active_ingredient"] is None:
                        if cell["button_milk"].signal(event.pos):
                            cell["active_ingredient"] = "milk"
                            cell["menu_level"] = 1
                        elif cell["button_espresso"].signal(event.pos):
                            cell["active_ingredient"] = "espresso"
                            cell["menu_level"] = 1

                    # --- Молоко ---
                    elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 1:
                        if cell["undo_btn"].signal(event.pos):
                            cell["active_ingredient"] = None
                            cell["menu_level"] = 0
                        for btn in cell["milk_ingredient_buttons"]:
                            if btn.signal(event.pos):
                                cell["selected_milk_type"] = btn.ingredient_milk
                                cell["menu_level"] = 2

                    elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 2:
                        if cell["undo_btn"].signal(event.pos):
                            cell["menu_level"] = 1
                        if cell["button_temp_milk"]["hot"].signal(event.pos):
                            cell["selected_milk_temp"] = "hot"
                            cell["menu_level"] = 3
                            cell["show_pour_button"] = True
                        elif cell["button_temp_milk"]["cold"].signal(event.pos):
                            cell["selected_milk_temp"] = "cold"
                            cell["menu_level"] = 3
                            cell["show_pour_button"] = True

                    elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 3:
                        if cell["undo_btn"].signal(event.pos):
                            cell["menu_level"] = 2
                            cell["is_pouring"] = False
                            cell["show_pour_button"] = True
                            self.stop_pour_sound()
                        elif cell["show_pour_button"] and cell["button_portion_milk"].signal(event.pos):
                            cell["is_pouring"] = True
                            cell["pour_start_time"] = current_time
                            self.start_pour_sound()

                    # --- Эспрессо ---
                    elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 1:
                        if cell["undo_btn"].signal(event.pos):
                            cell["active_ingredient"] = None
                            cell["menu_level"] = 0
                        for btn in cell["espresso_ingredient_buttons"]:
                            if btn.signal(event.pos):
                                cell["selected_espresso_type"] = btn.ingredient_espresso
                                cell["menu_level"] = 2

                    elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 2:
                        for portion_key, portion_btn in cell["button_portion_espresso"].items():
                            if portion_btn.signal(event.pos):
                                cell["selected_espresso_portion"] = int(portion_btn.text)
                                cell["menu_level"] = 3
                                cell["roast_slider_progress"] = 0
                                cell["roast_slider_stopped"] = False
                                cell["roast_slider_direction"] = 1
                                cell["pour_espresso_progress"] = 0.0
                                print(f"Выбрано порций: {cell['selected_espresso_portion']}")

                    elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 3:
                        if not cell.get("roast_slider_stopped", False) and cell["espresso_stop_button"].signal(event.pos):
                            zone_start = cell.get("ideal_zone_start", 40)
                            zone_end = cell.get("ideal_zone_end", 60)
                            stop_pos = cell["roast_slider_progress"]
                            if zone_start <= stop_pos <= zone_end:
                                cell["roast_target_progress"] = zone_end
                            else:
                                cell["roast_target_progress"] = stop_pos
                            cell["roast_slider_stopped"] = True
                            cell["roast_slider_stop_position"] = stop_pos

                            # Запуск плавной заливки
                            portions = cell["selected_espresso_portion"]
                            cell["target_espresso_progress"] = portions / 4.0
                            cell["is_pouring_espresso"] = True
                            cell["pour_espresso_start_time"] = current_time
                            cell["pour_espresso_progress"] = 0.0

                            if self.pour_espresso_channel and self.sound_manager.sfx_enabled:
                                self.pour_espresso_sound.set_volume(self.sound_manager.sfx_volume)
                                self.pour_espresso_channel.play(self.pour_espresso_sound, loops=-1)

            elif event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                for cell in self.cells:
                    self.start_drag_cap(cell, event.pos[0], event.pos[1])
                    self.start_drag_milk_cap(cell, event.pos[0], event.pos[1])
            elif event.type == py.MOUSEMOTION:
                for cell in self.cells:
                    self.update_drag_cap(cell, event.pos[0], event.pos[1])
                    self.update_drag_milk_cap(cell, event.pos[0], event.pos[1])

            elif event.type == py.MOUSEBUTTONUP and event.button == 1:
                for cell in self.cells:
                    self.stop_drag_cap(cell)
                    self.stop_drag_milk_cap(cell)
                    if cell.get("is_pouring", False):
                        cell["is_pouring"] = False
                        cell["show_pour_button"] = False
                        self.stop_pour_sound()
                        if cell["pour_progress"] > 0:
                            cell["is_extending"] = True
                            cell["extend_start_time"] = current_time
                            cell["extend_progress"] = 0.0
                            cell["pipe_height"] = 50
                            print(f"Заливка остановлена, прогресс: {cell['pour_progress']:.2f}, труба вытягивается")

    def activate(self):
        super().activate()
        if self.whisk_was_playing:
            self.start_whisk_sound()
            self.whisk_was_playing = False
        if self.roast_was_playing:
            self.start_roast_sound()
            self.roast_was_playing = False

    def deactivate(self):
        if self.whisk_channel and self.whisk_channel.get_busy():
            self.whisk_was_playing = True
        else:
            self.whisk_was_playing = False

        if self.roast_channel and self.roast_channel.get_busy():
            self.roast_was_playing = True
        else:
            self.roast_was_playing = False

        self.stop_pour_sound()
        self.stop_whisk_sound()
        if self.pour_espresso_channel:
            self.pour_espresso_channel.stop()
        self.stop_roast_sound()
        super().deactivate()