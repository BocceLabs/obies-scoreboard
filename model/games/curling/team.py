# imports
from .score import Score
from .player import Player

class Team:
    def __init__(self, teamName):
        self.teamName = teamName
        self.players = []
        self.score = Score()
        self.prev_spot = None
        self.timer = None

    def change_team_name(self, name):
        self.teamName = str(name)

    def add_player(self, player):
        print(self.players)
        print(type(self.players))
        if type(player) == Player:
            # ensure the player isn't already on the team
            if self.players:
                for p in self.players:
                    if str(p) == str(player):
                        raise ValueError("Duplicate")

            # if we reach this point the player wasn't already detected on the team
            self.players.append(player)
        else:
            raise TypeError

    def remove_player(self, player):
        # todo search through list and remove player
        pass

    def __str__(self):
        return self.teamName