__author__ = 'Jody Shumaker'

from utility.mouse import *
from utility.screen import *
from utility.logconfig import *
import argparse
import os.path
from loa import *

script_dir = os.path.dirname(os.path.realpath(__file__))

parser = argparse.ArgumentParser(description='Click for gauntlet. Works for top left only, start 5 seconds before first target',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--first', '-f', action='store_true', help="Going first this round.")
group.add_argument('--second', '-s', dest='first', action='store_false', help="Going second this round.")
parser.add_argument('--rounds', '-r', type=int, default=15, help="Number of rounds left.")
parser.add_argument('--debug', action='store_true', help="""
Enable debug mode, extra details will be added to log file.
""")
args = parser.parse_args()

loglevel = VERBOSE
if args.debug:
    loglevel = logging.DEBUG
logconfig('gauntlet', loglevel)

# Resources.


def handle_win_f4():
    sys.exit(0)


class Gauntlet:
    def __init__(self, game=None):
        if game is None:
            self.game = LeagueOfAngels()
        else:
            self.game = game
        self.morale_image = Image.open(os.path.join(script_dir, "misc/Morale.png"))

    def play(self, first, rounds=15):
        round_count = 0
        while round_count < rounds:
            starttime = time.time()
            round_count += 1
            if first:
                kill_count = 3
            else:
                kill_count = 2
            for i in range(kill_count):
                timeout = time.time() + 10.0
                while time.time() < timeout:
                    self.game.click(518, 125)
                    time.sleep(0.100)
                time.sleep(10.0)
            #Wait between rounds
            if first:
                # We were first, we're now going to be second so we want to wait an extra 10 sceonds.
                first = False
                timeout = starttime + 130.2
            else:
                timeout = starttime + 110.2
                first = True

            while time.time() < timeout:
                time.sleep(0.500)

gauntlet = Gauntlet()
gauntlet.play(args.first, args.rounds)