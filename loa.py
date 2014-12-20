__author__ = 'Jody Shumaker'

import argparse
import datetime
import win32gui
import win32ui
import win32con
from ctypes import windll
import logging
from PIL import ImageGrab, Image
import time
from collections import namedtuple
from enum import Enum
from utility.screen import *

Rect = namedtuple('Rect', ['left', 'top', 'right', 'bottom'])
FoundPosition = namedtuple('FoundPosition', ['x', 'y', 'xoffset', 'yoffset'])


def makelong(low, high):
    return low | (high << 16)



class SearchAlgorithm(Enum):
    Spiral = 0
    LeftToRight = 1

SEARCH_SPIRAL = 1
SEARCH_LEFT_TO_RIGHT = 2

def search_offset(radius=2, offsetx=0, offsety=0, xradius=None, yradius=None, algorithm=SearchAlgorithm.Spiral):
    """
    :param radius: Search radius, max distance from 0,0 to generate a point from. Defaults to 2, which will generate
     a -2, -2 to 2, 2 search pattern spiraling out from center.
    :return: Yields a x,y tuplet in a spiral sequence from 0,0 limited by radius.
    :offsetx: amount to offset returned x by.
    :offsety: amount to offset returned x by.
    """
    if xradius is None:
        xradius = radius
    elif xradius > radius:
        radius = xradius
    if yradius is None:
        yradius = radius
    elif yradius > radius:
        radius = yradius
    if algorithm == SearchAlgorithm.Spiral:
        x = y = 0
        dx = 0
        dy = -1
        for i in range((radius*2 + 1)**2):
            if abs(x) <= xradius and abs(y) <= yradius:
                yield (x + offsetx, y + offsety)
            if x == y or (x < 0 and x == -y) or (x > 0 and x == 1-y):
                dx, dy = -dy, dx
            x, y = x+dx, y+dy
    elif algorithm == SEARCH_LEFT_TO_RIGHT:
        for x in range(0 - xradius, xradius + 1):
            for y in range(0 - yradius, yradius + 1):
                yield (x + offsetx, y + offsety)
    else:
        raise ArgumentError("Invalid search algorithm specified.")


class Orient(Enum):
    Center = 0
    Left = 1
    Top = 2
    Right = 3
    Bottom = 4


