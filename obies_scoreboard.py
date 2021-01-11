# import packages, modules, classes, and functions
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication
from views.bocce.bocceui import MainWindow

# start application with windows for each camera
app = QApplication([])

# load and set the application icon (Obie)
app.setWindowIcon(QtGui.QIcon("views/oddball_graphics/obie.png"))

# set the application title
app.setApplicationName("Obie's Scoreboard")

# start windows
win = MainWindow()

# show windows
win.show()

# exit app when all windows are closed
app.exit(app.exec_())