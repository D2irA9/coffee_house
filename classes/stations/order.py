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
        self.map = Map('assets/tiled/tmx/OrderStation.tmx', 48, 1)
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
        self.order_active = True

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

        # ---- Загрузка увеличенного стакана для отображения переданного напитка ----
        scale_cup = 1.7
        original_img = py.image.load("assets/sprites/buttons/cap.png").convert_alpha()
        self.submitted_glass_img = py.transform.scale(original_img,
                                                      (int(original_img.get_width() * scale_cup),
                                                       int(original_img.get_height() * scale_cup)))
        self.submitted_glass_width, self.submitted_glass_height = self.submitted_glass_img.get_size()

        self.submitted_drink_zone_rect = py.Rect(20, 270, self.submitted_glass_width + 20, self.submitted_glass_height + 20)

        self.submitted_drink = None
        self.submitted_drink_rect = None

        # Состояние NPC
        self.npc_sit_timer = None          # время начала сидения
        self.npc_leaving = False
        self.leave_path = [(420, 140), (530, 140), (240, 140), (240, 0)]   # путь ухода

    def _play_npc_sound(self):
        if self.sound_manager.sfx_enabled:
            vol = self.sound_manager.sfx_volume
            self.npc_sound.set_volume(vol)
            self.npc_sound.play()

    def _load_sprites(self, folder):
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
        nps_folder = "assets/sprites/characters/nps"
        png_files = [f for f in os.listdir(nps_folder) if f.lower().endswith('.png')]
        chosen_file = random.choice(png_files)
        sprite_path = os.path.join(nps_folder, chosen_file)

        npc_name = os.path.splitext(chosen_file)[0]
        self.current_nps_info = {
            'db_name': npc_name,
            'display_name': npc_name
        }

        path = [(240, 140), (530, 140), (530, 120)]
        self.npc = Character(3, (240, 0), sprite_path, path)
        self.npc_sit_timer = None
        self.npc_leaving = False

    def receive_drink(self, drink_data):
        self.submitted_drink = drink_data
        self.order_active = False

    def add_completed_drink(self, drink_data):
        npc_name = self.current_nps_info['db_name'] if hasattr(self, 'current_nps_info') else "Unknown"
        if not self.order.current_order:
            print("Нет активного заказа")
            self.submitted_drink = None
            self.order_active = True
            if self.npc and self.npc.is_path_finished() and not self.npc_leaving:
                self.start_npc_sitting()
            return

        order = self.order.current_order
        is_correct, result_score, match_percentage, total_matches, total_checks = self.compare_with_order(drink_data, order)

        # здесь можно сохранить статистику, пока пропускаем

        left = drink_data.get('left_drink')
        right = drink_data.get('right_drink')
        def find_ingredient(ing_type):
            if left and left['type'] == ing_type:
                return left
            if right and right['type'] == ing_type:
                return right
            return None

        size_match = (drink_data['size'] == order['cup']['cup'])
        espresso = find_ingredient('espresso')
        espresso_match = espresso and (espresso['espresso_type'] == order['espresso']['type'] and espresso['portions'] == order['espresso']['portions'])
        milk = find_ingredient('milk')
        milk_match = milk and (milk['milk_type'] == order['milk']['type'] and milk['temperature'] == order['milk']['temp'] and milk['portions'] == order['milk']['portions'])
        order_syrups = [order['syrup']['name']] if order.get('syrup') else []
        syrups_match = set(order_syrups).issubset(set(drink_data.get('syrups', [])))

        if size_match and espresso_match and milk_match and syrups_match:
            print("✅ Заказ выполнен верно! Начисляем награду.")
            self.order.current_order = None
            self.callout_show = False
            self.animation_index = -1
            self.animation_timer = 0
            if hasattr(self.order, 'reset'):
                self.order.reset()
        else:
            print("❌ Напиток не соответствует заказу!")

        # После проверки запускаем таймер сидения NPC
        if self.npc and not self.npc_leaving:
            self.start_npc_leaving()

        self.submitted_drink = None
        self.submitted_drink_rect = None

    def start_npc_leaving(self):
        """Немедленно отправить NPC уходить (без ожидания таймера)"""
        if self.npc and not self.npc_leaving:
            self.npc_leaving = True
            self.npc_sit_timer = None
            self.npc.set_path(self.leave_path)
            self.order_active = False

    def start_npc_sitting(self):
        """Сажает NPC и запускает таймер 5 секунд"""
        if self.npc and not self.npc_leaving:
            self.npc.sit_down('sit_left')
            self.npc_sit_timer = py.time.get_ticks()
            self.order_active = False
            self.npc_leaving = False

    def update_npc_state(self):
        """Обновляет состояние NPC: идёт -> садится -> через 5 сек уходит"""
        if not self.npc:
            return

        # 1. Если NPC закончил путь и ещё не сидит и не уходит – садим его
        if (self.npc.is_path_finished() and not self.npc_leaving and self.npc_sit_timer is None):
            self.npc.sit_down('sit_left')
            self.npc_sit_timer = py.time.get_ticks()
            self.order_active = True     # разрешаем брать заказы (кнопка появится)
            print("NPC сел, теперь можно брать заказ")

        # 2. Если NPC сидит и прошло 5 секунд – отправляем уходить
        if (self.npc_sit_timer is not None and not self.npc_leaving):
            now = py.time.get_ticks()
            if now - self.npc_sit_timer >= 5000:   # 5 секунд
                self.start_npc_leaving()
                print("NPC посидел 5 секунд и уходит")

        # 3. Если NPC уходит и завершил путь – загружаем нового
        if self.npc_leaving and self.npc.is_path_finished():
            self._load_random_npc()
            self.order_active = True
            self.order.current_order = None
            self.callout_show = False
            self.animation_index = -1
            self.animation_timer = 0
            if hasattr(self.order, 'reset'):
                self.order.reset()
            print("Новый NPC появился")

    def compare_with_order(self, drink_data, order):
        # ... оставляем как было, без изменений ...
        size_match = (drink_data['size'] == order['cup']['cup'])
        left = drink_data.get('left_drink')
        right = drink_data.get('right_drink')
        def find_ingredient(ing_type):
            if left and left['type'] == ing_type:
                return left
            if right and right['type'] == ing_type:
                return right
            return None
        espresso = find_ingredient('espresso')
        espresso_match = False
        if espresso:
            espresso_match = (espresso['espresso_type'] == order['espresso']['type'] and
                              espresso['portions'] == order['espresso']['portions'])
        milk = find_ingredient('milk')
        milk_match = False
        if milk:
            milk_match = (milk['milk_type'] == order['milk']['type'] and
                          milk['temperature'] == order['milk']['temp'] and
                          milk['portions'] == order['milk']['portions'])
        order_syrups = [order['syrup']['name']] if order.get('syrup') else []
        syrups_match = set(order_syrups).issubset(set(drink_data.get('syrups', [])))
        matches = [size_match, espresso_match, milk_match, syrups_match]
        total_matches = sum(matches)
        total_checks = len(matches)
        match_percentage = (total_matches / total_checks) * 100 if total_checks > 0 else 0
        if match_percentage >= 80:
            result_score = 3
            is_correct = True
        elif match_percentage >= 60:
            result_score = 2
            is_correct = True
        elif match_percentage >= 40:
            result_score = 1
            is_correct = False
        else:
            result_score = 0
            is_correct = False
        print(f"РЕЗУЛЬТАТ: {total_matches}/{total_checks} ({match_percentage:.0f}%) - Оценка: {result_score}")
        return is_correct, result_score, match_percentage, total_matches, total_checks

    def draw(self, screen):
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True

        # нижние слои
        for i in range(self.split_player):
            self.map.draw_layer(screen, i)
        self.player.update()
        self.player.draw(screen)
        for i in range(self.split_player, self.split_nps):
            self.map.draw_layer(screen, i)

        # обновляем состояние NPC (сидение, уход)
        self.update_npc_state()

        self.npc.update()
        self.npc.draw(screen)

        now = py.time.get_ticks()

        if self.callout_show and self.order.current_order:
            if self.animation_index == -1:
                self.animation_index = 0
                self.animation_timer = now + 1000
                self._play_npc_sound()
                self.order.reveal_by_index(0)
            elif self.animation_timer and now > self.animation_timer:
                self.animation_index += 1
                self._play_npc_sound()
                if self.animation_index > 3:
                    self.callout_show = False
                    self.animation_index = -1
                    self.animation_timer = 0
                else:
                    self.order.reveal_by_index(self.animation_index)
                    self.animation_timer = now + 1000

            screen.blit(self.callout_img, self.callout_rect)
            order = self.order.current_order
            if self.animation_index == 0:
                cup_letter = order['cup']['cup']
                cup_text = font.text_ret(36, cup_letter, BLACK)
                cup_rect = cup_text.get_rect(center=self.callout_rect.center)
                screen.blit(cup_text, cup_rect)
            elif self.animation_index == 1:
                milk_name = order['milk']['type']
                if milk_name in self.milk_sprites:
                    milk_icon = self.milk_sprites[milk_name]
                    milk_rect = milk_icon.get_rect(center=(self.callout_rect.centerx, 130))
                    screen.blit(milk_icon, milk_rect)
            elif self.animation_index == 2:
                espresso_name = order['espresso']['type']
                if espresso_name in self.espresso_sprites:
                    espresso_icon = self.espresso_sprites[espresso_name]
                    espresso_rect = espresso_icon.get_rect(center=(self.callout_rect.centerx, 130))
                    screen.blit(espresso_icon, espresso_rect)
            elif self.animation_index == 3:
                syrup_name = order['syrup']['name']
                if syrup_name in self.syrup_sprites:
                    syrup_icon = self.syrup_sprites[syrup_name]
                    syrup_rect = syrup_icon.get_rect(center=(self.callout_rect.centerx, 130))
                    screen.blit(syrup_icon, syrup_rect)

        # Кнопка заказа
        if (not self.callout_show and self.npc and self.npc.is_path_finished() and
            self.order_active and not self.npc_leaving and self.npc_sit_timer is None):
            self.interact_btn_show = True
        else:
            self.interact_btn_show = False
        if self.interact_btn_show:
            self.interact_btn.draw(screen)

        # Рисуем переданный напиток
        if self.submitted_drink:
            py.draw.rect(screen, FON, self.submitted_drink_zone_rect)
            py.draw.rect(screen, CONTOUR, self.submitted_drink_zone_rect, 3)
            glass_x = self.submitted_drink_zone_rect.x + 10
            glass_y = self.submitted_drink_zone_rect.y + 10
            fill_height = int(self.submitted_glass_height * self.submitted_drink['fill_ratio'])
            if fill_height > 0:
                fill_rect = py.Rect(glass_x, glass_y + self.submitted_glass_height - fill_height,
                                    self.submitted_glass_width, fill_height)
                py.draw.rect(screen, self.submitted_drink['color'], fill_rect)
            screen.blit(self.submitted_glass_img, (glass_x, glass_y))
            self.submitted_drink_rect = py.Rect(glass_x, glass_y, self.submitted_glass_width, self.submitted_glass_height)

        # Верхние слои
        for i in range(self.split_nps, len(self.map.layers)):
            self.map.draw_layer(screen, i)

    def events(self, events):
        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                if self.interact_btn_show and self.interact_btn.signal(event.pos):
                    self.order.generate_random_order()
                    self.interact_btn_show = False
                    self.order_active = False
                    self.callout_show = True
                    self.animation_index = -1
                    self.animation_timer = 0

                if self.submitted_drink and self.submitted_drink_rect and self.submitted_drink_rect.collidepoint(event.pos):
                    self.add_completed_drink(self.submitted_drink)