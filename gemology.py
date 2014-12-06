import argparse
from grid import *
from utility.logconfig import *
from utility.mouse import *
import logging

script_dir = os.path.dirname(os.path.realpath(__file__))

class Board(Grid):
    def set_grid_pos(self):
        self.xoffset = self.game_center[0] - 265
        self.yoffset = self.game_center[1] - 151

    def set_energy_pos(self):
        self.energy_pos = (self.game_center[0] - 340, self.game_center[1] - 257)

    def clear(self, probabilitypoints=True):
        """
        Mark gems as cleared and count points.
        """
        # Build in sets up the self.cleared grid.
        Grid.clear(self, probabilitypoints)

        # Count what is removed.
        removed = {}
        for itemtype in Grid.GridItemTypes:
            removed[itemtype] = 0

        for x, y in [(x, y) for x in range(5) for y in range(5)]:
            if self.cleared[x][y]:
                removed[self.grid[x][y]] += 1

        # Calculate points
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

        if probabilitypoints:
            # Add some probabilitiy points based upon the number of gems cleared.
            points += (1.0 - (0.8 ** gems_cleared)) * gems_cleared
        # Not possible to gain more than 60 points on a single clear.
        if points > 60:
            points = 60
        return points

Grid.GridItemTypes = [
    GridItemType('Red', script_dir + '/grid/gemology/Red.png'),
    GridItemType('Green', script_dir + '/grid/gemology/Green.png'),
    GridItemType('Blue', script_dir + '/grid/gemology/Blue.png'),
    GridItemType('Purple', script_dir + '/grid/gemology/Purple.png'),
    GridItemType('Yellow', script_dir + '/grid/gemology/Yellow.png')
]

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Automatically play LoA Gemology')
    parser.add_argument('--energy', '-e', type=int, default=-1, help="""
    Remaining energy. Default is to auto detect.
    """)
    parser.add_argument('--both', '-b', action='store_true', help="""
    Play both regular and advanced gemology. Forces auto energy detection.
    """)
    parser.add_argument('--processes', '-p', type=int, default=-1, help="""
    How many processes to spin up for multiprocessing. Defaults to cpu count.
    """)
    parser.add_argument('--depth', type=int, default=3, help="""
    How many moves deep to predict. Defaults to 3.
    Warning: potentially 40^depth moves have to be tested. Increasing this
    exponentially increases processing time.
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

    loglevel = VERBOSE
    if args.debug:
        loglevel = logging.DEBUG

    logconfig('gemology', loglevel)

    if args.debug:
        logging.info("Enabling debug mode.")
        Grid.debug = True

    if args.fast0:
        Grid.fast0 = True

    if args.calibrate:
        board = Board(calibrate=True)

    if args.simulate:
        board = Board(0, 0, [[None]*5]*5, depth=args.depth, processes=args.processes)
        if args.energy < 1:
            board.simulate_play(args.depth)
        else:
            board.simulate_play(args.depth, args.energy)
    if args.both:
        board = Board(depth=args.depth, processes=args.processes)
        # Regular.
        Mouse.click(board.xoffset - 146, board.yoffset - 10)
        time.sleep(1.000)
        board.update()
        logging.info("The regular starting grid appears to be:")
        board.print_grid()
        board.play(-1, depth=args.depth)
        # Advanced
        Mouse.click(board.xoffset - 146, board.yoffset + 60)
        time.sleep(1.000)
        board.update()
        logging.info("The advanced starting grid appears to be:")
        board.print_grid()
        board.play(-1, depth=args.depth)
    else:
        board = Board(depth=args.depth, processes=args.processes)
        logging.info("The starting grid appears to be:")
        board.print_grid()

        board.play(args.energy, depth=args.depth)