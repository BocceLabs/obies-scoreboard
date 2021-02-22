from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QPushButton
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
import sys, os


MEDIA_DIR = os.path.join(os.getcwd(), "..", "media-leelanaucurlingclub")
ANNOUNCEMENT_DIR = os.path.join(MEDIA_DIR, "announcement_game", "lastname_firstname")
PLAYERS = {
    # "RFID": ("Name", Skip?, entry_video.mp4)
    "e4bce79c": ("Michael Scott", True, os.path.join(ANNOUNCEMENT_DIR, "Scott_Michael.mp4")),
    "d7acdcef": ("Dwight Schrute", False, os.path.join(ANNOUNCEMENT_DIR, "Schrute_Dwight.mp4")),
    "1ab03e86": ("Pam Beesley", False, os.path.join(ANNOUNCEMENT_DIR, "Beesley_Pam.mp4")),
    "b0e751fd": ("Jim Halpert", False, os.path.join(ANNOUNCEMENT_DIR, "Jim_Halpert.mp4"))
}

class VideoPlayer:

    def __init__(self, video_path):
        self.video = QVideoWidget()
        self.video.resize(300, 300)
        self.video.move(0, 0)
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))

    def callback(self):
        self.player.setPosition(0) # to start at the beginning of the video every time
        self.video.show()
        self.player.play()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    video_path = os.path.join(ANNOUNCEMENT_DIR, PLAYERS["e4bce79c"][2])
    v = VideoPlayer(video_path)
    b = QPushButton('start')
    b.clicked.connect(v.callback)
    b.show()
    sys.exit(app.exec_())