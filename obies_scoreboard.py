# import packages, modules, classes, and functions
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtGui
from views.viewsui import MainWindow

# start application with windows for each camera
app = QApplication([])

# load and set the application icon (Obie)
app.setWindowIcon(QtGui.QIcon("views/ui/obie.png"))

# set the application title
app.setApplicationName("Obie's Eyes")

# start windows
win = MainWindow()

# show windows
win.show()

# exit app when all windows are closed
app.exit(app.exec_())