__author__ = 'Jody Shumaker'

import sys
import glob
import argparse
import os.path
from utility.mouse import *
from utility.screen import *
from utility.logconfig import *
from PIL import ImageGrab, Image
import logging
import functools
import math
import operator
import time

parser = argparse.ArgumentParser(description='Automatically spend elemental stones.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('attempts', type=int, help="""
How many upgrade attempts to do.
""")
parser.add_argument('--favor1', action='store_true', help="Favor row 1.")
parser.add_argument('--favor2', action='store_true', help="Favor row 2.")
parser.add_argument('--favor3', action='store_true', help="Favor row 3.")
parser.add_argument('--favorthreshold', type=int, default=0, help="Net amount required before favoring.")
parser.add_argument('--ignore1', action='store_true', help="Ignore row 1.")
parser.add_argument('--ignore2', action='store_true', help="Ignore row 2.")
parser.add_argument('--ignore3', action='store_true', help="Ignore row 3.")
parser.add_argument('--debug', action='store_true', help="""
Enable debug mode, a element.log file will be output with extra details.
""")
args = parser.parse_args()


loglevel = VERBOSE
if args.debug:
    loglevel = logging.DEBUG
logconfig('element', loglevel)

upgrade_offset = (146, 225)
upgrade_image = Image.open('element/Upgrade.png')

game_window = get_game_window()

game_center = (int((game_window[2] - game_window[0]) / 2) + game_window[0],
               int((game_window[3] - game_window[1]) / 2) + game_window[1])

# Give the game focus.
safe_click_pos = (max(0, game_window[0] - 1), max(0, game_window[1]))
Mouse.click(*safe_click_pos)
time.sleep(0.200)

expected_x = game_center[0] + upgrade_offset[0]
expected_y = game_center[1] + upgrade_offset[1]
# Calibrate upgrade_image offset.
upgrade_pos = image_search(ImageGrab.grab(), upgrade_image, expected_x, expected_y, radius=10)
if upgrade_pos[0] == -1:
    logging.error("Failed to find upgrade button, expected it to be near {0}, {1}".format(expected_x, expected_y))
    sys.exit(1)

logging.log(VERBOSE, "Upgrade button found at: {0}, offset: {1},{2}".format(
    upgrade_pos, expected_x - upgrade_pos[0], expected_y - upgrade_pos[1]))

# Adjust pos to be a clicking position.
upgrade_pos = (upgrade_pos[0] + int(upgrade_image.size[0] / 2), upgrade_pos[1] + int(upgrade_image.size[1] / 2))
# Save button position offset from that.
save_pos = (upgrade_pos[0] + 139, upgrade_pos[1])

digit_positions = [
    ((game_center[0] + 387, game_center[1] + 55), args.ignore1, args.favor1),
    ((game_center[0] + 387, game_center[1] + 80), args.ignore2, args.favor2),
    ((game_center[0] + 387, game_center[1] + 107), args.ignore3, args.favor3)
]

digit_size = (14, 12)

logging.info("Loading digits...")
digits = []
scriptdir = os.path.dirname(os.path.realpath(__file__))
globstring = os.path.join(scriptdir, "element/digits/*.png")
for file in glob.glob(globstring):
    name = os.path.basename(file)
    name, ext = os.path.splitext(name)
    digits.append((name, Image.open(file)))
    logging.log(VERBOSE, "Loaded digit: {0}".format(name))


total_upgrade = 0


def save():
    Mouse.click(*save_pos)
    time.sleep(0.050)
    timeout = time.time() + 5.0
    while time.time() < timeout and Mouse.cursor_is_hand(save_pos):
        time.sleep(0.050)
        Mouse.click(*save_pos)
    time.sleep(0.500)
    if Mouse.cursor_is_hand(save_pos):
        logging.error("Error while waiting for save button to respond.")
        sys.exit(1)

for i in range(1, args.attempts + 1):
    # Click Upgrade.
    Mouse.click(*upgrade_pos)
    time.sleep(0.050)
    timeout = time.time() + 10.0
    while time.time() < timeout and not Mouse.cursor_is_hand(upgrade_pos):
        time.sleep(0.050)
    if time.time() > timeout:
        logging.error("Error while waiting for upgrade button to respond.")
        sys.exit(1)
    time.sleep(0.150)
    # Get the digit values.
    timeout = time.time() + 8.0
    failure = False
    while time.time() < timeout:
        digit_total = 0
        screengrab = ImageGrab.grab()
        digit_values = []
        for pos, ignore, favor in digit_positions:
            if ignore:
                continue
            name, x, y = detect_image(screengrab, digits, *pos, radius=3)
            if name is None:
                logging.debug("Failed to recognize digit, retrying in 100ms.")
                time.sleep(0.100)
                failure = True
                break
            logging.log(VERBOSE, "Recognized digit: {0} Offset: {1}, {2}".format(name, x - pos[0], y - pos[1]))
            digit_values.append((int(name), favor))
            digit_total += int(name)
        if not failure:
            break
    if time.time() > timeout:
        logging.error("Failed to recognize the digits.")
        sys.exit(1)
    if digit_total > 0:
        save()
        total_upgrade += digit_total
        logging.info("Gained {0} levels, {1} total, {2} per attempt.".format(
            digit_total, total_upgrade, total_upgrade / i))
    elif digit_total >= args.favorthreshold:
        shift = False
        for value, favor in digit_values:
            if favor and value > 0:
                logging.info("Shifting points into favored row. Net change: {}".format(digit_total))
                shift = True
        if shift:
            total_upgrade += digit_total
            save()


logging.info("Total Gained Levels: {0}, {1} per attempt.".format(
    total_upgrade, total_upgrade / args.attempts))
