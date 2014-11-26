import argparse
from grid import *
import logging


class Board(Grid):
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
    GridItemType('Red', Color(172, 30, 25, 0)),
    GridItemType('Green', Color(54, 116, 37, 0)),
    GridItemType('Blue', Color(41, 103, 180, 0)),
    GridItemType('Purple', Color(126, 31, 167, 0)),
    GridItemType('Yellow', Color(182, 129, 40, 0))
]

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Automatically play LoA Gemology')
    parser.add_argument('--energy', '-e', type=int, default=-1, help="""
    Remaining energy. If not specified then will be prompted.
    """)
    parser.add_argument('--processes', '-p', type=int, default=-1, help="""
    How many processes to spin up for multiprocessing. Defaults to cpu count.
    """)
    parser.add_argument('--depth', type=int, default=3, help="""
    How many moves deep to predict. Defaults to 3.
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

    if args.calibrate:
        calibrate_colors()
        sys.exit(0)

    if args.simulate:
        board = Board(0, 0, [[None]*5]*5, depth=args.depth, processes=args.processes)
        if args.energy < 1:
            board.simulate_play(args.depth)
        else:
            board.simulate_play(args.depth, args.energy)

    loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(filename='gemology.log', level=loglevel)

    if args.energy > 0:
        remaining_energy = args.energy
    else:
        remaining_energy = int(input("How much gemology energy remain: "))

    game_window = get_game_window()
    game_center = (int((game_window[2] - game_window[0]) / 2) + game_window[0],
                   int((game_window[3] - game_window[1]) / 2) + game_window[1])

    # Give the game focus.
    safe_click_pos = (max(0, game_window[0] - 1), max(0, game_window[1]))
    Mouse.click(*safe_click_pos)

    xoffset = game_center[0] - 269
    yoffset = game_center[1] - 155

    board = Board(xoffset, yoffset, depth=args.depth, processes=args.processes)
    print("The starting grid appears to be:")
    board.print_grid()

    board.play(remaining_energy, depth=args.depth)