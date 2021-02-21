# imports
import sys
import os

# add the parent directory (absolute, not relative) to the sys.path
# (this makes the games package imports work)
sys.path.append(os.path.abspath(os.pardir))

# PyQt imports
from PyQt5 import QtCore, QtWidgets
from PyQt5 import uic, QtGui, QtTest
from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter, QMovie, QFont
from PyQt5.QtCore import QThread, QTimer, QRect, Qt, QSize
from PyQt5.QtWidgets import QInputDialog, QWidget, QDialog, QLabel, QMessageBox, QGridLayout, QVBoxLayout, QLineEdit

# bocce game imports
from model.games.curling.team import Team, Player

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
RFID_INDICATOR_WIDTH = 90

# CARD WIDTH
CARD_WIDTH = 300

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

def load_png_qImg(pngPath, width):
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

def cv2img_to_qImg(image, width):
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

def draw_rgba_qimg(label, qImg):
    # set the logo in the GUI
    label.setPixmap(QPixmap(qImg))
    label.repaint()

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

class PlayerRFID():
    """Waits for Num Players and displays names"""
    # todo grab screen resolution and adjust the window size programmatically

    PLAYERS = {
        # "RFID": ("Name", Skip?)
        "e4bce79c": ("Laura Haugen", True),
        "d7acdcef": ("Jennifer Alderman", False),
        "1ab03e86": ("Jay Rosenblum", False),
        "b0e751fd": ("Wes Joseph", False)
    }

    def __init__(self, team, num_players):
        self.team = team
        self.num_players = num_players
        self.dlg = QDialog()
        self.dlg.setWindowTitle("players")
        self.dlg.setWindowModality(False)
        self.dlg.setFixedSize(1000, 1000)
        self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)

        # creat num_players indicators and names
        self.indicators = [QLabel() for x in range(num_players)]
        self.names = ["" for x in range(num_players)]

        # build the grid
        self.grid = QGridLayout()
        for (i, (indicator, name)) in enumerate(zip(self.indicators, self.names)):
            self.grid.addWidget(indicator, i, 0)
            qImg = load_png_qImg(os.path.join("views", "oddball_graphics", "cut_assets", "Mark-Primary.png"), RFID_INDICATOR_WIDTH)
            draw_rgba_qimg(indicator, qImg)
            label = QLabel(name)
            label.setFont(QFont("Luckiest Guy", 20))
            self.grid.addWidget(label, i, 1)

        # vertical layout
        layout = QVBoxLayout()

        # add the rfid text endtry box
        self.id = QLineEdit()
        self.id.setEchoMode(QLineEdit.Password)
        self.id.returnPressed.connect(self.rfid_entered)

        # add message to players
        self.teamLabel = QLabel(str(self.team))
        self.teamLabel.setAlignment(Qt.AlignCenter)
        self.teamLabel.setFont(QFont("Luckiest Guy", 56))
        instructionLabel = QLabel("players: Please badge in!")
        instructionLabel.setAlignment(Qt.AlignCenter)
        instructionLabel.setFont(QFont("Luckiest Guy", 32))

        # add the indicator / name grid
        layout.addWidget(self.id)
        layout.addWidget(self.teamLabel)
        layout.addWidget(instructionLabel)
        layout.addLayout(self.grid)

        # set the dialog layout
        self.dlg.setLayout(layout)

        # index of grid will increment up to num_players
        self.name_idx = 0


    def start(self):
        self.run()

    def run(self):
        self.dlg.show()


        #sleep(self.timeout)
        #self.quit()

    def rfid_entered(self):
        # grab the rfid string and set the text box back to empty
        rfid_string = self.id.text()
        self.id.setText("")

        # lookup the string in the players list
        try:
            name = self.PLAYERS[rfid_string][0]
            skip = self.PLAYERS[rfid_string][1]
        except KeyError:
            self.teamLabel.setStyleSheet("QLabel { color : red }")
            for i in range(5):
                self.teamLabel.setText("INVALID")
                sleep(.25)
                self.teamLabel.setText("")
                sleep(.25)
            self.teamLabel.setText(str(self.team))
            self.teamLabel.setStyleSheet("QLabel { color : black }")
            return

        # create a player
        player = Player(name, skip)

        # attempt to add the player to the team if the player isn't already on the team
        try:
            self.team.add_player(player)
        except ValueError:
            self.teamLabel.setStyleSheet("QLabel { color : red }")
            for i in range(5):
                self.teamLabel.setText("DUPLICATE")
                sleep(.25)
                self.teamLabel.setText("")
                sleep(.25)
            self.teamLabel.setText(str(self.team))
            self.teamLabel.setStyleSheet("QLabel { color : black }")
            return

        # grab the icon and name label widget
        iconLabel_widget = self.grid.itemAtPosition(self.name_idx, 0).widget()
        nameLabel_widget = self.grid.itemAtPosition(self.name_idx, 1).widget()

        # set the name Label
        print(type(nameLabel_widget))
        nameLabel_widget.setText(name)

        # set the icon
        if skip:
            qImg = load_png_qImg(os.path.join("views", "curling", "graphics",
                                              "skip.png"), RFID_INDICATOR_WIDTH)
            draw_rgba_qimg(iconLabel_widget, qImg)
        else:
            qImg = load_png_qImg(os.path.join("views", "oddball_graphics", "cut_assets",
                                              "Mark-2C-Teal.png"), RFID_INDICATOR_WIDTH)
            draw_rgba_qimg(iconLabel_widget, qImg)

        self.name_idx += 1

        if self.name_idx >= self.num_players:
            sleep(3)
            self.quit()


    def quit(self):
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
        qImg = self.load_png_qImg('views/oddball_graphics/cut_assets/Mark-2C-Pink.png',
                                   TOP_LEFT_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_sponsor_top_left, qImg)

        # draw the top center logo
        self.label_sponsor_top_center.setText("Leelanau Curling Club")

        # draw the top right logo
        qImg = self.load_png_qImg('views/curling/graphics/LCC_Final_LOGO_small-1.png',
                                   TOP_RIGHT_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_sponsor_top_right, qImg)

        # BOTTOM LOGOS
        # draw the bottom left logo
        # qImg = self.load_png_qImg('views/curling/long_white.png',
        #                            BOTTOM_LEFT_LOGO_WIDTH)
        # self.draw_rgba_qimg(self.label_sponsor_bottom_left, qImg)

        # draw the bottom center logo
        qImg = self.load_png_qImg('views/oddball_graphics/ODDBALLSPORTS.TV.png',
                                   BOTTOM_CENTER_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_sponsor_bottom_center, qImg)

        # draw the bottom right logo
        # qImg = self.load_png_qImg('views/curling/long_white.png',
        #                            BOTTOM_RIGHT_LOGO_WIDTH)
        # self.draw_rgba_qimg(self.label_sponsor_bottom_right, qImg)

        self.teamA = Team(teamName="tbd")
        self.teamB = Team(teamName="tbd")
        self.team_edit_mode = False

        self.teamA_points_place_labels = [
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
            self.label_teamA_points11
        ]
        self.teamB_points_place_labels = [
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
            self.label_teamB_points11
        ]

        # maps end card to a location
        # these are the initial positions for each card
        self.card_place_color_map = {
            1: [self.label_end_card1, "white"],
            2: [self.label_end_card2, "white"],
            3: [self.label_end_card3, "white"],
            4: [self.label_end_card4, "white"],
            5: [self.label_end_card5, "white"],
            6: [self.label_end_card6, "white"],
            7: [self.label_end_card7, "white"],
            8: [self.label_end_card8, "white"],
            9: [self.label_end_card9, "white"],
            10: [self.label_end_card10, "white"]
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

        self.ignore_keys = []

        self.NUM_ENDS = 8
        self.ends_chosen = False
        self.selected_card = self.NUM_ENDS

        # set the window focus
        self.setFocus()

    def game_launch_steps(self):

        # step #0 - wait for PWR key

        # step #1 - choose ends
        self.choose_ends()

        # step #2 - input team names
        self.input_team_names()

        # step #3 - rfid
        self.input_player_rfid_USB()
        #self.input_player_rfid_SimpleMFRC522()

        # step #4 - start game
        self.game_in_progress = True

        pass


    def choose_ends(self):
        # display all end cards
        self.display_all_end_cards_at_top()

        # set keys to ignore
        self.ignore_keys = [
            QtCore.Qt.Key_S,
            QtCore.Qt.Key_A,
            QtCore.Qt.Key_B,
            QtCore.Qt.Key_C,
            QtCore.Qt.Key_Up,
            QtCore.Qt.Key_Down
        ]

        # select the default
        self.select_card(self.NUM_ENDS, ignore_prev=True)

        # blink ends label
        text = self.label_end_cards.text()
        print(text)
        while not self.ends_chosen:
            sleep(.4)
            self.label_end_cards.setText("")
            sleep(.4)
            self.label_end_cards.setText(text)
        self.label_end_cards.setText(text)

        if self.ends_chosen:
            self.NUM_ENDS = self.selected_card

            # clear other cards
            for card_num, label_color in self.card_place_color_map.items():
                label = label_color[0]
                if card_num <= self.NUM_ENDS:
                    self.draw_card(card_num, "white", label)
                else:
                    self.draw_card(card_num, "clear_it", label)

        # clear ignored keys
        self.ignore_keys = []

    def select_card(self, card_num, ignore_prev=False):
        logging.info("selecting card {}".format(card_num))
        if self.ends_chosen:
            if not card_num <= self.NUM_ENDS and not card_num >= 1:
                raise ValueError("card_num invalid")
        else:
            if card_num > max(self.card_place_color_map.keys()):
                card_num = 1
            if card_num < 1:
                card_num = max(self.card_place_color_map.keys())

        prev_selected_card = self.selected_card
        self.selected_card = card_num
        label, _ = self.get_card(card_num)
        color = "blue"
        self.draw_card(card_num, color, label)

        if not ignore_prev:
            label, color = self.card_place_color_map[prev_selected_card]
            self.card_place_color_map[prev_selected_card] = [label, "white"]
            self.draw_card(prev_selected_card, "white", label)

    def get_card(self, card_num):
        return self.card_place_color_map[card_num]

    def draw_card(self, card_num, color, label):
        if color == "white":
            letter = ""
        elif color == "gray":
            letter = "x"
        elif color == "blue":
            letter = "b"
        elif color == "clear_it":
            label.clear()
            label.repaint()
            self.card_place_color_map[card_num] = [label, "clear"]
            return
        else:
            raise ValueError("invalid card color")

        logging.info("drawing end card {} {}".format(str(card_num), color))
        filename = "{}{}.png".format(str(card_num), letter)
        print(filename)
        path = os.path.join("views", "curling", "graphics", "cards", filename)
        logging.info("attempting to draw card at {}".format(path))
        qImg = self.load_png_qImg(path, width=CARD_WIDTH)
        self.draw_rgba_qimg(label, qImg)
        logging.info("success: drew card at {}".format(path))

    def display_all_end_cards_at_top(self):
        logging.info("drawing all end cards at top")
        try:
            print(self.card_place_color_map.items())
            for card_num, place_color in self.card_place_color_map.items():
                print("DEBUG {}".format(card_num))
                label = place_color[0]
                color = place_color[1]
                print(place_color)
                self.draw_card(card_num, color, label)
                logging.info("END card {} loaded into top position".format(str(card_num)))
        except Exception as e:
            logging.critical("card not loaded")
            print(str(e))
            return
        logging.info("success: drew all end cards at top")

    def input_team_names(self):
        self.show_team_change_popup(self.teamA)
        self.show_team_change_popup(self.teamB)

    def input_player_rfid_SimpleMFRC522(self):
        def wait_for_four_players():
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
            names = []
            while len(names) < 4:
                try:
                    ID, name = reader.read()
                    readTime = time.time()
                    elapsed = readTime - prevReadTime
                    if elapsed < 5:
                        continue
                    ID = str(ID).zfill(16)
                    name = name.strip()
                    names.append(name)

                    # play specific media
                    try:
                        lastname_firstname = name.strip(" ")[1] + name.strip(" ")[0]

                        media_path = os.path.join("..", "media-leelanaucurlingclub",
                            "announcement_enters_venue", "lastname_firstname",
                            lastname_firstname, ".mp4")

                        # todo determine length of video

                        self.load_animation(media_path, timeout=8)

                    # if error, play random media
                    except:
                        logging.WARNING("entry media not found, playing random entry media")
                        media_path = os.path.join("..", "media-leelanaucurlingclub",
                                                  "announcement_enters_venue",
                                                  "random")

                        media_path = random.choice(list_animations(media_path))

                        # todo determine length of video

                        self.load_animation(media_path, timeout=8)

                    prevReadTime = readTime
                except Exception as e:
                    print(str(e))
                    prevReadTime = 0
                    continue
            return names


        teamA_players = wait_for_four_players()
        teamB_players = wait_for_four_players()


    def input_player_rfid_USB(self):
        a = PlayerRFID(self.teamA, 4)
        a.start()
        logging.info("starting to collect TeamA names via RFID")
        sleep(40)
        #a.quit()


        teamA_players = None
        teamB_players = None



    def initialize_team(self, team, teamName):
        team.change_team_name(teamName)

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

    def play_entry_announcement(self, RFID_READER_CONNECTED):
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



            # everyone badged in, so play the names!
            play_team_player_name(tap1)
            play_team_player_name(tap2)
            play_team_player_name(tbp1)
            play_team_player_name(tbp2)






    # KEYPRESSES ##################################################################
    def handle_key_PWR(self):
        if not self.game_in_progress:
            self.game_launch_steps()

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
                qImg = self.load_png_qImg('views/oddball_graphics/numbers.png',
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
                qImg = self.load_png_qImg('views/oddball_graphics/team.png',
                                           BOTTOM_LEFT_LOGO_WIDTH)
                self.draw_rgba_qimg(self.label_sponsor_bottom_left, qImg)
                # press a or b for team popup
            elif self.team_edit_mode:
                self.label_sponsor_bottom_left.clear()
                self.label_sponsor_bottom_left.repaint()
                self.team_edit_mode = False

    def handle_key_RETURN(self):

        if not self.ends_chosen:
            self.ends_chosen = True

        elif self.clock_edit_mode and self._prevButton == QtCore.Qt.Key_C:
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
                qImg = self.load_png_qImg('views/oddball_graphics/gsheet_updated.png',
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
                qImg = self.load_png_qImg('views/oddball_graphics/select_game.png',
                                           TOP_LEFT_LOGO_WIDTH)
                self.draw_rgba_qimg(self.label_logoadvertisement, qImg)
                return
        else:
            if self.timer_paused:
                self.stop_game_timer()
                # draw the stopped graphic
                qImg = self.load_png_qImg('views/oddball_graphics/stopped.png',
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
        if not self.ends_chosen:
            self.select_card(self.selected_card - 1)

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
        if not self.ends_chosen:
            self.select_card(self.selected_card + 1)

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

    def keyPressEvent(self, event):
        logging.info("key pressed: {}".format(str(event.key())))
        self.buttonHistory.append(event.key())

        if not self.enableKeyPressEventHandler:
            logging.critical("key is not being handled")
            return

        if event.key() in self.ignore_keys:
            logging.info("key ignored!")
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
            qImg = self.load_png_qImg('views/oddball_graphics/lightning.png',
                                       TOP_LEFT_LOGO_WIDTH)
            self.draw_rgba_qimg(self.label_sponsor_bottom_left, qImg)

            team.score.ends[self.end_num].locked = True
            self.other_team(team).score.ends[self.end_num].locked = True

            self.end_num += 1

            # update current end in score model
            team.score.current_end += 1
            self.other_team(team).score.current_end += 1

            # place the hammer on the other team and display it
            self.other_team(team).score.set_hammer(self.other_team(team).score.current_end)

            if self.other_team(team) is self.teamA:
                hammer_icon_spot = self.teamA_points_place_labels[team.score.current_end]
            elif self.other_team(team) is self.teamB:
                hammer_icon_spot = self.teamB_points_place_labels[team.score.current_end]
            qImg = self.load_png_qImg('views/curling/graphics/hammer.png', 100)
            self.draw_rgba_qimg(hammer_icon_spot, qImg)



            self.add_points_mode = False

            # todo place the hammer

    def other_team(self, team):
        """convenience function returns the opposite team of what is provided"""
        if team is self.teamA:
            team = self.teamB
        elif team is self.teamB:
            team = self.teamA
        return team

    def set_widget_font_foreground_color(self, widget, color):
        # create a QColor and swap BGR to RGB
        color = QColor(color[2], color[1], color[0])

        # extract the widget palette
        palette = widget.palette()

        # set the text color and palette
        palette.setColor(palette.WindowText, color)
        widget.setPalette(palette)

    # formerly load_png_qImg
    def load_png_qImg(self, pngPath, width):
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
