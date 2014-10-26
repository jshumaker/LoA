__author__ = 'Jody Shumaker'

import sys
import glob
import argparse
import os.path
from utility.mouse import *
#from utility.screen import *
from PIL import ImageGrab, Image
import logging
import functools
import math
import operator
import time

parser = argparse.ArgumentParser(description='Automatically play LoA Tarot Cards')
parser.add_argument('--level', '-l', type=int, default=1, help="""
Level we are starting on, defaults to 1.
""")
parser.add_argument('--flips', '-f', type=int, default=15, help="""
Number of flips remaining, defaults to 15.
""")
parser.add_argument('--recognize_file', '-r', help="""
Parse a given file, giving card values for each position and outputting png's for unrecognized cards.
""")
parser.add_argument('--recognize_xoffset', '-x', type=int, help="""
X offset for recognize file.
""")
parser.add_argument('--recognize_yoffset', '-y', type=int, help="""
Y offset for recognize file.
""")
parser.add_argument('--debug', action='store_true', help="""
Enable debug mode, a tarot.log file will be output with extra details.
""")
parser.add_argument('--singlelevel', '-s', action='store_true', help="""
Only play 1 level, good for debugging.
""")
parser.add_argument('--force', action='store_true', help="""
Play a level even if not enough flips to complete it. Additionally
keep flipping even if we don't think we have enough flips left.
""")
args = parser.parse_args()


loglevel = logging.INFO
if args.debug:
    loglevel = logging.DEBUG
logger = logging.getLogger('')
logger.setLevel(loglevel)
# create file handler which logs even debug messages
fh = logging.FileHandler('tarot.log', mode='w')
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


level = args.level - 1
flips_left = args.flips

top_left_color = (1, 9, 14)
# Position in test images: l1-3,l9-10 184,211  l5-6 129, 214

# Level card positions. Positions are at top left part of card inside the boarder. When flipped this is a
# noinspection PyPep8
card_positions = [
    # Level 1
    [(236, 167), (506, 167), (776, 167),
     (236, 417), (506, 417), (776, 417)],
    # Level 2
    [(356, 117), (656, 117),
     (256, 297), (356, 297), (656, 297), (756, 297),
     (356, 477), (656, 477)],
    # Level 3
    [(307, 167), (507, 167), (707, 167),
     (207, 317), (407, 317), (607, 317), (807, 317),
     (307, 467), (507, 467), (707, 467)],
    # Level 4
    [(396, 167), (506, 167), (616, 167),
     (66, 297), (176, 297), (286, 297), (736, 297), (846, 297), (956, 297),
     (396, 417), (506, 417), (616, 417)],
    # Level 5
    [(36, 111), (116, 247), (196, 375), (276, 488), (376, 340), (462, 177),
     (552, 177), (636, 340), (736, 488), (816, 375), (896, 247), (976, 111)],
    # Level 6
    [(356, 167), (456, 167), (556, 167), (656, 167),
     (156, 314), (256, 314), (756, 314), (856, 314),
     (356, 417), (456, 417), (556, 417), (656, 417)],
    # Level 7
    [(206, 167), (306, 167), (406, 167), (506, 167), (606, 167), (706, 167), (806, 167),
     (206, 417), (306, 417), (406, 417), (506, 417), (606, 417), (706, 417), (806, 417)],
    # Level 8
    [(106, 117), (256, 117), (406, 117), (556, 117), (706, 117), (856, 117),
     (106, 286), (256, 286), (406, 286), (556, 286), (706, 286), (856, 286),
     (106, 457), (256, 457), (406, 457), (556, 457), (706, 457), (856, 457)],
    # Level 9
    [(106, 117), (213, 117), (320, 117), (427, 117), (534, 117), (641, 117), (748, 117), (855, 117),
     (106, 287), (213, 287), (320, 287), (427, 287), (534, 287), (641, 287), (748, 287), (855, 287),
     (106, 457), (213, 457), (320, 457), (427, 457), (534, 457), (641, 457), (748, 457), (855, 457)],
    # Level 10
    [(106, 117), (213, 117), (320, 117), (427, 117), (534, 117), (641, 117), (748, 117), (855, 117),
     (106, 287), (213, 287), (320, 287), (427, 287), (534, 287), (641, 287), (748, 287), (855, 287),
     (106, 457), (213, 457), (320, 457), (427, 457), (534, 457), (641, 457), (748, 457), (855, 457)],
]
# Number of flips gained upon completion of a level.
flips_gained = [10, 16, 18, 18, 20, 20, 24, 28, 34]

