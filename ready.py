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

    # Move the mouse out of the way.
    mousex, mousey = game.mouse_get(xorient=Orient.Right)
    game.mouse_move(91, 378, xorient=Orient.Right)
    time.sleep(0.100)
    ready_pos = game.image_find(ready_button, 132, 435, xorient=Orient.Right, radius=1,
                                threshold=200000, great_threshold=200000)
    if ready_pos.x != -1:
        logging.info("Ready button found ({},{}), clicking ready.".format(ready_pos.xoffset, ready_pos.yoffset))
        game.click(ready_pos.x + 40, ready_pos.y)
    # Move the mouse back.
    game.mouse_move(mousex, mousey, xorient=Orient.Right)
    time.sleep(4.0)