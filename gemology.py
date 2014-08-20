import argparse
from grid import *
import logging

class Board(Grid):
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

        possibly_removed = {}
        for itemtype in Grid.GridItemTypes:
            possibly_removed[itemtype] = []
        possibly_removed[Grid.GridItemTypeUnknown] = []

        for x, y in [(x, y) for x in range(5) for y in range(5)]:
            if self.grid[x][y].cleared >= 1.0:
                if self.grid[x][y].itemtype == Grid.GridItemTypeUnknown:
                    print("WARNING: unknown had probability {0:0.3f}".format(self.grid[x][y].cleared))
                else:
                    removed[self.grid[x][y].itemtype] += 1
            elif self.grid[x][y].cleared > 0.0:
                possibly_removed[self.grid[x][y].itemtype].append(self.grid[x][y].cleared)

        colors_cleared = 0
        gems_cleared = 0
        points = 0
        for itemtype, count in removed.items():
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

        # Not possible to gain more than 60 points on a single clear.
        if points >= 60:
            points = 60.0
        elif probabilitypoints:
            # We're not at max points, let's seee if we gain any from probability points.
            # Add probability points from unknown gems.
            colors_cleared_chance = 0.0
            for itemtype, chances in possibly_removed.items():
                # Skip colors that have no chance of clearing
                if len(chances) < 1:
                    continue
                chances = sorted(chances, reverse=True)
                probability3 = 0.0
                probability4 = 0.0
                probability5 = 0.0
                # If this is a chance of a known color clearing
                if itemtype != Grid.GridItemTypeUnknown:
                    # Simplistic algorithm only
                    if removed[itemtype] >= 5:
                        continue
                    elif removed[itemtype] == 0 and len(chances) > 2:
                        probability3 = chances[2]
                    elif removed[itemtype] == 3:
                        probability4 = chances[0]
                    elif removed[itemtype] == 4:
                        probability5 = chances[0]
                else:
                    # Unknown color, let's assume there might be an additional 3 gems of a unique color dropped.
                    if len(chances) >= 3:
                        probability3 = chances[0]
                # Probabilities calculated, let's add probability points.
                #print("Probabities 3: {0:0.3f} 4: {1:0.3f} 5: {2:0.3f}".format(
                #    probability3, probability4, probability5))
                points += probability3 * 10
                points += probability4 * 10
                points += probability5 * 20
                if colors_cleared < 2:
                    colors_cleared_chance = 1.0 - ((1.0 - colors_cleared_chance) * (1.0 - probability3))
            if colors_cleared < 2:
                points += colors_cleared_chance * 30
            if points > 60:
                points = 60.0

        return points


parser = argparse.ArgumentParser(description='Automatically play LoA Gemology')
parser.add_argument('--energy', '-e', type=int, default=-1, help="""
Remaining energy. If not specified then will be prompted.
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
    GridItemType('Red', Color(172, 30, 25, 0)),
    GridItemType('Green', Color(54, 116, 37, 0)),
    GridItemType('Blue', Color(41, 103, 180, 0)),
    GridItemType('Purple', Color(126, 31, 167, 0)),
    GridItemType('Yellow', Color(182, 129, 40, 0))
]

if args.calibrate:
    calibrate_colors()
    sys.exit(0)

if args.simulate:
    board = Board(0, 0, [])
    board.simulate_play(args.depth)


loglevel = logging.INFO
if args.debug:
    loglevel = logging.DEBUG
logging.basicConfig(filename='gemology.log', level=loglevel)
    
if args.energy > 0:
    remaining_energy = args.energy
else:
    remaining_energy = int(input("How much gemology energy remain: "))

var = input("Place mouse over top left gem and press enter.")
xoffset, yoffset = Mouse.get_position()

board = Board(xoffset, yoffset)
print("The starting grid appears to be:")
board.print_grid()

board.play(remaining_energy, depth=args.depth)