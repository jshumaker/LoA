__author__ = 'Jody Shumaker'

from ctypes import *
import win32con
import win32gui
import win32api


# noinspection PyPep8Naming
class _point_t(Structure):
    _fields_ = [
        ('x',  c_long),
        ('y',  c_long),
    ]


class Mouse:
    @staticmethod
    def get_position():
        point = _point_t()
        result = windll.user32.GetCursorPos(pointer(point))
        if result:
            return point.x, point.y
        else:
            return None

    @staticmethod
    def move(x, y):
        win32api.SetCursorPos((x, y))

    @staticmethod
    def click(x, y):
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    arrow_cursor = win32api.LoadCursor(0, win32con.IDC_ARROW)
    hand_cursor = win32api.LoadCursor(0, win32con.IDC_HAND)

    @staticmethod
    def get_cursor():
        flags, current_cursor, position = win32gui.GetCursorInfo()
        return current_cursor

    @staticmethod
    def cursor_is_hand():
        flags, current_cursor, position = win32gui.GetCursorInfo()
        return current_cursor == Mouse.hand_cursor

    @staticmethod
    def cursor_is_arrow():
        flags, current_cursor, position = win32gui.GetCursorInfo()
        return current_cursor == Mouse.arrow_cursor