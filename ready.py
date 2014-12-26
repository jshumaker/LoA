__author__ = 'Jody Shumaker'

from utility.mouse import *
from utility.screen import *
from utility.logconfig import *
import argparse
import os.path
from loa import *

script_dir = os.path.dirname(os.path.realpath(__file__))

parser = argparse.ArgumentParser(description='Click Ready whenever it appears.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--debug', action='store_true', help="""
Enable debug mode, extra details will be added to log file.
""")
args = parser.parse_args()

loglevel = VERBOSE
if args.debug:
    loglevel = logging.DEBUG
logconfig('ready', loglevel)


game = LeagueOfAngels()

ready_button = Image.open(script_dir + '/misc/Ready.png')


while True:
    logging.log(VERBOSE, "Searching for Ready button...")
    game.mouse_move(0, 0)
    time.sleep(0.100)
    ready_pos = game.image_find(ready_button, 132, 435, xorient=Orient.Right, radius=1,
                                threshold=200000, great_threshold=200000)
    if ready_pos.x != -1:
        logging.info("Ready button found ({},{}), clicking ready.".format(ready_pos.xoffset, ready_pos.yoffset))
        game.click(ready_pos.x + 40, ready_pos.y)
    time.sleep(5.0)