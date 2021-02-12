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

# bocce game imports
from model.games.bocce.team import Team
from model.games.bocce.ballflag import BallFlag

# tv remote import
from model.remotes.ati import ATI
#from model.remotes.flirc.sparkfun import Sparkfun

# Google sheet interface import
from model.googlesheets.gsheet import GSheet

# color constant imports
from .colors import *

# other imports
import numpy as np
import cv2
import imutils
from imutils import paths
import argparse
from playsound import playsound
import random
import threading

# INDICATOR AND GRAPHIC SIZES
BALL_INDICATOR_SIZE = 200
TOP_LEFT_LOGO_SIZE = 200
BOTTOM_LOGO_WIDTH = 500
TOP_RIGHT_LOGO_SIZE = 150

# DEFAULT MINUTES
DEFAULT_GAME_MINUTES = 20
DEFAULT_WARMUP_MINUTES = 5

# todo move sound and animation convenience functions to a helpers file

# SOUND FILE TYPES
SOUND_TYPES = (".m4a", ".mp3", ".wav")

# ANIMATION TYPES
ANIMATION_TYPES = (".gif", ".GIF")

###### SET ME!!!!!!!!!!!!!!!!!!! ####################
RFID_READER_CONNECTED = False

def list_sounds(dir, contains=None):
    """grabs all sound file paths in a directory"""
    return list(paths.list_files(dir, validExts=SOUND_TYPES, contains=contains))

def play_random_sound(sound_dir):
    """plays a random sound in a directory"""
    # play a random sound
    sounds = list_sounds(sound_dir)
    if len(sounds) == 0:
        return
    sound_filename = random.choice(sounds)
    threading.Thread(target=playsound, args=(sound_filename,)).start()

def list_animations(dir, contains=None):
    """grabs all animations in a directory path"""
    return list(paths.list_files(dir, validExts=ANIMATION_TYPES, contains=contains))

def sleep(timeout):
    """PyQt friendly non-blocking sleep (alternative to `time.sleep()`)"""
    QtTest.QTest.qWait(timeout * 1000)

