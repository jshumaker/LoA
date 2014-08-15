from ctypes import *
import time
import math
import itertools
import random
import sys
import os
import logging
from PIL import ImageGrab, Image
from enum import Enum
from copy import deepcopy
import win32api
import win32con
import argparse



class color:
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a
        # Calculate the furthest distance a color could be from this color.
        self.max_distance = math.sqrt( (self.r if self.r > 128 else 255 - self.r)**2 + (self.g if self.g > 128 else 255 - self.g)**2 + (self.b if self.b > 128 else 255 - self.b)**2 )
    def __str__(self):
        return "R{0:03d}G{1:03d}B{2:03d}A{3:03d}".format(int(self.r), int(self.g), int(self.b), int(self.a))
    def compare(self, color2):
        distance = math.sqrt((self.r - color2.r)**2 + (self.g - color2.g)**2 + (self.b - color2.b)**2)
        if distance < 1:
            distance = 1
        accuracy = (((self.max_distance - distance)  / self.max_distance )** 3)
        # Let's consider 20 % a rough floor. It's rare to get below that without looking at extremes
        accuracy = (accuracy - 0.20) / 0.8
        if accuracy < 0:
            accuracy = 0
        return accuracy


class GemColor(Enum):
    Unknown = 0
    Red = 1
    Green = 2
    Blue = 3
    Yellow = 4
    Purple = 5
gem_color_red = color(172, 30, 25, 0)
gem_color_green = color(54, 116, 37, 0)
gem_color_blue = color(41, 103, 180, 0)
gem_color_purple = color(126, 31, 167, 0)
gem_color_yellow = color(182, 129, 40, 0)

def guess_gem_color(pixel):
    closest_amount = gem_color_red.compare(pixel)
    closest_color = GemColor.Red
    green_amount = gem_color_green.compare(pixel)
    blue_amount = gem_color_blue.compare(pixel)
    purple_amount = gem_color_purple.compare(pixel)
    yellow_amount = gem_color_yellow.compare(pixel)
    if (green_amount > closest_amount):
        closest_color = GemColor.Green
        closest_amount = green_amount
    if (blue_amount > closest_amount):
        closest_color = GemColor.Blue
        closest_amount = blue_amount
    if (purple_amount > closest_amount):
        closest_color = GemColor.Purple
        closest_amount = purple_amount
    if (yellow_amount > closest_amount):
        closest_color = GemColor.Yellow
        closest_amount = yellow_amount
    return closest_color, closest_amount



def getpixel(image, x,y):
    r, g, b = image.getpixel((x, y))
    return color(r, g, b, 0)

def get_avg_pixel(image, x, y, r=15):
    avgpixel = color(0,0,0,0)
    count = (r * 2) ** 2
    for posx in range(x - r, x + r):
        for posy in range(y - r, y + r):
            p = getpixel(image, posx,posy)
            avgpixel.r += p.r / float(count)
            avgpixel.g += p.g / float(count)
            avgpixel.b += p.b / float(count)
            avgpixel.a += p.a / float(count)
    return avgpixel

