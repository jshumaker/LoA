import argparse
from grid import *
import logging


class Element(GridItemType):
    def __init__(self, name, color, factor):
        GridItemType.__init__(self, name, color)
        self.factor = factor


class Board(Grid):
    # Bonus points to give for higher counts cleared. Increase to favor higher numbers of gems cleared.
    count_factor = 0.0

    def update(self):
        # Move the mouse out of the way so tooltip isn't there.
        win32api.SetCursorPos((self.xoffset - 50, self.yoffset - 50))
        time.sleep(0.01)
        return Grid.update(self)


    def clear(self, probabilitypoints=True):
        """
        Mark gems as cleared and count points.
        """
        # Calculate which gems to remove, counting how many of each color are removed.
        # Scan rows
        for x, y in [(x, y) for x in range(3) for y in range(5)]:
            self.clear_items(self.grid[x][y], self.grid[x+1][y], self.grid[x+2][y])
        # Scan columns
        for x, y in [(x, y) for x in range(5) for y in range(3)]:
            self.clear_items(self.grid[x][y], self.grid[x][y+1], self.grid[x][y+2])
        # Count what is removed.
        removed = {}
        for itemtype in Grid.GridItemTypes:
            removed[itemtype] = 0

        for x, y in [(x, y) for x in range(5) for y in range(5)]:
            if self.grid[x][y].cleared:
                removed[self.grid[x][y].itemtype] += 1
        items_cleared = 0
        points = 0
        for element, count in removed.items():
            element_points = 0
            if count > 0:
                items_cleared += count
            if count == 3:
                element_points += 10
            elif count == 4:
                element_points += 15
            if count >= 5:
                element_points += 20
            if probabilitypoints:
                points += element_points * element.factor
                points += count * Board.count_factor
            else:
                points += element_points
        if probabilitypoints:
            # Add some probabilitiy points based upon the number of gems cleared.
            points += (1.0 - (0.8 ** items_cleared)) * items_cleared
        return points


parser = argparse.ArgumentParser(description='Automatically play LoA Dragon Souls')
parser.add_argument('--energy', '-e', type=int, default=-1, help="""
Remaining energy. If not specified then will be prompted.
""")
parser.add_argument('--count', type=float, default=0.0, help="""
Count factor, defaults to 0.0.  This is multiplied by the number of elements of a specific type being cleared.
 Set above 0 to favor clearing more elements at once, which increases odds of better elements gained.
""")
parser.add_argument('--wind', type=float, default=1.0, help="""
Wind factor, defaults to 1.0.  This is multiplied by the points for clearing a given element.  Set below 1 to favor
 less, or above 1.0 to favor more.
""")
parser.add_argument('--ice', type=float, default=1.0, help="""
Ice factor, defaults to 1.0.  This is multiplied by the points for clearing a given element.  Set below 1 to favor
 less, or above 1.0 to favor more.
""")
parser.add_argument('--electro', type=float, default=1.0, help="""
Electro factor, defaults to 1.0.  This is multiplied by the points for clearing a given element.  Set below 1 to favor
 less, or above 1.0 to favor more.
""")
parser.add_argument('--fire', type=float, default=1.0, help="""
Fire factor, defaults to 1.0.  This is multiplied by the points for clearing a given element.  Set below 1 to favor
 less, or above 1.0 to favor more.
""")
parser.add_argument('--random', type=float, default=1.0, help="""
Random factor, defaults to 1.0.  This is multiplied by the points for clearing a given element.  Set below 1 to favor
 less, or above 1.0 to favor more.
""")
parser.add_argument('--depth', type=int, default=2, help="""
How many moves deep to predict. Defaults to 2.
Warning: potentially 40^depth moves have to be tested. Increasing this
exponentially increases processing time.
""")
parser.add_argument('--delay', type=float, default=1.0, help="""
How many seconds to wait after clicking. Default is 1.0.
For slow connections or computers, increase this value.
""")
parser.add_argument('--fast0', action='store_true', help="""
If best move is a zero point move, perform the next submove without recalculating.
Runs faster, but at expensive of higher average points.
""")
parser.add_argument('--debug', action='store_true', help="""
Enable debug mode, a gemology.log file will be output with details on the tested moves.
""")
parser.add_argument('--simulate', action='store_true', help="""
Enable simulation mode. Script will create a new random board and simulate best moves and results.
""")
parser.add_argument('--calibrate', action='store_true', help="""
Enable calibration mode. Given a mouse position, outputs color grid.
""")
args = parser.parse_args()

if args.debug:
    print("Enabling debug mode.")
    Grid.debug = True

if args.fast0:
    Grid.fast0 = True

Grid.delay = args.delay
Grid.GridItemTypes = [
    Element('Wind', Color(109, 159, 46, 0), args.wind),
    Element('Electro', Color(165, 119, 230, 0), args.electro),
    Element('Ice', Color(61, 174, 210, 0), args.ice),
    Element('Fire', Color(222, 158, 24, 0), args.fire),
    Element('Random', Color(118, 81, 51, 0), args.random)
]

if args.calibrate:
    Mouse.get_cursor()
    calibrate_colors()
    sys.exit(0)

if args.simulate:
    board = Board(0, 0, [])
    board.simulate_play(args.depth)


loglevel = logging.INFO
if args.debug:
    loglevel = logging.DEBUG
logging.basicConfig(filename='dragonsoul.log', level=loglevel)
    
if args.energy > 0:
    remaining_energy = args.energy
else:
    remaining_energy = int(input("How much dragon soul energy remain: "))

var = input("Place mouse over top left element and press enter.")
xoffset, yoffset = Mouse.get_position()

#Move the mouse away
win32api.SetCursorPos((xoffset - 50, yoffset - 50))
board = Board(xoffset, yoffset)
print("The starting grid appears to be:")
board.print_grid()

board.play(remaining_energy, depth=args.depth)