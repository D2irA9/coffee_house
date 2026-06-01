from colors import *
from globals import *
from .base import Station
from ..node import font, ImageButton
from ..tiled import Map
import pygame as py

class BuildStation(Station):
    def __init__(self, sound_manager, milk_colors, espresso_colors, syrup_colors):
        self.sound_manager = sound_manager
        self.milk_colors = milk_colors
        self.espresso_colors = espresso_colors
        self.syrup_colors = syrup_colors
        super().__init__("Сборка")

        self.ready_drinks = []

        self.map = Map('assets/tiled/tmx/BuildStation.tmx', 48)
        self.map_loaded = False

        # Обычный стакан
        scale_cup = 1.7
        original_img = py.image.load("assets/sprites/buttons/cap.png").convert_alpha()
        new_w = int(original_img.get_width() * scale_cup)
        new_h = int(original_img.get_height() * scale_cup)
        self.glass_img = py.transform.scale(original_img, (new_w, new_h))
        self.glass_width = new_w
        self.glass_height = new_h

        drag_scale = 3
        self.drag_glass_img = py.transform.scale(original_img,(int(original_img.get_width() * drag_scale), int(original_img.get_height() * drag_scale)))
        self.drag_glass_width = self.drag_glass_img.get_width()
        self.drag_glass_height = self.drag_glass_img.get_height()

        self.show_display = True

        # Параметры сетки стаканов
        self.start_x = 40
        self.start_y = 65
        self.gap_x = 10
        self.gap_y = 10
        self.columns = 4

        # Drag & drop
        self.dragging = False
        self.dragged_index = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.drag_mouse_pos = (0, 0)

        # Зоны приёма
        self.left_zone_rect = py.Rect(100, 270, 250, 300)
        self.right_zone_rect = py.Rect(850, 270, 250, 300)

        # Напитки
        self.left_drink = None
        self.right_drink = None

        # Флаг и переменная для выбранного размера
        self.size_selected = False
        self.selected_size = None

        # Загрузка фона для кнопок выбора размера
        size_fon_img = py.image.load("assets/sprites/buttons/fon_cup.png").convert_alpha()
        self.fon_cup = py.transform.scale(size_fon_img,(int(size_fon_img.get_width() * drag_scale), int(size_fon_img.get_height() * drag_scale)))
        self.block_center = (600, 350)

        self.size_buttons = []
        sizes = ["S", "M", "L"]
        offsets = [-150, -30, 90]
        for i, size in enumerate(sizes):
            sprite_path = f"assets/sprites/buttons/{size}.png"
            pos_x = self.block_center[0] + offsets[i]
            pos_y = self.block_center[1]
            # Загружаем кнопку (если файла нет – используем старый способ с текстом)

            btn = ImageButton(sprite_path, (pos_x, 630), 3)
            print(pos_x, pos_y)

            btn.size = size
            self.size_buttons.append(btn)

    def get_glass_rect(self, index):
        row = index // self.columns
        col = index % self.columns
        x = self.start_x + col * (self.glass_width + self.gap_x)
        y = self.start_y + row * (self.glass_height + self.gap_y)
        return py.Rect(x, y, self.glass_width, self.glass_height)

    def add_ready_drink(self, drink_type, milk_type=None, milk_temp=None, portions=0,
                        quality="normal", espresso_type=None, espresso_quality=None, fill_ratio=None):
        if drink_type == "milk":
            milk_color = self.milk_colors.get(milk_type, (255, 250, 240))
            ratio = fill_ratio if fill_ratio is not None else (portions / 4.0)
            drink_info = {
                "type": "milk",
                "milk_type": milk_type,
                "temperature": milk_temp,
                "quality": quality,
                "color": milk_color,
                "fill_ratio": ratio
            }
        else:  # espresso
            espresso_color = self.espresso_colors.get(espresso_type, (110, 59, 9))
            ratio = fill_ratio if fill_ratio is not None else (portions / 4.0)
            drink_info = {
                "type": "espresso",
                "espresso_type": espresso_type,
                "quality": espresso_quality if espresso_quality else "normal",
                "color": espresso_color,
                "fill_ratio": ratio
            }
        self.ready_drinks.append(drink_info)
        if len(self.ready_drinks) > 20:
            self.ready_drinks.pop(0)
        print(f"BuildStation получил: {drink_info}")

    def draw_display(self, screen):
        py.draw.rect(screen, FON, (0, 100, 1200, 100))
        py.draw.rect(screen, CONTOUR, (0, 100, 1200, 100), 3)

        if not self.ready_drinks:
            return

        for idx, drink in enumerate(self.ready_drinks):
            if self.dragging and idx == self.dragged_index:
                continue
            rect = self.get_glass_rect(idx)
            glass_x, glass_y = rect.x, rect.y

            # Заливка
            fill_height = int(self.glass_height * drink["fill_ratio"])
            if fill_height > 0:
                fill_rect = py.Rect(glass_x, glass_y + self.glass_height - fill_height,
                                    self.glass_width, fill_height)
                py.draw.rect(screen, drink["color"], fill_rect)
            # Стакан
            screen.blit(self.glass_img, (glass_x, glass_y))

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
        """Рисует увеличенный стакан"""
        if drink is None:
            return

        # Позиция стакана по центру зоны
        glass_x = zone_rect.x + (zone_rect.width - self.drag_glass_width) // 2
        glass_y = zone_rect.y + (zone_rect.height - self.drag_glass_height) // 2

        # Заливка
        fill_height = int(self.drag_glass_height * drink["fill_ratio"])
        if fill_height > 0:
            fill_rect = py.Rect(glass_x, glass_y + self.drag_glass_height - fill_height,
                                self.drag_glass_width, fill_height)
            py.draw.rect(screen, drink["color"], fill_rect)

        # Стакан поверх заливки
        screen.blit(self.drag_glass_img, (glass_x, glass_y))

    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True
        self.map.draw_all(screen)

        # Левая область
        py.draw.rect(screen, (40, 102, 142), (0, 160, 400, 430))
        py.draw.rect(screen, CONTOUR, (0, 160, 400, 430), 3)
        py.draw.rect(screen, FON, self.left_zone_rect)
        py.draw.rect(screen, CONTOUR, self.left_zone_rect, 3)
        self.draw_drink_in_zone(screen, self.left_drink, self.left_zone_rect)

        # Правая область
        py.draw.rect(screen, (40, 102, 142), (800, 160, 400, 430))
        py.draw.rect(screen, CONTOUR, (800, 160, 400, 430), 3)
        py.draw.rect(screen, FON, self.right_zone_rect)
        py.draw.rect(screen, CONTOUR, self.right_zone_rect, 3)
        self.draw_drink_in_zone(screen, self.right_drink, self.right_zone_rect)

        if self.show_display:
            self.draw_display(screen)
        self.draw_dragged_glass(screen)
        # ---- Если оба стакана установлены и размер ещё не выбран ----
        if self.left_drink is not None and self.right_drink is not None and not self.size_selected:
            # Рисуем фон
            screen.blit(self.fon_cup, (400, 615))
            # Рисуем кнопки
            for btn in self.size_buttons:
                btn.draw(screen)

    def events(self, events):
        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                if self.left_drink is not None and self.right_drink is not None and not self.size_selected:
                    for btn in self.size_buttons:
                        if btn.signal(event.pos):
                            self.selected_size = btn.size
                            self.size_selected = True
                            print(f"Выбран размер стакана: {self.selected_size}")
                            # TODO: следующий шаг — переход к финальной сборке
                            # Здесь можно установить флаг show_final_stage = True
                            return
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