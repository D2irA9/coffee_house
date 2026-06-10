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
                INSERT INTO players (name, email, password, level_id, experience, coins)
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
            query = "SELECT level_id FROM players WHERE id = %s"
            self.cursor.execute(query, (id_player,))
            result = self.cursor.fetchone()
            if result:
                return result['level_id']
            else:
                return None
        except Exception as e:
            print(f"Ошибка получения уровня: {e}")
            return None

    def get_ingredients_level(self, id_player):
        """Получение ингредиентов, доступных по уровню игрока"""
        try:
            id_level = self.get_player_level(id_player)
            if id_level is None:
                return []

            query = "SELECT type, name, color FROM ingredients WHERE level_id <= %s ORDER BY type, name"
            self.cursor.execute(query, (id_level,))
            result = self.cursor.fetchall()
            return result if result else []
        except Exception as e:
            print(f"Ошибка получения ингредиентов: {e}")
            return []

    def get_npc_id_by_name(self, npc_name):
        """Возвращает id_npc по имени NPC (из таблицы npc)"""
        try:
            # Проверяем, существует ли таблица npc, если нет – создаём
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS npc (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE
                )
            """)
            self.connection.commit()

            query = "SELECT id FROM npc WHERE name = %s"
            self.cursor.execute(query, (npc_name,))
            result = self.cursor.fetchone()
            if result:
                return result['id']
            else:
                # Если NPC нет, добавляем
                insert_query = "INSERT INTO npc (name) VALUES (%s)"
                self.cursor.execute(insert_query, (npc_name,))
                self.connection.commit()
                return self.cursor.lastrowid
        except Exception as e:
            print(f"Ошибка получения/создания NPC: {e}")
            return None

    def add_statistics(self, id_player, npc_name, order_data, result):
        """
        Сохраняет результат выполнения заказа в таблицу statistics.
        :param id_player: int - id игрока
        :param npc_name: str - имя NPC
        :param order_data: dict - данные о заказе и выполненном напитке
        :param result: int - оценка (0-3)
        """
        try:
            # Получаем id_npc
            id_npc = self.get_npc_id_by_name(npc_name)
            if id_npc is None:
                print("Не удалось определить id_npc")
                return None

            # Преобразуем order_data в JSON-строку
            import json
            order_json = json.dumps(order_data, ensure_ascii=False, indent=2)

            query = """
                INSERT INTO statistics (id_player, id_npc, `order`, result)
                VALUES (%s, %s, %s, %s)
            """
            self.cursor.execute(query, (id_player, id_npc, order_json, result))
            self.connection.commit()
            stat_id = self.cursor.lastrowid
            print(f"Статистика сохранена (ID: {stat_id})")
            return stat_id
        except Exception as e:
            print(f"Ошибка сохранения статистики: {e}")
            self.connection.rollback()
            return None

    def get_or_create_nps_id(self, nps_name):
        """Получение ID NPS по имени, если нет - создаёт"""
        try:
            # Пробуем найти существующего NPS
            query = "SELECT id FROM nps WHERE name = %s"
            self.cursor.execute(query, (nps_name,))
            result = self.cursor.fetchone()

            if result:
                return result['id']

            # Создаём нового NPS
            query_insert = "INSERT INTO nps (name) VALUES (%s)"
            self.cursor.execute(query_insert, (nps_name,))
            self.connection.commit()

            print(f"Создан новый NPS: {nps_name} (ID: {self.cursor.lastrowid})")
            return self.cursor.lastrowid

        except Exception as e:
            print(f"Ошибка получения/создания NPS: {e}")
            return None

    def get_nps_id(self, nps_name):
        """Получение ID NPS по имени"""
        try:
            query = "SELECT id FROM nps WHERE name = %s"
            self.cursor.execute(query, (nps_name,))
            result = self.cursor.fetchone()
            if result:
                return result['id']
            else:
                # Если NPS не найден, добавляем его
                query_insert = "INSERT INTO nps (name) VALUES (%s)"
                self.cursor.execute(query_insert, (nps_name,))
                self.connection.commit()
                return self.cursor.lastrowid
        except Exception as e:
            print(f"Ошибка получения ID NPS: {e}")
            return 1  # возвращаем ID по умолчанию

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