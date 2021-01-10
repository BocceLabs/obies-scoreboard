# imports
import sys
import os

# add the parent directory (absolute, not relative) to the sys.path
# (this makes the games package imports work)
sys.path.append(os.path.abspath(os.pardir))

# PyQt imports
from PyQt5 import QtCore, QtWidgets
from PyQt5 import uic
from PyQt5.QtGui import QImage, QPixmap, QColor
from PyQt5.QtCore import QThread, QTimer
from PyQt5.QtWidgets import QInputDialog

# other imports
import numpy as np
import cv2
import imutils
import argparse

# remote
from model.remotes.ati import ATI

# define some colors (these are in BGR order)
# if you need to add colors, go to Google search engine and search ex: "purble bgr code"
# note that Google displays them in RGB order ;)
GRAY = (150, 150, 150)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)
PURPLE = (128, 0, 128)
TEAL = (179, 196, 98)
PINK = (186, 137, 219)

# MAX BALLS per team
MAX_BALLS_PER_TEAM = 4

class Team:
    def __init__(self, teamName):
        self.players = []
        self.teamName = teamName
        self.teamBallColor = None
        self.teamObieColor = None
        self.ballsIn = 0
        self.ballsThrown = 0
        self.score = None

    def change_team_name(self, name):
        self.teamName = name

    def __str__(self):
        return self.teamName

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        """
        constructor
        """
        super().__init__(*args, **kwargs)

        # construct the argument parser and parse the arguments
        ap = argparse.ArgumentParser()
        ap.add_argument("-g", "--game", default="bocce", help="what game are you playing?")
        ap.add_argument("-v", "--view", required=True, help="which ui do you want to run?")
        args = vars(ap.parse_args())

        # load the ui file which was made with Qt Creator
        if args["game"] == "bocce":
            if args["view"] == "digital":
                uic.loadUi("views/bocce/digital_scoreboard.ui", self)
            elif args["view"] == "traditional":
                uic.loadUi("views/bocce/traditional_scoreboard.ui", self)
        elif args["game"] == "shuffleboard":
            raise NotImplementedError
        elif args["game"] == "axethrowing":
            raise NotImplementedError
        elif args["game"] == "croquet":
            raise NotImplementedError
        elif args["game"] == "curling":
            raise NotImplementedError
        elif args["game"] == "kubb":
            raise NotImplementedError
        elif args["game"] == "shuffleboard":
            raise NotImplementedError
        elif args["game"] == "wiffleball":
            raise NotImplementedError
        else:
            raise NotImplementedError

        # game timer and down/back setting
        self.GAME_MINUTES = 20
        self.DOWN_BACK_ENABLED = None
        self.gameTimer = QTimer()
        self.time_min_left = 20
        self.time_sec_left = 0
        self.time_is_out = False
        self.down_and_back = False
        self.game_time_ui_update()

        # minimal game info
        # todo fix later
        self.homeTeam = Team("Press A + OK then type team name")
        self.homeTeam.teamBallColor = TEAL
        self.homeTeam.teamObieColor = "Teal"
        self.awayTeam = Team("Press B + OK then type team name")
        self.awayTeam.teamBallColor = PINK
        self.awayTeam.teamObieColor = "Pink"

        # score
        self.homeTeam.score = 0
        self.awayTeam.score = 0
        self.frame_count = 0
        self.recent_frame_winner = None

        # set font colors
        # home
        self.set_widget_font_foreground_color(self.label_homelabel, TEAL)
        self.set_widget_font_foreground_color(self.label_hometeam, TEAL)
        self.set_widget_font_foreground_color(self.lcdNumber_homescore, TEAL)
        # away
        self.set_widget_font_foreground_color(self.label_awaylabel, PINK)
        self.set_widget_font_foreground_color(self.label_awayteam, PINK)
        self.set_widget_font_foreground_color(self.lcdNumber_awayscore, PINK)

        # set team names
        self.label_hometeam.setText(str(self.homeTeam))
        self.label_awayteam.setText(str(self.awayTeam))

        # update the top left corner logo to indicating that the pallino needs to be thrown
        qImg = self.load_logo_qImg('views/oddball_graphics/cut_assets/Mark-1C-Yellow.png', 200)
        self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

        # draw the bottom logo
        qImg = self.load_logo_qImg('views/oddball_graphics/oddballsports_logo.png', 800)
        self.draw_rgba_qimg(self.label_bottomadvertisement, qImg)

        # draw home balls
        self.draw_balls(self.homeTeam, ballsIn=0, ballsThrown=0)
        self.draw_balls(self.awayTeam, ballsIn=0, ballsThrown=0)

        # run the ATI remote task (it is threaded with signals)
        self._prevButton_str = None
        self._wait_for_ok = False
        self.waitForRemoteButtonPressSignal()

    def waitForRemoteButtonPressSignal(self):
        # Step 1: implement a QObject with a signal `models.remote.ATI(QObject)`

        # Step 2: Create a QThread object
        self.thread = QThread()

        # Step 3: Create a worker object
        self.worker = ATI()
        self.worker.connect()

        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)

        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.run)
        # finished could be when the power button is pressed
        #self.worker.finished.connect(self.thread.quit)
        #self.worker.finished.connect(self.worker.deleteLater)
        # end finished
        # call a function when there is a new unique ATI remote keypress
        self.worker.newUniqueKeyPress.connect(self.handle_tv_remote_button_press)

        # Step 6: Start the thread
        self.thread.start()

        # Step 7: Final resets
        #nothing in this case

    def handle_tv_remote_button_press(self, button):
        # debug
        #print(button)

        # grab the button string
        button_str = str(button)

        # handle waiting for a "TIME" + "OK" two-button sequence or "STOP" + "OK" two-button sequence
        if button_str != "OK" \
            and (self._prevButton_str == "TIME"
            or self._prevButton_str == "STOP"
            or self._prevButton_str == "A"
            or self._prevButton_str == "B"):

            self._wait_for_ok = False

        # switch case
        if button_str == "VOL_UP":
            self.increment_in(self.homeTeam)
        elif button_str == "VOL_DOWN":
            self.decrement_in(self.homeTeam)
        elif button_str == "CHECK":
            self.increment_out(self.homeTeam)
        elif button_str == "CH_UP":
            self.increment_in(self.awayTeam)
        elif button_str == "CH_DOWN":
            self.decrement_in(self.awayTeam)
        elif button_str == "X":
            self.increment_out(self.awayTeam)
        elif button_str == "ATI":
            self.lock_in_frame_score()
        elif button_str == "TIME":
            self._wait_for_ok = True
        elif button_str == "OK":
            # if we're waiting for ok
            if self._wait_for_ok:
                # handle key press sequence
                if self._prevButton_str == "TIME":
                    self.start_game_timer()
                elif self._prevButton_str == "STOP":
                    self.stop_game_timer()
                elif self._prevButton_str == "A":
                    print("you pressed ok + a")
                    self.show_team_change_popup(self.homeTeam)
                elif self._prevButton_str == "B":
                    self.show_team_change_popup(self.awayTeam)

                # reset the wait for ok boolean
                self._wait_for_ok = False

        elif button_str == "STOP":
            self._wait_for_ok = True
        elif button_str == "A":
            self._wait_for_ok = True
        elif button_str == "B":
            self._wait_for_ok = True
            pass
        elif button_str == "":
            pass
        elif button_str == "":
            pass
        elif button_str == "":
            pass

        # set the previous button
        self._prevButton_str = button_str

        # debug messages:
        # print("\nFrameCount={}, Time={}:{}".format(self.frame_count, str(self.time_min_left).zfill(2), str(self.time_sec_left).zfill(2)))
        # print("Team={}, BallsThrown={}, BallsIn={}".format(self.homeTeam,
        #                                                    self.homeTeam.ballsThrown,
        #                                                    self.homeTeam.ballsIn))
        # print("Team={}, BallsThrown={}, BallsIn={}".format(self.awayTeam,
        #                                                    self.awayTeam.ballsThrown,
        #                                                    self.awayTeam.ballsIn))

    def increment_score(self, team):
        team.score += 1
        self.update_score_widget(team)

    def decrement_score(self, team):
        team.score -= 1
        if team.score < 0: team.score = 0
        self.update_score_widget(team)

    def verify_increment_in_valid(self, team):
        if not self.gameTimer.isActive() or self.down_and_back:
            print("Game is not in progress")
            return False

        # the home team's first ball thrown is never considered "in", therefore, we'll
        # ignore this increment so that the Umpire learns to press the correct button!
        # first throw of the game
        if self.recent_frame_winner is None \
                and (team is self.homeTeam and team.ballsThrown == 0) \
                and self.awayTeam.ballsThrown == 0:
            return False

        # ignore the Umpire's press of the wrong button for the first throw fo the frame
        if team.ballsThrown == 0 \
                and self.other_team(team).ballsThrown == 0:
            return False

        # the away team never throws first
        elif self.recent_frame_winner is None \
                and team is self.awayTeam and team.ballsThrown == 0 \
                and self.other_team(team).ballsThrown == 0:
            return False

        # the team can't be in until the other team throws
        elif team.ballsThrown == 1 and self.other_team(team).ballsThrown == 0:
            return False

        # whoever won the last frame must be the first team to throw
        elif self.recent_frame_winner is not None \
            and (team is self.recent_frame_winner and team.ballsThrown == 0) \
            and self.other_team(team).ballsThrown == 0:
            return True

        # whoever won the last frame must be the first team to throw
        elif self.recent_frame_winner is not None \
                and (team is not self.recent_frame_winner and team.ballsThrown == 0) \
                and self.other_team(team).ballsThrown == 0:
            return False

        # likewise, maybe the home team threw their first ball and this is the first ball
        # thrown by the away team; again, we need to train the umpire to use the correct
        # button
        elif self.recent_frame_winner is not None \
            and (team is self.homeTeam and team.ballsThrown == 1) \
            and self.awayTeam.ballsThrown == 0:
            return False

        return True

    def increment_in(self, team):
        # verify valid keypress for first press of the increment_in button
        if not self.verify_increment_in_valid(team):
            return

        # handles when both teams have each thrown exactly one bocce ball and the home
        # is in and away team is out
        homeSingleBallIn = False
        if team is self.homeTeam and team.ballsThrown == 1 \
            and self.awayTeam.ballsThrown == 0:
            # mark home team as one ball in only AND mark away team as one ball out
            self.increment_out(self.other_team(team), override=True)
            homeSingleBallIn = True

        if team.ballsIn < 4:
            # if only a single ball should be in, don't increment the throw counter
            if homeSingleBallIn:
                pass
            else:
                # mark the next ball as thrown
                if team.ballsThrown < 4:
                    team.ballsThrown += 1

            # mark the next ball as in
            if team.ballsIn < 4:
                team.ballsIn += 1

            # the other team's balls are no longer "in"
            self.other_team(team).ballsIn = 0

            # update the ball indicators
            self.draw_balls(self.homeTeam, self.homeTeam.ballsIn, self.homeTeam.ballsThrown)
            self.draw_balls(self.awayTeam, self.awayTeam.ballsIn, self.awayTeam.ballsThrown)

            # update the top left corner logo to indicate who is in
            qImg = self.load_logo_qImg('views/oddball_graphics/cut_assets/Mark-2C-{}.png'.format(team.teamObieColor), 200)
            self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

    def verify_increment_out_valid(self, team, override=False):
        if override:
            return override

        if not self.gameTimer.isActive() or self.down_and_back:
            print("Game is not in progress")
            return False

        # train the umpire that the first bocce ball of the game thrown can't be the away
        # ball
        # ignore the Umpire's press of the wrong button for the first throw of the game
        if self.recent_frame_winner is None \
            and (team is self.awayTeam and team.ballsThrown == 0) \
            and self.homeTeam.ballsThrown == 0:
            return False

        # the non previously in team can't go first
        elif self.recent_frame_winner is not None and team is not self.recent_frame_winner \
            and team.ballsThrown == 0 and self.other_team(team).ballsThrown == 0:
            return False

        # a team can't increment its balls thrown until the other team has balls
        elif team.ballsThrown == 0 and self.other_team(team).ballsThrown == 1:
            return False

        # a team can't increment its balls thrown until the other team has balls
        elif team.ballsThrown == 1 and self.other_team(team).ballsThrown == 0:
            return False

        # a team can't have two balls thrown before the other team has any balls thrown
        elif team.ballsThrown == 2 and self.other_team(team).ballsThrown == 0:
            team.ballsThrown -= 1
            return False

        return True

    def increment_out(self, team, override=False):
        # verify valid keypress for increment_out
        if not self.verify_increment_out_valid(team, override):
            return

        if team.ballsThrown < MAX_BALLS_PER_TEAM:
            # mark the next ball as thrown
            if team.ballsThrown < MAX_BALLS_PER_TEAM:
                team.ballsThrown += 1

            # update the ball indicators
            self.draw_balls(team, team.ballsIn, team.ballsThrown)

    def decrement_in(self, team):
        if team.ballsIn > 0:
            team.ballsIn -= 1
            self.draw_balls(team, team.ballsIn, team.ballsThrown)

    def lock_in_frame_score(self):
        # if both teams' balls are all thrown, then update the score
        if self.homeTeam.ballsThrown == 4 \
            and self.awayTeam.ballsThrown == 4:
            print("\nBoth teams have thrown 4 bocce balls")
            print("Determining who is in")

            # grab the "in" team
            teamIn = None
            if self.homeTeam.ballsIn > self.awayTeam.ballsIn:
                teamIn = self.homeTeam
            elif self.homeTeam.ballsIn < self.awayTeam.ballsIn:
                teamIn = self.awayTeam
            else:
                return

            # print who is in
            print("{} are in with {} balls".format(teamIn, teamIn.ballsIn))

            # increment the score accordingly
            teamIn.score += teamIn.ballsIn
            self.recent_frame_winner = teamIn
            self.update_score_widget(teamIn)

            # reset balls thrown and balls in for both teams
            self.homeTeam.ballsThrown = 0
            self.homeTeam.ballsIn = 0
            self.awayTeam.ballsThrown = 0
            self.awayTeam.ballsIn = 0
            self.draw_balls(self.homeTeam, self.homeTeam.ballsIn, self.homeTeam.ballsThrown)
            self.draw_balls(self.awayTeam, self.awayTeam.ballsIn, self.awayTeam.ballsThrown)

            # update the top left corner logo to indicating that the pallino needs to be thrown
            qImg = self.load_logo_qImg('views/oddball_graphics/cut_assets/Mark-1C-Yellow.png', 200)
            self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

            # increment the frame count
            self.increment_frame_count()

    def other_team(self, team):
        if team is self.homeTeam:
            team = self.awayTeam
        elif team is self.awayTeam:
            team = self.homeTeam
        return team

    def update_score_widget(self, team):
        widget = None
        if team is self.homeTeam:
            widget = self.lcdNumber_homescore
        elif team is self.awayTeam:
            widget = self.lcdNumber_awayscore
        widget.display(str(team.score))

    def set_widget_font_foreground_color(self, widget, color):
        # create a QColor and swap BGR to RGB
        color = QColor(color[2], color[1], color[0])

        # extract the widget palette
        palette = widget.palette()

        # set the text color and palette
        palette.setColor(palette.WindowText, color)
        widget.setPalette(palette)

    def load_logo_qImg(self, pngPath, width):
        """
        load the Obie logo
        """
        # load the logo and read all channels (including alpha transparency)
        logo = cv2.imread(pngPath, cv2.IMREAD_UNCHANGED)

        # swap color channels for Qt
        logo = cv2.cvtColor(logo, cv2.COLOR_BGRA2RGBA)

        # resize to a known width maintaining aspect ratio
        logo = imutils.resize(logo, width=width)

        # extract the dimensions of the image and set the bytes per line
        height, width, channel = logo.shape
        bytesPerLine = channel * width

        # create a QImage and ensure to use the alpha transparency format
        qImg = QImage(logo.data, width, height, bytesPerLine, QImage.Format_RGBA8888)

        return qImg

    def cv2img_to_qImg(self, image, width):
        # swap color channels for Qt
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)

        # resize to a known width maintaining aspect ratio
        image = imutils.resize(image, width=width)

        # extract the dimensions of the image and set the bytes per line
        height, width, channel = image.shape
        bytesPerLine = channel * width

        # create a QImage and ensure to use the alpha transparency format
        qImg = QImage(image.data, width, height, bytesPerLine, QImage.Format_RGBA8888)

        return qImg

    def draw_rgba_qimg(self, label, qImg):
        # set the logo in the GUI
        label.setPixmap(QPixmap(qImg))
        label.repaint()

    def make_ball(self, color=GRAY):
        # create a white box for the circle to reside in; NOTE: this box has an alpha channel
        image = np.zeros(shape=[200, 200, 4], dtype=np.uint8)
        colorWithAlpha = (color[0], color[1], color[2], 255)

        # extract the dimensions
        (height, width) = image.shape[:2]

        # draw the filled in circle in the box
        center = (int(width/2), int(height/2))
        radius = int(width/2) - 2
        cv2.circle(image, center, radius, colorWithAlpha, -1)

        return image

    def draw_balls(self, team, ballsIn=0, ballsThrown=0):
        # set three flags
        NOT_THROWN = 0
        THROWN = 1
        OBIE = 2

        def determine_flags(ballsThrown, ballsIn):
            ballFlags = []

            if ballsThrown == 0 and ballsIn == 0:
                ballFlags = [NOT_THROWN, NOT_THROWN, NOT_THROWN, NOT_THROWN]

            elif ballsThrown == 1 and ballsIn == 0:
                ballFlags = [THROWN, NOT_THROWN, NOT_THROWN, NOT_THROWN]

            elif ballsThrown == 1 and ballsIn == 1:
                ballFlags = [OBIE, NOT_THROWN, NOT_THROWN, NOT_THROWN]

            elif ballsThrown == 2 and ballsIn == 0:
                ballFlags = [THROWN, THROWN, NOT_THROWN, NOT_THROWN]

            elif ballsThrown == 2 and ballsIn == 1:
                ballFlags = [OBIE, THROWN, NOT_THROWN, NOT_THROWN]

            elif ballsThrown == 2 and ballsIn == 2:
                ballFlags = [OBIE, OBIE, NOT_THROWN, NOT_THROWN]

            elif ballsThrown == 3 and ballsIn == 0:
                ballFlags = [THROWN, THROWN, THROWN, NOT_THROWN]

            elif ballsThrown == 3 and ballsIn == 1:
                ballFlags = [OBIE, THROWN, THROWN, NOT_THROWN]

            elif ballsThrown == 3 and ballsIn == 2:
                ballFlags = [OBIE, OBIE, THROWN, NOT_THROWN]

            elif ballsThrown == 3 and ballsIn == 3:
                ballFlags = [OBIE, OBIE, OBIE, NOT_THROWN]

            elif ballsThrown == 4 and ballsIn == 0:
                ballFlags = [THROWN, THROWN, THROWN, THROWN]

            elif ballsThrown == 4 and ballsIn == 1:
                ballFlags = [OBIE, THROWN, THROWN, THROWN]

            elif ballsThrown == 4 and ballsIn == 2:
                ballFlags = [OBIE, OBIE, THROWN, THROWN]

            elif ballsThrown == 4 and ballsIn == 3:
                ballFlags = [OBIE, OBIE, OBIE, THROWN]

            elif ballsThrown == 4 and ballsIn == 4:
                ballFlags = [OBIE, OBIE, OBIE, OBIE]


            return ballFlags

        # determine the ball indicators
        ballIndicators = ()

        if team is self.homeTeam:
            ballIndicators = (
                self.label_homeballa,
                self.label_homeballb,
                self.label_homeballc,
                self.label_homeballd
            )
        elif team is self.awayTeam:
            ballIndicators = (
                self.label_awayballa,
                self.label_awayballb,
                self.label_awayballc,
                self.label_awayballd
            )
        ballFlags = determine_flags(team.ballsThrown, team.ballsIn)

        # initialize color and whether we should draw obie
        color = None

        # loop over balls
        for (ballIndicator, ballFlag) in zip(ballIndicators, ballFlags):
            # set the ball indicator
            # if we're not drawing Obie, just draw the ball
            if ballFlag == NOT_THROWN:
                color = GRAY
                image = self.make_ball(color)
                qImg = self.cv2img_to_qImg(image, 50)
                self.draw_rgba_qimg(ballIndicator, qImg)

            elif ballFlag == THROWN:
                color = team.teamBallColor
                image = self.make_ball(color)
                qImg = self.cv2img_to_qImg(image, 50)
                self.draw_rgba_qimg(ballIndicator, qImg)

            # otherwise, hurray! let's draw obie!
            elif ballFlag == OBIE:
                qImg = self.load_logo_qImg('views/oddball_graphics/cut_assets/Mark-2C-{}.png'.format(
                    team.teamObieColor), 100)
                self.draw_rgba_qimg(ballIndicator, qImg)



    def time_tick(self):
        """
        this method is called each time a second passes
        :return:
        """
        # subtract a second
        self.time_sec_left -= 1

        # if the seconds < 0, we need to account for minutes
        if self.time_sec_left < 0:
            # subtract a minute
            self.time_min_left -= 1

            # if there are no more minutes
            if self.time_min_left < 0:
                self.time_is_out = True
                self.time_min_left = 0
                self.time_sec_left = 0
                self.draw_down_and_back()

            # otherwise, the seconds are set to 59
            else:
                self.time_sec_left = 59

        # update the timer on the UI
        self.game_time_ui_update()

    def game_time_ui_update(self):
        """
        this method updates the time indicator on the GUI
        :return:
        """
        self.lcdNumber_game_time_remaining_min.display(str(self.time_min_left).zfill(2))
        self.lcdNumber_game_time_remaining_sec.display(str(self.time_sec_left).zfill(2))

    def start_game_timer(self):
        # repaint the down and back area
        if self.down_and_back:
            self.label_downandback.repaint()
            self.down_and_back = False

        # start timer
        self.gameTimer.timeout.connect(self.time_tick)
        self.gameTimer.start(60 * self.GAME_MINUTES)
        self.time_min_left = self.GAME_MINUTES - 1
        self.time_sec_left = 60

        # set the frame count
        self.frame_count = 0
        self.lcdNumber_framenumber.display(str(self.frame_count))

        # clear the down and back top right image
        self.label_downandback.clear()

    def increment_frame_count(self):
        self.frame_count += 1
        self.lcdNumber_framenumber.display(str(self.frame_count))

    def stop_game_timer(self):
        if self.gameTimer.isActive():
            self.gameTimer.stop()

    def draw_down_and_back(self):
        self.down_and_back = True
        qImg = self.load_logo_qImg('views/oddball_graphics/down_and_back.png', 200)
        self.draw_rgba_qimg(self.label_downandback, qImg)

    def set_team_name(self, team, newTeamName):
        if team is self.homeTeam:
            self.homeTeam.change_team_name(newTeamName)
            self.label_hometeam.setText(str(self.homeTeam))
        elif team is self.awayTeam:
            self.awayTeam.change_team_name(newTeamName)
            self.label_awayteam.setText(str(self.awayTeam))

    def show_team_change_popup(self, team):
        if team is self.homeTeam:
            teamText = "HOME"
        elif team is self.awayTeam:
            teamText = "AWAY"

        # pop up a text entry dialog
        newTeamName, ok = QInputDialog.getText(self, "Team Name Change", "Enter new {} team name".format(teamText))

        # if the ok button was pressed, then change the team name
        if ok:
            self.set_team_name(team, newTeamName)


if __name__ == '__main__':
    # initialize the app and window
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(sys.argv)

    # show the window and run the app
    window.show()
    app.exec_()