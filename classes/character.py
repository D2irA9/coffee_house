import pygame as py
from typing import List, Tuple, Optional

class Character(py.sprite.Sprite):
    """Класс Персонажей"""
    SPRITE_WIDTH = 16
    SPRITE_HEIGHT = 32
    FRAME_DELAY = 150
    DEFAULT_SPEED = 2

    def __init__(self, scale: int, pos: Tuple[int, int], sprite_path: str, path: Optional[List[Tuple[int, int]]] = None):
        super().__init__()
        self.scale = scale
        self.speed = self.DEFAULT_SPEED
        self.sprite_sheet = py.image.load(sprite_path).convert_alpha()
        self.animations = self._load_animations()
        self.current_animation = 'idle_down'
        self.current_frame = 0
        self.image = self.animations[self.current_animation][self.current_frame]
        self.rect = self.image.get_rect(topleft=pos)
        self.pos = py.math.Vector2(pos)
        self.last_update = 0

        self.path = []
        self.current_path_index = 0
        self.target_pos = None
        self.is_moving = False
        if path:
            self.set_path(path)
        self.path_finished = False

    def set_path(self, new_path: List[Tuple[int, int]]):
        """Установить новый путь"""
        self.path = [py.math.Vector2(p) for p in new_path]
        self.current_path_index = 0
        self.path_finished = False
        if self.path:
            self.target_pos = self.path[0]
            self.is_moving = True
        else:
            self.is_moving = False
            self.target_pos = None

    def _load_animations(self) -> dict:
        animations = {}
        anim_defs = {
            'idle_down': (32, 288, 6),
            'idle_up': (32, 96, 6),
            'idle_left': (32, 192, 6),
            'idle_right': (32, 0, 6),
            'walk_down': (64, 288, 6),
            'walk_up': (64, 96, 6),
            'walk_left': (64, 192, 6),
            'walk_right': (64, 0, 6),
            'sit_left': (160, 96, 6),
            'sit_right': (160, 0, 6),
        }
        for name, (start_y, start_x, count) in anim_defs.items():
            animations[name] = self._load_frames(start_y, start_x, count)
        return animations

    def _load_frames(self, start_y: int, start_x: int, count: int) -> List[py.Surface]:
        frames = []
        for i in range(count):
            x = start_x + i * self.SPRITE_WIDTH
            rect = (x, start_y, self.SPRITE_WIDTH, self.SPRITE_HEIGHT)
            frame = self.sprite_sheet.subsurface(rect)
            scaled = py.transform.scale(frame, (self.SPRITE_WIDTH * self.scale, self.SPRITE_HEIGHT * self.scale))
            frames.append(scaled)
        return frames

    def update(self):
        self._update_animation()
        if self.is_moving and self.target_pos:
            self._update_movement()

    def _update_animation(self):
        now = py.time.get_ticks()
        if now - self.last_update > self.FRAME_DELAY:
            self.current_frame = (self.current_frame + 1) % len(self.animations[self.current_animation])
            self.image = self.animations[self.current_animation][self.current_frame]
            self.last_update = now

    def _update_movement(self):
        direction = self.target_pos - self.pos
        distance = direction.length()
        if distance < self.speed:
            self.pos = self.target_pos
            self._next_target()
        else:
            direction.normalize_ip()
            self.pos += direction * self.speed
            self._update_walking_animation(direction)
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))

    def _next_target(self):
        self.current_path_index += 1
        if self.current_path_index < len(self.path):
            self.target_pos = self.path[self.current_path_index]
        else:
            self.is_moving = False
            self.target_pos = None
            self.path_finished = True
            if 'walk' in self.current_animation:
                self.current_animation = self.current_animation.replace('walk', 'idle')

    def _update_walking_animation(self, direction: py.math.Vector2):
        if abs(direction.x) > abs(direction.y):
            if direction.x > 0:
                self.current_animation = 'walk_right'
            else:
                self.current_animation = 'walk_left'
        else:
            if direction.y > 0:
                self.current_animation = 'walk_down'
            else:
                self.current_animation = 'walk_up'

    def sit_down(self, sit_animation: str = 'sit_left'):
        self.is_moving = False
        self.path = []
        self.target_pos = None
        self.path_finished = False
        if sit_animation in self.animations:
            self.current_animation = sit_animation
            self.current_frame = 0
            self.image = self.animations[self.current_animation][self.current_frame]

    def draw(self, screen: py.Surface):
        screen.blit(self.image, self.rect)

    def is_clicked(self, pos: Tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)

    def is_path_finished(self) -> bool:
        return self.path_finished