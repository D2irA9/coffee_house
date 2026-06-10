from colors import *
from globals import *
from classes.node import Button
from classes.stations import StationManager
from classes.sound_manager import SoundManager
from game import game
import sys, globals, json, hashlib

# Инициализация Pygame и микшера звука
py.init()
py.mixer.init()

# Настройка окна
py.display.set_caption("Мяу")
icon = py.image.load("assets/icon/icon.png").convert_alpha()
py.display.set_icon(icon)

# Часы для управления FPS
clock = py.time.Clock()
fps = 30

# Путь к файлу сохранения сессии
SESSION_FILE = "player_session.json"

# Менеджер звука (создаётся глобально, чтобы звук играл во время заставки)
sound_manager = SoundManager()

# Список треков мяуканья и мурлыканья
meow_tracks = sound_manager.get_sfx_tracks("cat/meow")
purr_tracks = sound_manager.get_sfx_tracks("cat/purring")

current_channel = None      # текущий звуковой канал
next_stage = "meow"         # этап заставки: "meow" -> "purr" -> "end"

station_manager = None       # менеджер станций (будет создан после входа)


def check_session() -> bool:
    """
    Проверяет наличие сохранённой сессии.
    Если файл существует и ID игрока валиден, загружает его в globals.
    Возвращает True, если сессия активна и игрок авторизован.
    """
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = f.read().strip()
                if data:
                    session = json.loads(data)
                    if "id_player" in session and "name_player" in session:
                        globals.id_player = session["id_player"]
                        globals.name_player = session["name_player"]
                        # Проверяем, существует ли игрок в базе данных
                        if db.check_player(globals.id_player):
                            return True
    except Exception as e:
        print(f"Ошибка загрузки сессии: {e}")
    return False


def save_session(id_player: int, name_player: str) -> None:
    """Сохраняет данные сессии в JSON-файл и в глобальные переменные."""
    try:
        session_data = {"id_player": id_player, "name_player": name_player}
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=4)
        globals.id_player = id_player
        globals.name_player = name_player
    except Exception as e:
        print(f"Ошибка сохранения сессии: {e}")


