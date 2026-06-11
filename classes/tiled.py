import pygame as py
from pytmx import load_pygame

class Tile(py.sprite.Sprite):
    """Класс плиток"""
    def __init__(self, pos, surf, groups, scale, tile_size):
        super().__init__(groups)
        self.tile_size = tile_size
        self.image = py.transform.scale(surf, (int(surf.get_width() * scale), int(surf.get_height() * scale)))
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect

class Map:
    """Класс карты"""
    def __init__(self, tmx_path, tile_size, scale=1):
        self.tile_size = tile_size
        self.scale = scale
        self.layers = []
        self.layer_names = []
        self.tmx_path = tmx_path
    def load_map(self):
        tmx_map = load_pygame(self.tmx_path)
        for layer in tmx_map.visible_layers:
            group = py.sprite.Group()
            layer_name = layer.name
            if hasattr(layer, 'data'):
                for x, y, surf in layer.tiles():
                    if surf:
                        pos = (x * self.tile_size * self.scale, y * self.tile_size * self.scale)
                        Tile(pos, surf, group, self.scale, self.tile_size)
            else:
                for obj in layer:
                    if obj.image:
                        pos = (obj.x * self.scale, obj.y * self.scale)
                        Tile(pos, obj.image, group, self.scale, self.tile_size)
            self.layers.append(group)
            self.layer_names.append(layer_name)
    def draw_layer(self, screen, layer_index):
        if 0 <= layer_index < len(self.layers):
            for tile in self.layers[layer_index]:
                screen.blit(tile.image, (tile.rect.x, tile.rect.y))
    def draw_all(self, screen):
        for layer in self.layers:
            for tile in layer:
                screen.blit(tile.image, (tile.rect.x, tile.rect.y))
    def draw_between(self, screen, split_index):
        for i in range(split_index):
            self.draw_layer(screen, i)