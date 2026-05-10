from colors import *
from globals import *
from .base import Station
from ..tiled import Map
from ..node import CircleButton, Button, ImageButton
import globals, math, random

class BrewStation(Station):
    """
    Станция приготовления молочной основы.
    Управляет выбором молока, температуры, наливкой, опусканием трубы и взбиванием.
    """

    def __init__(self, sound_manager, milk_colors, espresso_colors, syrup_colors):
        """
        Инициализация станции.
        :param sound_manager: объект SoundManager для управления звуками
        :param milk_colors: словарь {название молока: цвет RGB}
        :param espresso_colors: словарь цветов для эспрессо (не используется)
        :param syrup_colors: словарь цветов для сиропов (не используется)
        """
        self.sound_manager = sound_manager
        self.milk_colors = milk_colors
        self.espresso_colors = espresso_colors
        self.syrup_colors = syrup_colors
        super().__init__("Приготовление")

        #-- Загрузка карты и фона
        self.map = Map('assets/tiled/tmx/stations1.tmx', 48)
        self.map_loaded = False

        scale = 3
        self.cells = []
        self.cells_pos = [(0, 75), (303, 75), (606, 75), (909, 75)]   # позиции 4-х ячеек
        self.fon_img = py.image.load("assets/sprites/buttons/fon.png").convert_alpha()
        new_w = int(self.fon_img.get_width() * scale)
        new_h = int(self.fon_img.get_height() * scale)
        self.image = py.transform.scale(self.fon_img, (new_w, new_h))

        # Звуки
        self.pour_sound = py.mixer.Sound("assets/sounds/sound/gotovka/Заливка_молока.mp3")
        self.pour_channel = py.mixer.Channel(1) if py.mixer.get_init() else None
        self.is_sound_playing = False

        self.whisk_sound = py.mixer.Sound("assets/sounds/sound/gotovka/Взбивание.mp3")
        self.whisk_channel = py.mixer.Channel(2) if py.mixer.get_init() else None
        self.whisk_was_playing = False      # флаг для восстановления звука при переключении станций

        # Загрузка ингредиентов из БД
        self.type_ingredients = db.get_ingredients_level(globals.id_player)

        # Создание 4-х ячеек (рабочих мест)
        for i, (x, y) in enumerate(self.cells_pos):
            center_x = x + 114
            center_y = y + 210
            radius = 100

            #Кнопки выбора молока (расположение по кругу)
            milk_ingredient_buttons = []
            milk_ingredients = [ing for ing in self.type_ingredients if ing["type"] == "milk"]
            num_milk = len(milk_ingredients)
            for idx, ing in enumerate(milk_ingredients):
                angle = (2 * math.pi * idx) / num_milk
                btn_x = center_x + radius * math.cos(angle)
                btn_y = center_y + radius * math.sin(angle)
                btn = ImageButton(f'assets/sprites/ingredients/milk/{ing["name"]}.png', (int(btn_x), int(btn_y)), 3)
                btn.ingredient_name = ing["name"]   # сохраняем имя ингредиента для последующего выбора
                milk_ingredient_buttons.append(btn)

            #Кнопки выбора эспрессо (заглушка, пока не используется)
            espresso_ingredient_buttons = []
            espresso_ingredients = [ing for ing in self.type_ingredients if ing["type"] == "espresso"]
            num_espresso = len(espresso_ingredients)
            for idx, ing in enumerate(espresso_ingredients):
                angle = (2 * math.pi * idx) / num_espresso
                btn_x = center_x + radius * math.cos(angle)
                btn_y = center_y + radius * math.sin(angle)
                btn = ImageButton(f'assets/sprites/ingredients/espresso/{ing["name"]}.png', (int(btn_x), int(btn_y)), 3)
                espresso_ingredient_buttons.append(btn)

            #Структура ячейки: хранит все данные о текущем процессе
            cell = {
                "id": i,
                "x": x,
                "y": y,
                "image": self.image,

                # Состояния меню
                "active_ingredient": None,    # 'milk' или 'espresso'
                "menu_level": 0,              # 0-главное,1-выбор типа,2-температура,3-наливка,4-взбивание

                # Кнопки управления
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

                # Переменные наливки
                "is_pouring": False,
                "pour_start_time": 0,
                "pour_progress": 0.0,
                "show_pour_button": True,

                # Анимация опускания трубы
                "is_extending": False,
                "extend_start_time": 0,
                "extend_progress": 0.0,
                "pipe_height": 50,            # начальная высота трубы (короткая)

                # Взбивание
                "is_whisking": False,
                "whisk_start_time": 0,
                "whisk_progress": 0.0,
                "ideal_zone_start": 0,
                "ideal_zone_end": 0,
            }
            self.cells.append(cell)

    # Управление громкостью звуков
    def update_sound_volume(self):
        if self.pour_sound and self.sound_manager:
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.pour_sound.set_volume(vol)
        if self.whisk_sound and self.sound_manager:
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.whisk_sound.set_volume(vol)

    #Звуки наливки
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

    #Звуки взбивания
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

    # Анимация опускания трубы
    def update_extending(self, cell, current_time):
        """
        Анимация вытягивания трубы в стакан.
        Длительность 1 секунда. По окончании запускается взбивание.
        """
        if not cell.get("is_extending", False):
            return

        elapsed = (current_time - cell["extend_start_time"]) / 1000.0
        animation_duration = 1.0

        if elapsed >= animation_duration:
            # Анимация завершена – труба полностью опущена
            cell["is_extending"] = False
            cell["pipe_height"] = 219                # полная высота (до дна)
            cell["extend_progress"] = 1.0
            # Переход к взбиванию
            cell["is_whisking"] = True
            cell["whisk_start_time"] = current_time
            cell["whisk_progress"] = 0.0
            cell["menu_level"] = 4
            self.start_whisk_sound()
            print("Труба достала до дна, начинаем взбивание")
        else:
            # Плавное увеличение высоты трубы
            progress = elapsed / animation_duration
            cell["extend_progress"] = progress
            cell["pipe_height"] = int(50 + (219 - 50) * progress)

    # Процесс взбивания (таймер и качество)
    def update_whisking(self, cell, current_time):
        """
        Обновление таймера взбивания. Время зависит от количества порций.
        При достижении 100% звук и пузырьки отключаются.
        """
        if not cell.get("is_whisking", False):
            return

        # Подстройка громкости звука в реальном времени
        if self.whisk_channel and self.whisk_channel.get_busy():
            vol = self.sound_manager.sfx_volume if self.sound_manager.sfx_enabled else 0.0
            self.whisk_sound.set_volume(vol)

        elapsed = (current_time - cell["whisk_start_time"]) / 1000.0
        portions = int(cell["pour_progress"] * 4)
        if portions < 1:
            portions = 1

        # Задание времени взбивания и зелёной зоны (в процентах таймера)
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

        # По достижении 100% останавливаем взбивание
        if progress >= 100.0:
            cell["is_whisking"] = False
            self.stop_whisk_sound()
            print("Взбивание завершено (таймер остановлен, звук и эффекты прекращены)")

    # Обновление процесса наливки
    def update_pouring(self, cell, current_time):
        """
        Плавное увеличение pour_progress при зажатой кнопке.
        Полная заливка занимает 20 секунд (max_time = 20).
        """
        if not cell["is_pouring"]:
            return

        # Обновляем громкость звука заливки
        if self.is_sound_playing and self.pour_channel and self.pour_channel.get_busy():
            self.update_sound_volume()

        elapsed = (current_time - cell["pour_start_time"]) / 1000.0
        max_time = 20.0          # время полной заливки (можно регулировать)
        new_progress = min(1.0, elapsed / max_time)
        cell["pour_progress"] = new_progress

        if new_progress >= 1.0:
            # Автоматический переход к опусканию трубы
            cell["is_pouring"] = False
            cell["show_pour_button"] = False
            self.stop_pour_sound()
            cell["is_extending"] = True
            cell["extend_start_time"] = current_time
            cell["extend_progress"] = 0.0
            cell["pipe_height"] = 50
            print("Заливка завершена, труба вытягивается")

    # Отрисовка всех элементов
    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True

        self.map.draw_all(screen)

        for cell in self.cells:
            # Фон ячейки
            screen.blit(cell["image"], (cell["x"], cell["y"]))
            py.draw.rect(screen, CONTOUR, (cell["x"] - 3, cell["y"] - 3, 305, 501), 3)

            #Отрисовка в зависимости от состояния ячейки
            if cell["active_ingredient"] is None:
                # Главное меню (молоко / эспрессо)
                cell["button_milk"].draw(screen)
                cell["button_espresso"].draw(screen)

            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 1:
                # Выбор типа молока (кнопки по кругу)
                cell["undo_btn"].draw(screen)
                for btn in cell["milk_ingredient_buttons"]:
                    btn.draw(screen)

            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 2:
                # Выбор температуры
                self.milk_lvl2_draw(screen, cell)

            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 3:
                # Наливка (стакан, труба, кнопка наливки)
                self.milk_lvl3_draw(screen, cell)

            elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 4:
                # Взбивание (таймер, пузырьки)
                self.milk_whisk_draw(screen, cell)

            elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 1:
                # Заглушка эспрессо
                cell["undo_btn"].draw(screen)
                for btn in cell["espresso_ingredient_buttons"]:
                    btn.draw(screen)

        # Отладочные прямоугольники (можно удалить или оставить)
        py.draw.rect(screen, RED, (350, 620, 70, 50), 3)
        py.draw.rect(screen, GREEN, (780, 620, 70, 50), 3)

    # Вспомогательные отрисовки
    def milk_lvl2_draw(self, screen, cell):
        """Отрисовка кнопок выбора температуры (горячее/холодное)"""
        for btn in cell["button_temp_milk"].values():
            btn.draw(screen)

    def milk_lvl3_draw(self, screen, cell):
        """
        Отрисовка уровня наливки:
        - труба, которая может вытягиваться
        - стакан с прогрессом заливки
        - кнопка наливки (показывается только если не идёт анимация трубы)
        """
        x, y = cell["x"], cell["y"]
        pipe_height = cell.get("pipe_height", 50)
        pipe_y = y + 80

        # Фон области
        py.draw.rect(screen, FON, (x + 25, y + 80, 250, 300))
        py.draw.rect(screen, CONTOUR, (x + 25, y + 80, 250, 300), 3)

        # Труба (высота меняется во время анимации)
        py.draw.rect(screen, PIPE, (x + 125, pipe_y, 50, pipe_height))
        py.draw.rect(screen, CONTOUR, (x + 125, pipe_y, 50, pipe_height), 3)

        # Наконечник трубы (если труба уже не короткая)
        if pipe_height > 50:
            tip_y = pipe_y + pipe_height - 10
            py.draw.rect(screen, (100, 100, 100), (x + 125, tip_y, 50, 10))

        # Капли при вытягивании
        if cell.get("is_extending", False):
            for i in range(5):
                drop_x = x + 125 + random.randint(-10, 60)
                drop_y = pipe_y + pipe_height + random.randint(0, 20)
                py.draw.circle(screen, (200, 200, 255), (drop_x, drop_y), random.randint(2, 4))

        # Стакан
        glass_x, glass_y = x + 40, y + 150
        glass_w, glass_h = 219, 219
        py.draw.rect(screen, WHITE, (glass_x, glass_y, glass_w, glass_h), 3)

        # Заливка молоком (цвет зависит от выбранного типа)
        if cell["pour_progress"] > 0:
            fill_h = int(cell["pour_progress"] * glass_h)
            fill_rect = py.Rect(glass_x, glass_y + glass_h - fill_h, glass_w, fill_h)
            milk_color = self.milk_colors.get(cell.get("selected_milk_type"), (255, 250, 240))
            py.draw.rect(screen, milk_color, fill_rect)

        # Кнопка наливки (отображается, если не идёт анимация трубы)
        if cell["show_pour_button"] and not cell.get("is_extending", False):
            cell["button_portion_milk"].draw(screen)

        # Декоративная крышка
        cell["cap"].draw(screen)

    def milk_whisk_draw(self, screen, cell):
        """
        Отрисовка уровня взбивания:
        - труба полностью опущена
        - пузырьки (только если взбивание активно)
        - таймер взбивания
        - стакан с заливкой
        """
        x, y = cell["x"], cell["y"]

        py.draw.rect(screen, FON, (x + 25, y + 80, 250, 300))
        py.draw.rect(screen, CONTOUR, (x + 25, y + 80, 250, 300), 3)

        # Труба опущена (фиксированная высота 219)
        pipe_y = y + 80
        pipe_height = cell.get("pipe_height", 219)
        py.draw.rect(screen, PIPE, (x + 125, pipe_y, 50, pipe_height))
        py.draw.rect(screen, CONTOUR, (x + 125, pipe_y, 50, pipe_height), 3)

        # Эффект пузырьков только во время взбивания
        if cell["is_whisking"]:
            for i in range(10):
                bubble_x = x + 40 + random.randint(0, 219)
                bubble_y = y + 150 + random.randint(0, 219)
                offset = (py.time.get_ticks() // 50) % 20
                bubble_y = bubble_y - offset
                if bubble_y > y + 150:
                    py.draw.circle(screen, (200, 200, 255, 150), (bubble_x, bubble_y), random.randint(2, 5))

        # Таймер
        self.draw_whisk_timer(screen, cell)

        # Стакан
        glass_x, glass_y = x + 40, y + 150
        glass_w, glass_h = 219, 219
        py.draw.rect(screen, WHITE, (glass_x, glass_y, glass_w, glass_h), 3)

        # Заливка молоком (цвет берётся из словаря milk_colors)
        if cell["pour_progress"] > 0:
            fill_h = int(cell["pour_progress"] * glass_h)
            fill_rect = py.Rect(glass_x, glass_y + glass_h - fill_h, glass_w, fill_h)
            milk_color = self.milk_colors.get(cell.get("selected_milk_type"), (255, 250, 240))
            py.draw.rect(screen, milk_color, fill_rect)

        cell["cap"].draw(screen)

    def draw_whisk_timer(self, screen, cell):
        """Отрисовка таймера взбивания: серый фон, жёлтый прогресс, зелёная зона"""
        x, y = cell["x"], cell["y"]
        timer_y = y + 20
        timer_w = 260

        # Фон
        py.draw.rect(screen, (80, 80, 80), (x + 20, timer_y, timer_w, 40))
        # Заполненная часть (прогресс)
        fill_w = int(timer_w * (cell["whisk_progress"] / 100))
        py.draw.rect(screen, YELLOW, (x + 20, timer_y, fill_w, 40))

        # Зелёная зона (идеальное время остановки)
        zone_start = cell["ideal_zone_start"]
        zone_end = cell["ideal_zone_end"]
        zone_w = int(timer_w * (zone_end - zone_start) / 100)
        zone_x = x + 20 + int(timer_w * zone_start / 100)
        py.draw.rect(screen, GREEN, (zone_x, timer_y, zone_w, 40))
        # Контур
        py.draw.rect(screen, (40, 40, 40), (x + 20, timer_y, timer_w, 40), 3)

    # Обработка событий
    def events(self, events):
        current_time = py.time.get_ticks()

        # Обновление анимаций и процессов
        for cell in self.cells:
            if cell.get("is_pouring", False):
                self.update_pouring(cell, current_time)
            if cell.get("is_extending", False):
                self.update_extending(cell, current_time)
            if cell.get("is_whisking", False):
                self.update_whisking(cell, current_time)

        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                for cell in self.cells:
                    #Главное меню
                    if cell["active_ingredient"] is None:
                        if cell["button_milk"].signal(event.pos):
                            cell["active_ingredient"] = "milk"
                            cell["menu_level"] = 1
                        elif cell["button_espresso"].signal(event.pos):
                            cell["active_ingredient"] = "espresso"
                            cell["menu_level"] = 1

                    #Выбор типа молока (уровень 1)
                    elif cell["active_ingredient"] == "milk" and cell["menu_level"] == 1:
                        if cell["undo_btn"].signal(event.pos):
                            cell["active_ingredient"] = None
                            cell["menu_level"] = 0
                        for btn in cell["milk_ingredient_buttons"]:
                            if btn.signal(event.pos):
                                cell["selected_milk_type"] = btn.ingredient_name
                                cell["menu_level"] = 2

                    #Выбор температуры (уровень 2)
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

                    #Наливка (уровень 3)
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

                    #Эспрессо (заглушка)
                    elif cell["active_ingredient"] == "espresso" and cell["menu_level"] == 1:
                        if cell["undo_btn"].signal(event.pos):
                            cell["active_ingredient"] = None
                            cell["menu_level"] = 0
                        for btn in cell["espresso_ingredient_buttons"]:
                            if btn.signal(event.pos):
                                print("Выбран эспрессо (заглушка)")

            #Отпускание кнопки мыши: останавливаем наливку и запускаем опускание трубы
            elif event.type == py.MOUSEBUTTONUP and event.button == 1:
                for cell in self.cells:
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

    # Управление активацией/деактивацией станции
    def activate(self):
        """Активация станции. Если до переключения играл звук взбивания – возобновляем."""
        super().activate()
        if self.whisk_was_playing:
            self.start_whisk_sound()
            self.whisk_was_playing = False

    def deactivate(self):
        """Деактивация. Запоминаем, играл ли звук взбивания, и останавливаем все звуки."""
        if self.whisk_channel and self.whisk_channel.get_busy():
            self.whisk_was_playing = True
        else:
            self.whisk_was_playing = False
        self.stop_pour_sound()
        self.stop_whisk_sound()
        super().deactivate()