from colors import *
from globals import *
from .base import Station
from ..tiled import Map
from ..character import Character
from ..node import ImageButton, font
import os, random

class OrderStation(Station):
    def __init__(self, sound_manager, order):
        self.sound_manager = sound_manager
        self.order = order
        super().__init__("Заказы")
        self.map = Map('assets/tiled/tmx/coffee_house.tmx', 48, 1)
        self.map_loaded = False

        # Персонажи
        self.player = Character(3, (530, 60), 'assets/sprites/characters/player/Adam.png', [(530, 60)])
        self.split_player = 2

        # Nps
        self.npc = None
        self._load_random_npc()
        self.split_nps = 4
        self.npc_sound = py.mixer.Sound("assets/sounds/sound/nps/pop.mp3")

        self.interact_btn = ImageButton("assets/sprites/characters/nps/interactive/place_order.png", (545, 90), 3)
        self.interact_btn_show = False

        # Изображение callout
        self.callout_img = py.image.load("assets/sprites/characters/nps/interactive/callout.png").convert_alpha()
        self.callout_img = py.transform.scale(self.callout_img, (self.callout_img.get_width() * 3, self.callout_img.get_height() * 3))
        self.callout_rect = self.callout_img.get_rect(topleft=(545, 90))
        self.callout_show = False

        # Анимация показа
        self.animation_index = -1
        self.animation_timer = 0

        # Ингредиенты
        self.espresso_sprites = self._load_sprites("assets/sprites/ingredients/espresso")
        self.milk_sprites = self._load_sprites("assets/sprites/ingredients/milk")
        self.syrup_sprites = self._load_sprites("assets/sprites/ingredients/syrup")

        # Заказ
        self.order.set_sprites(
            espresso_sprites=self.espresso_sprites,
            milk_sprites=self.milk_sprites,
            syrup_sprites=self.syrup_sprites
        )

    def _play_npc_sound(self):
        """Проигрывает звук громкости SFX"""
        if self.sound_manager.sfx_enabled:
            vol = self.sound_manager.sfx_volume
            self.npc_sound.set_volume(vol)
            self.npc_sound.play()

    def _load_sprites(self, folder):
        """Загружает всех png из папки и возвращается словарь"""
        sprites = {}
        if not os.path.exists(folder):
            return sprites

        for filename in os.listdir(folder):
            if filename.lower().endswith(".png"):
                name = os.path.splitext(filename)[0]
                path = os.path.join(folder, filename)
                img = py.image.load(path).convert_alpha()
                img = py.transform.scale(img, (70, 70))
                sprites[name] = img
        return sprites

    def _load_random_npc(self):
        """Загружает случайного NPC"""
        nps_folder = "assets/sprites/characters/nps"
        png_files = [f for f in os.listdir(nps_folder) if f.lower().endswith('.png')]

        chosen_file = random.choice(png_files)
        name = os.path.splitext(chosen_file)[0]
        sprite_path = os.path.join(nps_folder, chosen_file)

        path = [(240, 140), (530, 140), (530, 120)]

        self.npc = Character(3, (240, 0), sprite_path, path)

    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True

        # Рисуем нижние слои
        for i in range(self.split_player):
            self.map.draw_layer(screen, i)

        # Рисуем игрока
        self.player.update()
        self.player.draw(screen)

        for i in range(self.split_player, self.split_nps):
            self.map.draw_layer(screen, i)

        self.npc.update()
        self.npc.draw(screen)

        now = py.time.get_ticks()

        if self.callout_show and self.order.current_order:
            if self.animation_index == -1:
                self.animation_index = 0
                self.animation_timer = now + 1000
                self._play_npc_sound()
                # Раскрываем чашку на тикете
                self.order.reveal_by_index(0)
            elif self.animation_timer and now > self.animation_timer:
                self.animation_index += 1
                self._play_npc_sound()
                if self.animation_index > 3:
                    self.callout_show = False
                    self.animation_index = -1
                    self.animation_timer = 0
                else:
                    # Раскрываем соответствующий компонент на тикете
                    self.order.reveal_by_index(self.animation_index)
                    self.animation_timer = now + 1000

            # Отрисовка текущего элемента
            screen.blit(self.callout_img, self.callout_rect)
            order = self.order.current_order

            if self.animation_index == 0:
                # Чашка
                cup_letter = order['cup']['cup']
                cup_text = font.text_ret(36, cup_letter, BLACK)
                cup_rect = cup_text.get_rect(center=self.callout_rect.center)
                screen.blit(cup_text, cup_rect)
            elif self.animation_index == 1:
                # Молоко
                milk_name = order['milk']['type']
                if milk_name in self.milk_sprites:
                    milk_icon = self.milk_sprites[milk_name]
                    milk_rect = milk_icon.get_rect(center=(self.callout_rect.centerx, 130))
                    screen.blit(milk_icon, milk_rect)
            elif self.animation_index == 2:
                # Эспрессо
                espresso_name = order['espresso']['type']
                if espresso_name in self.espresso_sprites:
                    espresso_icon = self.espresso_sprites[espresso_name]
                    espresso_rect = espresso_icon.get_rect(center=(self.callout_rect.centerx, 130))
                    screen.blit(espresso_icon, espresso_rect)
            elif self.animation_index == 3:
                # Сироп (если есть)
                syrup_name = order['syrup']['name']
                if syrup_name in self.syrup_sprites:
                    syrup_icon = self.syrup_sprites[syrup_name]
                    syrup_rect = syrup_icon.get_rect(center=(self.callout_rect.centerx, 130))
                    screen.blit(syrup_icon, syrup_rect)

        # Отображение кнопки
        if not self.callout_show and self.npc.is_path_finished():
            self.interact_btn_show = True
        else:
            self.interact_btn_show = False

        if self.interact_btn_show:
            self.interact_btn.draw(screen)

        # Рисуем верхние слои
        for i in range(self.split_nps, len(self.map.layers)):
            self.map.draw_layer(screen, i)

    def events(self, events):
        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                if self.interact_btn.signal(event.pos):
                    self.order.generate_random_order()
                    self.interact_btn_show = False
                    self.callout_show = True
                    self.animation_index = -1
                    self.animation_timer = 0