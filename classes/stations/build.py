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

        # Список готовых стаканов
        self.ready_drinks = []

        # Загрузка карты и фона
        self.map = Map('assets/tiled/tmx/BuildStation.tmx', 48)
        self.map_loaded = False

        scale = 3

        # Фон для стакана
        orig_fon_cup_img = py.image.load("assets/sprites/buttons/Build_.png").convert_alpha()
        self.fon_cup_img = py.transform.scale(orig_fon_cup_img, (int(orig_fon_cup_img.get_width() * scale), int(orig_fon_cup_img.get_height() * scale)))

        # Сигнал для отображения дисплея с напитками
        self.show_display = True

        # Загрузка и масштабирование стакана
        scale_cup = 1.7
        original_img = py.image.load("assets/sprites/buttons/cap.png").convert_alpha()
        new_w = int(original_img.get_width() * scale_cup)
        new_h = int(original_img.get_height() * scale_cup)
        self.glass_img = py.transform.scale(original_img, (new_w, new_h))
        self.glass_width = new_w
        self.glass_height = new_h

        # Параметры отображения сетки стаканов
        self.start_x = 40
        self.start_y = 65
        self.gap_x = 10
        self.gap_y = 10
        self.columns = 4

    def add_ready_drink(self, drink_type, milk_type=None, milk_temp=None, portions=0, quality="normal", espresso_type=None, espresso_quality=None, fill_ratio=None):
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
        """Отображение области дисплея и готовых стаканов в виде сетки"""
        py.draw.rect(screen, FON, (0, 100, 1200, 100))
        py.draw.rect(screen, CONTOUR, (0, 100, 1200, 100), 3)

        if not self.ready_drinks:
            return

        for idx, drink in enumerate(self.ready_drinks):
            row = idx // self.columns
            col = idx % self.columns
            glass_x = self.start_x + col * (self.glass_width + self.gap_x)
            glass_y = self.start_y + row * (self.glass_height + self.gap_y)

            # Заливка
            fill_height = int(self.glass_height * drink["fill_ratio"])
            if fill_height > 0:
                fill_rect = py.Rect(glass_x, glass_y + self.glass_height - fill_height,
                                    self.glass_width, fill_height)
                py.draw.rect(screen, drink["color"], fill_rect)

            # Стакан поверх заливки
            screen.blit(self.glass_img, (glass_x, glass_y))

    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True
        self.map.draw_all(screen)

        py.draw.rect(screen, (40, 102, 142), (0, 160, 400, 430))
        py.draw.rect(screen, CONTOUR, (0, 160, 400, 430), 3)
        screen.blit(self.fon_cup_img, (100, 270))

        py.draw.rect(screen, (40, 102, 142), (800, 160, 400, 430))
        py.draw.rect(screen, CONTOUR, (800, 160, 400, 430), 3)
        screen.blit(self.fon_cup_img, (850, 270))

        if self.show_display:
            self.draw_display(screen)

    def events(self, events):
        pass