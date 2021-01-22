# obie's-scoreboard

This is a PyQT Scoreboard that supports a wireless/infrared remote control and an TV/computer monitor screen.  It could be adapted to suport an LED-matrix / 7-segment display if you have the budget for one of those (\$2,000+ for custom displays).

![obie's-scoreboard](https://GitHub.com/OddballSports-tv/obies-scoreboard/scoreboard.png)

# Architecture

This project uses Model-View-Controller archicture (MVC).

## model

We currently have the following models:

* remotes/ati (works with the ATI Remote Wonder Plus wireless RF remote)

We'll be adding scoring models for the following sports:

* Bocce
* Curling
* Shuffleboard
* Wiffleball
* Croquet
* insert your favorite sport here

## view

This app supports multiple views that are separate from the business logic.  Of course this project has a heavy focus on User Experience and the User Interface, so arguably the View is the most important part.

Currently there is one view(s) with more coming:

* --game bocce --view digital
* --game bocce --view traditional (coming soon)
* --game curling --view yourclub (coming soon)
* --game shuffleboard --view royalpalms (coming soon)

Feel free to create your custom view for your odd game / sport.  

The above views are implemented in PyQt. If you are more comfortable with a different GUI toolkit such as Tk, Wx, Kivy, etc. go for it!  It would actually be nice to have multiple examples in this project, so please fork the project, implement it, and then submit a pull request.

NOTE: currently the bocce view file has both the UI widgets and the model logic for bocce (this was due to so many live changes being done during and between games; we definitely has room for improvement to move the bocce business logic into the model side of the architecture and we will get to it soon)


## controller

The controller is the program that kicks off the app -- `obies_scoreboard.py`.  This controller also sets the app icon.  The app icon needs to be tested in Ubuntu, Raspbian, and Windows (works great in macOS with no issues).

# Dependencies

Python packages (this should be all you need for macOS -- drivers were plug 'n play):

```
pyusb
pyqt5
opencv-contrib-python
imutils
pillow
```

If you're running Raspbian you'll need all of the above Python packages.  You may also need to install USB Core Dev libraries in your Raspberry Pi system.  Furthermore, you'll need to create a USB Device Rule.  Details are in the following repo: [OddballSports-tv/hid_wireless_remote](https://github.com/OddballSports-tv/hid_wireless_remote).

If you set up a Raspberry Pi, we recommend using the Raspbian BusterOS.  This OS has pre-compiled binaries for PyQt5 a pip install away.  Be sure to read the PyQt license agreement.


# Running the program

```
python obies_scoreboard.py --game bocce --view digital
```

or (example):

```
python obies_scoreboard.py --game bocce --view traditional
```

or (example):

```
python obies_scoreboard.py --game curling --view yourclubnamehere
```

# Future features

* Integration into `obies-eyes` (i.e., messages are passed to control the scoreboard when Obie detects a change in the game score)
* Integration with an LED-matrix / 7-segment display
* Support other games (contributers encouraged!)

# Contributing

Contributing to this project is encouraged!

Here's the process:

1. Fork the project
2. Implement your improvement / change / feature / view / support for different hardware
3. Submit a pull request (send us an email if you want to discuss it)
4. We might send you some feedback before we can pull in your change
5. Done (have a beer and share on social media; be sure to tag OddballSports!)

# Attributions

* [Python for the Lab](https://wwww.pythonforthelab.com) - Free resource; if you like it you can support them by buying the \$10 ebook

# LICENSE

Apache Version 2.0
