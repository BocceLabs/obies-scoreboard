# obies-scoreboard

This is a PyQT Scoreboard that supports a wireless/infrared remote control and an TV/computer monitor screen.  It could be adapted to suport an LED-matrix / 7-segment display if you have the budget for one of those (\$2,000+ for custom displays).

[ [ insert screenshots here ] ]

# Architecture

This project uses Model-View-Controller archicture (MVC).

## model

pass

## view

This app supports multiple views that are separate from the business logic.  Of course this project has a heavy focus on User Experience and the User Interface, so arguably the View is the most important part.

Currently there are two views:

* bocce - digital
* bocce - traditional

Feel free to create your custom view for your odd game / sport.  

The above views are implemented in PyQt. If you are more comfortable with a different GUI toolkit such as Tk, Wx, Kivy, etc. go for it!  It would actually be nice to have multiple examples in this project, so please fork the project, implement it, and then submit a pull request.


## controller

The controller is the program that kicks off the app -- `obies_scoreboard.py`.

# Dependencies

pass

# Running the program

```
python obies_scoreboard.py --game bocce --view digital
```

or

```
python obies_scoreboard.py --game bocce --view traditional
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
