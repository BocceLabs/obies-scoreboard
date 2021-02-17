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
from model.games.curling.team import Team

# remote
from model.remotes.ati import ATI

# color constant imports
from .colors import *

# other imports
import numpy as np
import cv2
import imutils
from imutils import paths
import argparse
from playsound import playsound
from tinytag import TinyTag
import random
import threading
from collections import deque
import time

# logging
import logging
logging.basicConfig(level=logging.INFO)

# INDICATOR AND GRAPHIC SIZES
TOP_LEFT_LOGO_WIDTH = 100
TOP_CENTER_LOGO_WIDTH = 800
TOP_RIGHT_LOGO_WIDTH = 100
BOTTOM_LEFT_LOGO_WIDTH = 300
BOTTOM_CENTER_LOGO_WIDTH = 800
BOTTOM_RIGHT_LOGO_WIDTH = 300

# DEFAULT MINUTES
DEFAULT_GAME_MINUTES = 20
DEFAULT_WARMUP_MINUTES = 5

# BUTTON HISTORY
BUTTON_HISTORY_LENGTH = 20

# todo move sound and animation convenience functions to a helpers file

# MEDIA for ABC
MEDIA_DIR = os.path.join("..", "media-abc")

# SOUND FILE TYPES
SOUND_TYPES = (".m4a", ".mp3", ".wav", ".WAV")

# ANIMATION TYPES
ANIMATION_TYPES = (".gif", ".GIF")

###### SET ME!!!!!!!!!!!!!!!!!!! ####################
RFID_READER_CONNECTED = False
#####################################################

