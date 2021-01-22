class BallFlag:
    NOT_THROWN = "Not Thrown"
    OUT = "Out"
    IN = "In"
    HOT_SHOT = "Hot Shot"
    KISS = "Kiss"
    MEASUREMENT = "Measurement"
    CASINO = "Casino"

    BALL_FLAG_CYCLE = [OUT, IN]

    def __init__(self):
        self.flag_idx = 0
        self.flag = self.NOT_THROWN
        self.ballsIsIn = False
        self.casino = False

    def toggle_in(self, ballIsIn, casino=False):
        self.ballsIsIn = ballIsIn
        self.casino = casino

    def cycle_up(self):
        # incremeent the flag index
        self.flag_idx += 1

        # check if we need to reset it back to 0
        if self.flag_idx >= len(self.BALL_FLAG_CYCLE):
            self.flag_idx = 0

        # return the current value in the cycle
        self.flag = self.BALL_FLAG_CYCLE[self.flag_idx]

    def cycle_down(self):
        # decrement the flag index
        self.flag_idx -= 1

        # check if we need to reset it back to 0
        if self.flag_idx < 0:
            self.flag_idx = len(self.BALL_FLAG_CYCLE) - 1

        # return the current value in the cycle
        self.flag = self.BALL_FLAG_CYCLE[self.flag_idx]

    def set_flag(self, flag):
        self.flag = flag
        self.flag_idx = self.BALL_FLAG_CYCLE.index(self.flag)

    def get_flag(self):
        if self.ballsIsIn:
            self.flag = self.IN
        elif not self.ballsIsIn:
            self.flag = self.OUT
            self.casino = False
        if self.casino:
            self.flag = self.CASINO

        return self.flag