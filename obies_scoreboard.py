# import packages, modules, classes, and functions
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication
import argparse
import os

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-g", "--game", default="bocce", choices=["bocce", "curling"],
    help="what game are you playing?")
ap.add_argument("-v", "--view", default="digital", choices=["digital", "leelanau"],
    help="which ui do you want to run?")
ap.add_argument("-r", "--remote", default="sparkfun", choices=["ati", "sparkfun"],
    help="which remote do you want to use")
args = vars(ap.parse_args())

# initialize ui
ui = None

# load the ui file which was made with Qt Creator
# bocce
if args["game"] == "bocce":
    from views.bocce.bocceui import MainWindow
    if args["view"] == "digital":
        ui = os.path.join(os.getcwd(), "views", "bocce", "digital_scoreboard.ui")
    elif args["view"] == "traditional":
        pass
        #ui = "views/bocce/traditional_scoreboard.ui"
    else:
        raise NotImplementedError

# future sports
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

# start application with windows for each camera
app = QApplication([])

# load and set the application icon (Obie)
app.setWindowIcon(QtGui.QIcon("views/oddball_graphics/obie.png"))

# set the application title
app.setApplicationName("Obie's Scoreboard")

# start windows
win = MainWindow(ui, args)

# show windows
win.show()

# exit app when all windows are closed
app.exit(app.exec_())