class Animation():
    """Plays GIF animations nearly fullscreen"""
    # todo grab screen resolution and adjust the window size programmatically

    def __init__(self, gif_path, timeout=8):
        #super(Animation, self).__init__()
        self.timeout=timeout
        self.dlg = QDialog()
        self.dlg.setWindowTitle("animation")
        self.dlg.setWindowModality(False)
        self.dlg.setFixedSize(800, 800)
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

    def __init__(self, ui, clargs, *args, **kwargs):
        """
        constructor
        """
        super().__init__(*args, **kwargs)

        # load the user interface
        uic.loadUi(ui, self)

        # MainWindow settings
        # set the window title
        self.setWindowTitle("Obie's Scoreboard - {} - {}".format(clargs["game"], clargs["view"]))
        # maximize the window
        self.showMaximized()

        # game timer and down/back setting
        self.GAME_MINUTES = DEFAULT_GAME_MINUTES
        self.GAME_WARMUP_MINUTES = DEFAULT_WARMUP_MINUTES
        self.DOWN_BACK_ENABLED = None
        self.gameTimer = QTimer()
        self.gameTimer.setInterval(1000) # milli-seconds in one second
        self.gameTimer.timeout.connect(self.time_tick)
        self.time_min_left = self.GAME_MINUTES
        self.time_sec_left = 0
        self.time_is_out = False
        self.down_and_back = False
        self.game_time_ui_update()
        self.timer_paused = False
        self.clock_edit_mode = False
        self.wait_for_clock_edit_or_start = False

        # minimal game info
        self.homeTeam = Team("TeamA")
        self.homeTeam.teamBallColor = TEAL
        self.homeTeam.teamObieColor = "Teal"
        self.awayTeam = Team("TeamB")
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
        # todo colors should be based on the ball color
        # todo patterned example ball should display next to team name
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
        
        # draw ball indicators
        self.draw_rgba_qimg(self.label_homeballindicator, self.cv2img_to_qImg(self.make_ball(color=(0, 0, 0)), BALL_INDICATOR_SIZE))
        self.draw_rgba_qimg(self.label_awayballindicator, self.cv2img_to_qImg(self.make_ball(color=(0, 0, 0)), BALL_INDICATOR_SIZE))
        
        # draw the bottom logo
        qImg = self.load_logo_qImg('views/packaworldintegration/long_white.png', BOTTOM_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_bottomadvertisement, qImg)

        # run the TV remote receiver task (it is threaded with signals)
        self.enableKeyPressEventHandler = False
        self.add_points_mode = False
        self._prevButton_str = None
        self._prevButton = None
        self._wait_for_ok = False
        self.waitForRemoteButtonPressSignal(clargs["remote"])

        # load team name data from Google Sheet
        self.gs = GSheet()
        self.team_name_values = self.gs.get_values("teams!A:A")
        self.court_and_games = self.gs.get_values("2020-02-11_games!A2:F")
        self.court_and_games_idx = 0
        self.display_game_info_at_bottom_of_screen()
        self.value_idx = 0

        # load graphic instruction to set game
        qImg = self.load_logo_qImg('views/oddball_graphics/select_game.png', TOP_LEFT_LOGO_SIZE)
        self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

        # display the game clock value
        self.lcdNumber_game_time_remaining_min.display(
            str(self.time_min_left).zfill(2))
        self.lcdNumber_game_time_remaining_sec.display(
            str(self.time_sec_left).zfill(2))

    def load_animation(self, gif_path, timeout=8):
        self.animation = Animation(gif_path, timeout)
        self.animation.start()
        self.setFocus()

    def stop_animation(self):
        self.animation.quit()
        self.animation = None
        self.setFocus()

    def closeEvent(self, event) -> None:
        """
        is called when you exit the application
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

    def play_random_animation(self, gif_dir, timeout=5):
        animations = list_animations(gif_dir)
        if len(animations)== 0:
            return
        gif_filename = random.choice(animations)
        self.load_animation(gif_path=gif_filename, timeout=timeout)

    def play_animation(self, path, timeout=5):
        gif_filename = path
        self.load_animation(gif_path=gif_filename, timeout=timeout)

    def _stop_animation(self, button_str):
        if self._prevButton_str == button_str:
            self.stop_animation()
            self._prevButton_str = None
            return True
        return False

    def waitForRemoteButtonPressSignal(self, remote):
        if remote == "ati":
            """uses PyQt QThread, signals, and slots concepts"""
            # Step 1: implement a QObject with a signal `models.remote.ATI(QObject)`
            # Step 2: Create a QThread object
            self.thread = QThread()

            # Step 3: Create a worker object
            if remote.lower() == "ati":
                self.worker = ATI()
            elif remote.lower() == "sparkfun":
                self.worker = Sparkfun()

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
            if remote.lower() == "ati":
                self.worker.newUniqueKeyPress.connect(self.handle_ati_remote_button_press)
            elif remote.lower() == "sparkfun":
                self.worker.newUniqueKeyPress.connect(self.handle_sparkfun_remote_button_press)

            # Step 6: Start the thread
            self.thread.start()

            # Step 7: Final resets
            #nothing in this case

        elif remote == "sparkfun":
            self.enableKeyPressEventHandler = True


    def update_gsheet_score(self):
        # grab game
        ROW = self.court_and_games_idx + 2
        A_SCORE_COLUMN = 4
        B_SCORE_COLUMN = 5

        values = [
            [self.homeTeam.score, self.awayTeam.score]
        ]

        self.gs.set_values("2020-02-11_games!E{}:F{}".format(ROW, ROW), values)

    def display_game_info_at_bottom_of_screen(self):
        try:
            court = self.court_and_games[self.court_and_games_idx][0]
            ttime = self.court_and_games[self.court_and_games_idx][1]
            ta = self.court_and_games[self.court_and_games_idx][2]
            tb = self.court_and_games[self.court_and_games_idx][3]
            self.homeTeam.change_team_name(ta)
            self.awayTeam.change_team_name(tb)
            self.label_hometeam.setText(str(self.homeTeam))
            self.label_awayteam.setText(str(self.awayTeam))
            print("Court: {}, Time: {}, {} vs. {}".format(court, ttime, ta, tb))
            self.label_court_and_game.setText("Court: {}, Time: {}".format(court, ttime)) #, {} vs. {}".format(court, ttime, ta, tb))
        except:
            print("empty cell in list of games")
            return

    def play_entry_announcement(self, RFID_READER_CONNECTED):
        NAME_COLUMN = 0
        RFID_COLUMN = 1
        NICKNAME_COLUMN = 3
        GIF_COLUMN = 4
        AUDIO_COLUMN = 5

        # grab Team A player names
        ta = self.court_and_games[self.court_and_games_idx][2]
        tap1 = ta.split(" & ")[0]
        tap2 = ta.split(" & ")[1]

        # grab Team B player names
        tb = self.court_and_games[self.court_and_games_idx][3]
        tbp1 = tb.split(" & ")[0]
        tbp2 = tb.split(" & ")[1]

        # lookup name in players sheet, and determine audio and gif
        player_info = self.gs.get_values("players!A2:F")

        def grab_RFIDs_required():
            rfids_required = {}
            for player in player_info:
                if player[NAME_COLUMN] == team_player_name:
                    rfids_required[player[RFID_COLUMN]] = False

        def play_team_player_name(team_player_name):
            for player in player_info:
                if player[NAME_COLUMN] == team_player_name:
                    # play sound
                    sound_filename = os.path.join("sounds", "player_announcement", player[AUDIO_COLUMN])
                    threading.Thread(target=playsound, args=(sound_filename,)).start()

                    # play animation
                    if player[GIF_COLUMN] == "random":
                        self.play_random_animation(os.path.join("animations", "player_announcement"), timeout=2.4)
                    else:
                        gif_path = os.path.join("animations", "player_announcement", player[GIF_COLUMN])
                        self.play_animation(gif_path, timeout=2.2)

                    sleep(1.5)




        # go ahead and play player names
        if not RFID_READER_CONNECTED:
            play_team_player_name(tap1)
            play_team_player_name(tap2)
            play_team_player_name(tbp1)
            play_team_player_name(tbp2)

        # otherwise, wait for them to badge in
        elif RFID_READER_CONNECTED:
            # grab rfids required
            rfids_required = grab_RFIDs_required()

            # import the RFID reader
            import RPi.GPIO as GPIO
            from mfrc522 import SimpleMFRC522
            GPIO.setwarnings(False)

            # initialize the reader
            reader = SimpleMFRC522()

            # set the previous id and previous read time
            prevID = None
            prevReadTime = time.time()

            # loop until everyone is present
            while True:
                try:
                    ID, name = reader.read()
                    readTime = time.time()
                    elapsed = readTime - prevReadTime
                    ID = str(ID).zfill(16)
                    name = name.strip()
                    for requiredID, isPresent in rfids_required.items():
                        if ID == requiredID and not isPresent:
                            rfids_required[ID] = True
                    if False in rfids_required.values():
                        continue
                    else:
                        break
                except Exception as e:
                    print(str(e))
                    continue

            # everyone badged in, so play the names!
            play_team_player_name(tap1)
            play_team_player_name(tap2)
            play_team_player_name(tbp1)
            play_team_player_name(tbp2)

    def keyPressEvent(self, event):
        if not self.enableKeyPressEventHandler:
            return

        # play a beep
        threading.Thread(target=playsound, args=("sounds/beep/beep_padded.mp3",)).start()

        if event.key() == QtCore.Qt.Key_A:
            # must be in clock mode to edit teams
            if self.clock_edit_mode:
                if not self.game_in_progress():
                    self.court_and_games_idx += 1
                    if self.court_and_games_idx >= len(self.court_and_games):
                        self.court_and_games_idx = 0

                    try:
                        self.display_game_info_at_bottom_of_screen()
                    except:
                        self.court_and_games_idx = 0
                        print("resetting index to 0")
                        self.display_game_info_at_bottom_of_screen()

            else:
                if self.game_in_progress():
                    if not self.add_points_mode:
                        # home is in
                        self.homeTeam.ballFlag.toggle_in(True)
                        self.awayTeam.ballFlag.toggle_in(False)
                        self.draw_ball_indicator(self.homeTeam)
                        self.draw_ball_indicator(self.awayTeam)
                        self.label_logoadvertisement.clear()
                        self.label_logoadvertisement.repaint()
                    elif self.add_points_mode:
                        # begin cycling points and clear other team's temp score
                        self.homeTeam.cycle_score()
                        self.awayTeam.temp_points = 0
                        # display both team scores
                        self.update_score_widget(self.homeTeam, showTempPoints=True)
                        self.update_score_widget(self.awayTeam, showTempPoints=True)

        elif event.key() == QtCore.Qt.Key_B:
            # must be in clock mode to edit teams
            if self._prevButton == QtCore.Qt.Key_C:
                if not self.game_in_progress():
                    self.court_and_games_idx -= 1
                    if self.court_and_games_idx < 0:
                        self.court_and_games_idx = len(self.court_and_games) - 1
                    try:
                        self.display_game_info_at_bottom_of_screen()
                    except:
                        print("empty cell in list of games")
                        return

            else:
                if self.game_in_progress():
                    if not self.add_points_mode:
                        # home is in
                        self.homeTeam.ballFlag.toggle_in(False)
                        self.awayTeam.ballFlag.toggle_in(True)
                        self.draw_ball_indicator(self.homeTeam)
                        self.draw_ball_indicator(self.awayTeam)
                        self.label_logoadvertisement.clear()
                        self.label_logoadvertisement.repaint()
                    elif self.add_points_mode:
                        # begin cycling points and clear other team's temp score
                        self.awayTeam.cycle_score()
                        self.homeTeam.temp_points = 0
                        # display both team scores
                        self.update_score_widget(self.homeTeam, showTempPoints=True)
                        self.update_score_widget(self.awayTeam, showTempPoints=True)

        elif event.key() == QtCore.Qt.Key_C:
            # wait for PWR
            if not self.clock_edit_mode:
                self.clock_edit_mode = True
                self.add_points_mode = False

                # show the clock graphic
                qImg = self.load_logo_qImg('views/oddball_graphics/clock.png', TOP_LEFT_LOGO_SIZE)
                self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

                # if the game isn't in session, wait for edit or start
                if not self.game_in_progress():
                    self.wait_for_clock_edit_or_start = True

            elif self.clock_edit_mode:
                self.clock_edit_mode = False
                self.wait_for_clock_edit_or_start = False
                self.label_logoadvertisement.clear()
                self.label_logoadvertisement.repaint()


        # pwr key
        elif event.key() == QtCore.Qt.Key_S:
            if self.clock_edit_mode:
                if not self.wait_for_clock_edit_or_start:
                    if self.game_in_progress():
                        # toggle the timer being paused
                        self.timer_paused = not self.timer_paused
                        self.clock_edit_mode = False
                        self.add_points_mode = False
                        if self.timer_paused:
                            qImg = self.load_logo_qImg('views/oddball_graphics/paused.png', TOP_LEFT_LOGO_SIZE)
                            self.draw_rgba_qimg(self.label_logoadvertisement, qImg)
                        elif not self.timer_paused:
                            self.label_logoadvertisement.clear()
                            self.label_logoadvertisement.repaint()


                elif self.wait_for_clock_edit_or_start:
                    # start the game
                    if not self.game_in_progress():
                        self.play_entry_announcement(RFID_READER_CONNECTED)
                        sleep(4)

                        # todo play game start sound
                        sound_filename = os.path.join("sounds", "game_status", "lets_roll.m4a")
                        threading.Thread(target=playsound, args=(sound_filename,)).start()

                        # start the timer
                        self.start_game_timer(self.GAME_MINUTES)

                        # reset modes
                        self.add_points_mode = False
                        self.clock_edit_mode = False
                        self.wait_for_clock_edit_or_start = False

                        # clear the previous key
                        self._prevButton = None
                        return

            # if we're in add points mode, lock in the points
            elif self.add_points_mode:
                    self.lock_in_frame_score()
                    # reset mode
                    self.add_points_mode = False

            # if we're not adding points, activate add points mode
            elif not self.add_points_mode:
                    self.add_points_mode = True

        elif event.key() == QtCore.Qt.Key_Return:
            # sequence: C + Return
            if self._prevButton == QtCore.Qt.Key_C:
                if self.down_and_back and self.game_in_progress():
                    # pause the timer
                    self.timer_paused = True

                    # lookup name in players sheet, and determine audio and gif
                    NAME_COLUMN = 0
                    RFID_COLUMN = 1
                    NICKNAME_COLUMN = 3
                    GIF_COLUMN = 4
                    AUDIO_COLUMN = 5
                    player_info = self.gs.get_values("players!A2:F")

                    def play_team_player_name(team_player_name):
                        for player in player_info:
                            if player[NAME_COLUMN] == team_player_name:
                                # play sound
                                sound_filename = os.path.join("sounds", "player_announcement", player[AUDIO_COLUMN])
                                threading.Thread(target=playsound, args=(sound_filename,)).start()

                                # play animation
                                if player[GIF_COLUMN] == "random":
                                    self.play_random_animation(os.path.join("animations", "player_announcement"), timeout=2.4)
                                else:
                                    gif_path = os.path.join("animations", "player_announcement", player[GIF_COLUMN])
                                    self.play_animation(gif_path, timeout=2.2)

                                sleep(1.5)

                    # play the tie game
                    if self.homeTeam.score == self.awayTeam.score:
                        sound_filename = os.path.join("sounds", "game_status", "finishedinatie.m4a")
                        threading.Thread(target=playsound, args=(sound_filename,)).start()

                    # home team wins
                    elif self.homeTeam.score > self.awayTeam.score:
                        p1 = str(self.homeTeam).split(" & ")[0]
                        p2 = str(self.homeTeam).split(" & ")[1]
                        sound_filename = os.path.join("sounds", "game_status", "winnerwinnerchickendinner.m4a")
                        threading.Thread(target=playsound, args=(sound_filename,)).start()
                        sleep(4)
                        play_team_player_name(p1)
                        play_team_player_name(p2)


                    # away team wins
                    elif self.awayTeam.score > self.homeTeam.score:
                        p1 = str(self.awayTeam).split(" & ")[0]
                        p2 = str(self.awayTeam).split(" & ")[1]
                        sound_filename = os.path.join("sounds", "game_status", "winnerwinnerchickendinner.m4a")
                        threading.Thread(target=playsound, args=(sound_filename,)).start()
                        sleep(.5)
                        play_team_player_name(p1)
                        play_team_player_name(p2)

                    # update g sheet
                    self.update_gsheet_score()

                    # set g sheet icon in top leftr
                    qImg = self.load_logo_qImg('views/oddball_graphics/gsheet_updated.png', TOP_LEFT_LOGO_SIZE)
                    self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

                    # stop the game
                    self.down_and_back = False
                    self.clock_edit_mode = False
                    self.add_points_mode = False
                    self.time_min_left = DEFAULT_GAME_MINUTES
                    self.stop_game_timer()

                    # clear the down and back indicator
                    self.label_downandback.clear()
                    self.label_downandback.repaint()

                    # reset prev button and return
                    self._prevButton = None

                    # wait for 5 seconds
                    sleep(5)

                    # load graphic instruction to set game
                    qImg = self.load_logo_qImg('views/oddball_graphics/select_game.png', TOP_LEFT_LOGO_SIZE)
                    self.draw_rgba_qimg(self.label_logoadvertisement, qImg)
                    return
            else:
                if self.timer_paused:
                    self.stop_game_timer()
                    # draw the stopped graphic
                    qImg = self.load_logo_qImg('views/oddball_graphics/stopped.png', TOP_LEFT_LOGO_SIZE)
                    self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

                    return

                elif not self.timer_paused and self.game_in_progress():
                    # ball drawing bottom left and bottom right
                    self.homeTeam.ballFlag.toggle_in(False)
                    self.awayTeam.ballFlag.toggle_in(True, casino=True)
                    self.draw_ball_indicator(self.homeTeam)
                    self.draw_ball_indicator(self.awayTeam)

                    # play a random sound and gif
                    play_random_sound("sounds/casino")
                    self.play_random_animation("animations/casino")




        elif event.key() == QtCore.Qt.Key_Right:
            # play "good shot"
            # play a random sound and gif
            play_random_sound("sounds/good_shot")
            self.play_random_animation("animations/good_shot")

        elif event.key() == QtCore.Qt.Key_Left:
            # play "bad shot"
            # play a random sound and gif
            play_random_sound("sounds/bad_shot")
            self.play_random_animation("animations/bad_shot")

        elif event.key() == QtCore.Qt.Key_Up:
            # increment minutes in clock edit mode
            if self.clock_edit_mode and not self.game_in_progress():
                self.GAME_MINUTES += 1
                self.time_min_left = self.GAME_MINUTES
                self.lcdNumber_game_time_remaining_min.display(
                    str(self.time_min_left).zfill(2))
                self.lcdNumber_game_time_remaining_sec.display(
                    str(self.time_sec_left).zfill(2))

            # play "too long"
            else:
                # play a random sound and gif
                play_random_sound("sounds/too_long")
                self.play_random_animation("animations/too_long")


        elif event.key() == QtCore.Qt.Key_Down:
            # decrement minutes in clock edit mode
            if self.clock_edit_mode and not self.game_in_progress():
                self.GAME_MINUTES -= 1
                self.time_min_left = self.GAME_MINUTES
                self.lcdNumber_game_time_remaining_min.display(
                    str(self.time_min_left).zfill(2))
                self.lcdNumber_game_time_remaining_sec.display(
                    str(self.time_sec_left).zfill(2))

            # play "too short"
            else:
                # play a random sound and gif
                play_random_sound("sounds/too_short")
                self.play_random_animation("animations/too_short")

        # set the previous button
        self._prevButton = event.key()

    def handle_ati_remote_button_press(self, button):
        # grab the button string
        button_str = str(button)

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
        # todo these button handlers need to be cleaned up

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
                elif self._prevButton_str == "PAUSE":
                    self.timer_paused = True
                elif self._prevButton_str == "PLAY":
                    self.timer_paused = False

                # reset the wait for ok boolean
                self._wait_for_ok = False

        elif button_str == "STOP":
            self._wait_for_ok = True

        elif button_str == "?":
            # grab latest Google sheet data
            self.team_name_values = self.gs.get_values(1)

        elif button_str == "A":
            self.value_idx += 1
            if self.value_idx >= len(self.team_name_values):
                self.value_idx = 0
            try:
                self.set_team_name(self.homeTeam, str(self.team_name_values[self.value_idx])[2:-2])
            except Exception as e:
                print(str(e))
                pass
        elif button_str == "B":
            self.value_idx += 1
            if self.value_idx >= len(self.team_name_values):
                self.value_idx = 0
            try:
                self.set_team_name(self.awayTeam, str(self.team_name_values[self.value_idx])[2:-2])
            except Exception as e:
                print(str(e))
                pass

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
        return False

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
        # todo there is a bug in here that needs to be resolved (previous frame points are
        # todo not removed
        # clear teams' temp score
        self.homeTeam.temp_points = 0
        self.awayTeam.temp_points = 0

        # remove previous points
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
        """convenience function returns the opposite team of what is provided"""
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
        """
        converts a BGRA OpenCV image to qImage RGBA format (A is the alpha transparency
        channel
        """
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
        """
        This simply draws a solid color ball indicator
        """
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

    def time_tick(self):
        """
        this method is called each time a second passes and updates the timer if it is not
        paused
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

        # reset the score at the start of a game
        self.homeTeam.score = 0
        self.awayTeam.score = 0
        self.update_score_widget(self.homeTeam)
        self.update_score_widget(self.awayTeam)

        # clear ball indicators (just in case a game just finished)
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
        self.timer_paused = False
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
