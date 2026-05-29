class Station:
    """ Базовый класс """
    def __init__(self, name):
        self.name = name
        self.is_active = False

    def draw(self, screen):
        pass

    def events(self, events):
        pass

    def activate(self):
        self.is_active = True

    def deactivate(self):
        self.is_active = False



