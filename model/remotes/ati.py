# imports
import usb.core
import usb.util
import time
import pandas as pd
from PyQt5.QtCore import QObject, QThread, pyqtSignal

USB_IF = 0
USB_TIMEOUT = 5

# read output from `sudo lsusb` and find your USB remote
# mine is X10 Wireless Technology, Inc. X10 Receiver
USB_VENDOR = 0x0bc7
USB_PRODUCT = 0x0004

class ExternalDeviceNotFound(IOError): pass

# a super simple button class so that we can have duplicate BTN keys in the BUTTONS
# dictionary below; objects are unique, but the `name` attribute doesn't have to be
class BTN(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return self.name
    def __str__(self):
        return self.name


################################
# ATI Remote Wonder Plus       #
# button map (for buttons we   #
# care about                   #
################################
# Explanation for duplicates: Double key presses are usually not intentional.  Debouncing
# a button signal is usually handled by a capacitor.  There are likely capacitors in the
# remote itself, but as a software safety measure, the remote alternates two different
# data values that correspond to the same key. This was determined via experimentation. (I
# don't have the engineering manual for this remote).
# If you need to add a key to the map (I didn't map all of them), please execute this
# script in "debug" mode in a terminal and the unmapped key values will be printed to the
# terminal.  Be sure to press the button a few times so you get a feel for the TWO values
# you should enter in the key map below.
BUTTONS = {
    BTN("A")        : (197,   0),
    BTN("A")        : ( 69, 128),
    BTN("B")        : ( 70, 129),
    BTN("B")        : (198,   1),
    BTN("?")        : (202,   5),
    BTN("?")        : ( 74, 133),
    BTN("PWR")      : (199,   2),
    BTN("PWR")      : ( 71, 130),
    BTN("FM")       : ( 97, 156),
    BTN("FM")       : (225,  28),
    BTN("TV")       : ( 72, 131),
    BTN("TV")       : (200,   3),
    BTN("GUIDE")    : ( 75, 134),
    BTN("GUIDE")    : (203,   6),
    BTN("TV2")      : (239,  42),
    BTN("TV2")      : (111, 170),
    BTN("DVD")      : (201,   4),
    BTN("DVD")      : ( 73, 132),
    BTN("EXPAND")   : (101, 160),
    BTN("EXPAND")   : (229,  32),
    BTN("HAND")     : ( 76, 135),
    BTN("HAND")     : (204,   7),
    BTN("CHECK")    : ( 61, 120),
    BTN("CHECK")    : (189, 248),
    BTN("X")        : (193, 252),
    BTN("X")        : ( 65, 124),
    BTN("VOL_UP")   : (205,   8),
    BTN("VOL_UP")   : ( 77, 136),
    BTN("VOL_DOWN") : ( 78, 137),
    BTN("VOL_DOWN") : (206,   9),
    BTN("ATI")      : (114, 173),
    BTN("ATI")      : (242,  45),
    BTN("MUTE")     : ( 79, 138),
    BTN("MUTE")     : (207,  10),
    BTN("CH_UP")    : ( 80, 139),
    BTN("CH_UP")    : (208,  11),
    BTN("CH_DOWN")  : (209,  12),
    BTN("CH_DOWN")  : ( 81, 140),
    BTN("REWIND")   : (105, 164),
    BTN("REWIND")   : (233,  36),
    BTN("PLAY")     : (106, 165),
    BTN("PLAY")     : (234,  37),
    BTN("FAST_FWD") : (107, 166),
    BTN("FAST_FWD") : (235,  38),
    BTN("REC")      : (108, 167),
    BTN("REC")      : (236,  39),
    BTN("PAUSE")    : (110, 169),
    BTN("PAUSE")    : (238,  41),
    BTN("STOP")     : (109, 168),
    BTN("STOP")     : (237,  40),
    BTN("C")        : (222,  25),
    BTN("C")        : ( 94, 153),
    BTN("TIME")     : (240,  43),
    BTN("TIME")     : (112, 171),
    BTN("INFO")     : (241,  44),
    BTN("INFO")     : (113, 172),
    BTN("D")        : (224,  27),
    BTN("D")        : ( 96, 155),
    BTN("OK")       : (227,  30),
    BTN("OK")       : ( 99, 158),
    BTN("D_DOWN")   : (231,  34),
    BTN("D_DOWN")   : (103, 162),
    BTN("D_UP")     : (223,  26),
    BTN("D_UP")     : ( 95, 154),
    BTN("D_LEFT")   : (226,  29),
    BTN("D_LEFT")   : ( 98, 157),
    BTN("D_RIGHT")  : (100, 159),
    BTN("D_RIGHT")  : (228,  31),
    BTN("E")        : (230,  33),
    BTN("E")        : (102, 161),
    BTN("F")        : (232,  35),
    BTN("F")        : (104, 163),
    BTN("0")        : ( 92, 151),
    BTN("0")        : (220,  23),
    BTN("1")        : ( 82, 141),
    BTN("1")        : (210,  13),
    BTN("2")        : ( 83, 142),
    BTN("2")        : (211,  14),
    BTN("3")        : ( 84, 143),
    BTN("3")        : (212,  15),
    BTN("4")        : ( 85, 144),
    BTN("4")        : (213,  16),
    BTN("5")        : ( 86, 145),
    BTN("5")        : (214,  17),
    BTN("6")        : (215,  18),
    BTN("6")        : ( 87, 146),
    BTN("7")        : (216,  19),
    BTN("7")        : ( 88, 147),
    BTN("8")        : (217,  20),
    BTN("8")        : ( 89, 148),
    BTN("9")        : (218,  21),
    BTN("9")        : ( 90, 149),
    BTN("ROUND_D_UP")        : ( 55, 114),
    BTN("ROUND_D_UP")        : ( 57, 116),
    BTN("ROUND_D_DOWN")        : ( 56, 115),
    BTN("ROUND_D_DOWN")        : (184, 243),


}


class ATI(QThread):
    # indicates new unique key press with an event signal
    newUniqueKeyPress = pyqtSignal(BTN)
    finished = pyqtSignal()

    def __init__(self, debug=False, *args, **kwargs):
        super(QThread, self).__init__(*args, **kwargs)
        self.debug = debug
        self.dev = None
        self._prevButton = None
        self.mostRecentButton = None
        self.doublePress = False
        self._prevTs = time.time()

    def connect(self):
        try:
            # initialize the device
            self.dev = usb.core.find(idVendor=USB_VENDOR, idProduct=USB_PRODUCT)
            # print(dev)

            # check if the kernel driver is active
            if self.dev.is_kernel_driver_active(USB_IF) is True:
                # detach from the default kernel driver
                self.dev.detach_kernel_driver(USB_IF)

                # claim the device temporarily
                usb.util.claim_interface(self.dev, USB_IF)

            # otherwise,
            else:
                pass

        except Exception as e:
            raise ExternalDeviceNotFound(str(e))

    def _handle_button_and_check_prev(self, button):
        # set button timestamp
        ts = time.time()

        # duplicate or bounced button
        if button == self._prevButton \
            or (str(button) == str(self._prevButton) and ts - self._prevTs < 0.1):
            self.doublePress = True
            self.mostRecentButton = None
            if self.debug:
                print("* double press filterd *" if self.doublePress else "")

        # new unique button press
        else:
            self._prevButton = button
            self.mostRecentButton = button
            self.doublePress = False
            # debug print statement
            if self.debug:
                print(str(button))

            self.newUniqueKeyPress.emit(self.mostRecentButton)

        # set the previous timestamp
        self._prevTs = ts

    def run(self):
        """
        This method should be run as a process or thread
        """
        endpoint = self.dev[0][(0, 0)][0]

        # loop indefinitely
        while True:
            # reset vars
            control = None
            button = "_"

            try:
                # see what device button is pressed
                control = self.dev.read(endpoint.bEndpointAddress,
                    endpoint.wMaxPacketSize, USB_TIMEOUT)

                # control is a mutable list in format [int_0, int_1, int_2, int_3]
                # we only need the middle two numbers to identify the key, so extract them
                data = (control[1], control[2])

                # ensure button is in our dictionary
                if data not in BUTTONS.values():
                    # this button is not implemented (i.e., it is not in the BUTTONS dictionary)
                    raise NotImplementedError("Button = {} is not implemented. Please " \
                        "add it to the BUTTON map if you intend to use it.".format(data))

                # assume we have a valid button from here
                # since our dicitionary is one-to-one and both keys and values are unique,
                # we can be confident that we can look up a key from a value
                # create a pandas dataframe
                df = pd.DataFrame({'id': list(BUTTONS.keys()), 'data': list(BUTTONS.values())})

                # look up the key (id) from the value (data)
                button = df.id[df.data==data].unique()[0]

                # set the most recent button pressed
                if button is not "_":
                    self._handle_button_and_check_prev(button)

            except Exception as e:
                # print the exception if you'd like
                if "Operation timed out" not in str(e): # don't print the timeout error
                    print(str(e))

                # do nothing because we didn't receive data
                pass

            # half a second should be enough time to capture each press of a button
            time.sleep(0.05)

    def disconnect(self):
        self.finished.emit()

if __name__ == "__main__":
    # create an ATI remote object
    a = ATI(debug=True)
    a.connect()
    a.run()