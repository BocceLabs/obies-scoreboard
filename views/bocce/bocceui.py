# imports
import sys
import os

# add the parent directory (absolute, not relative) to the sys.path
# (this makes the games package imports work)
sys.path.append(os.path.abspath(os.pardir))

# PyQt imports
from PyQt5 import QtCore, QtWidgets
from PyQt5 import uic, QtGui, QtTest
from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter, QMovie
from PyQt5.QtCore import QThread, QTimer, QRect, Qt, QSize
from PyQt5.QtWidgets import QInputDialog, QWidget, QDialog, QLabel, QMessageBox

# other imports
import numpy as np
import cv2
import imutils
from imutils import paths
import argparse
from playsound import playsound
import os
import random
import pickle
import os.path

# Google sheets stuff
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


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

# INDICATOR AND GRAPHIC SIZES
BALL_INDICATOR_SIZE = 250
TOP_LEFT_LOGO_SIZE = 350
BOTTOM_LOGO_WIDTH = 800
TOP_RIGHT_LOGO_SIZE = 200

# DEFAULT MINUTES
DEFAULT_GAME_MINUTES = 20
DEFAULT_WARMUP_MINUTES = 5

# SOUND FILE TYPES
SOUND_TYPES = (".m4a", ".mp3", ".wav")

# ANIMATION TYPES
ANIMATION_TYPES = (".gif", ".GIF")

def list_sounds(dir, contains=None):
    return list(paths.list_files(dir, validExts=SOUND_TYPES, contains=contains))

def play_random_sound(sound_dir):
    # play a random sound
    sounds = list_sounds(sound_dir)
    if len(sounds) == 0:
        return
    sound_filename = random.choice(sounds)
    playsound(sound_filename, False)

def list_animations(dir, contains=None):
    return list(paths.list_files(dir, validExts=ANIMATION_TYPES, contains=contains))

def sleep(timeout):
    QtTest.QTest.qWait(timeout * 1000)


############################
# Google sheet constants   #
############################
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
# the spreadsheet ID comes from the URL in your browser (after the /d/ and before the next /
SAMPLE_SPREADSHEET_ID = '1FoPvsKECQE-jigz6fM3W8uvwQolrqHgiwRznkcnIeDQ'
SAMPLE_RANGE_NAME = 'teams!A1:A20'

