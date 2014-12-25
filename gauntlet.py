#!pythonw
__author__ = 'Jody Shumaker'

from utility.mouse import *
from utility.screen import *
from utility.logconfig import *
import argparse
import os.path
from loa import *
import pyhk

script_dir = os.path.dirname(os.path.realpath(__file__))

parser = argparse.ArgumentParser(description='Click for gauntlet.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--first', '-f', action='store_true')
group.add_argument('--second', '-s', dest='first', action='store_false')
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


hot = pyhk.pyhk()
hot.addHotkey(['Win', 'F4'], handle_win_f4)


class Gauntlet:
    def __init__(self, game=None):
        if game is None:
            self.game = LeagueOfAngels()
        else:
            self.game = game

    def play(self, first):
        round_count = 0
        while round_count < 15:
            starttime = time.time()
            round_count += 1
            timeout = time.time() + 60.0
            while time.time() < timeout:
                self.game.click(518, 125)
                time.sleep(0.050)
            #Wait between rounds
            if first:
                # We were first, we're now going to be second so we want to wait an extra 10 sceonds.
                first = False
                timeout = starttime + 130
            else:
                timeout = starttime + 110
                first = True

            while time.time() < timeout:
                time.sleep(0.500)

