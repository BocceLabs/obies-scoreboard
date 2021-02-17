# imports
from .ballflag import BallFlag

# MAX BALLS per team
# todo should be calculated depending on how many players are added to the team
# todo 1 player = 2 balls
# todo 2 players = 4 balls
# todo 4 players = 4 balls
MAX_BALLS_PER_TEAM = 4

class Team:
    def __init__(self, teamName):
        self.players = []
        self.teamName = teamName
        self.teamBallColor = None
        self.teamObieColor = None
        self.ballsIn = 0
        self.ballIsIn = False
        self.ballsThrown = 0
        self.score = 0
        self.ballFlag = BallFlag()
        self.recent_points_added = 0
        self.temp_points = 0

    def change_team_name(self, name):
        self.teamName = name

    def cycle_score(self):
        self.temp_points += 1
        if self.temp_points > MAX_BALLS_PER_TEAM:
            self.temp_points = 0

    def add_points(self):
        self.score += self.temp_points
        self.recent_points_added = self.temp_points
        self.temp_points = 0

    def remove_points(self):
        self.score -= self.recent_points_added
        self.recent_points_added = 0
        self.temp_points = 0

    def __str__(self):
        return self.teamName