class GSheet:
    def __init__(self):
        pass

    def get_values(self, col_num):
        """Shows basic usage of the Sheets API.
        Prints values from a sample spreadsheet.
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        values = result.get('values', [])

        return values

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

class Animation():
    """Loading screen animation."""
    def __init__(self, gif_path, timeout=8):
        #super(Animation, self).__init__()
        self.timeout=timeout
        self.dlg = QDialog()
        self.dlg.setWindowTitle("animation")
        self.dlg.setWindowModality(False)
        self.dlg.setFixedSize(1500, 1500)
        self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        self.label_animation = QLabel(self.dlg)
        self.movie = QMovie(gif_path)
        self.movie.setScaledSize(QSize(self.dlg.width(), self.dlg.height()))
        self.label_animation.setMovie(self.movie)

    def start(self):
        self.run()

    def run(self):
        self.movie.start()
        self.dlg.show()
        sleep(self.timeout)
        self.quit()

    def quit(self):
        self.movie.stop()
        self.dlg.done(0)


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

        # MainWindow settings
        # set the window title
        self.setWindowTitle("Obie's Scoreboard - {} - {}".format(args["game"], args["view"]))
        # maximize the window
        self.showMaximized()


        # game timer and down/back setting
        self.GAME_MINUTES = DEFAULT_GAME_MINUTES
        self.GAME_WARMUP_MINUTES = DEFAULT_WARMUP_MINUTES
        self.DOWN_BACK_ENABLED = None
        self.gameTimer = QTimer()
        self.gameTimer.setInterval(1000) # milli-seconds in one second
        self.gameTimer.timeout.connect(self.time_tick)
        self.time_min_left = 0
        self.time_sec_left = 0
        self.time_is_out = False
        self.down_and_back = False
        self.game_time_ui_update()
        self.timer_paused = False

        # minimal game info
        # todo fix later
        self.homeTeam = Team("A cycles team names in Google Sheet")
        self.homeTeam.teamBallColor = TEAL
        self.homeTeam.teamObieColor = "Teal"
        self.awayTeam = Team("B cycles team names in Google Sheet")
        self.awayTeam.teamBallColor = PINK
        self.awayTeam.teamObieColor = "Pink"

        # score
        self.homeTeam.score = 0
        self.awayTeam.score = 0
        self.homeTeamCycleScore = 0
        self.awayTeamCycleScore = 0


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
        qImg = self.load_logo_qImg('views/oddball_graphics/cut_assets/Mark-1C-Yellow.png', TOP_LEFT_LOGO_SIZE)
        self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

        # draw the bottom logo
        qImg = self.load_logo_qImg('views/packaworldintegration/long_white.png', BOTTOM_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_bottomadvertisement, qImg)

        # draw home balls
        # self.draw_balls(self.homeTeam)
        # self.draw_balls(self.awayTeam)
        # self.draw_ball_indicator(self.homeTeam)
        # self.draw_ball_indicator(self.awayTeam)

        # run the ATI remote task (it is threaded with signals)
        self._prevButton_str = None
        self._wait_for_ok = False
        self.waitForRemoteButtonPressSignal()

        # load team name data from Google Sheet
        gs = GSheet()
        self.team_name_values = gs.get_values(1)
        self.value_idx = 0


# BEGIN GIF EXAMPLE

    def load_animation(self, gif_path, timeout=8):
        self.animation = Animation(gif_path, timeout)
        self.animation.start()

    def stop_animation(self):
        self.animation.quit()
        self.animation = None

    def closeEvent(self, event) -> None:
        """
        declare the close event to close the created window with the main application
        close
        """
        result = QMessageBox.question(self,
                                            "Confirm Exit...",
                                            "Are you sure you want to exit ?",
                                            QMessageBox.Yes | QMessageBox.No)
        event.ignore()

        if result == QMessageBox.Yes:
            try:
                self.animation.quit()
            except AttributeError:
                pass
            event.accept()
# END GIF EXAMPLE

    def play_random_animation(self, gif_dir):
        animations = list_animations(gif_dir)
        if len(animations)== 0:
            return
        gif_filename = random.choice(animations)
        self.load_animation(gif_path=gif_filename, timeout=5)

    def _stop_animation(self, button_str):
        if self._prevButton_str == button_str:
            self.stop_animation()
            self._prevButton_str = None
            return True
        return False

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

        # debug
        print(button_str)

        # handle waiting for a "TIME" + "OK" two-button sequence or "STOP" + "OK" two-button sequence
        if button_str != "OK" \
            and (self._prevButton_str == "TIME"
            or self._prevButton_str == "STOP"
            or self._prevButton_str == "A"
            or self._prevButton_str == "B"
            or self._prevButton_str == "ROUND_D_DOWN"
            or self._prevButton_str == "ROUND_D_UP"):

            self._wait_for_ok = False

        # switch case

        # Ball indicator controls - TEAM
        if button_str == "VOL_UP":
            self.homeTeam.ballFlag.toggle_in(True)
            self.awayTeam.ballFlag.toggle_in(False)
            self.draw_ball_indicator(self.homeTeam)
            self.draw_ball_indicator(self.awayTeam)
            self.label_logoadvertisement.clear()
            self.label_logoadvertisement.repaint()

        elif button_str == "VOL_DOWN":
            self.homeTeam.ballFlag.toggle_in(False)
            self.awayTeam.ballFlag.toggle_in(True)
            self.draw_ball_indicator(self.homeTeam)
            self.draw_ball_indicator(self.awayTeam)
            self.label_logoadvertisement.clear()
            self.label_logoadvertisement.repaint()

        elif button_str == "CH_UP":
            self.homeTeam.ballFlag.toggle_in(False)
            self.awayTeam.ballFlag.toggle_in(True)
            self.draw_ball_indicator(self.homeTeam)
            self.draw_ball_indicator(self.awayTeam)
            self.label_logoadvertisement.clear()
            self.label_logoadvertisement.repaint()

        elif button_str == "CH_DOWN":
            self.homeTeam.ballFlag.toggle_in(True)
            self.awayTeam.ballFlag.toggle_in(False)
            self.draw_ball_indicator(self.homeTeam)
            self.draw_ball_indicator(self.awayTeam)
            self.label_logoadvertisement.clear()
            self.label_logoadvertisement.repaint()


        # Top left logos - GENERIC (no team)
        elif button_str == "FM":
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/hotshot.png', TOP_LEFT_LOGO_SIZE)
            self.draw_rgba_qimg(self.label_logoadvertisement, qImg)
        elif button_str == "EXPAND":
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/kiss.png', TOP_LEFT_LOGO_SIZE)
            self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

        elif button_str == "HAND":
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/measurement.png', TOP_LEFT_LOGO_SIZE)
            self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

        # cycle frame score - HOME
        elif button_str == "CHECK":
            self.homeTeam.cycle_score()
            # clear other team's temp score
            self.awayTeam.temp_points = 0

            self.update_score_widget(self.homeTeam, showTempPoints=True)
            self.update_score_widget(self.awayTeam, showTempPoints=True)

        # cycle frame score - AWAY
        elif button_str == "X":
            self.awayTeam.cycle_score()
            # clear other team's temp score
            self.homeTeam.temp_points = 0
            # display both team scores
            self.update_score_widget(self.awayTeam, showTempPoints=True)
            self.update_score_widget(self.homeTeam, showTempPoints=True)

        # lock in frame score
        elif button_str == "ATI":
            self.lock_in_frame_score()

        # cancel frame score
        elif button_str == "MUTE":
            self.cancel_previous_frame_score()

        # time
        elif button_str == "TIME":
            self._wait_for_ok = True

        # warmup time
        elif button_str == "INFO":
            self._wait_for_ok = True

        # two key press
        elif button_str == "OK":
            # if we're waiting for ok
            if self._wait_for_ok:
                # handle key press sequence
                if self._prevButton_str == "TIME":
                    self.start_game_timer(self.GAME_MINUTES)
                if self._prevButton_str == "INFO":
                    self.start_game_timer(self.GAME_WARMUP_MINUTES)
                elif self._prevButton_str == "STOP":
                    self.stop_game_timer()

                # old A + OK functionality
                # elif self._prevButton_str == "A":
                #     self.show_team_change_popup(self.homeTeam)
                # elif self._prevButton_str == "B":
                #     self.show_team_change_popup(self.awayTeam)

                # new A + OK functionality
                # elif self._prevButton_str == "A":
                #     self.set_team_name(self.homeTeam, self.team_name_values[self.value_idx])
                #
                # elif self._prevButton_str == "B":
                #     self.set_team_name(self.awayTeam, self.team_name_values[self.value_idx])


                elif self._prevButton_str == "PAUSE":
                    self.timer_paused = True
                elif self._prevButton_str == "PLAY":
                    self.timer_paused = False

                # reset the wait for ok boolean
                self._wait_for_ok = False

        elif button_str == "STOP":
            self._wait_for_ok = True

        elif button_str == "A":
            self.value_idx += 1
            if self.value_idx >= len(self.team_name_values):
                self.value_idx = 0
            self.set_team_name(self.homeTeam, str(self.team_name_values[self.value_idx])[2:-2])

        elif button_str == "B":
            self.value_idx -= 1
            if self.value_idx >= len(self.team_name_values):
                self.value_idx = 0
            self.set_team_name(self.awayTeam, str(self.team_name_values[self.value_idx])[2:-2])


        elif button_str == "PAUSE":
            self._wait_for_ok = True
        elif button_str == "PLAY":
            self._wait_for_ok = True

        # sounds
        elif button_str == "D_UP":
            # play a random sound
            play_random_sound("sounds/too_long")

            # open a random gif
            self.play_random_animation("animations/too_long")

        elif button_str == "D_DOWN":
            # play a random sound
            play_random_sound("sounds/too_short")

            # open a random gif
            self.play_random_animation("animations/too_short")

        elif button_str == "D_LEFT":
            # play a random sound
            play_random_sound("sounds/bad_shot")

            # open a random gif
            self.play_random_animation("animations/bad_shot")

        elif button_str == "D_RIGHT":
            # play a random sound
            play_random_sound("sounds/good_shot")

            # open a random gif
            self.play_random_animation("animations/good_shot")

        elif button_str == "C":
            # ball drawing bottom left and bottom right
            self.homeTeam.ballFlag.toggle_in(True, casino=True)
            self.awayTeam.ballFlag.toggle_in(False)
            self.draw_ball_indicator(self.homeTeam)
            self.draw_ball_indicator(self.awayTeam)

            # play a random sound
            play_random_sound('sounds/casino')

            # open a random gif
            self.play_random_animation("animations/casino")


        elif button_str == "D":
            # ball drawing bottom left and bottom right
            self.homeTeam.ballFlag.toggle_in(False)
            self.awayTeam.ballFlag.toggle_in(True, casino=True)
            self.draw_ball_indicator(self.homeTeam)
            self.draw_ball_indicator(self.awayTeam)

            # play a random sound
            play_random_sound("sounds/casino")

            # open a random gif
            self.play_random_animation("animations/casino")

        elif button_str == "E":
            # play a random sound
            play_random_sound("sounds/shot_clock_warning")

            # open a random gif
            self.play_random_animation("animations/shot_clock_warning")

        # set the previous button
        self._prevButton_str = button_str



    def increment_score(self, team):
        team.score += 1
        self.update_score_widget(team)

    def decrement_score(self, team):
        team.score -= 1
        if team.score < 0: team.score = 0
        self.update_score_widget(team)

    def game_in_progress(self):
        if self.gameTimer.isActive():
            return True
        elif self.down_and_back:
            return True
        print("Game is not in progress")
        return False

    def verify_increment_in_valid(self, team):
        if not self.game_in_progress(): return False

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

        # if Umpire measured and adjusted in balls down then they can't add another in ball
        elif self._prevButton_str == "VOL_DOWN" or self._prevButton_str == "CH_DOWN":
            return False

        # a team's throw could result in more than one ball being in (riochets) without incrementing ball count
        elif self._prevButton_str == "VOL_UP" and team == self.homeTeam and self.homeTeam.ballsIn < self.homeTeam.ballsThrown:
            self.homeTeam.ballsIn += 1
            self.draw_balls(self.homeTeam)
            return False

        # a team's throw could result in more than one ball being in (riochets) without incrementing ball count
        elif self._prevButton_str == "CH_UP" and team == self.awayTeam and self.awayTeam.ballsIn < self.awayTeam.ballsThrown:
            self.awayTeam.ballsIn += 1
            self.draw_balls(self.awayTeam)
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

        # a team can't throw if it is in -- the other team throws until it is in or until
        # it hits its max ball count
        elif team.ballsIn > self.other_team(team).ballsIn and self.other_team(team).ballsThrown == MAX_BALLS_PER_TEAM:
            return True

        # a team can't throw if it is in -- the other team throws until it is in or until
        # it hits its max ball count
        elif team.ballsIn > self.other_team(team).ballsIn and self.other_team(team).ballsThrown < MAX_BALLS_PER_TEAM:
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
            self.draw_balls(self.homeTeam)
            self.draw_balls(self.awayTeam)

            # update the top left corner logo to indicate who is in
            qImg = self.load_logo_qImg('views/oddball_graphics/cut_assets/Mark-2C-{}.png'.format(team.teamObieColor), TOP_LEFT_LOGO_SIZE)
            self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

    def verify_increment_out_valid(self, team, override=False):
        if override:
            return override

        if not self.game_in_progress(): return False

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

        # a team can increment its balls thrown if the other team has balls
        # BUT that automatically means the other team's ball is set to "in"
        elif team.ballsThrown == 0 and self.other_team(team).ballsThrown == 1:
            self.other_team(team).ballsIn = 1
            self.draw_balls(self.other_team(team))
            return True

        # a team can't increment its balls thrown until the other team has balls
        elif team.ballsThrown == 1 and self.other_team(team).ballsThrown == 0:
            return False

        # a team can't have two balls thrown before the other team has any balls thrown
        elif team.ballsThrown == 2 and self.other_team(team).ballsThrown == 0:
            team.ballsThrown -= 1
            return False

        # a team can't throw if it is in -- the other team throws until it is in or until
        # it hits its max ball count
        elif team.ballsIn > self.other_team(team).ballsIn and self.other_team(team).ballsThrown == MAX_BALLS_PER_TEAM:
            return True

        # a team can't throw if it is in -- the other team throws until it is in or until
        # it hits its max ball count
        elif team.ballsIn > self.other_team(team).ballsIn and self.other_team(team).ballsThrown < MAX_BALLS_PER_TEAM:
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
            self.draw_balls(team)

    def decrement_in(self, team):
        if team.ballsIn > 0:
            team.ballsIn -= 1
            self.draw_balls(team)

    def lock_in_frame_score(self):

        self.homeTeam.add_points()
        self.awayTeam.add_points()

        self.update_score_widget(self.homeTeam)
        self.update_score_widget(self.awayTeam)

        # increment the frame count
        self.increment_frame_count()

        # repaint
        self.label_homeballindicator.clear()
        self.label_homeballindicator.repaint()
        self.label_awayballindicator.clear()
        self.label_awayballindicator.repaint()

    def cancel_previous_frame_score(self):
        # clear teams' temp score
        self.homeTeam.temp_points = 0
        self.awayTeam.temp_points = 0

        self.homeTeam.remove_points()
        self.awayTeam.remove_points()

        # decrement the frame count
        self.decrement_frame_count()

        # update score widget
        self.update_score_widget(self.homeTeam, cancelPreviousPoints=True)
        self.update_score_widget(self.awayTeam, cancelPreviousPoints=True)
        print("canceled previous frame points")

        # repaint
        self.label_homeballindicator.clear()
        self.label_homeballindicator.repaint()
        self.label_awayballindicator.clear()
        self.label_awayballindicator.repaint()
        self.label_logoadvertisement.clear()
        self.label_logoadvertisement.repaint()


    def other_team(self, team):
        if team is self.homeTeam:
            team = self.awayTeam
        elif team is self.awayTeam:
            team = self.homeTeam
        return team

    def update_score_widget(self, team, showTempPoints=False, cancelPreviousPoints=False):
        widget = None
        # get the widget
        if team is self.homeTeam:
            widget = self.lcdNumber_homescore
        elif team is self.awayTeam:
            widget = self.lcdNumber_awayscore

        # if points are temporary
        if showTempPoints:
            widget.display(str(team.score + team.temp_points))
            return

        # or if we need to remove points
        if not cancelPreviousPoints:
            # otherwise we'll add points
            # add team points
            team.add_points()

        # display the points
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
        image = np.zeros(shape=[BALL_INDICATOR_SIZE, BALL_INDICATOR_SIZE, 4], dtype=np.uint8)
        colorWithAlpha = (color[0], color[1], color[2], 255)

        # extract the dimensions
        (height, width) = image.shape[:2]

        # draw the filled in circle in the box
        center = (int(width/2), int(height/2))
        radius = int(width/2) - 40
        cv2.circle(image, center, radius, colorWithAlpha, -1)

        return image

    def draw_balls(self, team):
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
                qImg = self.cv2img_to_qImg(image, BALL_INDICATOR_SIZE)
                self.draw_rgba_qimg(ballIndicator, qImg)

            elif ballFlag == THROWN:
                color = team.teamBallColor
                image = self.make_ball(color)
                qImg = self.cv2img_to_qImg(image, BALL_INDICATOR_SIZE)
                self.draw_rgba_qimg(ballIndicator, qImg)

            # otherwise, hurray! let's draw obie!
            elif ballFlag == OBIE:
                qImg = self.load_logo_qImg('views/oddball_graphics/cut_assets/Mark-2C-{}.png'.format(
                    team.teamObieColor), BALL_INDICATOR_SIZE)
                self.draw_rgba_qimg(ballIndicator, qImg)

    def draw_ball_indicator(self, team):
        # initializations
        ballFlag = None
        ballIndicator = None
        color = None
        shortTeamString = None

        # repaint the top left area
        self.label_logoadvertisement.clear()
        self.label_logoadvertisement.repaint()

        # select the team
        if team is self.homeTeam:
            ballFlag = self.homeTeam.ballFlag.get_flag()
            ballIndicator = self.label_homeballindicator
            color = self.homeTeam.teamObieColor
            shortTeamString = "home"

        elif team is self.awayTeam:
            ballFlag = self.awayTeam.ballFlag.get_flag()
            ballIndicator = self.label_awayballindicator
            color = self.awayTeam.teamObieColor
            shortTeamString = "away"


        # handle ball flags
        # the ball isn't thrown
        if ballFlag == BallFlag.NOT_THROWN:
            color = GRAY
            image = self.make_ball(color)
            qImg = self.cv2img_to_qImg(image, BALL_INDICATOR_SIZE)
            self.draw_rgba_qimg(ballIndicator, qImg)

        # the ball is out
        elif ballFlag == BallFlag.OUT:
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/out_{}.png'.format(
                    shortTeamString), BALL_INDICATOR_SIZE)
            self.draw_rgba_qimg(ballIndicator, qImg)

        # the ball is in
        elif ballFlag == BallFlag.IN:
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/in_{}.png'.format(
                    shortTeamString), BALL_INDICATOR_SIZE)
            self.draw_rgba_qimg(ballIndicator, qImg)

        # the ball is in
        elif ballFlag == BallFlag.KISS:
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/kiss.png', BALL_INDICATOR_SIZE)
            self.draw_rgba_qimg(ballIndicator, qImg)

        # terrible shot; you need a hot shot
        elif ballFlag == BallFlag.HOT_SHOT:
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/hotshot.png', BALL_INDICATOR_SIZE)
            self.draw_rgba_qimg(ballIndicator, qImg)

        # need a measurement
        elif ballFlag == BallFlag.MEASUREMENT:
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/measurement.png', BALL_INDICATOR_SIZE)
            self.draw_rgba_qimg(ballIndicator, qImg)

        # you earned yourself a casino
        elif ballFlag == BallFlag.CASINO:
            # draw the team casino and the top left casino
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/casino_{}.png'.format(shortTeamString),
                BALL_INDICATOR_SIZE)
            self.draw_rgba_qimg(ballIndicator, qImg)
            qImg = self.load_logo_qImg(
                'views/oddball_graphics/ball_indicators/casino_{}.png'.format(
                    shortTeamString), TOP_LEFT_LOGO_SIZE)
            self.draw_rgba_qimg(self.label_logoadvertisement , qImg)


        print("handled")

    def time_tick(self):
        """
        this method is called each time a second passes
        :return:
        """
        # subtract a second
        if not self.timer_paused:
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

    def start_game_timer(self, MINUTES):
        # repaint the down and back area
        self.down_and_back = False
        self.label_downandback.repaint()

        # repaints balls
        self.homeTeam.score = 0
        self.awayTeam.score = 0
        self.update_score_widget(self.homeTeam)
        self.update_score_widget(self.awayTeam)

        self.homeTeam.ballsThrown = 0
        self.awayTeam.ballsThrown = 0
        self.homeTeam.ballsIn = 0
        self.awayTeam.ballsIn = 0
        #self.draw_balls(self.homeTeam)
        #self.draw_balls(self.awayTeam)
        self.label_homeballindicator.clear()
        self.label_homeballindicator.repaint()
        self.label_awayballindicator.clear()
        self.label_awayballindicator.repaint()


        # repaint the top left logo to Yello
        # update the top left corner logo to indicate who is in
        # update the top left corner logo to indicating that the pallino needs to be thrown
        qImg = self.load_logo_qImg('views/oddball_graphics/cut_assets/Mark-1C-Yellow.png',
                                   TOP_LEFT_LOGO_SIZE)
        self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

        # start timer
        self.gameTimer.start()
        self.time_min_left = MINUTES - 1
        self.time_sec_left = 60

        # set the frame count
        self.frame_count = 1
        self.lcdNumber_framenumber.display(str(self.frame_count))

        # clear the down and back top right image
        self.label_downandback.clear()

    def increment_frame_count(self):
        self.frame_count += 1
        self.lcdNumber_framenumber.display(str(self.frame_count))

    def decrement_frame_count(self):
        self.frame_count -= 1
        if self.frame_count <= 0:
            self.frame_count = 0
        self.lcdNumber_framenumber.display(str(self.frame_count))

    def stop_game_timer(self):
        if self.gameTimer.isActive():
            self.gameTimer.stop()
            self.time_min_left = 0
            self.time_sec_left = 0
            self.game_time_ui_update()
            self.label_homeballindicator.clear()
            self.label_homeballindicator.repaint()
            self.label_awayballindicator.clear()
            self.label_awayballindicator.repaint()
            self.frame_count = 0
            self.lcdNumber_framenumber.display(str(self.frame_count))

    def draw_down_and_back(self):
        self.down_and_back = True
        qImg = self.load_logo_qImg('views/oddball_graphics/down_and_back.png', TOP_RIGHT_LOGO_SIZE)
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