def soundfile_duration(path):
    tag = TinyTag.get(path)
    seconds = tag.duration
    return seconds


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


        # TOP LOGOS
        # draw the top left logo
        qImg = self.load_logo_qImg('views/oddball_graphics/cut_assets/Mark-2C-Pink.png',
                                   TOP_LEFT_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_sponsor_top_left, qImg)

        # draw the top center logo
        self.label_sponsor_top_center.setText("Leelanau Curling Club")

        # draw the top right logo
        qImg = self.load_logo_qImg('views/curling/graphics/LCC_Final_LOGO_small-1.png',
                                   TOP_RIGHT_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_sponsor_top_right, qImg)

        # BOTTOM LOGOS
        # draw the bottom left logo
        # qImg = self.load_logo_qImg('views/curling/long_white.png',
        #                            BOTTOM_LEFT_LOGO_WIDTH)
        # self.draw_rgba_qimg(self.label_sponsor_bottom_left, qImg)

        # draw the bottom center logo
        qImg = self.load_logo_qImg('views/oddball_graphics/ODDBALLSPORTS.TV.png',
                                   BOTTOM_CENTER_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_sponsor_bottom_center, qImg)

        # draw the bottom right logo
        # qImg = self.load_logo_qImg('views/curling/long_white.png',
        #                            BOTTOM_RIGHT_LOGO_WIDTH)
        # self.draw_rgba_qimg(self.label_sponsor_bottom_right, qImg)

        self.teamA = Team(teamName="tbd")
        self.teamB = Team(teamName="tbd")
        self.team_edit_mode = False

        # place the end card in the points place
        self.end_num = 0 # ends start at 1
        self.teamA_points_place_labels = [
            None, # not used
            self.label_teamA_points1,
            self.label_teamA_points2,
            self.label_teamA_points3,
            self.label_teamA_points4,
            self.label_teamA_points5,
            self.label_teamA_points6,
            self.label_teamA_points7,
            self.label_teamA_points8,
            self.label_teamA_points9,
            self.label_teamA_points10,
            self.label_teamA_points11,
            self.label_teamA_points12,
            self.label_teamA_points13,
            self.label_teamA_points14,
            self.label_teamA_points15
        ]
        self.teamB_points_place_labels = [
            None, # not used
            self.label_teamB_points1,
            self.label_teamB_points2,
            self.label_teamB_points3,
            self.label_teamB_points4,
            self.label_teamB_points5,
            self.label_teamB_points6,
            self.label_teamB_points7,
            self.label_teamB_points8,
            self.label_teamB_points9,
            self.label_teamB_points10,
            self.label_teamB_points11,
            self.label_teamB_points12,
            self.label_teamB_points13,
            self.label_teamB_points14,
            self.label_teamB_points15
        ]
        self.prev_label = self.label_teamA_points1

        # cards map to a label
        self.teamA_end_cards = {
            0: None, # not used
            1: None,
            2: None,
            3: None,
            4: None,
            5: None,
            6: None,
            7: None,
            8: None,
            9: None,
            10: None,
            11: None,
            12: None,
            13: None,
            14: None,
            15: None
        }
        self.teamB_end_cards = {
            0: None,
            1: None,
            2: None,
            3: None,
            4: None,
            5: None,
            6: None,
            7: None,
            8: None,
            9: None,
            10: None,
            11: None,
            12: None,
            13: None,
            14: None,
            15: None
        }


        # initialize points places to empty
        for point_placeA, point_placeB in zip(self.teamA_points_place_labels, self.teamB_points_place_labels):
            if point_placeA is not None:
                point_placeA.setText("")
            if point_placeB is not None:
                point_placeB.setText("")


        self.game_in_progress = False

        # game timer and down/back setting
        # self.GAME_MINUTES = DEFAULT_GAME_MINUTES
        # self.GAME_WARMUP_MINUTES = DEFAULT_WARMUP_MINUTES


        # TV REMOTE STATUS VARS
        # run the TV remote receiver task (it is threaded with signals)
        self.enableKeyPressEventHandler = False
        self.add_points_mode = False
        self._prevButton_str = None
        self._prevButton = None
        self._wait_for_ok = False
        self.buttonHistory = deque(maxlen=BUTTON_HISTORY_LENGTH)
        self.waitForRemoteButtonPressSignal(clargs["remote"])


        # set the window focus
        self.setFocus()

    def initialize_team(self, team, teamName, players=None):
        team.change_team_name(teamName)
        if players is None:
            team.players = None
        else:
            for player in players:
                team.add_player(player)



        return team



    def load_animation(self, gif_path, timeout=8):
        logging.info("loading animation")
        self.animation = Animation(gif_path, timeout)
        self.animation.start()
        logging.info("animation started")
        self.setFocus()
        logging.info("window focus set back to main window")


    def stop_animation(self):
        logging.info("stopping animation")
        self.animation.quit()
        self.animation = None
        logging.info("animation stopped and set to None")
        self.setFocus()
        logging.info("window focus set back to main window")

    def closeEvent(self, event) -> None:
        logging.info("close window pressed")
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
        logging.info("window closed")
        logging.info("most recent {} buttons = {}".format(str(len(self.buttonHistory)), str(self.buttonHistory)))

    def play_random_animation(self, gif_dir, timeout=5):
        logging.info("playing random animation")
        animations = list_animations(gif_dir)
        if len(animations)== 0:
            return
        gif_filename = random.choice(animations)
        self.load_animation(gif_path=gif_filename, timeout=timeout)

    def play_animation(self, path, timeout=5):
        logging.info("playing animation located at {}".format(str(path)))
        gif_filename = path
        self.load_animation(gif_path=gif_filename, timeout=timeout)

    def _stop_animation(self, button):
        if self.animation is not None:
            if self._prevButton_str == button or self._prevButton == button:
                logging.info("key was pressed twice, so stopping the animation")
                self.stop_animation()
                self._prevButton_str = None
                self._prevButton = None


    def waitForRemoteButtonPressSignal(self, remote):
        if remote.lower() == "ati":
            logging.info("using ATI remote so starting a QThread worker to listen")
            """uses PyQt QThread, signals, and slots concepts"""
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
            self.worker.newUniqueKeyPress.connect(self.handle_ati_remote_button_press)

            # Step 6: Start the thread
            self.thread.start()

            # Step 7: Final resets
            #nothing in this case

        elif remote == "sparkfun":
            logging.info("using Sparkfun remote")
            self.enableKeyPressEventHandler = True

    def update_gsheet_score(self):
        # grab game
        ROW = self.court_and_games_idx + 2
        A_SCORE_COLUMN = 4
        B_SCORE_COLUMN = 5

        values = [
            [self.homeTeam.score, self.awayTeam.score]
        ]

        self.gs.set_values("2020-02-12_games!E{}:F{}".format(ROW, ROW), values)

    def display_game_info_at_bottom_of_screen(self):
        try:
            self.court_and_games = self.gs.get_values("2020-02-12_games!A14:F19")
            # set g sheet icon in top leftr
            qImg = self.load_logo_qImg('views/oddball_graphics/cloud.png',
                                       TOP_LEFT_LOGO_WIDTH)
            self.draw_rgba_qimg(self.label_logoadvertisement, qImg)
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

        TEAM_A_COLUMN = 2
        TEAM_B_COLUMN = 3

        # grab Team A player names
        ta = self.court_and_games[self.court_and_games_idx][TEAM_A_COLUMN]
        print(ta)
        tap1 = ta.split(" & ")[0]
        tap2 = ta.split(" & ")[1]

        # grab Team B player names
        tb = self.court_and_games[self.court_and_games_idx][TEAM_B_COLUMN]
        tbp1 = tb.split(" & ")[0]
        tbp2 = tb.split(" & ")[1]

        # lookup name in players sheet, and determine audio and gif
        player_info = self.gs.get_values("players!A2:F")

        def grab_RFIDs_required(team_player_name):
            rfids_required = {}
            for player in player_info:
                if player[NAME_COLUMN] == team_player_name:
                    rfids_required[player[RFID_COLUMN]] = False
            return rfids_required

        def play_team_player_name(team_player_name):
            for player in player_info:
                if player[NAME_COLUMN] == team_player_name:
                    # play sound
                    seconds = None
                    try:
                        if player[AUDIO_COLUMN] == "random":
                            logging.info("playing random game announcement")
                            sound_filepath = os.path.join(MEDIA_DIR, "announcement_game", "random")
                            seconds = soundfile_duration(sound_filepath)
                            play_random_sound(sound_filepath)
                        else:
                            logging.info("playing {} game announcement".format(player[AUDIO_COLUMN]))
                            sound_filepath = os.path.join(MEDIA_DIR, "announcement_game", "lastname_firstname", player[AUDIO_COLUMN])
                            seconds = soundfile_duration(sound_filepath)
                            threading.Thread(target=playsound, args=(sound_filepath,)).start()
                    except:
                        logging.WARNING("couldn't find sound media file")

                    # play animation
                    try:
                        if seconds is not None:
                            timeout = seconds
                        else:
                            timeout = 3
                        if player[GIF_COLUMN] == "random":
                            logging.info("playing random game announcement gif")
                            self.play_random_animation(os.path.join(MEDIA_DIR, "announcement_game", "random"), timeout=timeout)
                        else:
                            logging.info("playing {} game announcement gif".format(player[GIF_COLUMN]))
                            gif_path = os.path.join(MEDIA_DIR, "announcement_game", "lastname_firstname", player[GIF_COLUMN])
                            self.play_animation(gif_path, timeout=3)
                    except:
                        logging.WARNING("couldn't find gif media file")

                    # wait N seconds before playing the next sound
                    sleep(2.3)




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




        # # place the card on the board
        # if self.end_num == 0 or self.end_num == 1:
        #     prev_total_score = 0
        # else:
        #     prev_total_score = team.score.score_through_ends(self.end_num-1)
        #
        # score_spot = prev_total_score + team.score.ends[self.end_num].points
        #
        # if score_spot != 0:
        #     label[score_spot - 1].setText(str(self.end_num))
        #
        # # clear the previous spot on the board
        # if self.prev_spot is not None and not self.prev_spot < 0:
        #     label[self.prev_spot].setText(str(""))
        #
        # # keep the prev spot for next time
        # prev_spot = score_spot - 1

    # KEYPRESSES ##################################################################
    def handle_key_PWR(self):
        if not self.game_in_progress:
            # play game start sound
            sound_filename = os.path.join("sounds", "game_status",
                                          "lets_roll.m4a")
            threading.Thread(target=playsound, args=(sound_filename,)).start()

            # clear modes
            self.add_points_mode = False
            self.clock_edit_mode = False

            self.label_sponsor_bottom_left.clear()
            self.label_sponsor_bottom_left.repaint()
            self.team_edit_mode = False

            # indicate game is in progress
            self.game_in_progress = True

            # start game on end num 1
            self.end_num = 1

            # clear the previous key
            self._prevButton = None
            return

        # # if we're in add points mode, lock in the points
        elif self.game_in_progress:
            if self.add_points_mode:
                self.lock_in_end_score(self.teamA)
                self.lock_in_end_score(self.teamB)
                # reset mode
                self.add_points_mode = False
                self.label_sponsor_bottom_left.clear()
                self.label_sponsor_bottom_left.repaint()

            # if we're not adding points, activate add points mode
            elif not self.add_points_mode:
                self.add_points_mode = True
                # show the team graphic
                qImg = self.load_logo_qImg('views/oddball_graphics/numbers.png',
                                           BOTTOM_LEFT_LOGO_WIDTH)
                self.draw_rgba_qimg(self.label_sponsor_bottom_left, qImg)

    def handle_key_A(self):
        # must be in clock mode to edit teams
        if not self.game_in_progress:
            if self.team_edit_mode:
                self.show_team_change_popup(self.teamA)

        else:
            if not self.add_points_mode:
                pass
            elif self.add_points_mode:
                self.teamA.score.cycle_end_points(self.end_num)
                try:
                    self.teamB.score.ends[self.end_num].temp_points = 0
                    logging.log(logging.INFO, "{} end {} temp points {}".format(str(self.teamA), self.end_num, self.teamA.score.ends[self.end_num].temp_points))

                    # determine which points place the end card needs to go in



                    self.teamA_end_cards[self.end_num] = self.teamA_points_place_labels[self.teamA.score.ends[self.end_num].temp_points]

                    print(type(self.teamA_end_cards[self.end_num]))
                    self.teamA_end_cards[self.end_num].setText(str(self.end_num))
                    self.prev_label.setText("")
                except Exception as e:
                    logging.log(logging.WARNING, "EXCEPTION {}".format(str(e)))
                finally:
                    #self.prev_label.setText("")
                    self.prev_label = self.teamA_end_cards[self.end_num]
                    logging.log(logging.INFO, "finally clause ran")



    def handle_key_B(self):
        print("B")
        # must be in clock mode to edit teams
        if not self.game_in_progress:
            if self.team_edit_mode:
                self.show_team_change_popup(self.teamB)

        else:
            if not self.add_points_mode:
                pass
            elif self.add_points_mode:
                self.teamB.score.cycle_end_points(self.end_num)
                try:
                    self.teamA.score.ends[self.end_num].temp_points = 0
                    logging.log(logging.INFO, "{} end {} temp points {}".format(str(self.teamB), self.end_num, self.teamB.score.ends[self.end_num].temp_points))

                    # determine which points place the end card needs to go in



                    self.teamB_end_cards[self.end_num] = self.teamB_points_place_labels[self.teamB.score.ends[self.end_num].temp_points]
                    print(type(self.teamB_end_cards[self.end_num]))
                    self.teamB_end_cards[self.end_num].setText(str(self.end_num))
                    print("here")
                    self.prev_label.setText("")
                except Exception as e:
                    logging.log(logging.WARNING, "EXCEPTION {}".format(str(e)))
                finally:
                    #self.prev_label.setText("")
                    self.prev_label = self.teamB_end_cards[self.end_num]
                    logging.log(logging.INFO, "finally clause ran")

    def handle_key_C(self):
        if not self.game_in_progress:
            if not self.team_edit_mode:
                self.team_edit_mode = True
                self.add_points_mode = False

                # show the team graphic
                qImg = self.load_logo_qImg('views/oddball_graphics/team.png',
                                           BOTTOM_LEFT_LOGO_WIDTH)
                self.draw_rgba_qimg(self.label_sponsor_bottom_left, qImg)
                # press a or b for team popup
            elif self.team_edit_mode:
                self.label_sponsor_bottom_left.clear()
                self.label_sponsor_bottom_left.repaint()
                self.team_edit_mode = False

    def handle_key_RETURN(self):
        # sequence: C + Return
        if self.clock_edit_mode and self._prevButton == QtCore.Qt.Key_C:
            if not self.game_in_progress():
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
                            sound_filename = os.path.join("sounds", "player_announcement",
                                                          player[AUDIO_COLUMN])
                            threading.Thread(target=playsound,
                                             args=(sound_filename,)).start()

                            # play animation
                            if player[GIF_COLUMN] == "random":
                                self.play_random_animation(
                                    os.path.join("animations", "player_announcement"),
                                    timeout=2.4)
                            else:
                                gif_path = os.path.join("animations",
                                                        "player_announcement",
                                                        player[GIF_COLUMN])
                                self.play_animation(gif_path, timeout=2.2)

                            sleep(1.5)

                # play the tie game
                if self.homeTeam.score == self.awayTeam.score:
                    sound_filename = os.path.join("sounds", "game_status",
                                                  "finishedinatie.m4a")
                    threading.Thread(target=playsound, args=(sound_filename,)).start()

                # home team wins
                elif self.homeTeam.score > self.awayTeam.score:
                    p1 = str(self.homeTeam).split(" & ")[0]
                    p2 = str(self.homeTeam).split(" & ")[1]
                    sound_filename = os.path.join("sounds", "game_status",
                                                  "winnerwinnerchickendinner.m4a")
                    threading.Thread(target=playsound, args=(sound_filename,)).start()
                    sleep(4)
                    play_team_player_name(p1)
                    play_team_player_name(p2)


                # away team wins
                elif self.awayTeam.score > self.homeTeam.score:
                    p1 = str(self.awayTeam).split(" & ")[0]
                    p2 = str(self.awayTeam).split(" & ")[1]
                    sound_filename = os.path.join("sounds", "game_status",
                                                  "winnerwinnerchickendinner.m4a")
                    threading.Thread(target=playsound, args=(sound_filename,)).start()
                    sleep(.5)
                    play_team_player_name(p1)
                    play_team_player_name(p2)

                # update g sheet
                self.update_gsheet_score()

                # set g sheet icon in top leftr
                qImg = self.load_logo_qImg('views/oddball_graphics/gsheet_updated.png',
                                           TOP_LEFT_LOGO_WIDTH)
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
                qImg = self.load_logo_qImg('views/oddball_graphics/select_game.png',
                                           TOP_LEFT_LOGO_WIDTH)
                self.draw_rgba_qimg(self.label_logoadvertisement, qImg)
                return
        else:
            if self.timer_paused:
                self.stop_game_timer()
                # draw the stopped graphic
                qImg = self.load_logo_qImg('views/oddball_graphics/stopped.png',
                                           TOP_LEFT_LOGO_WIDTH)
                self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

                return

            elif not self.timer_paused and self.game_in_progress():
                try:
                    self.stop_animation()
                except:
                    pass
                # play "shot_clock_warning"
                # play a random sound and gif
                play_random_sound("sounds/shot_clock_warning")
                self.play_random_animation("animations/shot_clock_warning")

    def handle_key_UP(self):
        # increment minutes in clock edit mode
        if self.clock_edit_mode and not self.game_in_progress():
            self.clock_increment_minute()

        # play "too long"
        else:
            try:
                self.stop_animation()
            except:
                pass
            # play a random sound and gif
            play_random_sound("sounds/too_long")
            self.play_random_animation("animations/too_long")

    def handle_key_DOWN(self):
        # decrement minutes in clock edit mode
        if self.clock_edit_mode and not self.game_in_progress():
            self.clock_decrement_minute()

        # play "too short"
        else:
            try:
                self.stop_animation()
            except:
                pass
            # play a random sound and gif
            play_random_sound("sounds/too_short")
            self.play_random_animation("animations/too_short")

    def handle_key_LEFT(self):
        if self.clock_edit_mode and not self.game_in_progress():
            self.clock_count_up = False
            self.clock_count_down = True
            self.GAME_MINUTES = DEFAULT_GAME_MINUTES
            self.time_min_left = self.GAME_MINUTES
            self.game_time_ui_update()

        else:
            try:
                self.stop_animation()
            except:
                pass
            # play "bad shot"
            # play a random sound and gif
            play_random_sound("sounds/bad_shot")
            self.play_random_animation("animations/bad_shot")

    def handle_key_RIGHT(self):
        if self.clock_edit_mode and not self.game_in_progress():
            self.clock_count_up = True
            self.clock_count_down = False
            self.GAME_MINUTES = 0
            self.time_min_left = 0
            self.game_time_ui_update()


        else:
            try:
                self.stop_animation()
            except:
                pass
            # play "good shot"
            # play a random sound and gif
            play_random_sound("sounds/good_shot")
            self.play_random_animation("animations/good_shot")

    # END KEYPRESSES ##################################################################

    def clock_increment_minute(self):
        if self.clock_count_down:
            self.GAME_MINUTES += 1
            if self.GAME_MINUTES >= 99:
                self.GAME_MINUTES = 99
                logging.info("game minutes pegged at 99")
            self.time_min_left = self.GAME_MINUTES
            self.game_time_ui_update()

    def clock_decrement_minute(self):
        if self.clock_count_down:
            self.GAME_MINUTES -= 1
            if self.GAME_MINUTES <= 0:
                self.GAME_MINUTES = 0
                logging.info("game minutes pegged at 1")
            self.time_min_left = self.GAME_MINUTES
            self.game_time_ui_update()

    def keyPressEvent(self, event):
        logging.info("key pressed: {}".format(str(event.key())))
        self.buttonHistory.append(event.key())

        if not self.enableKeyPressEventHandler:
            logging.CRITICAL("key is not being handled")
            return

        # play a beep
        threading.Thread(target=playsound, args=("sounds/beep/beep_padded.mp3",)).start()

        # pwr key reads as an "s"
        if event.key() == QtCore.Qt.Key_S:
            self.handle_key_PWR()
        elif event.key() == QtCore.Qt.Key_A:
            self.handle_key_A()
        elif event.key() == QtCore.Qt.Key_B:
            self.handle_key_B()
        elif event.key() == QtCore.Qt.Key_C:
            self.handle_key_C()
        # center of D pad reads as "return"
        elif event.key() == QtCore.Qt.Key_Return:
            self.handle_key_RETURN()
        elif event.key() == QtCore.Qt.Key_Up:
            self.handle_key_UP()
        elif event.key() == QtCore.Qt.Key_Down:
            self.handle_key_DOWN()
        elif event.key() == QtCore.Qt.Key_Left:
            self.handle_key_LEFT()
        elif event.key() == QtCore.Qt.Key_Right:
            self.handle_key_RIGHT()

        # set the previous button
        self._prevButton = event.key()


    def lock_in_end_score(self, team):
        # display lightning user feedback
        if self.add_points_mode:
            qImg = self.load_logo_qImg('views/oddball_graphics/lightning.png',
                                       TOP_LEFT_LOGO_WIDTH)
            self.draw_rgba_qimg(self.label_sponsor_bottom_left, qImg)

            team.score.ends[self.end_num].locked = True
            self.other_team(team).score.ends[self.end_num].locked = True

            self.end_num += 1
            self.add_points_mode = False

            # todo place the hammer

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
        if team is self.teamA:
            team = self.teamB
        elif team is self.teamB:
            team = self.teamA
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

    def time_tick(self):
        """
        this method is called each time a second passes and updates the timer if it is not
        paused
        """
        # subtract a second
        if not self.timer_paused:
            # counting down
            if self.clock_count_down and not self.clock_count_up:
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

                        # play beeping sound
                        sound_filename = os.path.join("sounds", "beeping.wav")
                        threading.Thread(target=playsound, args=(sound_filename,)).start()

                        # we will now be counting up
                        self.clock_count_up = True
                        self.clock_count_down = False

                    # otherwise, the seconds are set to 59
                    else:
                        self.time_sec_left = 59

            # counting up
            elif self.time_is_out and self.clock_count_up and not self.clock_count_down:
                self.time_sec_left += 1

                # if the seconds < 0, we need to account for minutes
                if self.time_sec_left >= 59:
                    # add a minute
                    self.time_min_left += 1

                    # set seconds to 0
                    self.time_sec_left = 0

                    # if we hit 99 minutes
                    if self.time_min_left >= 99:
                        self.timer_paused = True
                        self.time_min_left = 0
                        self.time_sec_left = 0

            # update the timer on the UI
            self.game_time_ui_update()

    def game_time_ui_update(self):
        """
        this method updates the time indicator on the GUI
        :return:
        """
        self.lcdNumber_game_time_remaining_min.display(str(self.time_min_left).zfill(2))
        self.lcdNumber_game_time_remaining_sec.display(str(self.time_sec_left).zfill(2))

    def start_game_timer(self, MINUTES, MODE="down"):
        if MODE == "down":
            self.clock_count_down = True
            self.clock_count_up = False
        elif MODE == "up":
            self.clock_count_down = False
            self.clock_count_up = True

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
                                   TOP_LEFT_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_logoadvertisement, qImg)

        # start timer
        self.timer_paused = False
        self.gameTimer.start()
        if self.clock_count_down:
            self.time_min_left = MINUTES - 1

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
            self.timer_paused = True
            self.clock_count_down = True
            self.clock_count_up = False
            self.time_min_left = 0
            self.time_sec_left = 0
            self.game_time_ui_update()
            self.GAME_MINUTES = DEFAULT_GAME_MINUTES
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


    def show_team_change_popup(self, team):
        teamText = None
        labelTeamName = None
        if team is self.teamA:
            teamText = "Team A"
            labelTeamName = self.label_teamA_name
        elif team is self.teamB:
            teamText = "Team B"
            labelTeamName = self.label_teamB_name

        # pop up a text entry dialog
        newTeamName, ok = QInputDialog.getText(self, "Team Name Change", "Enter new {} team name".format(teamText))

        # if the ok button was pressed, then change the team name
        if ok:
            team = self.initialize_team(team, newTeamName)
            labelTeamName.setText(str(team))



if __name__ == '__main__':
    # initialize the app and window
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(sys.argv)

    # show the window and run the app
    window.show()
    app.exec_()
