__author__ = 'Jody Shumaker'

import itertools
import copy
import sys
import logging
import time
import random
from multiprocessing import Pool, cpu_count
import signal
from utility.logconfig import *

from PIL import ImageGrab

from utility.mouse import *
from utility.screen import *

# Adjustment factor for each level deep in move sequence.
depth_factor = 0.75
# Offset from center used for comparison.
grid_compare_box = (-4, -4, 5, 5)


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

    def get_total_points(self):
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

    def __init__(self, name, image):
        self.name = name
        if image is not None:
            self.image = Image.open(image)
        else:
            self.image = None
        self.index = GridItemType.count
        GridItemType.count += 1

    def __hash__(self):
        return self.index

    def __eq__(self, other):
        return self.index == other.index

    def __str__(self):
        return self.name


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

    def __init__(self, grid=None, depth=3, processes=-1, calibrate=False):
        self.cleared = None
        self.depth = depth
        self.grid = None
        self.game_window = None
        self.game_center = None
        self.xoffset = None
        self.yoffset = None
        self.energy_pos = None
        if processes == -1:
            self.processes = cpu_count()
        else:
            self.processes = processes

        self.selected_image = Image.open('grid/selected.png')

        logging.info("Loading digits...")
        self.digits = []
        scriptdir = os.path.dirname(os.path.realpath(__file__))
        globstring = os.path.join(scriptdir, "grid/digits/*.png")
        for file in glob.glob(globstring):
            name = os.path.basename(file)
            name, ext = os.path.splitext(name)
            self.digits.append((name, Image.open(file)))
            logging.log(VERBOSE, "Loaded digit: {0}".format(name))
        if grid is None:
            self.game_window = get_game_window()
            self.game_center = (int((self.game_window[2] - self.game_window[0]) / 2) + self.game_window[0],
                                int((self.game_window[3] - self.game_window[1]) / 2) + self.game_window[1])

            # Give the game focus.
            safe_click_pos = (max(0, self.game_window[0] - 1), max(0, self.game_window[1]))
            Mouse.click(*safe_click_pos)

            self.set_grid_pos()

            if calibrate:
                self.calibrate()

            #Move the mouse away
            win32api.SetCursorPos((self.xoffset - 50, self.yoffset - 50))
            time.sleep(0.050)
            screengrab = ImageGrab.grab()

            # Adjust the offset.
            logging.info("Searching for top left item...")
            logging.log(VERBOSE, "Searching around {0},{1}".format(self.xoffset, self.yoffset))
            griditem, offsetx, offsety = self.detect_item_type(screengrab, self.xoffset, self.yoffset, radius=20)
            if griditem is None:
                logging.error('Failed to find top left item.')
                sys.exit(1)
            self.xoffset += offsetx
            self.yoffset += offsety
            logging.log(VERBOSE, "Centered on {0},{1}, item {2}".format(self.xoffset, self.yoffset, griditem.name))

            if not self.update():
                logging.error("Initial accuracy of board recognition is too low.")
                sys.exit(1)
        else:
            #Use the supplied grid.
            self.grid = grid

    @staticmethod
    def detect_item_type(screengrab, x, y, radius=2):
        searchx = x + grid_compare_box[0]
        searchy = y + grid_compare_box[1]
        images = []
        for itemtype in Grid.GridItemTypes:
            images.append((itemtype, itemtype.image))
        itemtype, x, y = detect_image(screengrab, images, searchx, searchy, radius=radius)
        offsetx = x - searchx
        offsety = y - searchy
        logging.debug("Found {} at offset {},{}".format(itemtype, offsetx, offsety))
        return itemtype, offsetx, offsety

    def set_grid_pos(self):
        self.xoffset = None
        self.yoffset = None
        raise Exception("set_grid_pos must be overridden.")

    def set_energy_pos(self):
        self.energy_pos = (0, 0)
        raise Exception("set_energy_pos must be overridden.")

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
        newgrid = []
        item_changed = False
        update_failed = 0
        for x in range(5):
            column = []
            for y in range(5):
                posx = self.xoffset + (x * 50)
                posy = self.yoffset + (y * 50)
                griditemtype, offsetx, offsety = self.detect_item_type(screengrab, posx, posy)
                if griditemtype is None:
                    update_failed += 1
                elif compareprevious and griditemtype != self.grid[x][y]:
                    item_changed = True
                column.append(griditemtype)
            newgrid.append(column)

        if update_failed > 0:
            logging.log(VERBOSE, "Failed to update the grid for {} items".format(update_failed))
            return False
        if compareprevious and not item_changed:
            logging.warning("Grid did not change.")
        oldgrid = self.grid
        self.grid = newgrid

        # Make sure the game didn't enter some bad state.
        self.clear()
        if self.drop() > 0:
            logging.warning("The updated grid contains gems that should have cleared.")
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
        logging.info("Grid\n" + self.describe_grid())

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
            logging.debug("Launching 4 threads...")
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

    def do_swap(self, swap, timeout=30.000):

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
                logging.error("ERROR: cursor was not hand at intended click target.")
                logging.error("Current: {0} Hand: {1} Arrow: {2}".format(
                    Mouse.get_cursor(), Mouse.hand_cursor, Mouse.arrow_cursor))
                return False
            time.sleep(0.100)
        Mouse.click(x1, y1)
        # Wait for selection reticule to come up.
        select_timeout = time.time() + 2.0
        while time.time() < select_timeout:
            x, y = image_search(ImageGrab.grab(), self.selected_image, x1 - 25, y1 - 25)
            if x != -1:
                logging.debug("Reticule offset: {0}, {1}".format(x - x1 + 25, y - y1 + 25))
                break
        starttime = time.time()
        Mouse.click(x2, y2)
        deselect_timeout = time.time() + 2.0
        while time.time() < deselect_timeout:
            x, y = image_search(ImageGrab.grab(), self.selected_image, x1 - 25, y1 - 25)
            if x == -1:
                break
        time.sleep(0.100)
        while True:
            # Jitter the mouse, or else it doesn't seem to always update.
            Mouse.move(x2-50, y2-50)
            Mouse.move(x2, y2)
            time.sleep(0.010)
            if Mouse.cursor_is_hand():
                return True
            if starttime + timeout < time.time():
                logging.error("Timed out waiting for move to complete.")
                return False
            time.sleep(0.100)

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
            logging.error("No cleared data, can't drop.")
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
            logging.info("Random starting grid:")
            self.print_grid()
            sim_moves = 0
            while sim_moves < energy:
                move = self.best_move(depth, thread=True)
                if move.get_total_points() == 0.0:
                    logging.error("Calculated move sequence gives zero points.")
                    sys.exit(1)
                points = 0
                while points == 0:
                    total_moves += 1
                    sim_moves += 1
                    self.swap(move)
                    points, sub_move = self.simulate(fillrandom=True, probabilitypoints=False)
                    total_points += points
                    if total_moves % 10 == 1:
                        logging.info("Move Points | Avg Points | Sim Moves | Total Moves | Avg Calc Time")
                    logging.info("{0:>11} | {1:>10.1f} | {2:>9} | {3:11} | {4:0.1f}".format(
                        points, (float(total_points) / total_moves), sim_moves, total_moves,
                        (time.time() - starttime) / total_moves))
                    if Grid.fast0:
                        move = move.submove
                    else:
                        points = -1

    def parse_energy(self):
        energy = 0
        # Find the first digit.
        screengrab = ImageGrab.grab()
        self.set_energy_pos()

        logging.log(VERBOSE, "Searching for first digit at offset {0},{1}".format(*self.energy_pos))
        name, digit_posx, digit_posy = detect_image(screengrab, self.digits, *self.energy_pos,
                                                    yradius=1, xradius=40, algorithm=SEARCH_LEFT_TO_RIGHT,
                                                    threshold=7440)

        if name is None:
            logging.error("Failed to find first energy digit.")
            sys.exit(1)
        logging.log(VERBOSE, "Found first energy digit {0}, at offset {1},{2}".format(name,
                    digit_posx - self.energy_pos[0], digit_posy - self.energy_pos[1]))

        while name is not None:
            energy = energy * 10 + int(name)
            lastx = digit_posx
            lasty = digit_posy
            name, digit_posx, digit_posy = detect_image(screengrab, self.digits, digit_posx + 25, digit_posy,
                                                        yradius=0, xradius=6, algorithm=SEARCH_LEFT_TO_RIGHT,
                                                        threshold=7440)
            if name is not None:
                logging.log(VERBOSE, "Found energy digit {0}, at {1},{2}".format(name,
                            digit_posx - lastx, digit_posy - lasty))
        return energy

    def play(self, remaining_energy, depth=2):
        if remaining_energy < 0:
            logging.info("Parsing energy remaining...")
            remaining_energy = self.parse_energy()
            logging.info("{0} energy remaining.".format(remaining_energy))
            if remaining_energy == 0:
                return

        startime = time.time()
        startenergy = remaining_energy
        while remaining_energy > 0:
            retry_count = 0
            while True:
                if not self.update():
                    retry_count += 1
                    if retry_count >= 20:
                        logging.error("Failed to accurately update board 20 times. Giving up.")
                        sys.exit(1)
                    else:
                        time.sleep(0.5)
                else:
                    break

            logging.log(VERBOSE, "Calculating move...")
            movestartime = time.time()
            if remaining_energy < depth:
                move = self.best_move(depth=remaining_energy, thread=True)
            else:
                move = self.best_move(depth, thread=True)
            duration = time.time() - movestartime
            logging.log(VERBOSE, "Calculating best move took: {0:.3f}s".format(duration))
            logging.info("Best Move Sequence: {0}".format(move.describe()))
            if move.get_total_points() == 0.0:
                logging.error("ERROR: Calculated move sequence gives zero points.")
                sys.exit(1)
            if remaining_energy <= depth and move.get_total_points() < 1.0:
                logging.info("Not using last energy, no move gives points.")
                break
            lastmove_points = 0
            # Iterate over moves until one is performed that is expected to give >0 points
            while lastmove_points == 0:
                remaining_energy -= 1
                if not self.do_swap(move):
                    sys.exit(1)
                if Grid.fast0:
                    lastmove_points = move.points
                    move = move.submove
                else:
                    lastmove_points = -1

        duration = time.time() - startime
        logging.info("Moves complete, total time: {0:.3f}s time per move: {1:.3f}s".format(
            duration, duration / startenergy))

    def calibrate(self):
        # Select the top left item.
        Mouse.click(self.xoffset, self.yoffset)
        time.sleep(0.500)
        # Search for the target reticule to get exact positioning.
        x, y = image_search(ImageGrab.grab(), self.selected_image, self.xoffset - 25, self.yoffset - 25, radius=15)
        if x != -1:
            logging.debug("Reticule offset: {0}, {1}".format(x - self.xoffset + 25, y - self.yoffset + 25))
        else:
            logging.error("Failed to find target reticule.")
            sys.exit(1)

        # Alter our offset based upon the target reticule
        self.xoffset = x + 25
        self.yoffset = y + 25

        # Deselect the top left item.
        Mouse.click(self.xoffset, self.yoffset)
        time.sleep(0.500)
        # Move mouse away
        Mouse.move(self.xoffset - 50, self.yoffset - 50)
        time.sleep(0.100)

        grid_images = []
        screengrab = ImageGrab.grab()
        for x in range(5):
            for y in range(5):
                image = screengrab.crop((
                    self.xoffset + (x * 50) + grid_compare_box[0],
                    self.yoffset + (y * 50) + grid_compare_box[1],
                    self.xoffset + (x * 50) + grid_compare_box[2],
                    self.yoffset + (y * 50) + grid_compare_box[3],
                ))
                match = False
                for image2 in grid_images:
                    if image_search(image, image2, 0, 0, radius=0)[0] != -1:
                        match = True
                        break
                if not match:
                    grid_images.append(image)

        logging.info("Found {} item types".format(len(grid_images)))
        image_count = 0
        for image in grid_images:
            image_count += 1
            image.save('grid{}.png'.format(image_count))
        sys.exit(0)