card_width = 70
card_height = 123

print("Loading cards...")
logging.info("Loading cards...")
cards = []
scriptdir = os.path.dirname(os.path.realpath(__file__))
globstring = os.path.join(scriptdir, "tarot_cards/*.png")
for file in glob.glob(globstring):
    name = os.path.basename(file)
    name, ext = os.path.splitext(name)
    cards.append((name, Image.open(file).histogram()))
    logging.debug("Loaded card: {0}".format(name))


def match_card(image):
    h1 = image.histogram()
    # This works as the threshold a match must be under to be reliable.
    best_rms = 5.0
    best_name = None
    for cardname, h2 in cards:
        rms = math.sqrt(functools.reduce(operator.add, map(lambda a, b: (a-b)**2, h1, h2))/len(h1))
        logging.debug("Compare vs. {0}, rms: {1}".format(cardname, rms))
        if rms < best_rms:
            best_name = cardname
    return best_name


def recognize_file():
    screengrab = Image.open(args.recognize_file)
    xoffset = args.recognize_xoffset
    yoffset = args.recognize_yoffset
    cardnum = 0

    logging.info("Loaded file, offset pixel is: {0}".format(screengrab.getpixel((xoffset, yoffset))))

    for posx, posy in card_positions[level]:
        cardnum += 1
        cardimage = screengrab.crop((xoffset + posx, yoffset + posy,
                                     xoffset + posx + card_width, yoffset + posy + card_height))
        # Check if we recognize this card.
        matched_name = match_card(cardimage)
        if matched_name is not None:
            logging.info("Matched card to: {0}".format(matched_name))
        else:
            filename = "card_l{0}_c{1}.png".format(level + 1, cardnum)
            cardimage.save(filename)
            logging.info("Failed to match, card image saved to: {0}".format(filename))
    sys.exit(0)

if args.recognize_file:
    recognize_file()

if len(card_positions[level]) == 0:
    logging.error("Don't know card positions for level {0}".format(level + 1))
    sys.exit(1)

# First let's find the top left of the board.
var = input("Place mouse near the top left of tbe blue/black portion of the Tarot Cards window.")
xoffset, yoffset = Mouse.get_position()
screengrab = ImageGrab.grab()


def offset_search():
    global xoffset, yoffset
    # Find the left most pixel and top most pixel that is 1, 9, 14
    for x in range(xoffset - 10, xoffset + 11):
        for y in range(yoffset - 10, yoffset + 11):
            if screengrab.getpixel((x, y)) == top_left_color:
                yoffset = y
                xoffset = x
                return

offset_search()
logging.info("Top left found at {0},{1}".format(xoffset, yoffset))
Mouse.click(xoffset, yoffset)
time.sleep(0.5)


def flip_card(l, cardnum):
    global flips_left
    if flips_left <= 0 and not args.force:
        logging.error("No flips remaining!")
        sys.exit(1)
    cardpos = (xoffset + card_positions[l][cardnum][0] + int(card_width / 2),
               yoffset + card_positions[l][cardnum][1] + int(card_height / 2))
    logging.debug("Flipping level {0} card {1} at position {2}".format(l, cardnum, cardpos))
    Mouse.click(*cardpos)
    flips_left -= 1
    logging.debug("Flips left: {0}".format(flips_left))


def detect_card(l, cardnum, dumb=False):
    bbox = (xoffset + card_positions[l][cardnum][0],
            yoffset + card_positions[l][cardnum][1],
            xoffset + card_positions[l][cardnum][0] + card_width,
            yoffset + card_positions[l][cardnum][1] + card_height)
    retries = 0
    # Retry up to 30 times with a delay of 100ms between tries to detect the card. As it takes ~100ms to screengrab
    # this equals about 6 seconds of retrying.
    if dumb:
        retry_max = 1
    else:
        retry_max = 30
    while retries < retry_max:
        retries += 1
        card_image = ImageGrab.grab(bbox)
        # Check if we recognize this card.
        card_name = match_card(card_image)
        if card_name is not None:
            logging.info("Matched card {0} to: {1}".format(cardnum, card_name))
            return card_name
        time.sleep(0.1)
    if dumb:
        return None

    logging.error("Failed to match card {0}!".format(cardnum))
    # Exit out, we shouldn't continue if we failed to detect a card. Better to potentially have this time out than
    #  to exhaust flips.
    sys.exit(1)