def click_mouse(x,y):
    win32api.SetCursorPos((x,y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)

class Move:
    """
    Captures data related to a move.
    """

    def __init__(self, x1, y1, color1, x2, y2, color2):
        self.x1 = x1
        self.y1 = y1
        self.color1 = color1
        self.x2 = x2
        self.y2 = y2
        self.color2 = color2

        self.points = 0
        self.submove = None

    def get_total_points(self, depth_factor=0.75):
        if self.submove is None:
            return self.points
        else:
            # Until something is accounted for unknown blocks creating matches, we need t oslightly favor clearing things earlier.
            return self.points + (self.submove.get_total_points() * depth_factor)

    def describe(self):
        description = "{0},{1}({2})<->{3},{4}({5}) {6:0.1f}pts".format(
            self.x1 + 1, self.y1 + 1, self.color1.name[0],
            self.x2 + 1, self.y2 + 1, self.color2.name[0],
            self.points)
        if self.submove is None:
            return description
        else:
            return "{0}, {1}".format(description, self.submove.describe())



class Gem:
    def __init__(self, color):
        self.color = color
        self.cleared = False

class Board:
    def __init__(self, xoffset, yoffset, grid= None):
        if grid is None:
            screengrab = ImageGrab.grab()

            # Let's try to adjust the offsets to see if there's a more accurate position.
            print("Searching for good reference point...")
            gem, best_accuracy = guess_gem_color(get_avg_pixel(screengrab, xoffset, yoffset))
            best_x = xoffset
            best_y = yoffset
            search_r = 25
            positions = list(itertools.product(range(xoffset - search_r, xoffset + search_r), range(yoffset - search_r, yoffset + search_r)))
            for posx, posy in positions:
                gem, accuracy = guess_gem_color(get_avg_pixel(screengrab, posx, posy))
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_x = posx
                    best_y = posy
                if best_accuracy > 0.90:
                    break;

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

    def update(self):
        screengrab = ImageGrab.grab()
        lowest_accuracy = 1.00
        self.grid = []
        for x in range(5):
            column = []
            for y in range(5):
                posx = self.xoffset + (x * 50)
                posy = self.yoffset + (y * 50)
                #print("{0}, {1} : {2}".format(x, y, get_avg_pixel(screengrab, posx, posy)))
                color, accuracy = guess_gem_color(get_avg_pixel(screengrab, posx, posy))
                #colors += " {0:>10}({1:>03.1f}%)".format(gem.name, accuracy * 100.0)
                column.append(Gem(color))
                if accuracy < lowest_accuracy:
                    lowest_accuracy = accuracy
            self.grid.append(column)
            
        if lowest_accuracy < 0.60:
            #print("WARNING: Lowest accuracy was {0:02.1f}%".format(lowest_accuracy * 100.0))
            return False
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
                    row += " {0:>7}(c)".format(self.grid[x][y].color.name)
                else:
                    row += " {0:>10}".format(self.grid[x][y].color.name)
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
                    row += self.grid[x][y].color.name[0].lower()
                else:
                    row += self.grid[x][y].color.name[0]
            desc += row + "\n"
        return desc

    def print_grid(self):
        print(self.describe_grid())

    def describe_move(self, move, sub_moves):
        return "Swap: {0},{1}({2}) with {3},{4}({5}) followed by {6}".format(move[0] + 1, move[1] + 1, self.grid[move[0]][move[1]].color.name, move[2] + 1, move[3] + 1, self.grid[move[2]][move[3]].color.name, sub_moves)

    def best_move(self, depth=3):
        """
        Find the best move.
        depth: How many moves deep to simulate.
        How many simulations get run can be calculated as 40^depth,
        However it will ignore useless moves like swapping identical colors
        """
        best_move = None

        possible_moves = []

        for x, y in [(x,y) for x in range(4) for y in range(4)]:
            # Swap right
            possible_moves.append(Move(x,y,self.grid[x][y].color, x+1,y,self.grid[x+1][y].color))
            # Swap down
            possible_moves.append(Move(x,y,self.grid[x][y].color, x,y+1,self.grid[x][y+1].color))
        # Check bottom row moves.
        y = 4
        for x in range(4):
            # Swap right
            possible_moves.append(Move(x,y,self.grid[x][y].color, x+1,y,self.grid[x+1][y].color))
        # Check right column moves.
        x = 4
        for y in range(4):
            # Swap down
            possible_moves.append(Move(x,y,self.grid[x][y].color, x,y+1,self.grid[x][y+1].color))

        for move in possible_moves:
            # Skip this move if it's identical color to identical color.
            if self.grid[move.x1][move.y1].color == self.grid[move.x2][move.y2].color:
                continue
            if args.debug:
                logging.debug("Depth: {0} Testing move: {1}".format(depth, move.describe()))
            newboard = deepcopy(self)
            newboard.swap(move)
            points, submove  = newboard.simulate(depth)
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
                    if (submove.points > best_submove.points):
                        best_move = move
                        break
                    best_submove = best_submove.submove
                    submove = submove.submove


        return best_move

    def do_swap(self, swap, delay):
        
        x1 = swap.x1 * 50 + self.xoffset
        y1 = swap.y1 * 50 + self.yoffset
        x2 = swap.x2 * 50 + self.xoffset
        y2 = swap.y2 * 50 + self.yoffset
        #print("Clicking: {0}".format((x1, y1)))
        click_mouse(x1, y1)
        time.sleep(delay)
        #print("Clicking: {0}".format((x2, y2)))
        click_mouse(x2, y2)

    def swap(self, swap):
        tempgem = self.grid[swap.x1][swap.y1]
        self.grid[swap.x1][swap.y1] = self.grid[swap.x2][swap.y2]
        self.grid[swap.x2][swap.y2] = tempgem

    def simulate(self, depth=1, fillrandom=False, probabilitypoints=True):
        """
        Estimate how many points the current board would generate.
        depth: How many moves deep to simulate. If greater than 1, then additional best moves will be calculated on each simulated result.
        """
        points =  0.0
        sub_move = None

        if args.debug:
            logging.debug("Simulating board:\n{0}".format(self.describe_grid()))
        firstpoints = self.clear(probabilitypoints)

        simpoints = 0
        newpoints = firstpoints
        while (newpoints > 0):
            simpoints += newpoints
            self.drop()
            self.fill(fillrandom)
            newpoints = self.clear(probabilitypoints)
        points += float(simpoints)
        if args.debug:
            logging.debug("Points: {0} End Board:\n{1}".format(points, self.describe_grid()))

        if depth > 1:
            # determine the next best move.
            sub_move = self.best_move(depth - 1)

        return points, sub_move


    def clear_chance(self, color1, color2, color3):
        if color1 == GemColor.Unknown or color2 == GemColor.Unknown or color3 == GemColor.Unknown:
            return 0.0
        elif color1 == color2 and color2 == color3:
            return 1.0
        else:
            return 0.0

    def clear(self, probabilitypoints=True):
        """
        Mark gems as cleared and count points.
        """
        # Calculate which gems to remove, counting how many of each color are removed.
        # TODO: Account for probability of unknown gems completing a match.
        # Scan rows
        for x, y in [(x,y) for x in range(3) for y in range(5)]:
            if self.clear_chance(self.grid[x][y].color, self.grid[x+1][y].color, self.grid[x+2][y].color) > 0.0:
                self.grid[x][y].cleared = True
                self.grid[x+1][y].cleared = True
                self.grid[x+2][y].cleared = True
        # Scan columns
        for x, y in [(x,y) for x in range(5) for y in range(3)]:
            if self.clear_chance(self.grid[x][y].color, self.grid[x][y+1].color, self.grid[x][y+2].color) > 0.0:
                self.grid[x][y].cleared = True
                self.grid[x][y+1].cleared = True
                self.grid[x][y+2].cleared = True
        # Count what is removed.
        removed = {
            GemColor.Red: 0,
            GemColor.Green: 0,
            GemColor.Blue: 0,
            GemColor.Purple: 0,
            GemColor.Yellow: 0
        }
        for x, y in [(x,y) for x in range(5) for y in range(5)]:
            if self.grid[x][y].cleared:
                removed[self.grid[x][y].color] += 1
        colors_cleared = 0
        gems_cleared = 0
        points = 0
        for color, count in removed.items():
            if count > 0:
                gems_cleared += count
                colors_cleared += 1
            if count == 3:
                points += 10
            elif count == 4:
                points += 20
            if count >= 5:
                points += 50
        # If more than one color is cleared, there's a 30 point bonus.
        if colors_cleared > 1:
            points += 30

        if probabilitypoints:
            # Add some probabilitiy points based upon the number of gems cleared.
            points += (1.0 - (0.8 ** gems_cleared)) * gems_cleared

        # Not possible to gain more than 60 points on a single clear.
        if points > 60:
            points = 60
        return points

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
                    self.grid[x][0] = None
                    # If there was nothing to drop down, we need to set the bottom most
        if args.debug:
            for x, y in [(x,y) for x in range(5) for y in range(5)]:
                if self.grid[x][y] is not None and self.grid[x][y].cleared:
                    print("ERROR: Grid was not fully cleared.")
                    sys.exit(1)

    def fill(self, fillrandom=False):
        """
        Fill the board with random gems.
        """
        for x, y in [(x,y) for x in range(5) for y in range(5)]:
            if self.grid[x][y] is None:
                if fillrandom:
                    self.grid[x][y] = Gem(GemColor(random.randint(1, 5)))
                else:
                    self.grid[x][y] = Gem(GemColor.Unknown)



parser = argparse.ArgumentParser(description='Automatically play LoA Gemology')
parser.add_argument('--depth', type=int, default=2, help='How many moves deep to predict. Defaults to 2. Warning: potentially 40^depth moves have to be tested. Increasing this exponentially increases processing time.')
parser.add_argument('--delay', type=float, default=1.5, help='How many seconds to wait after clicking. Default is 1.5. For slow connections or computers, increase this value.')
parser.add_argument('--fast0', action='store_true', help='If best move is a zero point move, perform the next submove without recalculating. Runs faster, but at expensive of highe raverage points.')
parser.add_argument('--debug', action='store_true', help='Enable debug mode, a gemology.log file will be output with details on the tested moves.')
parser.add_argument('--simulate', action='store_true', help='Enable simulation mode. Script will create a new random board and simulate best moves and results.')
args = parser.parse_args()



if args.simulate:
    # Do a simulation run
    randomgrid = []
    for x in range(5):
        column = []
        for y in range(5):
            column.append(Gem(GemColor(random.randint(1, 5))))
        randomgrid.append(column)
    board = Board(0,0,randomgrid)
    # Normalize the board so nothing is ready to clear.
    board.simulate(fillrandom=True, probabilitypoints=False)
    print("Random starting grid:")
    board.print_grid()

    total_points = 0
    total_moves = 0
    while True:
        move = board.best_move(args.depth)
        print("Best Move Sequence: {0}".format(move.describe()))
        if move.get_total_points() == 0.0:
            print("ERROR: Calculated move sequence gives zero points.")
            sys.exit(1)
        points = 0
        while points == 0:
            total_moves += 1
            board.swap(move)
            points, sub_move = board.simulate(fillrandom=True, probabilitypoints=False)
            total_points += points
            print("Actual points: {0} Average points: {1:0.1f} Energy Spent: {2}".format(points, (float(total_points) / total_moves), total_moves))
            if args.fast0:
                move = move.submove
            else:
                points = -1


gdi= windll.LoadLibrary("c:\\windows\\system32\\gdi32.dll")
dc = windll.user32.GetDC(0)

loglevel = logging.INFO
if args.debug:
    loglevel = logging.DEBUG
logging.basicConfig(filename='gemology.log',level=loglevel)


class _point_t(Structure):
    _fields_ = [
                ('x',  c_long),
                ('y',  c_long),
               ]

def get_cursor_position():
    point = _point_t()
    result = windll.user32.GetCursorPos(pointer(point))
    if result:  return (point.x, point.y)
    else:       return None
    


remaining_energy = int(input("How much gemology energy remain: "))

var = input("Place mouse over top left gem and press enter.")
xoffset, yoffset = get_cursor_position()

board = Board(xoffset, yoffset)
print("The starting grid appears to be:")
board.print_grid()

startime = time.time()
while remaining_energy > 0:
    retry_count = 0
    while True:
        if not board.update():
            retry_count += 1
            if retry_count >= 10:
                print("Failed to accurately update gemology board 10 times. Giving up.")
                sys.exit(1)
            else:
                time.sleep(1.0)
        else:
            break

    print("Calculating move...")
    movestartime = time.time()
    if remaining_energy < args.depth:
        move = board.best_move(depth=remaining_energy)
    else:
        move = board.best_move(args.depth)
    duration = time.time() - movestartime
    print("Calculating best move took: {0:.3f}s".format(duration))
    print("Best Move Sequence: {0}".format(move.describe()))
    if move.get_total_points() == 0.0:
        print("ERROR: Calculated move sequence gives zero points.")
        sys.exit(1)
    if remaining_energy <= args.depth and move.get_total_points() < 1.0:
        print("Not using last energy, no move give points.")
        break
    lastmove_points = 0
    # Iterate over moves until one is performed that is expected to give >0 points
    while lastmove_points == 0:
        remaining_energy -= 1
        board.do_swap(move,  args.delay)
        #blah = input("Press enter to calculate next move.")
        print("Waiting for move to complete...")
        if remaining_energy > 1:
            time.sleep(args.delay)
        if args.fast0:
            lastmove_points = move.points
            move = move.submove
        else:
            lastmove_points = -1

duration = time.time() - startime
print("Moves complete, total time: {0:.3f}s".format(duration))