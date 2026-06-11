from colors import *
from globals import *
from .base import Station
from ..tiled import Map
from ..character import Character
from ..node import ImageButton, font
import os, random

class OrderStation(Station):
    """Станция заказов"""
    def __init__(self, sound_manager, order):
        self.sound_manager = sound_manager
        self.order = order
        super().__init__("Заказы")

        # Загрузка карты (TMX)
        self.map = Map('assets/tiled/tmx/OrderStation.tmx', 48, 1)
        self.map_loaded = False

        # ----- Персонажи -----
        # Игрок (статичный, стоит за стойкой)
        self.player = Character(3, (530, 60), 'assets/sprites/characters/player/Adam.png', [(530, 60)])
        self.split_player = 2

        # NPC (появляется случайный)
        self.npc = None
        self._load_random_npc()
        self.split_nps = 4
        self.npc_sound = py.mixer.Sound("assets/sounds/sound/nps/pop.mp3")   # звук появления

        # Кнопка взаимодействия (берём заказ)
        self.interact_btn = ImageButton("assets/sprites/characters/nps/interactive/place_order.png", (545, 90), 3)
        self.interact_btn_show = False
        self.order_active = True

        # ----- Callout (облачко с заказом) -----
        self.callout_img = py.image.load("assets/sprites/characters/nps/interactive/callout.png").convert_alpha()
        self.callout_img = py.transform.scale(self.callout_img, (self.callout_img.get_width() * 3, self.callout_img.get_height() * 3))
        self.callout_rect = self.callout_img.get_rect(topleft=(545, 90))
        self.callout_show = False

        # Анимация появления заказа (поэтапное раскрытие)
        self.animation_index = -1
        self.animation_timer = 0

        # ----- Ингредиенты и их спрайты -----
        self.espresso_sprites = self._load_sprites("assets/sprites/ingredients/espresso")
        self.milk_sprites = self._load_sprites("assets/sprites/ingredients/milk")
        self.syrup_sprites = self._load_sprites("assets/sprites/ingredients/syrup")

        self.order.set_sprites(
            espresso_sprites=self.espresso_sprites,
            milk_sprites=self.milk_sprites,
            syrup_sprites=self.syrup_sprites
        )

        # ----- Стакан для переданного напитка (от BuildStation) -----
        scale_cup = 1.7
        original_img = py.image.load("assets/sprites/buttons/cap.png").convert_alpha()
        self.submitted_glass_img = py.transform.scale(original_img,
                                                      (int(original_img.get_width() * scale_cup),
                                                       int(original_img.get_height() * scale_cup)))
        self.submitted_glass_width, self.submitted_glass_height = self.submitted_glass_img.get_size()
        self.submitted_drink_zone_rect = py.Rect(20, 270, self.submitted_glass_width + 20, self.submitted_glass_height + 20)
        self.submitted_drink = None
        self.submitted_drink_rect = None

        # ----- Состояния и пути NPC (после выполнения заказа) -----
        self.npc_state = 'idle'
        self.path_to_chair = [(530, 120), (530, 140), (420, 140), (420, 220)]
        self.leave_path = [(420, 140), (240, 140), (240, 70)]
        self.sit_duration = 3000
        self.sit_start_time = 0

    # ----------------- Вспомогательные методы -----------------
    def _play_npc_sound(self):
        """Воспроизводит звук NPC с учётом громкости SFX."""
        if self.sound_manager.sfx_enabled:
            vol = self.sound_manager.sfx_volume
            self.npc_sound.set_volume(vol)
            self.npc_sound.play()

    def _load_sprites(self, folder):
        """
        Загружает все PNG-спрайты из указанной папки и масштабирует до 70x70.
        Возвращает словарь {имя_файла: поверхность}.
        """
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
        """
        Выбирает случайного NPC из папки assets/sprites/characters/nps,
        загружает его с путём прихода к стойке.
        Сохраняет информацию о NPC для базы данных.
        """
        nps_folder = "assets/sprites/characters/nps"
        png_files = [f for f in os.listdir(nps_folder) if f.lower().endswith('.png')]
        chosen_file = random.choice(png_files)
        sprite_path = os.path.join(nps_folder, chosen_file)

        npc_name = os.path.splitext(chosen_file)[0]
        self.current_nps_info = {
            'db_name': npc_name,
            'display_name': npc_name
        }

        # Путь прихода: с левого края к стойке
        path = [(240, 140), (530, 140), (530, 120)]
        self.npc = Character(3, (240, 0), sprite_path, path)
        self.npc_state = 'idle'
        self.sit_start_time = 0

    # ----------------- Приём и проверка заказа -----------------
    def receive_drink(self, drink_data):
        """
        Принимает готовый напиток от BuildStation.
        Сохраняет его для отображения и блокирует кнопку заказа до проверки.
        """
        self.submitted_drink = drink_data
        self.order_active = False

    def add_completed_drink(self, drink_data):
        """
        Вызывается, когда игрок кликает по переданному стакану.
        Сравнивает напиток с текущим заказом, сохраняет статистику,
        запускает прощание NPC.
        """
        if not self.order.current_order:
            print("Нет активного заказа")
            self.submitted_drink = None
            self.order_active = True
            return

        order = self.order.current_order
        print("=== DRINK DATA ===")
        print(drink_data)
        print("=== ORDER ===")
        print(order)

        # Вычисляем процент совпадения и оценку
        is_correct, result_score, match_percentage, total_matches, total_checks = self.compare_with_order(drink_data, order)
        # Сохраняем результат в БД
        self.save_order_result(drink_data, order, match_percentage, result_score)

        # Проверка для вывода сообщения (успех/неудача) – дублирует compare_with_order
        size_match = (drink_data['size'] == order['cup']['cup'])
        milk_match = (drink_data.get('milk_portions', 0) == order['milk']['portions'])
        espresso_match = (drink_data.get('espresso_portions', 0) == order['espresso']['portions'])
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

        # Запускаем процедуру ухода NPC
        if self.npc and self.npc_state == 'idle':
            self.start_npc_farewell()

        # Очищаем переданный напиток
        self.submitted_drink = None
        self.submitted_drink_rect = None

    def compare_with_order(self, drink_data, order):
        """
        Сравнивает готовый напиток с заказом и возвращает результат.
        """
        size_match = (drink_data['size'] == order['cup']['cup'])
        milk_match = (drink_data.get('milk_portions', 0) == order['milk']['portions'])
        espresso_match = (drink_data.get('espresso_portions', 0) == order['espresso']['portions'])
        order_syrups = [order['syrup']['name']] if order.get('syrup') else []
        syrups_match = set(order_syrups).issubset(set(drink_data.get('syrups', [])))

        matches = [size_match, espresso_match, milk_match, syrups_match]
        total_matches = sum(matches)
        total_checks = len(matches)
        match_percentage = (total_matches / total_checks) * 100 if total_checks > 0 else 0

        # Оценка от 0 до 3
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

    def save_order_result(self, drink_data, original_order, match_percentage, result_score):
        """
        Сохраняет результат выполнения заказа в базу данных.
        """
        if not db:
            print("База данных не подключена")
            return False

        try:
            from globals import id_player

            # Формируем объект completed_drink для БД
            completed_drink = {
                "size": drink_data.get("size"),
                "fill_ratio": drink_data.get("fill_ratio"),
                "color": drink_data.get("color"),
                "syrups": drink_data.get("syrups", []),
                "milk_portions": drink_data.get("milk_portions", 0),
                "espresso_portions": drink_data.get("espresso_portions", 0)
            }

            if original_order.get('syrup'):
                completed_drink["syrup"] = original_order['syrup']['name']

            order_data = {
                "original_order": original_order,
                "completed_drink": completed_drink,
                "percentage_matches": match_percentage
            }

            npc_name = self.current_nps_info['db_name'] if hasattr(self, 'current_nps_info') else "Unknown"
            stat_id = db.add_statistics(
                id_player=id_player,
                npc_name=npc_name,
                order_data=order_data,
                result=result_score
            )

            if stat_id:
                print(f"Статистика сохранена (ID: {stat_id})")
            else:
                print("Статистика НЕ сохранена")
            return stat_id is not None

        except Exception as e:
            print(f"Ошибка сохранения статистики: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start_npc_farewell(self):
        """
        Запускает процедуру прощания NPC: он идёт к стулу,
        затем сядет на 3 секунды и уйдёт.
        """
        if self.npc_state != 'idle':
            return
        self.npc_state = 'walking_to_chair'
        self.npc.set_path(self.path_to_chair)
        self.order_active = False      # во время ухода новый заказ не берём

    # ----------------- Обновление состояния NPC -----------------
    def update_npc_state(self):
        """
        Автомат состояний NPC: движение к стулу -> сидение -> уход -> смена NPC.
        Вызывается каждый кадр в draw().
        """
        if not self.npc:
            return
        if self.npc_state == 'walking_to_chair' and self.npc.is_path_finished():
            self.npc.sit_down('sit_left')
            self.npc_state = 'sitting'
            self.sit_start_time = py.time.get_ticks()
            print("NPC сел на стул")
        if self.npc_state == 'sitting':
            now = py.time.get_ticks()
            if now - self.sit_start_time >= self.sit_duration:
                self.npc_state = 'walking_away'
                self.npc.set_path(self.leave_path)
                print("NPC встал и пошёл к выходу")
        if self.npc_state == 'walking_away' and self.npc.is_path_finished():
            self._load_random_npc()
            self.order_active = True
            self.order.current_order = None
            self.callout_show = False
            self.animation_index = -1
            self.animation_timer = 0
            if hasattr(self.order, 'reset'):
                self.order.reset()
            print("Новый NPC появился")

    # ----------------- Отрисовка и события -----------------
    def draw(self, screen):
        """
        Отрисовка станции заказов: карта, игрок, NPC, callout, кнопка,
        переданный напиток.
        """
        if not self.map_loaded:
            self.map.load_map()
            self.map_loaded = True

        # Нижние слои (под игроком)
        for i in range(self.split_player):
            self.map.draw_layer(screen, i)
        self.player.update()
        self.player.draw(screen)
        for i in range(self.split_player, self.split_nps):
            self.map.draw_layer(screen, i)

        now = py.time.get_ticks()

        # ----- Анимация облачка заказа -----
        if self.callout_show and self.order.current_order:
            if self.animation_index == -1:
                # Начало анимации
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

            # Отрисовка текущего элемента
            screen.blit(self.callout_img, self.callout_rect)
            order = self.order.current_order
            if self.animation_index == 0:
                # Чашка (буква)
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
                # Сироп
                syrup_name = order['syrup']['name']
                if syrup_name in self.syrup_sprites:
                    syrup_icon = self.syrup_sprites[syrup_name]
                    syrup_rect = syrup_icon.get_rect(center=(self.callout_rect.centerx, 130))
                    screen.blit(syrup_icon, syrup_rect)

        # ----- Кнопка "Взять заказ" -----
        if (not self.callout_show and self.npc and self.npc.is_path_finished()
                and self.order_active and self.npc_state == 'idle'):
            self.interact_btn_show = True
        else:
            self.interact_btn_show = False
        if self.interact_btn_show:
            self.interact_btn.draw(screen)

        # ----- Отрисовка переданного напитка (стакан с заливкой) -----
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
            # Запоминаем прямоугольник для клика
            self.submitted_drink_rect = py.Rect(glass_x, glass_y,
                                                self.submitted_glass_width,
                                                self.submitted_glass_height)

        # ----- Обновление NPC и отрисовка верхних слоёв -----
        self.update_npc_state()
        self.npc.update()
        self.npc.draw(screen)

        for i in range(self.split_nps, len(self.map.layers)):
            self.map.draw_layer(screen, i)

    def events(self, events):
        """
        Обрабатывает события мыши: клик по кнопке заказа и клик по переданному напитку.
        """
        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                # Кнопка "Взять заказ"
                if self.interact_btn_show and self.interact_btn.signal(event.pos):
                    self.order.generate_random_order()
                    self.interact_btn_show = False
                    self.order_active = False
                    self.callout_show = True
                    self.animation_index = -1
                    self.animation_timer = 0

                # Клик по готовому напитку, переданному из BuildStation
                if self.submitted_drink and self.submitted_drink_rect and self.submitted_drink_rect.collidepoint(event.pos):
                    self.add_completed_drink(self.submitted_drink)