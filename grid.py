__author__ = 'Jody Shumaker'

from ctypes import *
import math
import win32api
import win32con
import win32gui
import itertools
from PIL import ImageGrab
from copy import deepcopy
import sys
import logging
import time
import random


class Color:
    def __init__(self, r, g, b, a):
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


def guess_grid_item(pixel):
    closest_amount = 0.0
    closest_item = None
    for griditemtype in Grid.GridItemTypes:
        amount = griditemtype.color.compare(pixel)
        if amount > closest_amount:
            closest_amount = amount
            closest_item = griditemtype
    return closest_item, closest_amount


def calibrate_colors():
    input("Place mouse over center of top left gem and press enter.")
    xoffset, yoffset = Mouse.get_position()
    # Move the mouse away
    win32api.SetCursorPos((xoffset - 50, yoffset - 50))
    screengrab = ImageGrab.grab()
    for y in range(5):
        row = []
        for x in range(5):
            posx = xoffset + (x * 50)
            posy = yoffset + (y * 50)
            row.append(get_avg_pixel(screengrab, posx, posy))

        print(", ".join([str(color) for color in row]))


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


class Move:
    """
    Captures data related to a move.
    """

    def __init__(self, x1, y1, itemtype1, x2, y2, itemtype2):
        self.x1 = x1
        self.y1 = y1
        self.itemtype1 = itemtype1
        self.x2 = x2
        self.y2 = y2
        self.itemtype2 = itemtype2

        self.points = 0
        self.submove = None

    def get_total_points(self, depth_factor=0.75):
        if self.submove is None:
            return self.points
        else:
            # Until something is accounted for unknown blocks creating matches,
            # we need to slightly favor clearing things earlier.
            return self.points + (self.submove.get_total_points() * depth_factor)

    def describe(self):
        description = "{0},{1}({2})<->{3},{4}({5}) {6:0.1f}pts".format(
            self.x1 + 1, self.y1 + 1, self.itemtype1.name[0],
            self.x2 + 1, self.y2 + 1, self.itemtype2.name[0],
            self.points)
        if self.submove is None:
            return description
        else:
            return "{0}, {1}".format(description, self.submove.describe())


class GridItem:
    def __init__(self, itemtype):
        self.itemtype = itemtype
        self.cleared = False


class GridItemType:
    count = 0

    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.index = GridItemType.count
        GridItemType.count += 1

    def __hash__(self):
        return self.index

    def __eq__(self, other):
        return self.index == other.index


