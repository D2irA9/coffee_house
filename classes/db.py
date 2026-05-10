import pymysql as sql
import hashlib

class DB:
    def __init__(self):
        # Параметры подключения
        self.host = '127.0.0.1'
        self.user = 'root'
        self.password = '1111'
        self.db_name = 'cate'

        self.connection = None
        self.cursor = None

    def connect(self):
        """Подключение к MySQL серверу"""
        try:
            self.connection = sql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.db_name,
                charset='utf8mb4',
                cursorclass=sql.cursors.DictCursor
            )
            self.cursor = self.connection.cursor()
            print("="*40)
            print("Успешное подключение к серверу")
        except sql.Error as e:
            print(f"Ошибка подключения: {e}")

    def add_player(self, name, email, password, coins):
        """Добавление нового игрока"""
        try:
            # Хешируем пароль (для безопасности)
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

            query = """
                INSERT INTO players (name, email, password, id_level, experience, coins)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (name, email, hashed_password, 1, 0, coins)
            self.cursor.execute(query, values)
            self.connection.commit()
            print(f"Игрок {name} успешно добавлен")
            return self.cursor.lastrowid
        except sql.Error as e:
            print(f"Ошибка добавления пользователя: {e}")
            self.connection.rollback()
            return None

    def get_player_id(self, email):
        """
        Возвращает id игрока по email, если существует, иначе None.
        """
        try:
            query = "SELECT id FROM players WHERE email = %s"
            self.cursor.execute(query, (email,))
            result = self.cursor.fetchone()
            if result:
                return result['id']
            else:
                return None
        except Exception as e:
            print(f"Ошибка получения id игрока: {e}")
            return None

    def get_player_by_email(self, email):
        """Возвращает данные пользователя по email или None"""
        try:
            query = "SELECT id, name, password FROM players WHERE email = %s"
            self.cursor.execute(query, (email,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Ошибка получения пользователя: {e}")
            return None

    def check_player(self, id_player):
        """Проверка, если ли такой пользователь"""
        try:
            query = "SELECT p.id FROM players p WHERE p.id = %s"
            self.cursor.execute(query, (id_player,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return []

    def get_coins_player(self, id_player):
        """Возвращает количество монет игрока или None"""
        try:
            query = "SELECT coins FROM players WHERE id = %s"
            self.cursor.execute(query, (id_player,))
            result = self.cursor.fetchone()
            if result:
                return result['coins']
            else:
                return None
        except Exception as e:
            print(f"Ошибка получения монет: {e}")
            return None

    def get_player_level(self, id_player):
        """Получает уровень игрока по id"""
        try:
            query = "SELECT id_level FROM players WHERE id = %s"
            self.cursor.execute(query, (id_player,))
            result = self.cursor.fetchone()
            if result:
                return result['id_level']
            else:
                return None
        except Exception as e:
            print(f"Ошибка получения монет: {e}")
            return None

    def get_ingredients_level(self, id_player):
        """Получение ингредиентов, доступных по уровню игрока"""
        try:
            id_level = self.get_player_level(id_player)
            if id_level is None:
                return []

            query = "SELECT type, name FROM ingredients WHERE level <= %s ORDER BY type, name"
            self.cursor.execute(query, (id_level,))
            result = self.cursor.fetchall()
            return result if result else []
        except Exception as e:
            print(f"Ошибка получения ингредиентов: {e}")
            return []

    def get_ingredients_color(self):
        if self.cursor is None:
            print("Ошибка: курсор не инициализирован. Вызовите connect() сначала.")
            return []
        try:
            query = "SELECT type, name, color FROM ingredients"
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            return result if result else []
        except Exception as e:
            print(f"Ошибка получения ингредиентов: {e}")
            return []

    def close(self):
        """Закрытие соединения"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("Соединение закрыто")
        print("=" * 40)