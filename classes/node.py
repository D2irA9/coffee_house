import pygame as py

class Label:
    """Текст"""
    def __init__(self, font_path = 'assets/font/PixelizerBold.ttf'):
        self.font_path = font_path

    def text_ret(self, size, text, color, antialias=True):
        """ Создание переменной текста """
        label = py.font.Font(self.font_path, size)
        return label.render(text, antialias, color)

font = Label()

class Button:
    """Кнопки с возможностью отображения текста"""
    def __init__(self, width, height, bg_color, pos, text="", text_color=(0,0,0), font_size=24, border_color=(58,58,80), border_width=3):
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.pos = pos
        self.border_color = border_color
        self.border_width = border_width
        self.text = text
        self.text_color = text_color
        self.font_size = font_size
        # Создаём поверхность
        self.image = py.Surface((self.width, self.height))
        self.rect = self.image.get_rect(topleft=self.pos)
        self.redraw()  # сразу рисуем кнопку с текстом

    def redraw(self):
        """ Перерисовка кнопки (фон, рамка, текст) """
        # Заливка фона
        self.image.fill(self.bg_color)
        # Рамка
        py.draw.rect(self.image, self.border_color, (0, 0, self.width, self.height), self.border_width)
        # Текст, если есть
        if self.text:
            # Используем глобальный объект font для создания текста
            text_surface = font.text_ret(self.font_size, self.text, self.text_color)
            # Центрируем текст на кнопке
            text_rect = text_surface.get_rect(center=(self.width // 2, self.height // 2))
            self.image.blit(text_surface, text_rect)
        # Обновляем rect (на случай, если позиция изменилась, но мы её не меняем)
        self.rect = self.image.get_rect(topleft=self.pos)

    def change_color(self, new_color):
        """ Изменить цвет фона """
        self.bg_color = new_color
        self.redraw()

    def set_text(self, new_text):
        """ Изменить текст на кнопке """
        self.text = new_text
        self.redraw()

    def draw(self, screen):
        """ Отображение кнопки на экране """
        screen.blit(self.image, self.rect)

    def signal(self, pos):
        """ Проверка, находится ли точка внутри кнопки """
        return self.rect.collidepoint(pos)


class ImageButton:
    """Кнопка на основе изображения (текстуры) с возможностью текста поверх"""

    def __init__(self, image_path, pos, scale=1.0, text="", text_color=(0, 0, 0), font_size=20, text_pos="center"):
        # Загружаем и масштабируем изображение
        self.image_original = py.image.load(image_path).convert_alpha()
        if scale != 1.0:
            new_w = int(self.image_original.get_width() * scale)
            new_h = int(self.image_original.get_height() * scale)
            self.base_image = py.transform.scale(self.image_original, (new_w, new_h))
        else:
            self.base_image = self.image_original.copy()
        self.image = self.base_image.copy()

        # Параметры текста
        self.text = text
        self.text_color = text_color
        self.font_size = font_size
        self.text_pos = text_pos

        if text:
            self._add_text_to_image()

        self.rect = self.image.get_rect(topleft=pos)

    def _add_text_to_image(self):
        """Добавляет текст на текущее изображение кнопки"""
        text_surface = font.text_ret(self.font_size, self.text, self.text_color)
        text_rect = text_surface.get_rect()
        img_rect = self.image.get_rect()

        if self.text_pos == "center":
            text_rect.center = img_rect.center
        elif self.text_pos == "topleft":
            text_rect.topleft = (5, 5)
        elif self.text_pos == "topright":
            text_rect.topright = (img_rect.width - 5, 5)
        elif self.text_pos == "bottomleft":
            text_rect.bottomleft = (5, img_rect.height - 5)
        elif self.text_pos == "bottomright":
            text_rect.bottomright = (img_rect.width - 5, img_rect.height - 5)
        else:
            text_rect.center = img_rect.center

        self.image.blit(text_surface, text_rect)

    def set_text(self, text):
        """Изменить текст на кнопке"""
        self.text = text
        self.image = self.base_image.copy()
        if self.text:
            self._add_text_to_image()

    def set_text_color(self, color):
        self.text_color = color
        self.set_text(self.text)

    def set_font_size(self, size):
        self.font_size = size
        self.set_text(self.text)

    def set_text_pos(self, pos):
        self.text_pos = pos
        self.set_text(self.text)

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def signal(self, pos):
        return self.rect.collidepoint(pos)

    def flip(self, xbool=True, ybool=False):
        self.image = py.transform.flip(self.image, xbool, ybool)
        self.base_image = py.transform.flip(self.base_image, xbool, ybool)
        self.rect = self.image.get_rect(topleft=self.rect.topleft)
        return self

class CircleButton:
    """Круглые кнопки с текстом"""
    def __init__(self, radius, bg_color, pos, text="", text_color=(0, 0, 0), font_size=20):
        self.radius = radius
        self.bg_color = bg_color
        self.pos = pos
        self.text = text
        self.text_color = text_color
        self.font_size = font_size
        self.border_width = 3
        diameter = radius * 2
        self.image = py.Surface((diameter, diameter), py.SRCALPHA)

        self.redraw()
        self.rect = self.image.get_rect(center=pos)

        self.visible = True
        self.was_clicked = False

    def redraw(self):
        """Перерисовка кнопки с текстом"""
        diameter = self.radius * 2
        self.image.fill((0, 0, 0, 0))

        # Рисуем круг
        py.draw.circle(self.image, self.bg_color, (self.radius, self.radius), self.radius)
        py.draw.circle(self.image, (58, 58, 80), (self.radius, self.radius), self.radius, self.border_width)

        # Если есть текст
        if self.text:
            text_surface = font.text_ret(self.font_size, self.text, self.text_color)

            # Центрируем текст
            text_rect = text_surface.get_rect(center=(self.radius, self.radius))

            # Проверяем, помещается ли текст в круг
            text_width, text_height = text_surface.get_size()
            max_dimension = self.radius * 1.5

            # Если текст слишком большой
            if text_width > max_dimension or text_height > max_dimension:
                scale = min(max_dimension / text_width, max_dimension / text_height)
                new_font_size = max(12, int(self.font_size * scale * 0.8))
                text_surface = font.text_ret(new_font_size, self.text, self.text_color)
                text_rect = text_surface.get_rect(center=(self.radius, self.radius))

            self.image.blit(text_surface, text_rect)

    def change_color(self, new_color):
        """Смена цвета фона"""
        self.bg_color = new_color
        self.redraw()

    def change_text_color(self, new_color):
        """Смена цвета текста"""
        self.text_color = new_color
        self.redraw()

    def set_text(self, text):
        """Изменить текст кнопки"""
        self.text = text
        self.redraw()

    def set_font_size(self, size):
        """Изменить размер шрифта"""
        self.font_size = size
        self.redraw()

    def draw(self, screen):
        """Отрисовка кнопки"""
        if self.visible:
            screen.blit(self.image, self.rect)

    def signal(self, pos):
        """Получение сигнала (клик)"""
        if not self.visible:
            return False

        distance = ((pos[0] - self.rect.centerx) ** 2 + (pos[1] - self.rect.centery) ** 2) ** 0.5
        return distance <= self.radius

    def set_visible(self, visible):
        """Установить видимость кнопки"""
        self.visible = visible
        self.redraw()

    def set_pos(self, pos):
        """Изменить положение кнопки"""
        self.pos = pos
        self.rect = self.image.get_rect(center=pos)
        self.redraw()