class Grid:
    """
    Abstraction of the 5x5 board grid applicable to both Gemology and Dragon Souls
    """
    debug = False
    fast0 = False
    delay = 1.5
    GridItemTypes = []
    # Special type for unknown grid items.
    GridItemTypeUnknown = GridItemType('Unknown', None)

    def __init__(self, xoffset, yoffset, grid=None):
        if grid is None:
            screengrab = ImageGrab.grab()

            # Let's try to adjust the offsets to see if there's a more accurate position.
            print("Searching for good reference point...")
            griditem, best_accuracy = guess_grid_item(get_avg_pixel(screengrab, xoffset, yoffset))
            best_x = xoffset
            best_y = yoffset
            search_r = 15
            positions = list(itertools.product(
                range(xoffset - search_r, xoffset + search_r),
                range(yoffset - search_r, yoffset + search_r))
            )
            for posx, posy in positions:
                griditem, accuracy = guess_grid_item(get_avg_pixel(screengrab, posx, posy))
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_x = posx
                    best_y = posy
                if best_accuracy > 0.90:
                    break

            xoffset = best_x
            yoffset = best_y

            self.xoffset = xoffset
            self.yoffset = yoffset

            if not self.update():
                print("ERROR: Initial accuracy of board recognition is too low.")
                sys.exit(1)
        else:
            self.grid = grid

            self.xoffset = xoffset
            self.yoffset = yoffset

    def update(self, compareprevious=False):
        screengrab = ImageGrab.grab()
        lowest_accuracy = 1.00
        newgrid = []
        item_changed = False
        for x in range(5):
            column = []
            for y in range(5):
                posx = self.xoffset + (x * 50)
                posy = self.yoffset + (y * 50)
                #print("{0}, {1} : {2}".format(x, y, get_avg_pixel(screengrab, posx, posy)))
                griditemtype, accuracy = guess_grid_item(get_avg_pixel(screengrab, posx, posy))
                #colors += " {0:>10}({1:>03.1f}%)".format(gem.name, accuracy * 100.0)
                column.append(GridItem(griditemtype))
                if accuracy < lowest_accuracy:
                    lowest_accuracy = accuracy
                if compareprevious and griditemtype != self.grid[x][y].itemtype:
                    item_changed = True
            newgrid.append(column)

        if lowest_accuracy < 0.60:
            #print("WARNING: Lowest accuracy was {0:02.1f}%".format(lowest_accuracy * 100.0))
            return False
        if compareprevious and not item_changed:
            print("Warning, grid did not change.")
        self.grid = newgrid
        return True

    def describe_grid_large(self):
        desc = ""

        row = " "
        for x in range(5):
            row += " {0:>10}".format(x+1)
        desc += row + "\n"
        for y in range(5):
            row = "{0}".format(y+1)
            for x in range(5):
                if self.grid[x][y] is None:
                    row += " {0:>10}".format("Empty")
                elif self.grid[x][y].cleared:
                    row += " {0:>7}(c)".format(self.grid[x][y].itemtype.name)
                else:
                    row += " {0:>10}".format(self.grid[x][y].itemtype.name)
            desc += row + "\n"
        return desc

    def describe_grid(self):
        desc = ""

        row = " "
        for x in range(5):
            row += str(x+1)
        desc += row + "\n"
        for y in range(5):
            row = str(y+1)
            for x in range(5):
                if self.grid[x][y] is None:
                    row += " "
                elif self.grid[x][y].cleared:
                    row += self.grid[x][y].itemtype.name[0].lower()
                else:
                    row += self.grid[x][y].itemtype.name[0]
            desc += row + "\n"
        return desc

    def print_grid(self):
        print(self.describe_grid())

    def best_move(self, depth=2):
        """
        Find the best move.
        depth: How many moves deep to simulate.
        How many simulations get run can be calculated as 40^depth,
        However it will ignore useless moves like swapping identical colors
        """
        best_move = None

        possible_moves = []

        for x, y in [(x, y) for x in range(4) for y in range(4)]:
            # Swap right
            possible_moves.append(Move(x, y, self.grid[x][y].itemtype, x+1, y, self.grid[x+1][y].itemtype))
            # Swap down
            possible_moves.append(Move(x, y, self.grid[x][y].itemtype, x, y+1, self.grid[x][y+1].itemtype))
        # Check bottom row moves.
        y = 4
        for x in range(4):
            # Swap right
            possible_moves.append(Move(x, y, self.grid[x][y].itemtype, x+1, y, self.grid[x+1][y].itemtype))
        # Check right column moves.
        x = 4
        for y in range(4):
            # Swap down
            possible_moves.append(Move(x, y, self.grid[x][y].itemtype, x, y+1, self.grid[x][y+1].itemtype))

        for move in possible_moves:
            # Skip this move if it's identical color to identical color.
            if self.grid[move.x1][move.y1].itemtype == self.grid[move.x2][move.y2].itemtype:
                continue
            if Grid.debug:
                logging.debug("Depth: {0} Testing move: {1}".format(depth, move.describe()))
            newboard = deepcopy(self)
            newboard.swap(move)
            points, submove = newboard.simulate(depth)
            move.points = points
            move.submove = submove

            if best_move is None:
                best_move = move
            elif move.get_total_points() > best_move.get_total_points():
                best_move = move
            elif move.get_total_points() == best_move.get_total_points():
                # Favor the move that acquries points earlier.
                best_submove = best_move.submove
                submove = move.submove
                while best_submove is not None and submove is not None:
                    if submove.points > best_submove.points:
                        best_move = move
                        break
                    best_submove = best_submove.submove
                    submove = submove.submove

        return best_move

    def do_swap(self, swap, delay, timeout=30.000):

        x1 = swap.x1 * 50 + self.xoffset
        y1 = swap.y1 * 50 + self.yoffset
        x2 = swap.x2 * 50 + self.xoffset
        y2 = swap.y2 * 50 + self.yoffset

        retry_count = 0
        while True:
            retry_count += 1
            Mouse.move(x1, y1)
            time.sleep(0.010)
            if Mouse.cursor_is_hand():
                break
            elif retry_count > 5:
                print("ERROR: cursor was not hand at intended click target.")
                print("Current: {0} Hand: {1} Arrow: {2}".format(
                    Mouse.get_cursor(), Mouse.hand_cursor, Mouse.arrow_cursor))
                return False
            time.sleep(0.200)
        #print("Clicking: {0}".format((x1, y1)))
        Mouse.click(x1, y1)
        time.sleep(delay)
        starttime = time.time()
        #print("Clicking: {0}".format((x2, y2)))
        Mouse.click(x2, y2)
        time.sleep(0.100)
        #if swap.points > 0 and Mouse.cursor_is_hand():
        #    print("ERROR: Move didn't start.")
        #    return False
        time.sleep(delay)
        while True:
            Mouse.move(x2, y2)
            time.sleep(0.010)
            if Mouse.cursor_is_hand():
                return True
            if starttime + timeout < time.time():
                print("ERROR: Timed out waiting for move to complete.")
                return False
            time.sleep(0.100)
        time.sleep(delay)

    def swap(self, swap):
        tempgem = self.grid[swap.x1][swap.y1]
        self.grid[swap.x1][swap.y1] = self.grid[swap.x2][swap.y2]
        self.grid[swap.x2][swap.y2] = tempgem

    def simulate(self, depth=1, fillrandom=False, probabilitypoints=True):
        """
        Estimate how many points the current board would generate.
        depth: How many moves deep to simulate. If greater than 1, then
         additional best moves will be calculated on each simulated result.
        """
        points = 0.0
        sub_move = None

        if Grid.debug:
            logging.debug("Simulating board:\n{0}".format(self.describe_grid()))
        firstpoints = self.clear(probabilitypoints)

        simpoints = 0
        newpoints = firstpoints
        while newpoints > 0:
            simpoints += newpoints
            self.drop()
            self.fill(fillrandom)
            newpoints = self.clear(probabilitypoints)
        points += float(simpoints)
        if Grid.debug:
            logging.debug("Points: {0} End Board:\n{1}".format(points, self.describe_grid()))

        if depth > 1:
            # determine the next best move.
            sub_move = self.best_move(depth - 1)

        return points, sub_move

    def drop(self):
        """
        Examine grid for cleared gems, drop remaining gems above.
        """
        # Drop the columns.
        for x in range(5):
            for y in reversed(range(5)):
                while not self.grid[x][y] is None and self.grid[x][y].cleared:
                    if y > 0:
                        # Drop down the items above.
                        for y2 in reversed(range(y)):
                            self.grid[x][y2 + 1] = self.grid[x][y2]
                    # Clear the top item.
                    self.grid[x][0] = None
        if Grid.debug:
            for x, y in [(x, y) for x in range(5) for y in range(5)]:
                if self.grid[x][y] is not None and self.grid[x][y].cleared:
                    print("ERROR: Grid was not fully cleared.")
                    sys.exit(1)

    def fill(self, fillrandom=False):
        """
        Replace empty spots on the grid with unknown or random items.
        """
        for x, y in [(x, y) for x in range(5) for y in range(5)]:
            if self.grid[x][y] is None:
                if fillrandom:
                    self.grid[x][y] = GridItem(Grid.GridItemTypes[random.randrange(len(Grid.GridItemTypes))])
                else:
                    self.grid[x][y] = GridItem(Grid.GridItemTypeUnknown)

    @staticmethod
    def clear_items(item1, item2, item3):
        if item1.itemtype == Grid.GridItemTypeUnknown or \
                item2.itemtype == Grid.GridItemTypeUnknown or \
                item3.itemtype == Grid.GridItemTypeUnknown:
            return
        elif item1.itemtype == item2.itemtype and item2.itemtype == item3.itemtype:
            item1.cleared = True
            item2.cleared = True
            item3.cleared = True

    def clear(self, probabilitypoints=True):
        # This method should be overriden and dfeined fot the specific game.
        raise Exception("clear method not implemented.")

    def simulate_play(self, depth=2):
        # Do a simulation run
        randomgrid = []
        for x in range(5):
            column = []
            for y in range(5):
                column.append(GridItem(Grid.GridItemTypes[random.randrange(len(Grid.GridItemTypes))]))
            randomgrid.append(column)
        self.grid = randomgrid
        # Normalize the board so nothing is ready to clear.
        self.simulate(fillrandom=True, probabilitypoints=False)
        print("Random starting grid:")
        self.print_grid()

        total_points = 0
        total_moves = 0
        while True:
            move = self.best_move(depth)
            print("Best Move Sequence: {0}".format(move.describe()))
            if move.get_total_points() == 0.0:
                print("ERROR: Calculated move sequence gives zero points.")
                sys.exit(1)
            points = 0
            while points == 0:
                total_moves += 1
                self.swap(move)
                points, sub_move = self.simulate(fillrandom=True, probabilitypoints=False)
                total_points += points
                print("Actual points: {0} Average points: {1:0.1f} Energy Spent: {2}".format(
                    points, (float(total_points) / total_moves), total_moves))
                if Grid.fast0:
                    move = move.submove
                else:
                    points = -1

    def play(self, remaining_energy, depth=2):
        startime = time.time()
        while remaining_energy > 0:
            retry_count = 0
            while True:
                if not self.update():
                    retry_count += 1
                    if retry_count >= 10:
                        print("Failed to accurately update board 10 times. Giving up.")
                        sys.exit(1)
                    else:
                        time.sleep(1.0)
                else:
                    break

            print("Calculating move...")
            movestartime = time.time()
            if remaining_energy < depth:
                move = self.best_move(depth=remaining_energy)
            else:
                move = self.best_move(depth)
            duration = time.time() - movestartime
            print("Calculating best move took: {0:.3f}s".format(duration))
            print("Best Move Sequence: {0}".format(move.describe()))
            if move.get_total_points() == 0.0:
                print("ERROR: Calculated move sequence gives zero points.")
                sys.exit(1)
            if remaining_energy <= depth and move.get_total_points() < 1.0:
                print("Not using last energy, no move give points.")
                break
            lastmove_points = 0
            # Iterate over moves until one is performed that is expected to give >0 points
            while lastmove_points == 0:
                remaining_energy -= 1
                if not self.do_swap(move, Grid.delay):
                    sys.exit(1)
                if remaining_energy > 1:
                    time.sleep(Grid.delay)
                if Grid.fast0:
                    lastmove_points = move.points
                    move = move.submove
                else:
                    lastmove_points = -1

        duration = time.time() - startime
        print("Moves complete, total time: {0:.3f}s".format(duration))