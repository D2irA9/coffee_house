from colors import *
from globals import *
from .base import Station
from ..node import font

class BuildStation(Station):
    def __init__(self):
        super().__init__("Сборка")
        self.ready_drinks = []   # список готовых напитков

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
        screen.fill(BLUE)
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