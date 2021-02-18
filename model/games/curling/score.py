# imports

class End:
    def __init__(self, end_num, hammer=False):
        self.hammer = hammer
        self.end_num = end_num
        self.temp_points = 0
        self.points = None
        self.locked = False

    def cycle_points(self):
        self.locked = False
        # increment, but cycle back to 0 at 8 stones
        if self.temp_points >= 0 and self.temp_points < 8:
            self.temp_points += 1
            return
        else:
            self.temp_points = 0
            return

    def lock_points(self):
        self.points = self.temp_points
        self.locked = True


class Score:
    def __init__(self, hammer=False):

        # todo maybe implement this as a stack
        self.ends = (
            None,
            End(1, hammer),
            End(2, False),
            End(3, False),
            End(4, False),
            End(5, False),
            End(6, False),
            End(7, False),
            End(8, False),
            End(9, False),
            End(10, False),
        )
        self.score = None
        self.current_end = 1

    def update_total_score(self):
        total_points = 0
        for end in self.ends:
            if end.points is None:
                continue
            total_points += end.points

        self.score = total_points
        return self.score

    def update_temp_score(self):
        total_points = self.update_total_score()

        for end in self.ends:
            if end.temp_points is None:
                continue
            total_points += end.temp_points

        return total_points

    def score_through_ends(self, end_num):
        score = 0
        for end in self.ends:
            if end.end_num <= end_num:
                score += end.points
        return score

    def cycle_end_points(self, end_num):
        self.ends[end_num].cycle_points()

    def remove_points(self):
        # todo implement remove points
        pass

    def set_hammer(self, end_num):
        for end in self.ends:
            # todo
            if self.ends[end_num].end_num == end_num:
                self.ends[end_num].hammer = True
            else:
                self.ends[end_num].hammer = False