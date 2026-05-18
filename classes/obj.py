import random, globals
from globals import *
from colors import *

class TicketsOrder:
    def __init__(self):
        self.player_level = db.get_player_level(globals.id_player)
        self.cup_sizes = []
        self.espresso_types = []
        self.milk_types = []
        self.syrups = []

        self._load_data()
        self.current_order = None
        self.show_order = False
        self.revealed = set()

        self.espresso_sprites = {}
        self.milk_sprites = {}
        self.syrup_sprites = {}

    def set_sprites(self, espresso_sprites, milk_sprites, syrup_sprites):
        self.espresso_sprites = espresso_sprites
        self.milk_sprites = milk_sprites
        self.syrup_sprites = syrup_sprites

    def _parse_color(self, color_str):
        if not color_str:
            return (200, 200, 200)
        parts = color_str.strip('()').split(',')
        if len(parts) == 3:
            return tuple(int(p.strip()) for p in parts)
        return (200, 200, 200)

    def _load_data(self):
        """Загружает данные, доступные на уровне игрока"""
        # Чашки
        db.cursor.execute("SELECT id, cup, capacity FROM cup_sizes")
        cups = db.cursor.fetchall()
        # Если в cup_sizes нет level_id, то все чашки доступны с 1 уровня.
        # При желании можно добавить поле level_id в cup_sizes и фильтровать.
        for cup in cups:
            cup['cup'] = cup['cup']
            cup['capacity'] = cup['capacity']
            # цвет для чашки можно не загружать или добавить позже
            cup['color'] = (200, 200, 200)  # временно
        self.cup_sizes = cups

        # Эспрессо
        db.cursor.execute("SELECT id, name, color FROM ingredients WHERE type='espresso' AND level_id <= %s", (self.player_level,))
        self.espresso_types = db.cursor.fetchall()
        for e in self.espresso_types:
            e['color'] = self._parse_color(e['color'])

        # Молоко
        db.cursor.execute("SELECT id, name, color FROM ingredients WHERE type='milk' AND level_id <= %s", (self.player_level,))
        self.milk_types = db.cursor.fetchall()
        for m in self.milk_types:
            m['color'] = self._parse_color(m['color'])

        # Сиропы
        db.cursor.execute("SELECT id, name, color FROM ingredients WHERE type='syrup' AND level_id <= %s", (self.player_level,))
        self.syrups = db.cursor.fetchall()
        for s in self.syrups:
            s['color'] = self._parse_color(s['color'])

    def generate_random_order(self):
        """Генерирует случайный заказ из доступных ингредиентов"""
        if not self.cup_sizes:
            return None

        cup = random.choice(self.cup_sizes)
        capacity = cup['capacity']

        # Эспрессо
        min_esp = 2
        max_esp = min(4, capacity - 2)
        if max_esp < min_esp:
            max_esp = min_esp
        esp_qty = random.randint(min_esp, max_esp)
        milk_qty = capacity - esp_qty
        if milk_qty < 2:
            milk_qty = 2
            esp_qty = capacity - milk_qty
        if milk_qty > 4:
            milk_qty = 4
            esp_qty = capacity - milk_qty

        espresso = random.choice(self.espresso_types) if self.espresso_types else None
        milk = random.choice(self.milk_types) if self.milk_types else None
        syrup = random.choice(self.syrups) if self.syrups else None
        milk_temperature = random.choice(["горячее", "холодное"])

        self.current_order = {
            'cup': {
                'id': cup['id'],
                'cup': cup['cup'],
                'capacity': cup['capacity'],
                'color': cup['color']
            },
            'espresso': {
                'id': espresso['id'] if espresso else None,
                'type': espresso['name'] if espresso else 'нет',
                'portions': esp_qty,
                'color': espresso['color'] if espresso else (110, 59, 9)
            },
            'milk': {
                'id': milk['id'] if milk else None,
                'type': milk['name'] if milk else 'нет',
                'portions': milk_qty,
                'temperature': milk_temperature,
                'color': milk['color'] if milk else (248, 248, 248)
            },
            'syrup': {
                'id': syrup['id'] if syrup else None,
                'name': syrup['name'] if syrup else None,
                'color': syrup['color'] if syrup else (200, 200, 200)
            }
        }

        # Сбрасываем раскрытые блоки для нового заказа
        self.revealed.clear()
        self.show_order = True

        # Вывод в консоль
        print(f"Сгенерирован заказ: размер {cup['cup']}, емкость {capacity}")
        print(f"  Эспрессо: {esp_qty} порций, тип: {espresso['name'] if espresso else 'нет'}")
        print(f"  Молоко: {milk_qty} порций, тип: {milk['name'] if milk else 'нет'}, температура: {milk_temperature}")
        print(f"  Сироп: {syrup['name'] if syrup else 'нет'}")

        return self.current_order

    def reveal_by_index(self, index):
        """Раскрывает компонент по индексу анимации"""
        if index == 0:
            self.reveal_cup()
        elif index == 1:
            self.reveal_milk()
        elif index == 2:
            self.reveal_espresso()
        elif index == 3:
            self.reveal_syrup()

    def reveal_cup(self):
        self.revealed.add('cup')

    def reveal_milk(self):
        self.revealed.add('milk')

    def reveal_espresso(self):
        self.revealed.add('espresso')

    def reveal_syrup(self):
        self.revealed.add('syrup')

    def draw(self, screen):
        if self.show_order:
            self._draw_order(screen)
        else:
            self._draw_click_indicator(screen)

    def _draw_click_indicator(self, screen):
        x, y = 150, 0
        width, height = 50, 100
        py.draw.rect(screen, ORDER_TICKET, (x, y, width, height))
        py.draw.rect(screen, CONTOUR, (x, y, width, height), 3)

    def _draw_order(self, screen):
        if not self.current_order:
            return

        x, y = 960, 160
        width, height = 240, 400
        bg_color = (200, 200, 200)
        line_thickness = 3

        # Фон тикета
        py.draw.rect(screen, bg_color, (x, y, width, height))

        # Внешняя рамка
        py.draw.rect(screen, CONTOUR, (x, y, width, height), line_thickness)

        # Горизонтальные разделители
        py.draw.line(screen, CONTOUR, (x, y + 80), (x + width, y + 80), line_thickness)
        py.draw.line(screen, CONTOUR, (x, y + 80 + 280), (x + width, y + 80 + 280), line_thickness)
        py.draw.line(screen, CONTOUR, (x, y + height - 40), (x + width, y + height - 40), line_thickness)

        # Сироп
        syrup = self.current_order['syrup']
        if 'syrup' in self.revealed and syrup['name'] and syrup['name'] != 'нет':
            py.draw.rect(screen, syrup['color'], (x + 2, y + 2, width - 4, 76))
            if syrup['name'] in self.syrup_sprites:
                img = self.syrup_sprites[syrup['name']]
                img_rect = img.get_rect(center=(x + width//2, y + 40))
                screen.blit(img, img_rect)
        else:
            py.draw.rect(screen, (200,200,200), (x + 2, y + 2, width - 4, 76))
        py.draw.rect(screen, CONTOUR, (x, y, width, 80), line_thickness)

        # Молоко и эспрессо
        mid_y = y + 80
        mid_height = 280
        half_width = width // 2

        milk = self.current_order['milk']
        espresso = self.current_order['espresso']

        # Молоко
        milk_rect = (x, mid_y, half_width, mid_height)
        if 'milk' in self.revealed:
            py.draw.rect(screen, milk['color'], (milk_rect[0]+2, milk_rect[1]+2, milk_rect[2]-4, milk_rect[3]-4))
            if milk['type'] != 'нет' and milk['type'] in self.milk_sprites:
                img = self.milk_sprites[milk['type']]
                img_rect = img.get_rect(center=(x + half_width//2, mid_y + 100))
                screen.blit(img, img_rect)
                if font:
                    portions = font.text_ret(24, f"x{milk['portions']}", BLACK)
                    p_rect = portions.get_rect(center=(x + half_width//2, mid_y + 160))
                    screen.blit(portions, p_rect)
                    temp_symbol = "г" if milk['temperature'] == "горячее" else "х"
                    temp_text = font.text_ret(20, temp_symbol, BLACK)
                    t_rect = temp_text.get_rect(center=(x + half_width//2, mid_y + 190))
                    screen.blit(temp_text, t_rect)
        else:
            py.draw.rect(screen, (200,200,200), (milk_rect[0]+2, milk_rect[1]+2, milk_rect[2]-4, milk_rect[3]-4))
        py.draw.rect(screen, CONTOUR, milk_rect, line_thickness)

        # Эспрессо
        espresso_rect = (x + half_width, mid_y, half_width, mid_height)
        if 'espresso' in self.revealed:
            py.draw.rect(screen, espresso['color'], (espresso_rect[0]+2, espresso_rect[1]+2, espresso_rect[2]-4, espresso_rect[3]-4))
            if espresso['type'] != 'нет' and espresso['type'] in self.espresso_sprites:
                img = self.espresso_sprites[espresso['type']]
                img_rect = img.get_rect(center=(x + half_width + half_width//2, mid_y + 100))
                screen.blit(img, img_rect)
                if font:
                    portions = font.text_ret(24, f"x{espresso['portions']}", BLACK)
                    p_rect = portions.get_rect(center=(x + half_width + half_width//2, mid_y + 160))
                    screen.blit(portions, p_rect)
        else:
            py.draw.rect(screen, (200,200,200), (espresso_rect[0]+2, espresso_rect[1]+2, espresso_rect[2]-4, espresso_rect[3]-4))
        py.draw.rect(screen, CONTOUR, espresso_rect, line_thickness)

        py.draw.line(screen, CONTOUR, (x + half_width, mid_y), (x + half_width, mid_y + mid_height), line_thickness)

        # Чашка
        cup = self.current_order['cup']
        cup_rect = (x, y + height - 40, width, 40)
        if 'cup' in self.revealed:
            py.draw.rect(screen, cup['color'], (cup_rect[0]+2, cup_rect[1]+2, cup_rect[2]-4, cup_rect[3]-4))
            if font:
                cup_text = font.text_ret(40, cup['cup'], BLACK)
                text_rect = cup_text.get_rect(center=(x + width//2, y + height - 20))
                screen.blit(cup_text, text_rect)
        else:
            py.draw.rect(screen, (200,200,200), (cup_rect[0]+2, cup_rect[1]+2, cup_rect[2]-4, cup_rect[3]-4))
        py.draw.rect(screen, CONTOUR, cup_rect, line_thickness)

    def events(self, events):
        for event in events:
            if event.type == py.KEYDOWN and event.key == py.K_SPACE:
                self.show_order = not self.show_order