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

parser = argparse.ArgumentParser(description='Automatically play LoA Tarot Cards')
parser.add_argument('--level', '-l', type=int, default=1, help="""
Level we are starting on, defaults to 1.
""")
parser.add_argument('--skipstart', '-n', action='store_true', help="""
Skip the start/next button click at the beginning, use when having script continue a level that is in-progress.
Also triggers automatic level detection.
""")
parser.add_argument('--force', action='store_true', help="""
Play a level even if not enough flips to complete it. Additionally
keep flipping even if we don't think we have enough flips left.
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
parser.add_argument('--guessflips', action='store_true', help="""
Try to parse the number of flips remaining.
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

flips_offsetx = 680
flips_offsety = 20
level_offsetx = 85
level_offsety = 52
digit_width = 10
digit_height = 16


def search_offset(radius=2, offsetx=0, offsety=0):
    """
    :param radius: Search radius, max distance from 0,0 to generate a point from. Defaults to 2, which will generate
     a -2, -2 to 2, 2 search pattern spiraling out from center.
    :return: Yields a x,y tuplet in a spiral sequence from 0,0 limited by radius.
    :offsetx: amount to offset returned x by.
    :offsety: amount to offset returned x by.
    """
    x = y = 0
    dx = 0
    dy = -1
    for i in range((radius*2 + 1)**2):
        yield (x + offsetx, y + offsety)
        if x == y or (x < 0 and x == -y) or (x > 0 and x == 1-y):
            dx, dy = -dy, dx
        x, y = x+dx, y+dy


class CardOnBoard:
    def __init__(self, position):
        self.name = None
        self.matched = False
        self.position = position

    def __eq__(self, other):
        return self.name == other.name and self.position != other.position


class TarotCards:
    def __init__(self, level):
        self.flips_left = 0
        self.xoffset = 0
        self.yoffset = 0
        self.level = level
        self.cards_on_board = None

        logging.info("Loading cards...")
        self.tarot_cards = []
        scriptdir = os.path.dirname(os.path.realpath(__file__))
        globstring = os.path.join(scriptdir, "tarot_cards/*.png")
        for file in glob.glob(globstring):
            name = os.path.basename(file)
            name, ext = os.path.splitext(name)
            self.tarot_cards.append((name, Image.open(file).histogram()))
            logging.debug("Loaded card: {0}".format(name))

        logging.info("Loading digits...")
        self.digits = []
        scriptdir = os.path.dirname(os.path.realpath(__file__))
        globstring = os.path.join(scriptdir, "digits/*.png")
        for file in glob.glob(globstring):
            name = os.path.basename(file)
            name, ext = os.path.splitext(name)
            self.digits.append((name, Image.open(file)))
            logging.debug("Loaded digit: {0}".format(name))

    def find_origin(self, searchx, searchy):
        # Search for the origin points using x, and y as a guide.
        origin_image = Image.open("tarot_origin.png")
        screengrab = ImageGrab.grab()
        # Find the origin point.
        best_rms = 20.0
        best_x = -1
        best_y = -1
        for x, y in search_offset(radius=20, offsetx=searchx, offsety=searchy):
            rms = compare_images(origin_image, screengrab.crop((x - 2, y - 2, x + 3, y + 3)))
            logging.debug("Origin {0},{1}  rms: {2}".format(x, y, rms))
            if rms < best_rms:
                best_y = y
                best_x = x
            if rms < 0.2:
                break
        self.xoffset = best_x
        self.yoffset = best_y

        if best_x == -1:
            logging.error("Failed to find origin!")
            sys.exit(1)

        logging.info("Origin found at {0},{1}".format(self.xoffset, self.yoffset))
        Mouse.click(self.xoffset, self.yoffset)
        origin_image.close()
        time.sleep(0.2)

    def match_card(self, image):
        h1 = image.histogram()
        # This works as the threshold a match must be under to be reliable.
        best_rms = 5.0
        best_name = None
        for cardname, h2 in self.tarot_cards:
            rms = math.sqrt(functools.reduce(operator.add, map(lambda a, b: (a-b)**2, h1, h2))/len(h1))
            logging.debug("Compare vs. {0}, rms: {1}".format(cardname, rms))
            if rms < best_rms:
                best_name = cardname
        return best_name

    def match_digit(self, i1):
        # This works as the threshold a match must be under to be reliable.
        best_rms = 3000.0
        best_digit = None
        for digit, i2 in self.digits:
            rms = compare_images(i1, i2)
            logging.debug("Compare vs. {0}, rms: {1}".format(digit, rms))
            if rms < best_rms:
                best_digit = digit
        return best_digit

    def parse_flips(self):
        value = 0
        for x in range(3):
            for posx, posy in search_offset(offsetx=flips_offsetx + self.xoffset,
                                            offsety=flips_offsety + self.yoffset):
                digit_pos = (posx + (x * digit_width),
                             posy,
                             posx + (x * digit_width) + digit_width - 1,
                             posy + digit_height - 1)
                digit_image = ImageGrab.grab(digit_pos)
                digit_value = self.match_digit(digit_image)
                if digit_value is not None:
                    break
            if digit_value == 'end':
                # Last digit was read.
                break
            if digit_value is None:
                imagefile = "digit{0}.png".format(x)
                logger.warning('Failed to match digit, saving to ' + imagefile)
                digit_image.save(imagefile)
            else:
                value = value * 10 + int(digit_value)
            digit_image.close()

        self.flips_left = value

    def parse_level(self):
        value = 0
        for x in range(2):
            for posx, posy in search_offset(offsetx=level_offsetx + self.xoffset,
                                            offsety=level_offsety + self.yoffset):
                digit_pos = (posx + (x * digit_width),
                             posy,
                             posx + (x * digit_width) + digit_width - 1,
                             posy + digit_height - 1)
                digit_image = ImageGrab.grab(digit_pos)
                digit_value = self.match_digit(digit_image)
                if digit_value is not None:
                    break
            if digit_value is not None and digit_value != 'end':
                value = value * 10 + int(digit_value)
            digit_image.close()
        return value

    def flip_card(self, cardnum):
        if self.flips_left <= 0:
            # Let's double check the flips left.
            self.parse_flips()
        if self.flips_left <= 0:
            logging.error("No flips remaining!")
            sys.exit(1)
        cardpos = (self.xoffset + card_positions[self.level][cardnum][0] + int(card_width / 2),
                   self.yoffset + card_positions[self.level][cardnum][1] + int(card_height / 2))
        logging.debug("Flipping level {0} card {1} at position {2}".format(self.level, cardnum, cardpos))
        cursor = Mouse.get_cursor(cardpos)
        logging.debug("Pre-flip, cursor is: {0}".format(cursor))
        timeout = time.time() + 12
        while time.time() < timeout:
            Mouse.click(*cardpos)
            # Wait for cursor to change to pointer.
            clicktimeout = time.time() + 1.0
            while time.time() < clicktimeout and Mouse.get_cursor(cardpos) != Mouse.arrow_cursor:
                time.sleep(0.050)
            if Mouse.cursor_is_arrow(cardpos):
                break
            logging.warning("Card click was not registered for 1 second, clicking again.")
        cursor = Mouse.get_cursor(cardpos)
        logging.debug("Post-flip, cursor is: {0}".format(cursor))
        self.flips_left -= 1
        logging.debug("Flips left: {0}".format(self.flips_left))

    def detect_card(self, cardnum, dumb=False):
        bbox = (self.xoffset + card_positions[self.level][cardnum][0],
                self.yoffset + card_positions[self.level][cardnum][1],
                self.xoffset + card_positions[self.level][cardnum][0] + card_width,
                self.yoffset + card_positions[self.level][cardnum][1] + card_height)
        retries = 0
        # Retry up to 15 times with a delay of 100ms between tries to detect the card. As it takes ~100ms to screengrab
        # this equals about 3 seconds of retrying.
        if dumb:
            retry_max = 1
        else:
            retry_max = 60
        while retries < retry_max:
            retries += 1
            card_image = ImageGrab.grab(bbox)
            # Check if we recognize this card.
            card_name = self.match_card(card_image)
            if card_name is not None:
                logging.info("Matched card {0} to: {1}".format(cardnum, card_name))
                self.cards_on_board[cardnum].name = card_name
                return
            time.sleep(0.1)
        if dumb:
            return

        logging.error("Failed to match card {0}!".format(cardnum))
        # Exit out, we shouldn't continue if we failed to detect a card. Better to potentially have this time out than
        #  to exhaust flips.
        sys.exit(1)

    def wait_unflip(self, cardnum):
        cardpos = (self.xoffset + card_positions[self.level][cardnum][0] + int(card_width / 2),
                   self.yoffset + card_positions[self.level][cardnum][1] + int(card_height / 2))
        while True:
            Mouse.move(*cardpos)
            if Mouse.cursor_is_hand():
                break
            time.sleep(0.100)

    def play_level(self, skip_start=False):
        logging.info("Playing level {0}".format(self.level + 1))
        self.cards_on_board = []
        for i in range(len(card_positions[self.level])):
            self.cards_on_board.append(CardOnBoard(i))

        # Check if game has already started
        cards_flipped = 0
        for cardnum in range(len(card_positions[self.level])):
            self.detect_card(cardnum, dumb=True)
            if self.cards_on_board[cardnum].name is not None:
                self.cards_on_board[cardnum].matched = True
                cards_flipped += 1

        unknownpos = 0
        matches_remaining = len(card_positions[self.level]) / 2
        if cards_flipped == 0:
            if not skip_start:
                # Click start.
                start_pos = (545 + self.xoffset, 430 + self.yoffset)
                next_pos = (540 + self.xoffset, 380 + self.yoffset)
                if self.level == 0:
                    Mouse.click(*start_pos)
                else:
                    Mouse.click(*next_pos)
                time.sleep(1.0)
        else:
            # Game has already started.
            matches_remaining -= int(cards_flipped / 2)
            for card in self.cards_on_board:
                if not card.matched:
                    unknownpos = card.position
                    break

            if cards_flipped % 2 == 1:
                # We're in the middle of matching cards. Try and match another card before main loop starts.
                # Find what the last flipped card is, and unmark it as matched.
                for card in reversed(self.cards_on_board):
                    if card.matched:
                        card.matched = False
                        break
                self.flip_card(unknownpos)
                # Detect the card.
                self.detect_card(unknownpos)
                # Check if this is a match
                if self.cards_on_board[unknownpos] == self.cards_on_board[unknownpos - 1]:
                    self.cards_on_board[unknownpos].matched = True
                    self.cards_on_board[unknownpos - 1].matched = True
                    matches_remaining -= 1
                else:
                    # Let's wait for the cards to flip back over
                    self.wait_unflip(unknownpos)
                unknownpos += 1

        # Click pairs to find cards, and eventually match.
        while matches_remaining > 0:
            # seek past any previously matched cards.
            while self.cards_on_board[unknownpos].matched:
                unknownpos += 1
            # Check if we know of any matches we can flip.
            for c1 in range(len(self.cards_on_board)):
                if self.cards_on_board[c1].name is not None and not self.cards_on_board[c1].matched:
                    for c2 in range(len(self.cards_on_board)):
                        if c1 != c2 and self.cards_on_board[c1] == self.cards_on_board[c2]:
                            self.flip_card(c1)
                            self.flip_card(c2)
                            self.cards_on_board[c1].matched = True
                            self.cards_on_board[c2].matched = True
                            matches_remaining -= 1
                            continue

            # Flip the next unknown card.
            self.flip_card(unknownpos)
            # Detect the card.
            self.detect_card(unknownpos)

            # Check if this card matches any we know.
            matched = False
            for i in range(len(self.cards_on_board)):
                if i != unknownpos and self.cards_on_board[i] == self.cards_on_board[unknownpos]:
                    # We know the match for this, match it!
                    self.flip_card(i)
                    matches_remaining -= 1
                    self.cards_on_board[i].matched = True
                    self.cards_on_board[unknownpos].matched = True
                    matched = True
                    break
            unknownpos += 1
            if not matched:
                # No match known, let's detect another card.
                self.flip_card(unknownpos)
                # Detect the card.
                self.detect_card(unknownpos)
                # Check if this is a match
                if self.cards_on_board[unknownpos] == self.cards_on_board[unknownpos - 1]:
                    self.cards_on_board[unknownpos].matched = True
                    self.cards_on_board[unknownpos - 1].matched = True
                    matches_remaining -= 1
                else:
                    # Let's wait for the cards to flip back over
                    self.wait_unflip(unknownpos)
                unknownpos += 1

    def play(self, skip_first_start=False):
        self.parse_flips()
        while self.level < 10:
            max_flips = int(len(card_positions[self.level]) * 1.75)
            if max_flips > self.flips_left:
                logging.warning("Not enough flips remaining. Bad case flips for next level: {0}".format(max_flips))
                if not args.force:
                    answer = input("Do you wish to continue? (y/n): ")
                    if answer != 'y':
                        sys.exit(1)
                    else:
                        Mouse.click(self.xoffset, self.yoffset)
                        time.sleep(0.1)
                        # Check if flips were added
                        self.parse_flips()
            self.play_level(skip_first_start)
            skip_first_start = False
            if self.level < len(flips_gained):
                self.flips_left += flips_gained[self.level]
                logger.debug("Added {0} flips.".format(flips_gained[self.level]))
            time.sleep(0.5)
            self.parse_flips()
            logging.info("Flips left: {0}".format(self.flips_left))
            self.level += 1
            if args.singlelevel:
                sys.exit(0)
            time.sleep(3.0)

    def recognize_file(self):
        screengrab = Image.open(args.recognize_file)
        cardnum = 0

        logging.info("Loaded file, offset pixel is: {0}".format(
            screengrab.getpixel((self.xoffset, self.yoffset))))

        for posx, posy in card_positions[self.level]:
            cardnum += 1
            cardimage = screengrab.crop((self.xoffset + posx, self.yoffset + posy,
                                         self.xoffset + posx + card_width, self.yoffset + posy + card_height))
            # Check if we recognize this card.
            matched_name = self.match_card(cardimage)
            if matched_name is not None:
                logging.info("Matched card to: {0}".format(matched_name))
            else:
                filename = "card_l{0}_c{1}.png".format(self.level + 1, cardnum)
                cardimage.save(filename)
                logging.info("Failed to match, card image saved to: {0}".format(filename))
        sys.exit(0)

tarot = TarotCards(args.level - 1)
if args.recognize_file:
    tarot.xoffset = args.recognize_xoffset
    tarot.yoffset = args.recognize_yoffset
    tarot.recognize_file()

if args.level - 1 > len(card_positions) or len(card_positions[args.level - 1]) == 0:
    logging.error("Don't know card positions for level {0}".format(args.level))
    sys.exit(1)

# First let's find the top left of the board.
var = input("Place mouse near the top left of tbe blue/black portion of the Tarot Cards window.")
tarot.find_origin(*Mouse.get_position())

if args.guessflips:
    tarot.parse_flips()
    print("Guessed {0} flips left.".format(tarot.flips_left))
    sys.exit(0)

if args.skipstart:
    # Let's autodetect the level
    level = tarot.parse_level()
    if level > 0:
        tarot.level = level - 1
        logging.info("Detected Level: {0}".format(level))

if args.level != 1:
    level = tarot.parse_level()
    if level != args.level:
        logging.error("Detected Level: {0} which does not match level specified.".format(tarot.level + 1))
        if not args.force:
            sys.exit(0)

tarot.play(args.skipstart)

