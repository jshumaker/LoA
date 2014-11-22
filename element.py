__author__ = 'Jody Shumaker'

import sys
import glob
import argparse
import os.path
from utility.mouse import *
from utility.screen import *
from PIL import ImageGrab, Image
import logging
import functools
import math
import operator
import time

parser = argparse.ArgumentParser(description='Automatically spend elemental stones.')
parser.add_argument('--attempts', '-a', type=int, default=1, help="""
How many upgrade attempts to do. Defaults to %default%.
""")
parser.add_argument('--debug', action='store_true', help="""
Enable debug mode, a element.log file will be output with extra details.
""")
args = parser.parse_args()


loglevel = logging.INFO
if args.debug:
    loglevel = logging.DEBUG
logger = logging.getLogger('')
logger.setLevel(loglevel)
# create file handler which logs even debug messages
fh = logging.FileHandler('element.log', mode='w')
fh.setLevel(loglevel)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

upgrade_offset = (146, 225)
upgrade_image = Image.open('element/Upgrade.png')

game_window = get_game_window()

game_center = (int((game_window[2] - game_window[0]) / 2) + game_window[0],
               int((game_window[3] - game_window[1]) / 2) + game_window[1])

# Give the game focus.
safe_click_pos = (max(0, game_window[0] - 1), max(0, game_window[1]))
Mouse.click(*safe_click_pos)


expected_x = game_center[0] + upgrade_offset[0]
expected_y = game_center[1] + upgrade_offset[1]
# Calibrate upgrade_image offset.
upgrade_pos = image_search(ImageGrab.grab(), upgrade_image, expected_x, expected_y)

logging.debug("Upgrade button found at: {0}, offset: {1},{2}".format(
    upgrade_pos, expected_x - upgrade_pos[0], expected_y - upgrade_pos[1]))

# Adjust pos to be a clicking position.
upgrade_pos = (upgrade_pos[0] + int(upgrade_image.size[0] / 2), upgrade_pos[1] + int(upgrade_image.size[1] / 2))
# Save button position offset from that.
save_pos = (upgrade_pos[0] + 139, upgrade_pos[1])

digit_positions = [
    (game_center[0] + 387, game_center[1] + 55),
    (game_center[0] + 387, game_center[1] + 80),
    (game_center[0] + 387, game_center[1] + 107)
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
    logging.debug("Loaded digit: {0}".format(name))


total_upgrade = 0

for i in range(1, args.attempts + 1):
    # Click Upgrade.
    Mouse.click(*upgrade_pos)
    time.sleep(0.050)
    timeout = time.time() + 5.0
    while time.time() < timeout and not Mouse.cursor_is_hand(upgrade_pos):
        time.sleep(0.050)
    time.sleep(0.100)
    if time.time() > timeout:
        logging.error("Error while waiting for upgrade button to respond.")
        sys.exit(1)
    # Get the digit values.
    timeout = time.time() + 5.0
    failure = False
    while time.time() < timeout:
        digit_total = 0
        screengrab = ImageGrab.grab()
        for pos in digit_positions:
            name, x, y = detect_image(screengrab, digits, *pos, radius=5)
            if name is None:
                logging.debug("Failed to recognize digit, retrying in 100ms.")
                time.sleep(0.100)
                failure = True
                break
            logging.debug("Recognized digit: {0} Offset: {1}, {2}".format(name, x - pos[0], y - pos[1]))
            digit_total += int(name)
        if not failure:
            break
    if digit_total > 0:
        Mouse.click(*save_pos)
        time.sleep(0.050)
        timeout = time.time() + 5.0
        while time.time() < timeout and Mouse.cursor_is_hand(save_pos):
            time.sleep(0.050)
            Mouse.click(*save_pos)
        time.sleep(0.100)
        if Mouse.cursor_is_hand(save_pos):
            logging.error("Error while waiting for save button to respond.")
            sys.exit(1)
        total_upgrade += digit_total
        logging.info("Gained {0} levels, {1} total, {2} per attempt.".format(
            digit_total, total_upgrade, total_upgrade / i))


logging.info("Total Gained Levels: {0}, {1} per attempt.".format(
    total_upgrade, total_upgrade / args.attempts))
