__author__ = 'Jody Shumaker'

import itertools
import copy
import sys
import logging
import time
import random
from multiprocessing import Pool, cpu_count
import signal

from PIL import ImageGrab

from utility.mouse import *
from utility.screen import *


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

    def __init__(self, xoffset, yoffset, grid=None, depth=3, processes=-1):
        self.cleared = None
        self.depth = depth
        self.grid = None
        if processes == -1:
            self.processes = cpu_count()
        else:
            self.processes = processes

        if grid is None:
            screengrab = ImageGrab.grab()

            # Let's try to adjust the offsets to see if there's a more accurate position.
            print("Searching for good reference point...")
            griditem, best_accuracy = guess_grid_item(get_avg_pixel(screengrab, xoffset, yoffset))
            best_x = xoffset
            best_y = yoffset
            for posx, posy in search_offset(radius=15, offsetx=xoffset, offsety=yoffset):
                griditem, accuracy = guess_grid_item(get_avg_pixel(screengrab, posx, posy))
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_x = posx
                    best_y = posy
                if best_accuracy > 0.95:
                    break

            xoffset = best_x
            yoffset = best_y

            self.xoffset = xoffset
            self.yoffset = yoffset

            if not self.update():
                print("ERROR: Initial accuracy of board recognition is too low.")
                sys.exit(1)
        else:
            #Use the supplied grid.
            self.grid = grid
            self.xoffset = xoffset
            self.yoffset = yoffset

    def copy_grid(self):
        """
        Copies our existing grid array to separate from a prior copy of this class
        :return:
        """
        newgrid = []
        for x in range(5):
            column = []
            for y in range(5):
                column.append(self.grid[x][y])
            newgrid.append(column)
        self.grid = newgrid

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
                column.append(griditemtype)
                if accuracy < lowest_accuracy:
                    lowest_accuracy = accuracy
                if compareprevious and griditemtype != self.grid[x][y]:
                    item_changed = True
            newgrid.append(column)

        if lowest_accuracy < 0.60:
            return False
        if compareprevious and not item_changed:
            print("WARNING: grid did not change.")
        oldgrid = self.grid
        self.grid = newgrid

        # Make sure the game didn't enter some bad state.
        self.clear()
        if self.drop() > 0:
            print("WARNING: The updated grid contains gems that should have cleared.")
            self.grid = oldgrid
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
                elif self.cleared is not None and self.cleared[x][y]:
                    row += " {0:>7}(c)".format(self.grid[x][y].name)
                else:
                    row += " {0:>10}".format(self.grid[x][y].name)
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
                elif self.cleared is not None and self.cleared[x][y]:
                    row += self.grid[x][y].name[0].lower()
                else:
                    row += self.grid[x][y].name[0]
            desc += row + "\n"
        return desc

    def print_grid(self):
        print(self.describe_grid())

    def process_move_multiprocess(self, move):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        newboard = copy.copy(self)
        newboard.copy_grid()
        newboard.swap(move)
        move.points, move.submove = newboard.simulate(self.depth)
        return move

    def best_move(self, depth=2, thread=False):
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
            possible_moves.append(Move(x, y, self.grid[x][y], x+1, y, self.grid[x+1][y]))
            # Swap down
            possible_moves.append(Move(x, y, self.grid[x][y], x, y+1, self.grid[x][y+1]))
        # Check bottom row moves.
        y = 4
        for x in range(4):
            # Swap right
            possible_moves.append(Move(x, y, self.grid[x][y], x+1, y, self.grid[x+1][y]))
        # Check right column moves.
        x = 4
        for y in range(4):
            # Swap down
            possible_moves.append(Move(x, y, self.grid[x][y], x, y+1, self.grid[x][y+1]))

        # Strip useless moves. We only want moves where the 2 items to swap are not equal.
        possible_moves = [move for move in possible_moves if self.grid[move.x1][move.y1] != self.grid[move.x2][move.y2]]

        # Shuffle the moves so we don't favor some specific order.
        random.shuffle(possible_moves)

        if thread and self.processes > 1:
            # Let the other processes know what depth to start at.
            self.depth = depth
            # Spin up threads to calculate the submoves.
            logging.info("Launching 4 threads...")
            try:
                pool = Pool(processes=self.processes)
                result = pool.map_async(self.process_move_multiprocess, possible_moves)
                while not result.ready():
                    time.sleep(0.010)
                possible_moves = result.get()
                pool.close()
            except KeyboardInterrupt:
                pool.terminate()
                sys.exit(1)
        else:
            for move in possible_moves:
                if Grid.debug:
                    logging.debug("Depth: {0} Testing move: {1}".format(depth, move.describe()))
                newboard = copy.copy(self)
                newboard.copy_grid()
                newboard.swap(move)
                move.points, move.submove = newboard.simulate(depth)

        # Determine which was the best move.
        for move in possible_moves:
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
        tempitem = self.grid[swap.x1][swap.y1]
        self.grid[swap.x1][swap.y1] = self.grid[swap.x2][swap.y2]
        self.grid[swap.x2][swap.y2] = tempitem

    def simulate(self, depth=1, fillrandom=False, probabilitypoints=True):
        """
        Estimate how many points the current board would generate.
        depth: How many moves deep to simulate. If greater than 1, then
         additional best moves will be calculated on each simulated result.
        """
        if Grid.debug:
            logging.debug("Simulating board:\n{0}".format(self.describe_grid()))
        
        sub_move = None
        points = self.clear(probabilitypoints)

        while self.drop() > 0:
            self.fill(fillrandom)
            points += self.clear(probabilitypoints)

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
        if self.cleared is None:
            print("No cleared data, can't drop.")
            sys.exit(1)
        drop_count = 0
        # Drop the columns.
        for x in range(5):
            newcolumn = [None, None, None, None, None]
            # Which row in the old column to pull from.
            yold = 4
            for ynew in reversed(range(5)):
                # Find the next uncleared gem.
                while yold >= 0 and self.cleared[x][yold]:
                    yold -= 1
                if yold < 0:
                    # Can't find uncleared item to drop.
                    drop_count += 1
                else:
                    newcolumn[ynew] = self.grid[x][yold]
                    yold -= 1
            self.grid[x] = newcolumn
        self.cleared = None
        return drop_count

    def fill(self, fillrandom=False):
        """
        Replace empty spots on the grid with unknown or random items.
        """
        for x, y in [(x, y) for x in range(5) for y in range(5)]:
            if self.grid[x][y] is None:
                if fillrandom:
                    self.grid[x][y] = Grid.GridItemTypes[random.randrange(len(Grid.GridItemTypes))]
                else:
                    self.grid[x][y] = Grid.GridItemTypeUnknown

    def clear_items(self, x1, y1, x2, y2, x3, y3):
        if self.grid[x1][y1] == Grid.GridItemTypeUnknown or \
                self.grid[x2][y2] == Grid.GridItemTypeUnknown or \
                self.grid[x3][y3] == Grid.GridItemTypeUnknown:
            return
        elif self.grid[x1][y1] == self.grid[x2][y2] and self.grid[x2][y2] == self.grid[x3][y3]:
            self.cleared[x1][y1] = True
            self.cleared[x2][y2] = True
            self.cleared[x3][y3] = True

    def clear(self, probabilitypoints=True):
        self.cleared = []
        for x in range(5):
            self.cleared.append([False]*5)
        # Scan rows
        for x, y in [(x, y) for x in range(3) for y in range(5)]:
            self.clear_items(x, y, x+1, y, x+2, y)
        # Scan columns
        for x, y in [(x, y) for x in range(5) for y in range(3)]:
            self.clear_items(x, y, x, y+1, x, y+2)
        # Method should be overridden from here to calculate and return the points
        return -1

    def simulate_play(self, depth=2, energy=100):

        starttime = time.time()
        total_points = 0
        total_moves = 0
        while True:
            # Do a simulation run of the given energy.
            randomgrid = []
            for x in range(5):
                column = []
                for y in range(5):
                    column.append(Grid.GridItemTypes[random.randrange(len(Grid.GridItemTypes))])
                randomgrid.append(column)
            self.grid = randomgrid
            # Normalize the board so nothing is ready to clear.
            self.simulate(fillrandom=True, probabilitypoints=False)
            print("Random starting grid:")
            self.print_grid()
            sim_moves = 0
            while sim_moves < energy:
                move = self.best_move(depth, thread=True)
                #print("Best Move Sequence: {0}".format(move.describe()))
                if move.get_total_points() == 0.0:
                    print("ERROR: Calculated move sequence gives zero points.")
                    sys.exit(1)
                points = 0
                while points == 0:
                    total_moves += 1
                    sim_moves += 1
                    self.swap(move)
                    points, sub_move = self.simulate(fillrandom=True, probabilitypoints=False)
                    total_points += points
                    if total_moves % 10 == 1:
                        print("Move Points | Avg Points | Sim Moves | Total Moves | Avg Calc Time")
                    print("{0:>11} | {1:>10.1f} | {2:>9} | {3:11} | {4:0.1f}".format(
                        points, (float(total_points) / total_moves), sim_moves, total_moves,
                        (time.time() - starttime) / total_moves))
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
                move = self.best_move(depth=remaining_energy, thread=True)
            else:
                move = self.best_move(depth, thread=True)
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