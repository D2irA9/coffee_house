import pygame as py
from colors import *
from globals import *
from .base import Station
from ..node import font, ImageButton, Button
from ..tiled import Map

class BuildStation(Station):
    def __init__(self, sound_manager, milk_colors, espresso_colors, syrup_colors):
        self.sound_manager = sound_manager
        self.milk_colors = milk_colors
        self.espresso_colors = espresso_colors
        self.syrup_colors = syrup_colors
        super().__init__("Сборка")

        self.ready_drinks = []          # исходные стаканы (молоко/эспрессо)
        self.map = Map('assets/tiled/tmx/BuildStation.tmx', 48)
        self.map_loaded = False

        # ---- Стаканы для отображения ----
        scale_cup = 1.7
        original_img = py.image.load("assets/sprites/buttons/cap.png").convert_alpha()
        new_w = int(original_img.get_width() * scale_cup)
        new_h = int(original_img.get_height() * scale_cup)
        self.glass_img = py.transform.scale(original_img, (new_w, new_h))
        self.glass_width, self.glass_height = new_w, new_h

        drag_scale = 3
        self.drag_glass_img = py.transform.scale(original_img,
            (int(original_img.get_width() * drag_scale),
             int(original_img.get_height() * drag_scale)))
        self.drag_glass_width, self.drag_glass_height = self.drag_glass_img.get_size()

        # ---- Отдельный стакан для центра (cap_.png) ----
        center_img = py.image.load("assets/sprites/buttons/cap_.png").convert_alpha()
        self.center_cap_img = py.transform.scale(center_img,
            (int(center_img.get_width() * drag_scale),
             int(center_img.get_height() * drag_scale)))
        self.center_cap_width, self.center_cap_height = self.center_cap_img.get_size()
        self.center_cap_pos = ((1200 - self.center_cap_width)//2, 300)

        # ---- Параметры сетки исходных стаканов (дисплей) ----
        self.start_x, self.start_y = 40, 65
        self.gap_x, self.gap_y = 10, 10
        self.columns = 4
        self.show_display = True

        # ---- Drag & drop для исходных стаканов ----
        self.dragging = False
        self.dragged_index = None
        self.drag_offset_x = self.drag_offset_y = 0
        self.drag_mouse_pos = (0, 0)

        # ---- Зоны приёма (левая и правая) ----
        self.left_zone_rect = py.Rect(100, 270, 250, 300)
        self.right_zone_rect = py.Rect(850, 270, 250, 300)
        self.left_drink = None
        self.right_drink = None

        # ---- Размер стакана ----
        self.size_selected = False
        self.selected_size = None

        # ---- Кнопки выбора размера ----
        size_fon_img = py.image.load("assets/sprites/buttons/fon_cup.png").convert_alpha()
        self.fon_cup = py.transform.scale(size_fon_img,
            (int(size_fon_img.get_width() * drag_scale),
             int(size_fon_img.get_height() * drag_scale)))
        self.block_center = (600, 350)
        self.size_buttons = []
        sizes = ["S", "M", "L"]
        offsets = [-150, -30, 90]
        for i, size in enumerate(sizes):
            btn = ImageButton(f"assets/sprites/buttons/{size}.png",
                              (self.block_center[0] + offsets[i], 630), 3)
            btn.size = size
            self.size_buttons.append(btn)

        # ---- Режим добавления сиропов ----
        self.show_syrups_mode = False
        self.available_syrups = []       # список доступных сиропов (словари)
        self.added_syrups = []           # добавленные сиропы (имена)
        self.current_color = None         # текущий цвет заливки
        self.current_fill_ratio = 0.0     # текущая заполненность (0..1)

        # Флаги добавления основных ингредиентов в стакан
        self.left_added = False
        self.right_added = False

        # Спрайты для отображения основных напитков (будут загружены при необходимости)
        self.left_ingredient_sprite = None
        self.right_ingredient_sprite = None
        self.left_item_rect = None
        self.right_item_rect = None

        # ---- Кнопка "ГОТОВО" ----
        self.complete_button = Button(150, 40, GREEN, (525, 600))
        self.complete_button.visible = False
        self.complete_button.text = "ГОТОВО"

        # ---- Пагинация для полосы сиропов ----
        self.syrups_start_index = 0
        self.max_visible_syrups = 6
        self.prev_syrups_button = Button(40, 40, (100,100,150), (20, 180))
        self.next_syrups_button = Button(40, 40, (100,100,150), (1140, 180))

        # ---- Ссылка на станцию заказов (устанавливается извне) ----
        self.order_station = None

        # ---- Загрузка доступных сиропов для игрока ----
        self.load_available_syrups()

    def load_available_syrups(self):
        """Загружает из БД сиропы, доступные по уровню игрока."""
        from globals import db, id_player
        ingredients = db.get_ingredients_level(id_player)
        self.available_syrups = []
        for ing in ingredients:
            if ing['type'] == 'syrup':
                syrup_name = ing['name']
                color = self.syrup_colors.get(syrup_name, (200,100,200))
                sprite_path = f"assets/sprites/ingredients/syrup/{syrup_name}.png"
                # пробуем загрузить спрайт, если нет – используем заглушку
                try:
                    img = py.image.load(sprite_path).convert_alpha()
                    img = py.transform.scale(img, (80, 80))
                except:
                    img = None
                self.available_syrups.append({
                    'name': syrup_name,
                    'color': color,
                    'sprite': img,
                    'rect': None   # будет вычислено при отрисовке
                })

    def load_ingredient_sprite(self, drink):
        """Загружает спрайт ингредиента (молоко/эспрессо) по его типу и имени."""
        if drink is None:
            return None
        if drink['type'] == 'milk':
            folder = "assets/sprites/ingredients/milk"
            name = drink.get('milk_type')
        else:
            folder = "assets/sprites/ingredients/espresso"
            name = drink.get('espresso_type')
        if not name:
            return None
        path = os.path.join(folder, f"{name}.png")
        try:
            img = py.image.load(path).convert_alpha()
            img = py.transform.scale(img, (80, 80))
            return img
        except:
            return None

    def get_glass_rect(self, index):
        row = index // self.columns
        col = index % self.columns
        x = self.start_x + col * (self.glass_width + self.gap_x)
        y = self.start_y + row * (self.glass_height + self.gap_y)
        return py.Rect(x, y, self.glass_width, self.glass_height)

    def add_ready_drink(self, drink_type, milk_type=None, milk_temp=None, portions=0,
                        quality="normal", espresso_type=None, espresso_quality=None, fill_ratio=None):
        """Добавляет готовый напиток (молоко/эспрессо) на дисплей."""
        if drink_type == "milk":
            milk_color = self.milk_colors.get(milk_type, (255,250,240))
            ratio = fill_ratio if fill_ratio is not None else (portions / 4.0)
            drink_info = {
                "type": "milk",
                "milk_type": milk_type,
                "temperature": milk_temp,
                "quality": quality,
                "color": milk_color,
                "fill_ratio": ratio,
                "portions": portions
            }

            print(f"add_ready_drink called: portions={portions}, fill_ratio={fill_ratio}")
        else:  # espresso
            espresso_color = self.espresso_colors.get(espresso_type, (110,59,9))
            ratio = fill_ratio if fill_ratio is not None else (portions / 4.0)
            drink_info = {
                "type": "espresso",
                "espresso_type": espresso_type,
                "quality": espresso_quality if espresso_quality else "normal",
                "color": espresso_color,
                "fill_ratio": ratio,
                "portions": portions
            }
        self.ready_drinks.append(drink_info)
        if len(self.ready_drinks) > 20:
            self.ready_drinks.pop(0)
        print(f"BuildStation получил: {drink_info}")

    # ---------- Отрисовка исходных стаканов (дисплей) ----------
    def draw_display(self, screen):
        py.draw.rect(screen, FON, (0, 100, 1200, 100))
        py.draw.rect(screen, CONTOUR, (0, 100, 1200, 100), 3)
        if not self.ready_drinks:
            return
        for idx, drink in enumerate(self.ready_drinks):
            if self.dragging and idx == self.dragged_index:
                continue
            rect = self.get_glass_rect(idx)
            fill_height = int(self.glass_height * drink["fill_ratio"])
            if fill_height > 0:
                fill_rect = py.Rect(rect.x, rect.y + self.glass_height - fill_height,
                                    self.glass_width, fill_height)
                py.draw.rect(screen, drink["color"], fill_rect)
            screen.blit(self.glass_img, (rect.x, rect.y))

    def draw_dragged_glass(self, screen):
        if not self.dragging or self.dragged_index is None:
            return
        drink = self.ready_drinks[self.dragged_index]
        draw_x = self.drag_mouse_pos[0] - self.drag_offset_x
        draw_y = self.drag_mouse_pos[1] - self.drag_offset_y
        fill_height = int(self.drag_glass_height * drink["fill_ratio"])
        if fill_height > 0:
            fill_rect = py.Rect(draw_x, draw_y + self.drag_glass_height - fill_height,
                                self.drag_glass_width, fill_height)
            py.draw.rect(screen, drink["color"], fill_rect)
        screen.blit(self.drag_glass_img, (draw_x, draw_y))

    def draw_drink_in_zone(self, screen, drink, zone_rect):
        """Рисует увеличенный стакан в левой/правой зоне."""
        if drink is None:
            return
        glass_x = zone_rect.x + (zone_rect.width - self.drag_glass_width)//2
        glass_y = zone_rect.y + (zone_rect.height - self.drag_glass_height)//2
        fill_height = int(self.drag_glass_height * drink["fill_ratio"])
        if fill_height > 0:
            fill_rect = py.Rect(glass_x, glass_y + self.drag_glass_height - fill_height,
                                self.drag_glass_width, fill_height)
            py.draw.rect(screen, drink["color"], fill_rect)
        screen.blit(self.drag_glass_img, (glass_x, glass_y))

    # ---------- Отрисовка центрального стакана (смесь + сиропы) ----------
    def draw_center_glass(self, screen):
        x, y = self.center_cap_pos
        # заливка
        if self.current_fill_ratio > 0 and self.current_color:
            fill_height = int(self.center_cap_height * self.current_fill_ratio)
            fill_rect = py.Rect(x, y + self.center_cap_height - fill_height,
                                self.center_cap_width, fill_height)
            py.draw.rect(screen, self.current_color, fill_rect)
        # стакан поверх
        screen.blit(self.center_cap_img, (x, y))
    # ---------- Полоса сиропов ----------
    def draw_top_bar(self, screen):
        """Отрисовка горизонтальной полосы с основными ингредиентами и сиропами."""
        bar_x, bar_y = 0, 100
        bar_w, bar_h = 1200, 100
        py.draw.rect(screen, (70, 70, 90), (bar_x, bar_y, bar_w, bar_h))
        py.draw.rect(screen, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h), 3)

        # --- Основные ингредиенты (левый и правый) ---
        item_w, item_h = 120, 80
        spacing = 20
        start_x = bar_x + 70

        # Левый напиток
        if self.left_drink and not self.left_added:
            self._draw_ingredient_item(screen, self.left_drink, start_x, bar_y, item_w, item_h, 'left')
            left_rect = py.Rect(start_x, bar_y + (bar_h - item_h) // 2, item_w, item_h)
            self.left_item_rect = left_rect
            start_x += item_w + spacing
        else:
            self.left_item_rect = None

        # Правый напиток
        if self.right_drink and not self.right_added:
            self._draw_ingredient_item(screen, self.right_drink, start_x, bar_y, item_w, item_h, 'right')
            right_rect = py.Rect(start_x, bar_y + (bar_h - item_h) // 2, item_w, item_h)
            self.right_item_rect = right_rect
            start_x += item_w + spacing
        else:
            self.right_item_rect = None

        # --- Сиропы (с пагинацией) ---
        if len(self.available_syrups) > self.max_visible_syrups:
            self.prev_syrups_button.draw(screen)
            self.next_syrups_button.draw(screen)
            self.prev_syrups_button.change_color((100, 100, 150) if self.syrups_start_index > 0 else (70, 70, 100))
            self.next_syrups_button.change_color((100, 100, 150) if self.syrups_start_index + self.max_visible_syrups < len(self.available_syrups) else (70, 70, 100))

        visible = self.available_syrups[self.syrups_start_index:self.syrups_start_index + self.max_visible_syrups]
        for i, syrup in enumerate(visible):
            x = start_x + i * (item_w + spacing)
            y = bar_y + (bar_h - item_h) // 2
            py.draw.rect(screen, syrup['color'], (x, y, item_w, item_h))
            py.draw.rect(screen, (255, 255, 200), (x, y, item_w, item_h), 3)
            if syrup['sprite']:
                sprite_rect = syrup['sprite'].get_rect(center=(x + item_w // 2, y + item_h // 2))
                screen.blit(syrup['sprite'], sprite_rect)
            else:
                name_text = font.text_ret(18, syrup['name'][:10], (0, 0, 0))
                screen.blit(name_text, (x + 5, y + 30))
            syrup['rect'] = py.Rect(x, y, item_w, item_h)

    def _draw_ingredient_item(self, screen, drink, x, bar_y, item_w, item_h, side):
        """Рисует отдельный элемент основного ингредиента."""
        y = bar_y + (100 - item_h) // 2
        color = drink['color']
        py.draw.rect(screen, color, (x, y, item_w, item_h))
        py.draw.rect(screen, (255, 255, 200), (x, y, item_w, item_h), 3)
        # Пытаемся загрузить спрайт, если ещё не загружен
        if side == 'left' and self.left_ingredient_sprite is None:
            self.left_ingredient_sprite = self.load_ingredient_sprite(drink)
        elif side == 'right' and self.right_ingredient_sprite is None:
            self.right_ingredient_sprite = self.load_ingredient_sprite(drink)
        sprite = self.left_ingredient_sprite if side == 'left' else self.right_ingredient_sprite
        if sprite:
            sprite_rect = sprite.get_rect(center=(x + item_w // 2, y + item_h // 2))
            screen.blit(sprite, sprite_rect)
        else:
            # Текст с названием
            name = drink.get('milk_type') or drink.get('espresso_type') or drink['type']
            name_text = font.text_ret(18, name[:10], (0, 0, 0))
            screen.blit(name_text, (x + 5, y + 30))
        # Отображаем порции
        portions = drink.get('portions', 1)
        portions_text = font.text_ret(18, f"{portions} порц.", (0, 0, 0))
        screen.blit(portions_text, (x + 5, y + 55))

    # ---------- Логика смешивания ----------
    def compute_initial_mix(self):
        """Вычисляет начальный цвет и заполненность на основе левого и правого напитков."""
        if not self.left_drink or not self.right_drink:
            return
        # порции
        left_ports = self.left_drink.get('portions', 1)
        right_ports = self.right_drink.get('portions', 1)
        total_ports = left_ports + right_ports
        max_ports = {'S':6, 'M':5, 'L':4}[self.selected_size]
        self.current_fill_ratio = min(total_ports / max_ports, 1.0)

        # смешивание цветов с весами по порциям
        col1 = self.left_drink['color']
        col2 = self.right_drink['color']
        w1 = left_ports / total_ports
        w2 = right_ports / total_ports
        r = int(col1[0]*w1 + col2[0]*w2)
        g = int(col1[1]*w1 + col2[1]*w2)
        b = int(col1[2]*w1 + col2[2]*w2)
        self.current_color = (r,g,b)

    def add_main_ingredient(self, side):
        """Добавляет основной ингредиент (левый или правый) в стакан."""
        drink = self.left_drink if side == 'left' else self.right_drink
        if not drink:
            return
        if (side == 'left' and self.left_added) or (side == 'right' and self.right_added):
            return

        max_ports = {'S': 6, 'M': 5, 'L': 4}[self.selected_size]
        portions = drink.get('portions', 1)
        increment = portions / max_ports
        self.current_fill_ratio = min(self.current_fill_ratio + increment, 1.0)

        # Смешиваем цвет с учётом порций (вес нового ингредиента = increment / (текущая_сумма+increment))
        if self.current_color is None:
            self.current_color = drink['color']
        else:
            total_ratio = self.current_fill_ratio  # уже включает increment
            old_weight = (self.current_fill_ratio - increment) / self.current_fill_ratio if self.current_fill_ratio > 0 else 0
            new_weight = increment / self.current_fill_ratio if self.current_fill_ratio > 0 else 1
            # Но проще использовать накопление цветов через взвешенное среднее с весами = порции
            # Для простоты используем среднее арифметическое (как в прототипе)
            r = (self.current_color[0] + drink['color'][0]) // 2
            g = (self.current_color[1] + drink['color'][1]) // 2
            b = (self.current_color[2] + drink['color'][2]) // 2
            self.current_color = (r, g, b)

        if side == 'left':
            self.left_added = True
        else:
            self.right_added = True
        print(f"Добавлен {side} ингредиент: {drink}, заполнено: {self.current_fill_ratio * 100:.0f}%")

    def add_syrup(self, syrup):
        """Добавляет сироп в стакан – увеличивает заполненность (опционально) и смешивает цвет."""
        self.added_syrups.append(syrup['name'])
        # Увеличиваем заполненность на 10% (или фиксированно)
        increment = 0.1
        self.current_fill_ratio = min(self.current_fill_ratio + increment, 1.0)
        # Смешиваем цвет
        if self.current_color is None:
            self.current_color = syrup['color']
        else:
            self.current_color = (
                (self.current_color[0] + syrup['color'][0]) // 2,
                (self.current_color[1] + syrup['color'][1]) // 2,
                (self.current_color[2] + syrup['color'][2]) // 2,
            )
        print(f"Добавлен сироп: {syrup['name']}, заполнено: {self.current_fill_ratio * 100:.0f}%")

    def complete_drink(self):
        """Передаёт готовый напиток в OrderStation и сбрасывает состояние."""
        if not self.order_station:
            print("Ошибка: OrderStation не подключена к BuildStation")
            return
        drink_data = {
            'size': self.selected_size,
            'left_drink': self.left_drink,
            'right_drink': self.right_drink,
            'syrups': self.added_syrups,
            'color': self.current_color,
            'fill_ratio': self.current_fill_ratio
        }
        self.order_station.add_completed_drink(drink_data)
        self.reset_build_station()

    def reset_build_station(self):
        """Сбрасывает всё состояние станции для нового заказа."""
        self.left_drink = None
        self.right_drink = None
        self.size_selected = False
        self.selected_size = None
        self.show_syrups_mode = False
        self.added_syrups = []
        self.current_color = None
        self.current_fill_ratio = 0.0
        self.complete_button.visible = False
        self.syrups_start_index = 0
        # очищаем готовые напитки (стаканы на дисплее) – по желанию
        self.ready_drinks.clear()
        self.left_added = False
        self.right_added = False
        self.left_ingredient_sprite = None
        self.right_ingredient_sprite = None
        self.left_item_rect = None
        self.right_item_rect = None

    # ---------- Основные методы отрисовки и событий ----------
    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True
        self.map.draw_all(screen)

        # Левая и правая зоны
        py.draw.rect(screen, (40,102,142), (0,160,400,430))
        py.draw.rect(screen, CONTOUR, (0,160,400,430), 3)
        py.draw.rect(screen, FON, self.left_zone_rect)
        py.draw.rect(screen, CONTOUR, self.left_zone_rect, 3)
        self.draw_drink_in_zone(screen, self.left_drink, self.left_zone_rect)

        py.draw.rect(screen, (40,102,142), (800,160,400,430))
        py.draw.rect(screen, CONTOUR, (800,160,400,430), 3)
        py.draw.rect(screen, FON, self.right_zone_rect)
        py.draw.rect(screen, CONTOUR, self.right_zone_rect, 3)
        self.draw_drink_in_zone(screen, self.right_drink, self.right_zone_rect)

        if self.show_display and not self.show_syrups_mode:
            self.draw_display(screen)
        self.draw_dragged_glass(screen)

        # Кнопки выбора размера (если оба ингредиента есть и размер не выбран)
        if self.left_drink and self.right_drink and not self.size_selected:
            screen.blit(self.fon_cup, (400,615))
            for btn in self.size_buttons:
                btn.draw(screen)

        # Режим добавления сиропов
        if self.size_selected and self.show_syrups_mode:
            self.draw_center_glass(screen)
            self.draw_top_bar(screen)
            self.complete_button.draw(screen)

    def events(self, events):
        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                # Выбор размера
                if self.left_drink and self.right_drink and not self.size_selected:
                    for btn in self.size_buttons:
                        if btn.signal(event.pos):
                            self.selected_size = btn.size
                            self.size_selected = True
                            self.show_syrups_mode = True
                            self.current_color = None
                            self.current_fill_ratio = 0.0
                            self.added_syrups = []
                            self.complete_button.visible = True
                            return

                # Режим добавления ингредиентов и сиропов
                if self.size_selected and self.show_syrups_mode:
                    # Кнопка "ГОТОВО"
                    if self.complete_button.signal(event.pos):
                        self.complete_drink()
                        return

                    # Пагинация сиропов
                    if self.prev_syrups_button.signal(event.pos) and self.syrups_start_index > 0:
                        self.syrups_start_index -= 1
                        return
                    if self.next_syrups_button.signal(event.pos) and self.syrups_start_index + self.max_visible_syrups < len(self.available_syrups):
                        self.syrups_start_index += 1
                        return

                    # Клик по левому основному ингредиенту
                    if self.left_item_rect and self.left_item_rect.collidepoint(event.pos):
                        self.add_main_ingredient('left')
                        return

                    # Клик по правому основному ингредиенту
                    if self.right_item_rect and self.right_item_rect.collidepoint(event.pos):
                        self.add_main_ingredient('right')
                        return

                    # Клик по сиропу
                    for syrup in self.available_syrups:
                        if syrup.get('rect') and syrup['rect'].collidepoint(event.pos):
                            self.add_syrup(syrup)
                            return

                # Начало перетаскивания (только если не в режиме сиропов)
                if not self.show_syrups_mode:
                    for idx, _ in enumerate(self.ready_drinks):
                        rect = self.get_glass_rect(idx)
                        if rect.collidepoint(event.pos):
                            self.dragging = True
                            self.dragged_index = idx
                            self.drag_offset_x = event.pos[0] - rect.x
                            self.drag_offset_y = event.pos[1] - rect.y
                            self.drag_mouse_pos = event.pos
                            break

            elif event.type == py.MOUSEMOTION and self.dragging:
                self.drag_mouse_pos = event.pos

            elif event.type == py.MOUSEBUTTONUP and event.button == 1 and self.dragging:
                zone = None
                if self.left_zone_rect.collidepoint(event.pos):
                    zone = 'left'
                elif self.right_zone_rect.collidepoint(event.pos):
                    zone = 'right'

                if zone is not None and self.dragged_index is not None:
                    drink = self.ready_drinks.pop(self.dragged_index)
                    if zone == 'left':
                        self.left_drink = drink
                    else:
                        self.right_drink = drink
                    print(f"Напиток помещён в {zone} стакан: {drink}")

                self.dragging = False
                self.dragged_index = None