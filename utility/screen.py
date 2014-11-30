__author__ = 'Jody Shumaker'

import math
import sys
import logging
import win32gui
import win32con
from ctypes import *
from PIL import ImageGrab, Image
import time

class Color:
    def __init__(self, r, g, b, a=0):
        self.r = r
        self.g = g
        self.b = b
        self.a = a
        # Calculate the furthest distance a color could be from this color.
        self.max_distance = math.sqrt(
            (self.r if self.r > 128 else 255 - self.r)**2 +
            (self.g if self.g > 128 else 255 - self.g)**2 +
            (self.b if self.b > 128 else 255 - self.b)**2
        )

    def __str__(self):
        return "R{0:03d}G{1:03d}B{2:03d}A{3:03d}".format(int(self.r), int(self.g), int(self.b), int(self.a))

    def compare(self, color2):
        distance = math.sqrt((self.r - color2.r)**2 + (self.g - color2.g)**2 + (self.b - color2.b)**2)
        if distance < 1:
            distance = 1
        accuracy = (((self.max_distance - distance) / self.max_distance) ** 3)
        # Let's consider 20 % a rough floor. It's rare to get below that without looking at extremes
        accuracy = (accuracy - 0.20) / 0.8
        if accuracy < 0:
            accuracy = 0
        return accuracy


def get_pixel(image, x, y):
    r, g, b = image.getpixel((x, y))
    return Color(r, g, b, 0)


def get_avg_pixel(image, x, y, r=15):
    avgpixel = Color(0, 0, 0, 0)
    count = (r * 2) ** 2
    for posx in range(x - r, x + r):
        for posy in range(y - r, y + r):
            p = get_pixel(image, posx, posy)
            avgpixel.r += p.r / float(count)
            avgpixel.g += p.g / float(count)
            avgpixel.b += p.b / float(count)
            avgpixel.a += p.a / float(count)
    return avgpixel


def compare_images(i1, i2):
    rms = 0.0
    if i1.size != i2.size:
        raise ValueError("Image sizes for comparison do not match. {0} vs {1}".format(i1.size, i2.size))
    width, height = i1.size
    for x in range(width):
        for y in range(height):
            pixel1 = i1.getpixel((x, y))
            pixel2 = i2.getpixel((x, y))

            pixel_rms = math.sqrt((pixel1[0] - pixel2[0])**2 + (pixel1[1] - pixel2[1])**2 + (pixel1[2] - pixel2[2])**2)
            if len(pixel2) > 3:
                # Second image has an alpha channel, let's scale our rms value by the alpha channel.
                # This ignores fully transparent pixels, and can give less weight to partially transparent pixels.
                rms += pixel_rms * pixel2[3] / 255
            else:
                rms += pixel_rms
    return rms


def get_game_window():
    game_hwnd = None

    windows = []

    def foreach_window(hwnd, lParam):
        nonlocal windows
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if "League of Angels" in window_text:
                windows.append((hwnd, window_text))
                logging.debug("Found game window hwnd: {0} title: {1}".format(hwnd, window_text))
        return True

    win32gui.EnumWindows(foreach_window, None)
    if len(windows) == 0:
        logging.error("Failed to find game window.")
        sys.exit(1)
    elif len(windows) > 1:
        print("Found {0} possible game windows.".format(len(windows)))
        for i in range(1, len(windows) + 1):
            print("{0}: {1}".format(i, windows[i-1][1]))
        windownum = input("Enter the number for the window you which to use [1]: ")
        if windownum == "":
            windownum = 0
        else:
            windownum = int(windownum) - 1
        logging.info("Using window {0}".format(windows[windownum][1]))
        game_hwnd = windows[windownum][0]
    else:
        game_hwnd = windows[0][0]

    windowleft, windowtop, windowright, windowbottom = win32gui.GetWindowRect(game_hwnd)
    clientleft, clienttop, clientright, clientbottom = win32gui.GetClientRect(game_hwnd)
    logging.debug("Window position: {},{},{},{}".format(windowleft, windowtop, windowright, windowbottom))

    if windowleft < 0:
        windowleft = 0
    if windowtop < 0:
        windowtop = 0

    top = -1
    left = -1
    right, bottom = win32gui.ClientToScreen(game_hwnd, (clientright, clientbottom))

    # Make this window active.
    win32gui.SetWindowPos(game_hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE + win32con.SWP_NOSIZE + win32con.SWP_SHOWWINDOW)
    time.sleep(0.050)

    screengrab = ImageGrab.grab()
    # Let's find the left edge
    blackcount = 0
    for x in range(windowleft + 5, windowleft + 200):
        p = screengrab.getpixel((x, windowtop + 300))
        if p[0] == 0 and p[1] == 0 and p[2] == 0:
            blackcount += 1
        else:
            if blackcount > 10:
                left = x
                break
            else:
                blackcount = 0
    if left == -1:
        logging.error("Failed to find left edge.")
        sys.exit(1)

    # Let's find the top edge
    for y in range(windowtop + 300, windowtop - 1, -1):
        p = screengrab.getpixel((left - 1, y))
        if p[0] != 0 or p[1] != 0 or p[2] != 0:
            top = y + 1
            break
    if top == -1:
        logging.debug("Pixels were black to 0, assuming full screen.")
        top = 0

    # TODO: Figure out right and bottom better, currently it's frequently off by several pixels.

    return left, top, right, bottom