class CardOnBoard:
    def __init__(self, position):
        self.name = None
        self.matched = False
        self.position = position

    def __eq__(self, other):
        return self.name == other.name and self.position != other.position


def play_level(l):
    cards_on_board = []
    for i in range(len(card_positions[l])):
        cards_on_board.append(CardOnBoard(i))

    # Check if game has already started?
    started = False
    for cardnum in range(len(card_positions[l])):
        cards_on_board[cardnum].name = detect_card(l, cardnum, dumb=True)
        if cards_on_board[cardnum].name is not None:
            cards_on_board[cardnum].matched = True
            started = True

    if not started:
        # Click start.
        start_pos = (545 + xoffset, 430 + yoffset)
        next_pos = (540 + xoffset, 380 + yoffset)
        if l == 0:
            Mouse.click(*start_pos)
        else:
            Mouse.click(*next_pos)
        time.sleep(1.0)

    # Click pairs to find cards, and eventually match.
    unknownpos = 0
    matches_remaining = len(card_positions[l]) / 2
    while matches_remaining > 0:
        if unknownpos >= len(cards_on_board):
            # We've detected all cards, but there's some match remaining
            for c1 in range(len(cards_on_board)):
                if not cards_on_board[c1].matched:
                    for c2 in range(len(cards_on_board)):
                        if c1 != c2 and cards_on_board[c1] == cards_on_board[c2]:
                            flip_card(l, c1)
                            time.sleep(0.5)
                            flip_card(l, c2)
                            time.sleep(1.0)
                            cards_on_board[c1].matched = True
                            cards_on_board[c2].matched = True
                            matches_remaining -= 1
        else:
            # Flip the next unknown card.
            flip_card(l, unknownpos)
            # Detect the card.
            cards_on_board[unknownpos].name = detect_card(l, unknownpos)

            # Check if this card matches any we know.
            matched = False
            for i in range(len(cards_on_board)):
                if i != unknownpos and cards_on_board[i] == cards_on_board[unknownpos]:
                    # We know the match for this, match it!
                    flip_card(l, i)
                    matches_remaining -= 1
                    cards_on_board[i].matched = True
                    cards_on_board[unknownpos].matched = True
                    matched = True
                    break
            unknownpos += 1
            if not matched:
                # No match known, let's detect another card.
                flip_card(l, unknownpos)
                # Detect the card.
                cards_on_board[unknownpos].name = detect_card(l, unknownpos)
                # Check if this is a match
                if cards_on_board[unknownpos] == cards_on_board[unknownpos - 1]:
                    cards_on_board[unknownpos].matched = True
                    cards_on_board[unknownpos - 1].matched = True
                    matches_remaining -= 1
                unknownpos += 1
            time.sleep(1.3)

while level < 10:
    play_level(level)
    if level < len(flips_gained):
        flips_left += flips_gained[level]
        logger.debug("Added {0} flips.".format(flips_gained[level]))
    logging.info("Flips left: {0}".format(flips_left))
    level += 1
    max_flips = int(len(card_positions[level]) * 1.5) + 1
    if len(card_positions[level]) % 4 != 0:
        max_flips += 1
    if max_flips > flips_left:
        if args.force:
            logging.warning("Not enough flips remaining to guarantee beating next level. Max flips for next level: {0}".format(max_flips))
        else:
            logging.error("Not enough flips remaining to guarantee beating next level. Max flips for next level: {0}".format(max_flips))
            sys.exit(1)
    if args.singlelevel:
        sys.exit(0)
    if level == 1:
        logging.warning("The flips left can change as you start first level, please start again from level 2.")
        sys.exit(0)
    time.sleep(3.0)

