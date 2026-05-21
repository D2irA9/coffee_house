from ..node import ImageButton, font, Button
from .order import OrderStation
from .brew import BrewStation
from .build import BuildStation
from globals import *
from colors import *
from ..obj import TicketsOrder

class Slider:
    def __init__(self, line_rect, handle_sprite, initial_val=1.0):
        self.line_rect = line_rect
        self.handle_sprite = handle_sprite
        self.handle_width = handle_sprite.get_width()
        self.handle_height = handle_sprite.get_height()
        self.min_val = 0.0
        self.max_val = 1.0
        self.val = initial_val
        self.grabbed = False

    def get_handle_pos(self):
        """Возвращает позицию центра ручки"""
        x = self.line_rect.x + self.val * self.line_rect.width
        y = self.line_rect.centery
        return (x, y)

    def handle_rect(self):
        """Прямоугольник для проверки попадания мыши в ручку"""
        x, y = self.get_handle_pos()
        return py.Rect(x - self.handle_width//2, y - self.handle_height//2,
                       self.handle_width, self.handle_height)

    def update(self, events):
        for event in events:
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                if self.handle_rect().collidepoint(event.pos):
                    self.grabbed = True
                elif self.line_rect.collidepoint(event.pos):
                    rel_x = event.pos[0] - self.line_rect.x
                    self.val = rel_x / self.line_rect.width
                    self.val = max(self.min_val, min(self.max_val, self.val))
                    self.grabbed = True
            elif event.type == py.MOUSEBUTTONUP and event.button == 1:
                self.grabbed = False
            elif event.type == py.MOUSEMOTION and self.grabbed:
                rel_x = event.pos[0] - self.line_rect.x
                self.val = rel_x / self.line_rect.width
                self.val = max(self.min_val, min(self.max_val, self.val))
        return self.val

    def draw(self, screen):
        x, y = self.get_handle_pos()
        screen.blit(self.handle_sprite, (x - self.handle_width//2, y - self.handle_height//2))


class StationManager:
    def __init__(self, sound_manager, logout_callback, milk_colors, espresso_colors, syrup_colors):
        self.order = TicketsOrder()
        self.stations = {
            "order": OrderStation(sound_manager, self.order),
            "brew": BrewStation(sound_manager, milk_colors, espresso_colors, syrup_colors),
            "build": BuildStation(sound_manager, milk_colors, espresso_colors, syrup_colors),
        }
        self.current_station = "order"

        # Загружаем спрайты кнопок
        self.nav_sprites = {}
        scale = 3
        for st in ["order", "brew", "build"]:
            path = f"assets/sprites/buttons/{st}.png"
            img = py.image.load(path).convert_alpha()
            w = 102 * scale
            h = 35 * scale
            self.nav_sprites[st] = py.transform.scale(img, (w, h))

        # Позиции кнопок внизу по углам
        button_width = 102 * scale
        button_height = 35 * scale
        left_pos = (0, 720 - button_height)
        right_pos = (1200 - button_width, 720 - button_height)

        self.navigation_buttons = {
            "left": ImageButton("assets/sprites/buttons/order.png", left_pos, scale=1),
            "right": ImageButton("assets/sprites/buttons/order.png", right_pos, scale=1)
        }
        self.show_left_button = False
        self.show_right_button = False

        self.navigation_map = {
            "order": {"left": "build", "right": "brew"},
            "brew": {"left": "build", "right": "order"},
            "build": {"left": "order", "right": "brew"}
        }

        self.connect_stations()
        self.update_navigation()

        self.sound_manager = sound_manager
        self.logout_callback = logout_callback

        # Настройки
        self.settings_show = False
        self.settings_btn = ImageButton("assets/sprites/settings/settings.png", (300, 0), 3)

        scale = 4
        # Кнопка музыки
        music_on_img = py.image.load("assets/sprites/settings/on_music.png").convert_alpha()
        music_off_img = py.image.load("assets/sprites/settings/off_music.png").convert_alpha()
        w = music_on_img.get_width() * scale
        h = music_on_img.get_height() * scale
        self.music_on_scaled = py.transform.scale(music_on_img, (w, h))
        self.music_off_scaled = py.transform.scale(music_off_img, (w, h))

        self.music_btn = ImageButton("assets/sprites/settings/on_music.png", (400, 280), 1)
        self.music_btn.image = self.music_on_scaled
        self.music_btn.rect = self.music_btn.image.get_rect(topleft=(400, 280))

        # Кнопка звуков
        sfx_on_img = py.image.load("assets/sprites/settings/on_volume.png").convert_alpha()
        sfx_off_img = py.image.load("assets/sprites/settings/off_volume.png").convert_alpha()
        w_sfx = sfx_on_img.get_width() * scale
        h_sfx = sfx_on_img.get_height() * scale
        self.sfx_on_scaled = py.transform.scale(sfx_on_img, (w_sfx, h_sfx))
        self.sfx_off_scaled = py.transform.scale(sfx_off_img, (w_sfx, h_sfx))

        self.sfx_btn = ImageButton("assets/sprites/settings/on_volume.png", (400, 350), 1)
        self.sfx_btn.image = self.sfx_on_scaled
        self.sfx_btn.rect = self.sfx_btn.image.get_rect(topleft=(400, 350))

        # Ползунки
        slider_handle_img = py.image.load("assets/sprites/settings/slider.png").convert_alpha()
        self.slider_handle = py.transform.scale(slider_handle_img, (20, 20))
        self.music_slider_line = py.Rect(460, 305, 350, 10)
        self.music_slider = Slider(self.music_slider_line, self.slider_handle, initial_val=self.sound_manager.music_volume)
        self.sfx_slider_line = py.Rect(460, 375, 350, 10)
        self.sfx_slider = Slider(self.sfx_slider_line, self.slider_handle, initial_val=self.sound_manager.sfx_volume)
        self.music_btn.image = self.music_on_scaled if self.sound_manager.music_enabled else self.music_off_scaled
        self.sfx_btn.image = self.sfx_on_scaled if self.sound_manager.sfx_enabled else self.sfx_off_scaled

        self.sound_manager.start_music("background")

        # Кнопка выход
        self.exit_btn = ImageButton("assets/sprites/settings/exit.png", (1200 // 2 - 100, 450), 3)

        # Кнопка карточек
        self.cards_btn = ImageButton("assets/sprites/settings/cards.png", (1200 // 2 + 30, 450), 3)

    def connect_stations(self):
        """Связываем станции между собой"""
        brew_station = self.stations["brew"]
        build_station = self.stations["build"]
        order_station = self.stations["order"]

        brew_station.build_station = build_station
        build_station.order_station = order_station

    def switch_to(self, station_name):
        if station_name in self.stations:
            self.stations[self.current_station].deactivate()
            self.current_station = station_name
            self.stations[station_name].activate()
            self.update_navigation()

    def update_navigation(self):
        """Обновление видимости и изображений кнопок навигации"""
        current_nav = self.navigation_map[self.current_station]

        # Левая кнопка
        left_target = current_nav.get("left")
        if left_target:
            sprite = self.nav_sprites[left_target].copy()
            # Отражаем горизонтально для левой кнопки
            sprite = py.transform.flip(sprite, True, False)
            self.navigation_buttons["left"].image = sprite
            self.navigation_buttons["left"].rect = sprite.get_rect(topleft=self.navigation_buttons["left"].rect.topleft)
            self.show_left_button = True
        else:
            self.show_left_button = False

        # Правая кнопка
        right_target = current_nav.get("right")
        if right_target:
            sprite = self.nav_sprites[right_target].copy()
            self.navigation_buttons["right"].image = sprite
            self.navigation_buttons["right"].rect = sprite.get_rect(topleft=self.navigation_buttons["right"].rect.topleft)
            self.show_right_button = True
        else:
            self.show_right_button = False

    def settings_draw(self, screen):
        py.draw.rect(screen, SETTINGS_FON, (250, 180, 700, 400))
        py.draw.rect(screen, CONTOUR, (250, 180, 700, 400), 3)

        # Текст Настройки
        text_setting = font.text_ret(size=42, text='Настройки', color=GRAY)
        screen.blit(text_setting, (506, 230))

        # Музыка
        self.music_btn.draw(screen)
        py.draw.rect(screen, CONTOUR, self.music_slider_line)
        self.music_slider.draw(screen)

        # Звуки
        self.sfx_btn.draw(screen)
        py.draw.rect(screen, CONTOUR, self.sfx_slider_line)
        self.sfx_slider.draw(screen)

        # Кнопка выход
        self.exit_btn.draw(screen)
        # Кнопка карточек
        self.cards_btn.draw(screen)

        # Текст версии
        text_version = font.text_ret(size=25, text=f'v {version}', color=GRAY)
        screen.blit(text_version, (890, 550))

    def handle_events(self, events):
        # Обновление состояния музыки
        self.sound_manager.update()

        if self.settings_show:
            # Обработка ползунков
            new_music_vol = self.music_slider.update(events)
            if new_music_vol != self.sound_manager.music_volume:
                self.sound_manager.set_music_volume(new_music_vol)

            new_sfx_vol = self.sfx_slider.update(events)
            if new_sfx_vol != self.sound_manager.sfx_volume:
                self.sound_manager.set_sfx_volume(new_sfx_vol)

        self.order.events(events)

        for event in events:
            if event.type == py.KEYDOWN and event.key == py.K_ESCAPE:
                self.settings_show = not self.settings_show

            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                if self.settings_btn.signal(event.pos):
                    self.settings_show = not self.settings_show

                if self.settings_show:
                    # Кнопка музыки
                    if self.music_btn.signal(event.pos):
                        enabled = self.sound_manager.toggle_music()
                        self.music_btn.image = self.music_on_scaled if enabled else self.music_off_scaled
                        self.music_btn.rect = self.music_btn.image.get_rect(topleft=(400, 280))
                    # Кнопка звука
                    if self.sfx_btn.signal(event.pos):
                        enabled = self.sound_manager.toggle_sfx()
                        self.sfx_btn.image = self.sfx_on_scaled if enabled else self.sfx_off_scaled
                        self.sfx_btn.rect = self.sfx_btn.image.get_rect(topleft=(400, 350))
                    # Кнопка выхода их аккаунта
                    elif self.exit_btn.signal(event.pos):
                        self.logout_callback()
                        self.settings_show = False
                    elif self.cards_btn.signal(event.pos):
                        print("Карточки")

                # Навигационные кнопки
                current_nav = self.navigation_map[self.current_station]
                if self.show_right_button and self.navigation_buttons["right"].signal(event.pos):
                    target = current_nav.get("right")
                    if target:
                        self.switch_to(target)
                if self.show_left_button and self.navigation_buttons["left"].signal(event.pos):
                    target = current_nav.get("left")
                    if target:
                        self.switch_to(target)

        self.stations[self.current_station].events(events)

    def draw(self, screen):
        self.stations[self.current_station].draw(screen)
        self.settings_btn.draw(screen)
        self.order.draw(screen)
        if self.settings_show:
            self.settings_draw(screen)

        if self.show_left_button:
            self.navigation_buttons["left"].draw(screen)
        if self.show_right_button:
            self.navigation_buttons["right"].draw(screen)