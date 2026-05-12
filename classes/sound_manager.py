import pygame as py
import random
import os
import json

class SoundManager:
    """Класс звуков и музыки"""
    def __init__(self, music_folder="assets/sounds/music", sfx_folder="assets/sounds/sound"):
        self.music_folder = music_folder
        self.sfx_folder = sfx_folder
        self.music_sounds = {}
        self.sfx_sounds = {}
        self.current_music = None
        self.music_channel = py.mixer.Channel(0) if py.mixer.get_init() else None
        self.music_volume = 1.0
        self.music_enabled = True
        self.sfx_volume = 1.0
        self.sfx_enabled = True
        self.music_playing = False

        self.load_settings()
        self._load_all_sounds()

    def _load_all_sounds(self):
        """Загружает все звуки из папок рекурсивно"""
        self.music_sounds = self._load_sounds_recursive(self.music_folder)
        self.sfx_sounds = self._load_sounds_recursive(self.sfx_folder)

    def _load_sounds_recursive(self, base_folder):
        sounds_dict = {}
        if not os.path.exists(base_folder):
            print(f"Папка {base_folder} не найдена")
            return sounds_dict
        for root, dirs, files in os.walk(base_folder):
            for file in files:
                if file.lower().endswith((".wav", ".ogg", ".mp3")):
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, base_folder)
                    folder = os.path.dirname(rel_path).replace('\\', '/')
                    try:
                        sound = py.mixer.Sound(path)
                        if folder not in sounds_dict:
                            sounds_dict[folder] = []
                        sounds_dict[folder].append(sound)
                    except Exception as e:
                        print(f"Ошибка загрузки {path}: {e}")
        return sounds_dict

    def get_music_tracks(self, subfolder=""):
        """Возвращает список музыки из указанной подпапки"""
        return self.music_sounds.get(subfolder, [])

    def get_sfx_tracks(self, subfolder=""):
        """Возвращает список звуков из указанной подпапки"""
        # print(self.sfx_sounds.get(subfolder, []))
        return self.sfx_sounds.get(subfolder, [])

    def start_music(self, subfolder="background"):
        """Запускает фоновую музыку из указанной подпапки"""
        if self.music_playing:
            return
        tracks = self.get_music_tracks(subfolder)
        if not tracks:
            print(f"Нет музыки в подпапке {subfolder}")
            return
        self.current_music = random.choice(tracks)
        self._play_music()
        self.music_playing = True

    def _play_music(self):
        if not self.current_music or not self.music_channel:
            return
        self.music_channel.play(self.current_music)
        self._apply_music_volume()

    def _apply_music_volume(self):
        if self.music_channel:
            vol = self.music_volume if self.music_enabled else 0.0
            self.music_channel.set_volume(vol)

    def _next_music(self):
        """Выбирает следующий трек"""
        if not self.music_playing:
            return
        tracks = self.get_music_tracks("background")
        if len(tracks) > 1:
            others = [s for s in tracks if s != self.current_music]
            self.current_music = random.choice(others) if others else random.choice(tracks)
        else:
            self.current_music = tracks[0] if tracks else None
        self._play_music()

    def update(self):
        """Вызывать каждый кадр для автоматической смены трека"""
        if self.music_playing and self.music_channel and not self.music_channel.get_busy():
            self._next_music()

    # Управление музыкой
    def set_music_volume(self, value):
        self.music_volume = max(0.0, min(1.0, value))
        self._apply_music_volume()
        self.save_settings()

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        self._apply_music_volume()
        self.save_settings()
        return self.music_enabled

    # Управление звуковыми эффектами
    def play_sfx(self, subfolder=""):
        """Проигрывает случайный звук из указанной подпапки и возвращает канал"""
        if not self.sfx_enabled or not self.sfx_sounds:
            return None
        tracks = self.get_sfx_tracks(subfolder)
        if not tracks:
            all_sounds = []
            for lst in self.sfx_sounds.values():
                all_sounds.extend(lst)
            if not all_sounds:
                return None
            sound = random.choice(all_sounds)
        else:
            sound = random.choice(tracks)
        sound.set_volume(self.sfx_volume)
        return sound.play()

    def set_sfx_volume(self, value):
        self.sfx_volume = max(0.0, min(1.0, value))
        self.save_settings()

    def toggle_sfx(self):
        self.sfx_enabled = not self.sfx_enabled
        self.save_settings()
        return self.sfx_enabled

    # Сохранение/загрузка настроек
    def save_settings(self):
        try:
            with open("settings.json", "w") as f:
                json.dump({
                    "music_volume": self.music_volume,
                    "music_enabled": self.music_enabled,
                    "sfx_volume": self.sfx_volume,
                    "sfx_enabled": self.sfx_enabled
                }, f)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def load_settings(self):
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    data = json.load(f)
                    self.music_volume = data.get("music_volume", 1.0)
                    self.music_enabled = data.get("music_enabled", True)
                    self.sfx_volume = data.get("sfx_volume", 1.0)
                    self.sfx_enabled = data.get("sfx_enabled", True)
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")