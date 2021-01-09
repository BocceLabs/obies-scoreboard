# imports
import sys
import os

# add the parent directory (absolute, not relative) to the sys.path
# (this makes the games package imports work)
sys.path.append(os.path.abspath(os.pardir))

# PyQt imports
from PyQt5 import QtCore, QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import QThread, QTimer
from PyQt5.QtGui import QImage, QPixmap, QColor
from PyQt5.QtWidgets import QTableWidgetItem

# other imports
import cv2


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        """
        constructor
        """
        super().__init__(*args, **kwargs)

        # load the ui file which was made with Qt Creator
        if args["game"] == "bocce":
            if args["view"] == "digital"
                uic.loadUi("views/ui/bocce/digital_scoreboard.ui", self)
            elif args["view"] == "traditional":
                uic.loadUi("views/ui/bocce/traditional_scoreboard.ui", self)
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

        # load the Obie logo file
        self.load_logo()

        # minimal game info
        self.teamHome_name = ""
        self.teamAway_name = ""

    def load_logo(self):
        """
        load the Obie logo
        """
        # load the logo and read all channels (including alpha transparency)
        logo = cv2.imread('views/ui/obie.png', cv2.IMREAD_UNCHANGED)
        obie = imutils.resize(obie, width=600)
        height, width, channel = obie.shape
        bytesPerLine = 3 * width

        # create a QImage and ensure to use the alpha transparency format
        qImg = QImage(obie.data, width, height, bytesPerLine, QImage.Format_RGBA888)

        # set the logo
        # todo create logo area in .ui file
        self.logo.setPixmap(QPixmap(qImg))
        self.logo.repaint()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()