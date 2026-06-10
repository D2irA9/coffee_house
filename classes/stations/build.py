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

        self.ready_drinks = []          # исходные стаканы (молоко/эспрессо) с дисплея
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
        self.center_cap_rect = py.Rect(self.center_cap_pos[0], self.center_cap_pos[1],
                                       self.center_cap_width, self.center_cap_height)

        # ---- Параметры сетки исходных стаканов (дисплей) ----
        self.start_x, self.start_y = 40, 65
        self.gap_x, self.gap_y = 10, 10
        self.columns = 4
        self.show_display = True

        # ---- Drag & drop для исходных стаканов (из дисплея в зоны) ----
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

        # ---- Зацикленная лента ингредиентов (сиропы + левый/правый) ----
        self.top_bar_items = []          # все доступные ингредиенты (сиропы и напитки)
        self.current_bar_index = 0       # сдвиг ленты (индекс первого видимого)
        self.max_visible_items = 6       # сколько элементов показываем
        self.bar_dragging = False        # флаг перетаскивания ленты
        self.bar_drag_start_x = 0
        self.bar_drag_start_index = 0
        # --- новая полоса: центрированная, шириной 1000px ---
        self.bar_width = 1000
        self.bar_height = 100
        self.bar_x = (1200 - self.bar_width) // 2
        self.bar_y = 100
        self.bar_rect = py.Rect(self.bar_x, self.bar_y, self.bar_width, self.bar_height)

        # ---- Перетаскивание основных ингредиентов из зон в центральный стакан ----
        self.dragging_ingredient = None
        self.drag_ingredient_icon = None

        # ---- Анимация наливания ----
        self.pouring = False
        self.pouring_item = None
        self.pour_start_time = 0
        self.pour_duration = 1.0
        self.pour_progress = 0.0
        self.start_fill_ratio = 0.0
        self.start_color = None
        self.target_fill_ratio = 0.0
        self.target_color = None

        # ---- Ссылка на станцию заказов ----
        self.order_station = None

        # ---- Загрузка сиропов из БД ----
        self.load_available_syrups()

        # ---- Добавляем сиропы в ленту ----
        for syrup in self.available_syrups:
            self.top_bar_items.append({
                "type": "syrup",
                "name": syrup['name'],
                "color": syrup['color'],
                "sprite": syrup['sprite'],
                "portions": 0,
                "is_syrup": True
            })

        # ---- Переменные для левого/правого ингредиентов ----
        self.left_in_bar = False
        self.right_in_bar = False

        # ---- Состояние стакана (заливка, цвет) ----
        self.current_color = None
        self.current_fill_ratio = 0.0
        self.target_fill_ratio = 0.0
        self.target_color = None
        self.start_fill_ratio = 0.0
        self.start_color = None

        # ---- Флаги добавления основных ингредиентов ----
        self.left_added = False
        self.right_added = False
        self.show_final_stage = False

        # ---- Кнопки принятия/отмены ----
        self.accept_button = Button(100, 40, GREEN, (480, 600))
        self.accept_button.text = "Принять"
        self.cancel_button = Button(100, 40, RED, (620, 600))
        self.cancel_button.text = "Отмена"
        self.accept_button.visible = False
        self.cancel_button.visible = False
        self.left_ingredient_added = False
        self.right_ingredient_added = False

    def load_available_syrups(self):
        from globals import db, id_player
        ingredients = db.get_ingredients_level(id_player)
        self.available_syrups = []
        for ing in ingredients:
            if ing['type'] == 'syrup':
                syrup_name = ing['name']
                color = self.syrup_colors.get(syrup_name, (200,100,200))
                sprite_path = f"assets/sprites/ingredients/syrup/{syrup_name}.png"
                try:
                    img = py.image.load(sprite_path).convert_alpha()
                    img = py.transform.scale(img, (80, 80))
                except:
                    img = None
                self.available_syrups.append({
                    'name': syrup_name,
                    'color': color,
                    'sprite': img
                })

    def load_ingredient_sprite(self, drink):
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
        import os
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
        else:
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

    # ---------- Отрисовка центрального стакана с анимацией ----------
    def draw_center_glass(self, screen):
        x, y = self.center_cap_pos
        if self.current_fill_ratio > 0 and self.current_color:
            fill_height = int(self.center_cap_height * self.current_fill_ratio)
            fill_rect = py.Rect(x, y + self.center_cap_height - fill_height,
                                self.center_cap_width, fill_height)
            py.draw.rect(screen, self.current_color, fill_rect)
        if self.pouring and self.pour_progress > 0 and self.pouring_item:
            temp_color = self.pouring_item.get('color', (255,255,255))
            poured_ratio = (self.current_fill_ratio - self.start_fill_ratio) if self.current_fill_ratio > self.start_fill_ratio else 0
            if poured_ratio > 0:
                fill_h = int(self.center_cap_height * poured_ratio)
                fill_rect = py.Rect(x, y + self.center_cap_height - fill_h,
                                    self.center_cap_width, fill_h)
                s = py.Surface((self.center_cap_width, fill_h), py.SRCALPHA)
                s.fill((*temp_color, 128))
                screen.blit(s, fill_rect)
        screen.blit(self.center_cap_img, (x, y))

    # ---------- Зацикленная лента ингредиентов (центрированная) ----------
    def get_visible_bar_items(self):
        if not self.top_bar_items:
            return []
        total = len(self.top_bar_items)
        visible = []
        for i in range(self.max_visible_items):
            idx = (self.current_bar_index + i) % total
            visible.append(self.top_bar_items[idx])
        return visible

    def draw_top_bar(self, screen):
        py.draw.rect(screen, (70,70,90), self.bar_rect)
        py.draw.rect(screen, (40,40,60), self.bar_rect, 3)

        visible_items = self.get_visible_bar_items()
        item_w, item_h = 120, 80
        spacing = 20
        total_width = self.max_visible_items * item_w + (self.max_visible_items - 1) * spacing
        start_x = self.bar_x + (self.bar_width - total_width) // 2
        for i, item in enumerate(visible_items):
            x = start_x + i * (item_w + spacing)
            y = self.bar_y + (self.bar_height - item_h)//2
            item['rect'] = py.Rect(x, y, item_w, item_h)
            py.draw.rect(screen, item['color'], (x, y, item_w, item_h))
            if i == self.max_visible_items // 2:
                py.draw.rect(screen, (255,255,100), (x, y, item_w, item_h), 4)
            else:
                py.draw.rect(screen, (255,255,200), (x, y, item_w, item_h), 3)
            if 'sprite' in item and item['sprite']:
                sprite_rect = item['sprite'].get_rect(center=(x+item_w//2, y+item_h//2))
                screen.blit(item['sprite'], sprite_rect)
            else:
                name_text = font.text_ret(18, item['name'][:12], (0,0,0))
                screen.blit(name_text, (x+5, y+30))
            if item['type'] in ('milk', 'espresso') and item.get('portions', 0) > 0:
                portions_text = font.text_ret(14, f"{item['portions']} порц.", (0,0,0))
                screen.blit(portions_text, (x+5, y+55))

        if self.dragging_ingredient and self.drag_ingredient_icon:
            mx, my = py.mouse.get_pos()
            icon = self.drag_ingredient_icon
            screen.blit(icon, (mx - icon.get_width()//2, my - icon.get_height()//2))

    # ---------- Логика добавления в стакан ----------
    def start_pouring(self, item, portion_increment=None):
        if item is None:
            return
        if item['type'] in ('milk', 'espresso'):
            max_ports = {'S':4, 'M':5, 'L':6}[self.selected_size]
            portions = item.get('portions', 1)
            inc = portions / max_ports
        else:  # syrup
            inc = 0.05
        if portion_increment is not None:
            inc = portion_increment
        self.pouring = True
        self.pouring_item = item
        self.pour_start_time = py.time.get_ticks()
        self.pour_progress = 0.0
        self.start_fill_ratio = self.current_fill_ratio
        self.start_color = self.current_color if self.current_color else (0,0,0)
        self.target_fill_ratio = min(self.start_fill_ratio + inc, 1.0)
        if self.start_color == (0,0,0):
            self.target_color = item['color']
        else:
            self.target_color = ((self.start_color[0] + item['color'][0]) // 2,
                                 (self.start_color[1] + item['color'][1]) // 2,
                                 (self.start_color[2] + item['color'][2]) // 2)

    def update_pouring(self):
        if not self.pouring:
            return
        now = py.time.get_ticks()
        elapsed = (now - self.pour_start_time) / 1000.0
        progress = min(1.0, elapsed / self.pour_duration)
        self.pour_progress = progress
        if progress < 1.0:
            t = progress
            self.current_fill_ratio = self.start_fill_ratio + (self.target_fill_ratio - self.start_fill_ratio) * t
            r = int(self.start_color[0] + (self.target_color[0] - self.start_color[0]) * t)
            g = int(self.start_color[1] + (self.target_color[1] - self.start_color[1]) * t)
            b = int(self.start_color[2] + (self.target_color[2] - self.start_color[2]) * t)
            self.current_color = (r, g, b)
        else:
            self.current_fill_ratio = self.target_fill_ratio
            self.current_color = self.target_color
            self.finish_pouring()

    def finish_pouring(self):
        item = self.pouring_item
        if item['type'] in ('milk', 'espresso'):
            target_side = None
            if item is self.left_drink:
                target_side = 'left'
            elif item is self.right_drink:
                target_side = 'right'

            if target_side:
                drink = self.left_drink if target_side == 'left' else self.right_drink
                portions = drink.get('portions', 1)
                max_ports = {'S':4, 'M':5, 'L':6}[self.selected_size]   # исправлено
                used_ratio = self.target_fill_ratio - self.start_fill_ratio
                used_portions = round(used_ratio * max_ports)
                if used_portions <= 0:
                    used_portions = 1
                new_portions = max(portions - used_portions, 0)

                if target_side == 'left':
                    self.left_ingredient_added = True
                elif target_side == 'right':
                    self.right_ingredient_added = True

                if self.left_ingredient_added and self.right_ingredient_added:
                    self.accept_button.visible = True
                    self.cancel_button.visible = True

                if new_portions == 0:
                    if target_side == 'left':
                        self.left_drink = None
                        self.left_added = True
                    else:
                        self.right_drink = None
                        self.right_added = True
                    for i, it in enumerate(self.top_bar_items):
                        if it.get('id') == target_side:
                            self.top_bar_items.pop(i)
                            break
                else:
                    drink['portions'] = new_portions
                    drink['fill_ratio'] = new_portions / 4.0
                    for it in self.top_bar_items:
                        if it.get('id') == target_side:
                            it['portions'] = new_portions
                            break
        elif item['type'] == 'syrup':
            item['used'] = True

        self.pouring = False
        self.pouring_item = None
        self.dragging_ingredient = None
        self.drag_ingredient_icon = None
    def complete_drink(self):
        if not self.order_station:
            print("Ошибка: OrderStation не подключена")
            return
        drink_data = {
            'size': self.selected_size,
            'left_drink': self.left_drink,
            'right_drink': self.right_drink,
            'syrups': [item['name'] for item in self.top_bar_items if item.get('is_syrup') and item.get('used', False)],
            'color': self.current_color,
            'fill_ratio': self.current_fill_ratio
        }
        self.order_station.receive_drink(drink_data)   # изменён вызов
        self.reset_build_station()

    def reset_build_station(self):
        self.left_ingredient_added = False
        self.right_ingredient_added = False
        self.accept_button.visible = False
        self.cancel_button.visible = False
        self.left_drink = None
        self.right_drink = None
        self.size_selected = False
        self.selected_size = None
        self.show_final_stage = False
        self.current_color = None
        self.current_fill_ratio = 0.0
        self.ready_drinks.clear()
        self.left_added = False
        self.right_added = False
        self.left_in_bar = False
        self.right_in_bar = False
        self.dragging_ingredient = None
        self.drag_ingredient_icon = None
        self.pouring = False
        self.top_bar_items = []
        for syrup in self.available_syrups:
            self.top_bar_items.append({
                "type": "syrup",
                "name": syrup['name'],
                "color": syrup['color'],
                "sprite": syrup['sprite'],
                "portions": 0,
                "is_syrup": True
            })
        self.current_bar_index = 0
        self.bar_dragging = False

    # ---------- Основные методы ----------
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

        if self.show_display and not self.size_selected:
            self.draw_display(screen)
        self.draw_dragged_glass(screen)

        if self.left_drink and self.right_drink and not self.size_selected:
            screen.blit(self.fon_cup, (400,615))
            for btn in self.size_buttons:
                btn.draw(screen)

        if self.size_selected:
            self.draw_center_glass(screen)
            self.draw_top_bar(screen)
            if self.left_ingredient_added and self.right_ingredient_added:
                self.accept_button.draw(screen)
                self.cancel_button.draw(screen)

    def events(self, events):
        if self.pouring:
            self.update_pouring()

        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                # Выбор размера
                if self.left_drink and self.right_drink and not self.size_selected:
                    for btn in self.size_buttons:
                        if btn.signal(event.pos):
                            self.selected_size = btn.size
                            self.size_selected = True
                            self.show_final_stage = True
                            if self.left_drink and not self.left_in_bar:
                                left_item = self.left_drink
                                left_item['id'] = 'left'
                                left_item['sprite'] = self.load_ingredient_sprite(left_item)
                                self.top_bar_items.append(left_item)
                                self.left_in_bar = True
                            if self.right_drink and not self.right_in_bar:
                                right_item = self.right_drink
                                right_item['id'] = 'right'
                                right_item['sprite'] = self.load_ingredient_sprite(right_item)
                                self.top_bar_items.append(right_item)
                                self.right_in_bar = True
                            return

                # Режим сборки
                if self.size_selected:
                    # Кручение ленты
                    if self.bar_rect.collidepoint(event.pos) and not self.bar_dragging:
                        self.bar_dragging = True
                        self.bar_drag_start_x = event.pos[0]
                        self.bar_drag_start_index = self.current_bar_index

                    if self.size_selected and self.left_ingredient_added and self.right_ingredient_added:
                        if self.accept_button.signal(event.pos):
                            self.complete_drink()
                            return
                        if self.cancel_button.signal(event.pos):
                            self.reset_build_station()
                            return

                    # Перетаскивание из зон
                    if not self.dragging_ingredient and not self.pouring:
                        if self.left_drink and self.left_zone_rect.collidepoint(event.pos):
                            self.dragging_ingredient = self.left_drink
                            icon_surf = py.Surface((80,80), py.SRCALPHA)
                            icon_surf.fill(self.left_drink['color'])
                            py.draw.rect(icon_surf, (255,255,200), (0,0,80,80), 3)
                            portions_text = font.text_ret(18, f"{self.left_drink.get('portions',1)} порц.", (0,0,0))
                            icon_surf.blit(portions_text, (5, 60))
                            self.drag_ingredient_icon = icon_surf
                            return
                        if self.right_drink and self.right_zone_rect.collidepoint(event.pos):
                            self.dragging_ingredient = self.right_drink
                            icon_surf = py.Surface((80,80), py.SRCALPHA)
                            icon_surf.fill(self.right_drink['color'])
                            py.draw.rect(icon_surf, (255,255,200), (0,0,80,80), 3)
                            portions_text = font.text_ret(18, f"{self.right_drink.get('portions',1)} порц.", (0,0,0))
                            icon_surf.blit(portions_text, (5, 60))
                            self.drag_ingredient_icon = icon_surf
                            return

                    # Клик по центральному элементу ленты
                    visible = self.get_visible_bar_items()
                    center_idx = self.max_visible_items // 2
                    if center_idx < len(visible):
                        center_item = visible[center_idx]
                        if center_item.get('rect') and center_item['rect'].collidepoint(event.pos):
                            self.start_pouring(center_item)
                            return

                # Перетаскивание исходных стаканов (из дисплея в зоны)
                if not self.size_selected:
                    for idx, _ in enumerate(self.ready_drinks):
                        rect = self.get_glass_rect(idx)
                        if rect.collidepoint(event.pos):
                            self.dragging = True
                            self.dragged_index = idx
                            self.drag_offset_x = event.pos[0] - rect.x
                            self.drag_offset_y = event.pos[1] - rect.y
                            self.drag_mouse_pos = event.pos
                            break

            elif event.type == py.MOUSEMOTION:
                if self.dragging:
                    self.drag_mouse_pos = event.pos
                if self.bar_dragging:
                    dx = event.pos[0] - self.bar_drag_start_x
                    step = 140
                    delta = int(dx / step)
                    if delta != 0:
                        total = len(self.top_bar_items)
                        if total > 0:
                            new_index = (self.bar_drag_start_index - delta) % total
                            self.current_bar_index = new_index
                            self.bar_drag_start_x = event.pos[0]
                            self.bar_drag_start_index = new_index

            elif event.type == py.MOUSEBUTTONUP and event.button == 1:
                if self.dragging:
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
                    self.dragging = False
                    self.dragged_index = None

                if self.bar_dragging:
                    self.bar_dragging = False

                if self.dragging_ingredient and not self.pouring:
                    if self.center_cap_rect.collidepoint(event.pos):
                        self.start_pouring(self.dragging_ingredient)
                    self.dragging_ingredient = None
                    self.drag_ingredient_icon = None