class LeagueOfAngels:
    def __init__(self, auto=True, screenshot=None):
        self.hwnd = None
        self.gamepos = None
        self.screenshot = screenshot
        if screenshot is None:
            self.get_game_hwnd(auto=auto)
            self.get_game_bbox()
        else:
            self.gamepos = 0, 0, screenshot.size[0], screenshot.size[1]

        self.resources = {}

    def get_game_hwnd(self, auto=True):
        windows = []

        def foreach_window(hwnd, lparam):
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
            raise Exception("Failed to find game window.")
        elif len(windows) > 1 and not auto:
            print("Found {0} possible game windows.".format(len(windows)))
            for i in range(1, len(windows) + 1):
                print("{0}: {1}".format(i, windows[i-1][1]))
            windownum = input("Enter the number for the window you which to use [1]: ")
            if windownum == "":
                windownum = 0
            else:
                windownum = int(windownum) - 1
            logging.info("Using window {0}".format(windows[windownum][1]))
            self.hwnd = windows[windownum][0]
        else:
            self.hwnd = windows[0][0]

    def capture_screenshot(self):
        im = None
        left, top, right, bot = win32gui.GetClientRect(self.hwnd)
        w = right - left
        h = bot - top

        hwnddc = win32gui.GetWindowDC(self.hwnd)
        mfcdc = win32ui.CreateDCFromHandle(hwnddc)
        savedc = mfcdc.CreateCompatibleDC()

        savebitmap = win32ui.CreateBitmap()
        savebitmap.CreateCompatibleBitmap(mfcdc, w, h)

        savedc.SelectObject(savebitmap)

        # Change the line below depending on whether you want the whole window
        # or just the client area.
        result = windll.user32.PrintWindow(self.hwnd, savedc.GetSafeHdc(), 1)
        logging.debug("PrintWindow result: {}".format(result))

        if result == 1:
            bmpinfo = savebitmap.GetInfo()
            logging.debug(bmpinfo)
            bmpstr = savebitmap.GetBitmapBits(True)

            im = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1)

        win32gui.DeleteObject(savebitmap.GetHandle())
        savedc.DeleteDC()
        mfcdc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwnddc)

        return im

    def get_game_bbox(self):
        logging.debug("Searching for game bounding box within client area.")
        screenshot = self.capture_screenshot()
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        logging.debug("Client rect: {},{},{},{}".format(left, top, right, bottom))
        # Let's find the left edge
        left = -1
        blackcount = 0
        for x in range(0, 200):
            p = screenshot.getpixel((x, int(bottom / 2)))
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
            raise Exception("Failed to find left edge.")

        # Let's find the top edge
        for y in range(300, -1, -1):
            p = screenshot.getpixel((left - 1, y))
            if p[0] != 0 or p[1] != 0 or p[2] != 0:
                top = y + 1
                break
        if top == -1:
            logging.debug("Pixels were black to 0, assuming full screen.")
            top = 0

        # Let's find the bottom edge
        for y in range(bottom - 20, bottom, +1):
            p = screenshot.getpixel((left - 1, y))
            if p[0] != 0 or p[1] != 0 or p[2] != 0:
                # Let's assume if there's a border on the bottom, there's one on the right too.
                right -= bottom - y
                bottom = y
                break

        logging.debug("Game position: {},{},{},{}".format(left, top, right, bottom))
        self.gamepos = Rect(left, top, right, bottom)

    def game_to_client(self, x, y, xorient=Orient.Left, yorient=Orient.Top):
        if xorient == Orient.Center:
            x += int((self.gamepos.right - self.gamepos.left) / 2) + self.gamepos.left
        elif xorient == Orient.Right:
            x = self.gamepos.right - abs(x)
        elif xorient == Orient.Left:
            x += self.gamepos.left
        else:
            raise Exception("Invalid xorient.")
        if yorient == Orient.Center:
            y += int((self.gamepos.bottom - self.gamepos.top) / 2) + self.gamepos.top
        elif yorient == Orient.Bottom:
            y = self.gamepos.bottom - abs(y)
        elif yorient == Orient.Top:
            y += self.gamepos.top
        else:
            raise Exception("Invalid yorient.")
        return x, y

    def client_to_game(self, x, y):
        return x - self.gamepos.left, y - self.gamepos.top

    def click(self, x, y, xorient=Orient.Left, yorient=Orient.Top):
        x, y = self.game_to_client(x, y, xorient, yorient)
        logging.debug('Clicking {},{}'.format(x, y))
        position = makelong(x, y)
        win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, position)
        time.sleep(0.01)
        win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, position)

    def mouse_move(self, x, y, xorient=Orient.Left, yorient=Orient.Top):
        x, y = self.game_to_client(x, y, xorient, yorient)
        logging.debug('Moving mouse to {},{}'.format(x, y))
        position = makelong(x, y)
        win32gui.PostMessage(self.hwnd, win32con.WM_MOUSEMOVE, 0, position)

    def image_find(self, image, x, y, xorient=Orient.Left, yorient=Orient.Top, screenshot=None,
                   radius=2, threshold=None, great_threshold=None):
        """
        Finds an image in the game and returns the client coordinates and offset.
        """
        searchpos = self.game_to_client(x, y, xorient, yorient)
        if screenshot is None:
            screenshot = self.capture_screenshot()
        pos = image_search(screenshot, image, *searchpos, radius=radius,
                           threshold=threshold, great_threshold=great_threshold)

        if pos[0] != -1:
            offsetx = searchpos[0] - pos[0]
            offsety = searchpos[1] - pos[1]
            pos = self.client_to_game(*pos)
        else:
            offsetx = 0
            offsety = 0
        return FoundPosition(pos[0], pos[1], offsetx, offsety)

    def find_back_button(self):
        if not "Back" in self.resources:
            self.resources['Back'] = Image.open(script_dir + '/misc/Back.png')
        # Arena
        back_pos = self.image_find(self.resources['Back'], 73, 65, Orient.Right, Orient.Bottom)
        # Domination
        if back_pos.x == -1:
            back_pos = self.image_find(self.resources['Back'], 135, 62, Orient.Center, Orient.Bottom)
        return back_pos

    def goto_homepage(self):
        back_found = True
        while back_found:
            back_found = False
            back_pos = self.find_back_button()
            if back_pos.x != -1:
                self.click(back_pos.x + 25, back_pos.y + 25)
                back_found = True
                time.sleep(2.000)

        # Cycle between mount and character dialog to clear back to empty home page.
        #self.keypress('c')
        #time.sleep(5.0)
        #self.keypress('m')
        #time.sleep(5.0)
        #self.keypress('m')



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Automatically join world boss.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--screenshot', '-s', action='store_true', help="Take a screenshot of the game.")
    parser.add_argument('--mouse', '-m', action='store_true', help="Give details on coordinates of mouse.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    game = LeagueOfAngels()
    if args.screenshot:
        game.capture_screenshot().crop(game.gamepos).save("screenshot_{}.png".format(
            datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
    if args.mouse:
        x, y = win32gui.GetCursorPos()
        x, y = win32gui.ScreenToClient(game.hwnd, (x, y))
        leftx, topy = game.client_to_game(x, y)
        centerx, centery = game.game_to_client(0, 0, Orient.Center, Orient.Center)
        centerx = x - centerx
        centery = y - centery
        rightx, bottomy = game.game_to_client(0, 0, Orient.Right, Orient.Bottom)
        rightx -= x
        bottomy -= y
        logging.info('X  Left: {:>5} Center: {:>5}  Right: {:>5}'.format(
            leftx, centerx, rightx
        ))
        logging.info('Y   Top: {:>5} Center: {:>5} Bottom: {:>5}'.format(
            topy, centery, bottomy
        ))