def search_offset(radius=2, offsetx=0, offsety=0):
    """
    :param radius: Search radius, max distance from 0,0 to generate a point from. Defaults to 2, which will generate
     a -2, -2 to 2, 2 search pattern spiraling out from center.
    :return: Yields a x,y tuplet in a spiral sequence from 0,0 limited by radius.
    :offsetx: amount to offset returned x by.
    :offsety: amount to offset returned x by.
    """
    x = y = 0
    dx = 0
    dy = -1
    for i in range((radius*2 + 1)**2):
        yield (x + offsetx, y + offsety)
        if x == y or (x < 0 and x == -y) or (x > 0 and x == 1-y):
            dx, dy = -dy, dx
        x, y = x+dx, y+dy


def image_search(screengrab, image, searchx, searchy, threshold=None, radius=5, great_threshold=None):
    """
    Search for an image in the screengrab starting at the given searchx and searchy coordinages, and expanding out
    to the max distance of radius. Returned
    :param screengrab:
    :param image:
    :param searchx:
    :param searchy:
    :param threshold: rms that the match must be below before a match can be possible.
    :param radius:
    :return: Coordinates of top left of image.
    """
    image_width, image_height = image.size
    if threshold is None:
        best_rms = image_width * image_height * 30.0
    else:
        best_rms = threshold

    if great_threshold is None:
        # use an automatic value based upon size.
        great_threshold = image_width * image_height

    best_x = -1
    best_y = -1
    for x, y in search_offset(radius=radius, offsetx=searchx, offsety=searchy):
        rms = compare_images(screengrab.crop((x, y, x + image_width, y + image_height)), image)
        logging.debug("Image Search {0},{1}  rms: {2:>10.3f}".format(x, y, rms))
        if best_rms is None or rms < best_rms:
            best_y = y
            best_x = x
            best_rms = rms
        if rms < great_threshold:
            break
    return best_x, best_y


def detect_image(screengrab, imageset, searchx, searchy, threshold=None, radius=2, great_threshold=None):
    """
    Detect an image from a screengrab from among a set of images.
    :param screengrab:
    :param imageset:
    :param searchx: x coordinate to start searching the screengrab at.
    :param searchy:
    :param threshold: maximum rms to consider a possible match
    :param radius: max +/- x/y to search for a match.
    :param great_threshold: threshold for which rms value beneath this is accepted immediately.
    :return: (x, y, name) tuple of top left corner of detected image, and the name of the image.
    """
    image_width, image_height = imageset[0][1].size
    if threshold is None:
        # Use an automatic threshold.
        best_rms = image_width * image_height * 20.0
    else:
        best_rms = threshold

    if great_threshold is None:
        # use an automatic value based upon size.
        great_threshold = best_rms / 10.0
    best_x = -1
    best_y = -1
    best_name = None
    for x, y in search_offset(radius=radius, offsetx=searchx, offsety=searchy):
        for name, image in imageset:
            image_width, image_height = image.size
            rms = compare_images(screengrab.crop((x, y, x + image_width, y + image_height)), image)
            logging.debug("Image Search {0},{1}  rms: {2:>10.3f} name: {3}".format(x, y, rms, name))
            if best_rms is None or rms < best_rms:
                best_y = y
                best_x = x
                best_name = name
                best_rms = rms
            if rms < great_threshold:
                break
        if best_name is not None:
            break
    return best_name, best_x, best_y


def find_image(screengrab, image, threshold=None):
    """
    Find all occurences of image within screengrab.
    :param screengrab:
    :param image:
    :param threshold: Maximum rms to be considered a match. Defaults to None which causes an automatic value to be
    calculated of image width * height.
    :return:
    List of tuples of matches.
    """
    matches = []
    image_width, image_height = image.size
    screen_width, screen_height = screengrab.size
    if threshold is None:
        # Use an automatic threshold.
        threshold = image_width * image_height * 10.0
    for x in range(screen_width - image_width):
        for y in range(screen_height - image_height):
            if compare_images(screengrab.crop((x, y, x + image_width, y + image_height)), image) < threshold:
                matches.append((x, y))
    return matches