# ----- Настройка изображения для заставки -----
scale_factor = 5
new_width = icon.get_width() * scale_factor
new_height = icon.get_height() * scale_factor
image = py.transform.scale(icon, (new_width, new_height))
image_rect = image.get_rect()
image_rect.center = (WIDTH // 2, HEIGHT // 2)

alpha = 0             # текущая прозрачность (0..255)
fade_speed = 5        # скорость появления
fade_done = False     # появилась ли картинка полностью?
is_saver = True       # активна ли заставка


def saver() -> None:
    """Отрисовывает заставку с плавным появлением иконки."""
    global alpha, fade_done
    screen.fill(WHITE)
    if not fade_done:
        alpha += fade_speed
        if alpha >= 255:
            alpha = 255
            fade_done = True
    image.set_alpha(alpha)
    screen.blit(image, image_rect)


def screen_login() -> None:
    """
    Экран входа в игру.
    Позволяет ввести email и пароль, проверяет их в БД.
    При успехе сохраняет сессию и завершает экран.
    """
    py.display.set_caption("Вход")

    # Поля ввода: email и пароль
    input_boxes = [
        py.Rect(400, 300, 400, 50),   # Email
        py.Rect(400, 400, 400, 50)    # Пароль
    ]
    labels = ["Email", "Пароль"]
    input_texts = ['', '']
    input_visible = [True, False]     # пароль скрыт звёздочками
    active_input = -1                 # индекс активного поля (-1 = не активен)
    color_inactive = py.Color('lightskyblue3')
    color_active = py.Color('dodgerblue2')

    # Позиции курсора в каждом поле
    cursor_position = [0, 0]
    cursor_visible = True
    cursor_timer = 0

    message = ''                     # текст сообщения об ошибке
    message_color = RED

    registration_button = Button(400, 50, GREEN, (400, 600), "Регистрация")

    running = True
    while running:
        for event in py.event.get():
            if event.type == py.QUIT:
                db.close()
                py.quit()
                sys.exit()
            if event.type == py.KEYDOWN:
                if event.key == py.K_ESCAPE:
                    return                     # выход из экрана входа
                if active_input != -1:
                    if event.key == py.K_RETURN:
                        # Попытка входа
                        if all(input_texts):
                            email = input_texts[0].strip()
                            password = input_texts[1]
                            # хешируем введённый пароль
                            hashed = hashlib.sha256(password.encode()).hexdigest()
                            # получаем данные пользователя из БД
                            user_data = db.get_player_by_email(email)
                            if user_data and user_data['password'] == hashed:
                                # успешный вход
                                save_session(user_data['id'], user_data['name'])
                                running = False   # успех, выходим из цикла
                            else:
                                message = "Неверный email или пароль"
                                message_color = RED
                        else:
                            message = "Заполните все поля"
                            message_color = RED
                    # Обработка клавиш редактирования текста
                    elif event.key == py.K_BACKSPACE:
                        if cursor_position[active_input] > 0:
                            text = input_texts[active_input]
                            pos = cursor_position[active_input]
                            input_texts[active_input] = text[:pos-1] + text[pos:]
                            cursor_position[active_input] -= 1
                    elif event.key == py.K_DELETE:
                        if cursor_position[active_input] < len(input_texts[active_input]):
                            text = input_texts[active_input]
                            pos = cursor_position[active_input]
                            input_texts[active_input] = text[:pos] + text[pos+1:]
                    elif event.key == py.K_LEFT:
                        cursor_position[active_input] = max(0, cursor_position[active_input] - 1)
                    elif event.key == py.K_RIGHT:
                        cursor_position[active_input] = min(len(input_texts[active_input]), cursor_position[active_input] + 1)
                    else:
                        if event.unicode.isprintable():
                            text = input_texts[active_input]
                            pos = cursor_position[active_input]
                            input_texts[active_input] = text[:pos] + event.unicode + text[pos:]
                            cursor_position[active_input] += 1

            if event.type == py.MOUSEBUTTONDOWN:
                active_input = -1
                for i, box in enumerate(input_boxes):
                    if box.collidepoint(event.pos):
                        active_input = i
                        cursor_position[i] = len(input_texts[i])
                        break
                if registration_button.signal(event.pos):
                    if screen_registration():
                        running = False   # после успешной регистрации выходим на игру

        # ----- Отрисовка -----
        screen.fill(WHITE)
        title = font.text_ret(48, "Вход", BLACK)
        title_rect = title.get_rect(center=(WIDTH//2, 150))
        screen.blit(title, title_rect)

        for i, box in enumerate(input_boxes):
            label = font.text_ret(24, labels[i], BLACK)
            label_rect = label.get_rect(center=(box.centerx, box.top - 20))
            screen.blit(label, label_rect)

            color = color_active if i == active_input else color_inactive
            py.draw.rect(screen, color, box, 3)

            display_text = input_texts[i]
            if not input_visible[i]:
                display_text = '*' * len(display_text)
            text_surface = font.text_ret(24, display_text, BLACK)
            screen.blit(text_surface, (box.x + 5, box.y + 10))

            if i == active_input and cursor_visible:
                cursor_x = box.x + 5 + font.text_ret(24, display_text[:cursor_position[i]], BLACK).get_width()
                cursor_y = box.y + 10
                py.draw.line(screen, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + 30), 2)

        hint = font.text_ret(18, "Enter - войти", GRAY)
        hint_rect = hint.get_rect(center=(WIDTH//2, 550))
        screen.blit(hint, hint_rect)

        if message:
            msg_surface = font.text_ret(24, message, message_color)
            msg_rect = msg_surface.get_rect(center=(WIDTH//2, 500))
            screen.blit(msg_surface, msg_rect)

        # Анимация курсора
        cursor_timer += 1
        if cursor_timer >= 30:
            cursor_visible = not cursor_visible
            cursor_timer = 0

        registration_button.draw(screen)

        py.display.flip()
        clock.tick(fps)


def screen_registration() -> bool:
    """
    Экран регистрации нового игрока.
    Возвращает True при успешной регистрации, иначе False.
    """
    py.display.set_caption("Регистрация")

    # Поля: email, имя, пароль, подтверждение пароля
    input_boxes = [
        py.Rect(400, 250, 400, 50),
        py.Rect(400, 350, 400, 50),
        py.Rect(400, 450, 400, 50),
        py.Rect(400, 550, 400, 50)
    ]
    labels = ["Email", "Имя", "Пароль", "Подтверждение пароля"]
    input_texts = ['', '', '', '']
    input_visible = [True, True, False, False]   # пароли скрыты
    active_input = -1
    color_inactive = py.Color('lightskyblue3')
    color_active = py.Color('dodgerblue2')

    cursor_position = [0, 0, 0, 0]
    cursor_visible = True
    cursor_timer = 0

    message = ''
    message_color = RED

    success = False
    running = True
    while running:
        for event in py.event.get():
            if event.type == py.QUIT:
                db.close()
                py.quit()
                sys.exit()

            if event.type == py.KEYDOWN:
                if event.key == py.K_ESCAPE:
                    return False

                if active_input != -1:
                    if event.key == py.K_RETURN:
                        if all(input_texts):
                            email = input_texts[0].strip()
                            name = input_texts[1].strip()
                            password = input_texts[2]
                            confirm = input_texts[3]

                            # Валидация
                            if '@' not in email or '.' not in email:
                                message = "Некорректный email"
                                message_color = RED
                            elif len(password) < 6:
                                message = "Пароль должен быть не менее 6 символов"
                                message_color = RED
                            elif password != confirm:
                                message = "Пароли не совпадают"
                                message_color = RED
                            else:
                                # Проверка уникальности email
                                if db.get_player_id(email) is not None:
                                    message = "Email уже зарегистрирован"
                                    message_color = RED
                                else:
                                    player_id = db.add_player(name, email, password, 1000)
                                    if player_id:
                                        save_session(player_id, name)
                                        print(f"Пользователь {name} зашёл в игру")
                                        success = True
                                        running = False
                                    else:
                                        message = "Ошибка базы данных"
                                        message_color = RED
                        else:
                            message = "Заполните все поля"
                            message_color = RED
                    # Обработка редактирования текста (аналогично экрану входа)
                    elif event.key == py.K_BACKSPACE:
                        if cursor_position[active_input] > 0:
                            text = input_texts[active_input]
                            pos = cursor_position[active_input]
                            input_texts[active_input] = text[:pos-1] + text[pos:]
                            cursor_position[active_input] -= 1
                    elif event.key == py.K_DELETE:
                        if cursor_position[active_input] < len(input_texts[active_input]):
                            text = input_texts[active_input]
                            pos = cursor_position[active_input]
                            input_texts[active_input] = text[:pos] + text[pos+1:]
                    elif event.key == py.K_LEFT:
                        cursor_position[active_input] = max(0, cursor_position[active_input] - 1)
                    elif event.key == py.K_RIGHT:
                        cursor_position[active_input] = min(len(input_texts[active_input]), cursor_position[active_input] + 1)
                    else:
                        if event.unicode.isprintable():
                            text = input_texts[active_input]
                            pos = cursor_position[active_input]
                            input_texts[active_input] = text[:pos] + event.unicode + text[pos:]
                            cursor_position[active_input] += 1

            if event.type == py.MOUSEBUTTONDOWN:
                active_input = -1
                for i, box in enumerate(input_boxes):
                    if box.collidepoint(event.pos):
                        active_input = i
                        cursor_position[i] = len(input_texts[i])
                        break

        # Отрисовка
        screen.fill(WHITE)
        title = font.text_ret(48, "Регистрация", BLACK)
        title_rect = title.get_rect(center=(WIDTH//2, 100))
        screen.blit(title, title_rect)

        for i, box in enumerate(input_boxes):
            label = font.text_ret(24, labels[i], BLACK)
            label_rect = label.get_rect(center=(box.centerx, box.top - 20))
            screen.blit(label, label_rect)

            # Рамка поля
            color = color_active if i == active_input else color_inactive
            py.draw.rect(screen, color, box, 3)

            # Текст
            display_text = input_texts[i]
            if not input_visible[i]:
                display_text = '*' * len(display_text)
            text_surface = font.text_ret(24, display_text, BLACK)
            screen.blit(text_surface, (box.x + 5, box.y + 10))

            # Курсор
            if i == active_input and cursor_visible:
                cursor_x = box.x + 5 + font.text_ret(24, display_text[:cursor_position[i]], BLACK).get_width()
                cursor_y = box.y + 10
                py.draw.line(screen, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + 30), 2)

        hint = font.text_ret(18, "Enter - подтвердить | Escape - назад", GRAY)
        hint_rect = hint.get_rect(center=(WIDTH//2, 650))
        screen.blit(hint, hint_rect)

        if message:
            msg_surface = font.text_ret(24, message, message_color)
            msg_rect = msg_surface.get_rect(center=(WIDTH//2, 600))
            screen.blit(msg_surface, msg_rect)

        cursor_timer += 1
        if cursor_timer >= 30:
            cursor_visible = not cursor_visible
            cursor_timer = 0

        py.display.flip()
        clock.tick(fps)

    return success


def logout() -> None:
    """
    Выход из аккаунта.
    Удаляет файл сессии, сбрасывает глобальные переменные и возвращает игру на заставку.
    """
    global station_manager, is_saver, next_stage, current_channel
    # Удаляем файл сессии
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception as e:
        print(f"Ошибка удаления сессии: {e}")

    globals.id_player = None
    globals.name_player = None

    station_manager = None   # при следующем входе создастся новый
    is_saver = True
    next_stage = "meow"
    current_channel = None


def parse_color(color_str: str) -> tuple:
    """Преобразует строку вида "(R, G, B)" в кортеж (R, G, B)."""
    if not color_str:
        return (200, 200, 200)
    parts = color_str.strip('()').split(',')
    return tuple(int(p.strip()) for p in parts[:3])


def load_ingredient_colors() -> tuple:
    """
    Загружает цвета ингредиентов из базы данных.
    Возвращает три словаря: milk_colors, espresso_colors, syrup_colors.
    """
    colors_data = db.get_ingredients_color()
    milk = {}
    espresso = {}
    syrup = {}
    for item in colors_data:
        color = parse_color(item['color'])
        if item['type'] == 'milk':
            milk[item['name']] = color
        elif item['type'] == 'espresso':
            espresso[item['name']] = color
        elif item['type'] == 'syrup':
            syrup[item['name']] = color
    return milk, espresso, syrup


# ----- Подключение к базе данных и загрузка цветов ингредиентов -----
db.connect()
milk_colors, espresso_colors, syrup_colors = load_ingredient_colors()


# ----- Основной игровой цикл -----
while True:
    events = py.event.get()
    for event in events:
        if event.type == py.QUIT:
            py.quit()
            sys.exit()
        elif event.type == py.KEYDOWN:
            if event.key == py.K_LALT:
                py.quit()
                sys.exit()
            else:
                if is_saver:
                    is_saver = False   # нажатие любой клавиши прерывает заставку

    if is_saver:
        # Показываем заставку
        saver()
        # Поочерёдное воспроизведение звуков
        if (current_channel is None or not current_channel.get_busy()) and meow_tracks and purr_tracks:
            if next_stage == "meow":
                current_channel = sound_manager.play_sfx("cat/meow")
                if current_channel:
                    next_stage = "purr"
                    print("Играет мяу")
            elif next_stage == "purr":
                current_channel = sound_manager.play_sfx("cat/purring")
                if current_channel:
                    next_stage = "end"
                    print("Играет мурлыканье")
            else:
                is_saver = False
                print("Заставка завершена")
    else:
        # Проверяем сессию и запускаем игру или экран входа
        if check_session():
            if station_manager is None:
                station_manager = StationManager(sound_manager, logout,
                                                 milk_colors, espresso_colors, syrup_colors)
            game(screen, events, station_manager)
        else:
            screen_login()

    py.display.flip()
    clock.tick(fps)