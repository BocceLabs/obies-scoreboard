# imports

class Player:
    def __init__(self, name, skip=False):
        self.name = name
        self.skip = skip

    def __str__(self):
        if self.skip:
            return self.name + " (skip)"
        else:
            return self.name