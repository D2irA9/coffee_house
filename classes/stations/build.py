from colors import *
from globals import *
from .base import Station
from ..node import font
from ..tiled import Map

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

    def add_ready_drink(self, drink_type, milk_type=None, milk_temp=None, portions=0, quality="normal", espresso_type=None, espresso_quality=None):
        """Сохранение готового напитка для отображения"""
        if drink_type == "milk":
            drink_info = {
                "type": "молоко",
                "milk_type": milk_type,
                "temperature": milk_temp,
                "portions": portions,
                "quality": quality
            }
        else:  # espresso
            drink_info = {
                "type": "эспрессо",
                "espresso_type": espresso_type,
                "portions": portions,
                "quality": espresso_quality if espresso_quality else "normal"
            }
        self.ready_drinks.append(drink_info)
        # Ограничим список, чтобы не переполнить экран
        if len(self.ready_drinks) > 10:
            self.ready_drinks.pop(0)

        # Вывод в консоль (для отладки)
        print(f"BuildStation получил: {drink_info}")

    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True
        self.map.draw_all(screen)

        if not self.ready_drinks:
            text = font.text_ret(36, "Нет готовых напитков", WHITE)
            screen.blit(text, (50, 50))
            return

        y_offset = 50
        for idx, drink in enumerate(self.ready_drinks):
            if drink["type"] == "молоко":
                line = f"{idx+1}. Молоко: {drink['milk_type']}, {drink['temperature']}, {drink['portions']} порц., качество: {drink['quality']}"
            else:
                line = f"{idx+1}. Эспрессо: {drink['espresso_type']}, {drink['portions']} порц., качество: {drink['quality']}"
            text = font.text_ret(24, line, WHITE)
            screen.blit(text, (50, y_offset))
            y_offset += 30

    def events(self, events):
        pass