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

parser = argparse.ArgumentParser(description='Automatically play LoA Tarot Cards.')
parser.add_argument('--attempts', '-a', type=int, default=1, help="""
How many attempts to do. Only continues upon a successful lvl 10 completion. Defaults to 1.
""")
parser.add_argument('--skipstart', '-n', action='store_true', help="""
Broken currently.
Skip the start/next button click at the beginning, use when having script continue a level that is in-progress.
Also triggers automatic level detection.
""")
parser.add_argument('--force', action='store_true', help="""
Play a level even if not enough flips to complete it. Additionally
keep flipping even if we don't think we have enough flips left.
""")
parser.add_argument('--singlelevel', '-s', action='store_true', help="""
Only play 1 level, good for debugging.
""")
parser.add_argument('--guessflips', action='store_true', help="""
Try to parse the number of flips remaining.
""")
parser.add_argument('--learn', action='store_true', help="""
Try and learn new cards while playing.
""")
parser.add_argument('--debug', action='store_true', help="""
Send debug output to console. It is always sent to log file, so this is rarely recommended.
""")
args = parser.parse_args()


VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")
loglevel = VERBOSE
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
    [(-307, -139), (-37, -139), (233, -139),
     (-307, 111), (-37, 111), (233, 111)],
    # Level 2
    [(-187, -189), (113, -189),
     (-287, -9), (-187, -9), (113, -9), (213, -9),
     (-187, 171), (113, 171)],
    # Level 3
    [(-236, -139), (-36, -139), (164, -139),
     (-336, 11), (-136, 11), (64, 11), (264, 11),
     (-236, 161), (-36, 161), (164, 161)],
    # Level 4
    [(-147, -139), (-37, -139), (73, -139),
     (-477, -9), (-367, -9), (-257, -9), (193, -9), (303, -9), (413, -9),
     (-147, 111), (-37, 111), (73, 111)],
    # Level 5
    [(-507, -195), (-427, -59), (-347, 69), (-267, 182), (-167, 34), (-81, -129),
     (9, -129), (93, 34), (193, 182), (273, 69), (353, -59), (433, -195)],
    # Level 6
    [(-187, -139), (-87, -139), (13, -139), (113, -139),
     (-387, 8), (-287, 8), (213, 8), (313, 8),
     (-187, 111), (-87, 111), (13, 111), (113, 111)],
    # Level 7
    [(-337, -139), (-237, -139), (-137, -139), (-37, -139), (63, -139), (163, -139), (263, -139),
     (-337, 111), (-237, 111), (-137, 111), (-37, 111), (63, 111), (163, 111), (263, 111)],
    # Level 8
    [(-437, -189), (-287, -189), (-137, -189), (13, -189), (163, -189), (313, -189),
     (-437, -20), (-287, -20), (-137, -20), (13, -20), (163, -20), (313, -20),
     (-437, 151), (-287, 151), (-137, 151), (13, 151), (163, 151), (313, 151)],
    # Level 9
    [(-437, -189), (-330, -189), (-223, -189), (-116, -189), (-9, -189), (98, -189), (205, -189), (312, -189),
     (-437, -19), (-330, -19), (-223, -19), (-116, -19), (-9, -19), (98, -19), (205, -19), (312, -19),
     (-437, 151), (-330, 151), (-223, 151), (-116, 151), (-9, 151), (98, 151), (205, 151), (312, 151)],
    # Level 10
    [(-437, -189), (-330, -189), (-223, -189), (-116, -189), (-9, -189), (98, -189), (205, -189), (312, -189),
     (-437, -19), (-330, -19), (-223, -19), (-116, -19), (-9, -19), (98, -19), (205, -19), (312, -19),
     (-437, 151), (-330, 151), (-223, 151), (-116, 151), (-9, 151), (98, 151), (205, 151), (312, 151)],
    # Level 11
    [(-450, -282), (-343, -282), (-236, -282), (-129, -282), (-22, -282), (85, -282), (192, -282), (299, -282),
     (-450, -122), (-343, -122), (-236, -122), (-129, -122), (-22, -122), (85, -122), (192, -122), (299, -122),
     (-450, 38), (-343, 38), (-236, 38), (-129, 38), (-22, 38), (85, 38), (192, 38), (299, 38),
     (-129, 198), (-22, 198)],
    # Level 12
    [(-450, -282), (-343, -282), (-236, -282), (-129, -282), (-22, -282), (85, -282), (192, -282), (299, -282),
     (-450, -122), (-343, -122), (-236, -122), (-129, -122), (-22, -122), (85, -122), (192, -122), (299, -122),
     (-450, 38), (-343, 38), (-236, 38), (-129, 38), (-22, 38), (85, 38), (192, 38), (299, 38),
     (-236, 198), (-129, 198), (-22, 198), (85, 198)],
    # Level 13
    [(-450, -282), (-343, -282), (-236, -282), (-129, -282), (-22, -282), (85, -282), (192, -282), (299, -282),
     (-450, -122), (-343, -122), (-236, -122), (-129, -122), (-22, -122), (85, -122), (192, -122), (299, -122),
     (-450, 38), (-343, 38), (-236, 38), (-129, 38), (-22, 38), (85, 38), (192, 38), (299, 38),
     (-343, 198), (-236, 198), (-129, 198), (-22, 198), (85, 198), (192, 198)],
    # Level 14
    [(-450, -282), (-343, -282), (-236, -282), (-129, -282), (-22, -282), (85, -282), (192, -282), (299, -282),
     (-450, -122), (-343, -122), (-236, -122), (-129, -122), (-22, -122), (85, -122), (192, -122), (299, -122),
     (-450, 38), (-343, 38), (-236, 38), (-129, 38), (-22, 38), (85, 38), (192, 38), (299, 38),
     (-450, 198), (-343, 198), (-236, 198), (-129, 198), (-22, 198), (85, 198), (192, 198), (299, 198)],
]
# Number of flips gained upon completion of a level.
flips_gained = [10, 16, 18, 18, 20, 20, 24, 28, 34, 40, 44, 48, 52]

card_width = 70
card_height = 123

flips_offsetx = 345
flips_offsety = 52
level_offsetx = 749
level_offsety = 20
digit_width = 10
digit_height = 16


class CardOnBoard:
    def __init__(self, position):
        self.name = None
        self.matched = False
        self.position = position

    def __eq__(self, other):
        return self.name == other.name and self.position != other.position


class TarotCards:
    def __init__(self, learn=False):
        self.flips_left = 0
        self.level = -1
        self.cards_on_board = None
        self.gamepos = None
        self.gamesize = None
        self.gamecenter = None
        self.safeclick = None
        self.skipstart = False
        self.learn = learn
        self.learncount = 0

        logging.info("Loading cards...")
        self.tarot_cards = []
        scriptdir = os.path.dirname(os.path.realpath(__file__))
        globstring = os.path.join(scriptdir, "tarot/cards/*.png")
        for file in glob.glob(globstring):
            name = os.path.basename(file)
            name, ext = os.path.splitext(name)
            # Limit compared card size to 30x20
            self.tarot_cards.append((name, Image.open(file).crop((0, 0, 15, 15))))
            logging.debug("Loaded card: {0}".format(name))

        logging.info("Loading digits...")
        self.digits = []
        scriptdir = os.path.dirname(os.path.realpath(__file__))
        globstring = os.path.join(scriptdir, "tarot/digits/*.png")
        for file in glob.glob(globstring):
            name = os.path.basename(file)
            name, ext = os.path.splitext(name)
            self.digits.append((name, Image.open(file)))
            logging.log(VERBOSE, "Loaded digit: {0}".format(name))

    def find_next(self):
        # Search for next button.
        logging.log(VERBOSE, "Searching for next button...")
        next_image = Image.open("tarot/next.png")
        searchx = self.gamecenter[0] - 45
        searchy = self.gamecenter[1] + 65
        best_x, best_y = image_search(ImageGrab.grab(), next_image, searchx, searchy)
        next_image.close()
        return best_x, best_y

    def orient(self):
        # Get the game window
        self.gamepos = get_game_window()
        self.gamesize = (self.gamepos[2] - self.gamepos[0] + 1, self.gamepos[3] - self.gamepos[1] + 1)
        logging.log(VERBOSE, "Game Window position: {0},{1},{2},{3}".format(*self.gamepos))

        if self.gamesize[0] < 1040:
            logging.error("Game window size is too narrow, please make game window atleast 1040 pixels wide.")
            sys.exit(1)

        self.safeclick = (max(0, self.gamepos[0] + 2), max(0, self.gamepos[1] + 2))
        Mouse.click(*self.safeclick)
        time.sleep(0.2)

        self.gamecenter = (self.gamepos[0] + int(self.gamesize[0] / 2),
                           self.gamepos[1] + int(self.gamesize[1] / 2))
        # Search for start button to center.
        logging.log(VERBOSE, "Searching for start button...")
        start_image = Image.open("tarot/start.png")
        searchx = self.gamecenter[0] - 31
        searchy = self.gamecenter[1] + 97
        best_x, best_y = image_search(ImageGrab.grab(), start_image, searchx, searchy)
        start_image.close()

        if best_x != -1:
            self.gamecenter = (best_x + 31, best_y - 96)
            self.level = 0
            logging.log(VERBOSE, "Start button found, offset from expected: {0}, {1}".format(best_x - searchx, best_y - searchy))
        else:
            self.level = self.parse_level() - 1
            best_x, best_y = self.find_next()
            if best_x != -1:
                self.gamecenter = (best_x + 45, best_y - 68)
                logging.log(VERBOSE, "Next button found, offset from expected: {0}, {1}".format(best_x - searchx, best_y - searchy))
            else:
                logging.warning("Level appears to already be started.")
                self.skipstart = True

        logging.info("Center found at {0}".format(self.gamecenter))
        logging.info("Starting play at level {0}".format(self.level + 1))

        # Let's calibrate this with the first card which is never really covered. Requires first card to be unflipped.
        if self.level < 3:
            card_corner = Image.open("tarot/back1.png")
        elif self.level < 5:
            card_corner = Image.open("tarot/back3.png")
        elif self.level < 8:
            card_corner = Image.open("tarot/back5.png")
        else:
            card_corner = Image.open("tarot/back8.png")
        # Adjust card positions.
        screengrab = ImageGrab.grab()
        logging.log(VERBOSE, "Calibrating via card 0")
        searchx, searchy = card_positions[self.level][0]
        searchx += self.gamecenter[0] - 6
        searchy += self.gamecenter[1] - 6
        newx, newy = image_search(screengrab, card_corner, searchx, searchy, radius=20)
        if newx == -1:
            logging.error("Failed to calibrate")
            sys.exit(1)
        logging.info("Card offset: {0},{1}".format(newx - searchx, newy - searchy))
        self.gamecenter = (self.gamecenter[0] + newx - searchx,
                           self.gamecenter[1] + newy - searchy)
        card_corner.close()

        logging.info("Center adjusted to {0}".format(self.gamecenter))

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
        logging.log(VERBOSE, "Parsing flips...")
        value = 0
        for x in range(3):
            for posx, posy in search_offset(offsetx=flips_offsetx + self.gamepos[0],
                                            offsety=flips_offsety + self.gamepos[1]):
                digit_pos = (posx + (x * digit_width),
                             posy,
                             posx + (x * digit_width) + digit_width - 1,
                             posy + digit_height - 1)
                digit_image = ImageGrab.grab(digit_pos)
                digit_value = self.match_digit(digit_image)
                if digit_value is not None:
                    logging.log(VERBOSE, "Digit found, offset from expected: {0},{1}".format(
                        posx - flips_offsetx - self.gamepos[0],
                        posy - flips_offsety - self.gamepos[1]
                    ))
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
        logging.log(VERBOSE, "Parsing level...")
        value = 0
        for x in range(2):
            for posx, posy in search_offset(offsetx=level_offsetx + self.gamepos[0],
                                            offsety=level_offsety + self.gamepos[1]):
                digit_pos = (posx + (x * digit_width),
                             posy,
                             posx + (x * digit_width) + digit_width - 1,
                             posy + digit_height - 1)
                digit_image = ImageGrab.grab(digit_pos)
                digit_value = self.match_digit(digit_image)
                if digit_value is not None:
                    logging.log(VERBOSE, "Digit found, offset from expected: {0},{1}".format(
                        posx - level_offsetx - self.gamepos[0],
                        posy - level_offsety - self.gamepos[1]
                    ))
                    break
            if digit_value is not None and digit_value != 'end':
                value = value * 10 + int(digit_value)
            digit_image.close()
        return value

    def flip_card(self, cardnum, detect=False):
        if self.flips_left <= 0:
            # Let's double check the flips left.
            self.parse_flips()
        if self.flips_left <= 0:
            logging.error("No flips remaining!")
            sys.exit(1)
        cardpos = (self.gamecenter[0] + card_positions[self.level][cardnum][0] + int(card_width / 2),
                   self.gamecenter[1] + card_positions[self.level][cardnum][1] + 15)
        logging.log(VERBOSE, "Flipping level {0} card {1} at position {2}".format(self.level, cardnum, cardpos))
        cursor = Mouse.get_cursor(cardpos)
        logging.debug("Pre-flip, cursor is: {0}".format(cursor))
        timeout = time.time() + 12
        while time.time() < timeout:
            Mouse.click(*cardpos)
            # Wait for cursor to change to pointer.
            time.sleep(0.50)
            clicktimeout = time.time() + 1.0
            while time.time() < clicktimeout and Mouse.get_cursor(cardpos) != Mouse.arrow_cursor:
                time.sleep(0.010)
            if Mouse.cursor_is_arrow(cardpos):
                if detect:
                    if self.detect_card(cardnum):
                        break
                    if self.find_next()[0] != -1:
                        logging.log(VERBOSE, "Next button is up, the level finished.")
                        break
                    if time.time() > timeout:
                        logging.error("Failed to detect card {0} level {1}".format(cardnum, self.level))
                        ImageGrab.grab().save("failed_detection.png")
                        logging.info("Screenshot saved to failed_detection.png")
                        sys.exit(1)
                else:
                    break
            logging.warning("Card click was not registered for 1 second, clicking again.")
        cursor = Mouse.get_cursor(cardpos)
        logging.debug("Post-flip, cursor is: {0}".format(cursor))
        self.flips_left -= 1
        logging.log(VERBOSE, "Flips left: {0}".format(self.flips_left))

    def detect_card_back(self, cardnum, radius=3):
        if self.level < 3:
            card_corner = Image.open("tarot/back1.png")
        elif self.level < 5:
            card_corner = Image.open("tarot/back3.png")
        elif self.level < 8:
            card_corner = Image.open("tarot/back5.png")
        else:
            card_corner = Image.open("tarot/back8.png")
        # Search for card back.
        screengrab = ImageGrab.grab()
        searchx, searchy = card_positions[self.level][cardnum]
        searchx += self.gamecenter[0] - 6
        searchy += self.gamecenter[1] - 6
        newx, newy = image_search(screengrab, card_corner, searchx, searchy, radius=radius)
        card_corner.close()
        return newx, newy

    def detect_card(self, cardnum, dumb=False):
        retries = 0
        if dumb:
            retry_max = 1
        else:
            # Wait for card to not be a card back.
            timeout = time.time() + 1.0
            while time.time() < timeout and self.detect_card_back(cardnum)[0] != -1:
                time.sleep(0.050)
            # Wait for flip to complete.
            time.sleep(0.100)
            retry_max = 15
        # Try to detect the card.
        while retries < retry_max:
            retries += 1
            searchx = self.gamecenter[0] + card_positions[self.level][cardnum][0]
            searchy = self.gamecenter[1] + card_positions[self.level][cardnum][1]
            card_name, x, y = detect_image(ImageGrab.grab(),
                                           self.tarot_cards,
                                           searchx,
                                           searchy,
                                           radius=2)
            if card_name is not None:
                logging.info("Matched card {0} to: {1}  offset: {2}, {3}".format(cardnum, card_name, searchx - x, searchy - y))
                self.cards_on_board[cardnum].name = card_name
                return True
                time.sleep(0.1)
            elif not dumb and self.learn:
                # Wait a little longer for the card flip to definitely complete.
                time.sleep(0.150)
                card_image = ImageGrab.grab((searchx, searchy, searchx + 70, searchy + 123))
                self.learncount += 1
                card_name = "Unknown{0}".format(self.learncount)
                card_image.save("tarot/cards/{0}.png".format(card_name))
                logging.warning("Learned new card, saved as {0}.".format(card_name))
                self.tarot_cards.append((card_name, card_image.crop((0, 0, 15, 15))))
        return False

    def wait_unflip(self, cardnum):
        cardpos = (self.gamecenter[0] + card_positions[self.level][cardnum][0] + int(card_width / 2),
                   self.gamecenter[1] + card_positions[self.level][cardnum][1] + 15)
        while True:
            Mouse.move(*cardpos)
            if Mouse.cursor_is_hand():
                break
            time.sleep(0.100)

    def play_level(self):
        logging.info("Playing level {0}".format(self.level + 1))
        self.cards_on_board = []
        for i in range(len(card_positions[self.level])):
            self.cards_on_board.append(CardOnBoard(i))

        unknownpos = 0
        matches_remaining = len(card_positions[self.level]) / 2
        cards_flipped = 0
        if self.skipstart:
            # scan cards
            logging.log(VERBOSE, "Scanning for already flipped cards.")
            for cardnum in range(len(card_positions[self.level])):
                self.detect_card(cardnum, dumb=True)
                if self.cards_on_board[cardnum].name is not None:
                    self.cards_on_board[cardnum].matched = True
                    cards_flipped += 1

        if cards_flipped == 0:
            if not self.skipstart:
                # Click start.
                start_pos = (self.gamecenter[0], 109 + self.gamecenter[1])
                next_pos = (self.gamecenter[0], 74 + self.gamecenter[1])
                if self.level == 0:
                    Mouse.click(*start_pos)
                else:
                    Mouse.click(*next_pos)
                time.sleep(1.0)
            if self.level < 3:
                card_corner = Image.open("tarot/back1.png")
            elif self.level < 5:
                card_corner = Image.open("tarot/back3.png")
            elif self.level < 8:
                card_corner = Image.open("tarot/back5.png")
            else:
                card_corner = Image.open("tarot/back8.png")
            # Adjust card positions.
            screengrab = ImageGrab.grab()
            timeout = time.time() + 6.0
            for i in range(len(card_positions[self.level])):
                logging.log(VERBOSE, "Calibrating card {0}".format(i))
                while True:
                    searchx, searchy = card_positions[self.level][i]
                    searchx += self.gamecenter[0] - 6
                    searchy += self.gamecenter[1] - 6
                    newx, newy = image_search(screengrab, card_corner, searchx, searchy, radius=10)
                    if time.time() > timeout or newx != -1:
                        break
                    if newx == -1:
                        # Update our screengrab.
                        screengrab = ImageGrab.grab()

                if newx == -1:
                    logging.warning("Failed to calibrate card position {0}".format(i))
                else:
                    card_positions[self.level][i] = (newx + 6 - self.gamecenter[0], newy + 6 - self.gamecenter[1])
                    logging.log(VERBOSE, "Card {0} offset: {1},{2}".format(i, newx - searchx, newy - searchy))
        else:
            # Game has already started and some cards flipped.
            matches_remaining -= int(cards_flipped / 2)
            for card in self.cards_on_board:
                if not card.matched:
                    unknownpos = card.position
                    break

            if cards_flipped % 2 == 1:
                # We're in the middle of matching cards. Try and match another card before main loop starts.
                self.flip_card(unknownpos, detect=True)
                # Check if this is a match
                match = False
                for card in self.cards_on_board:
                    if self.cards_on_board[unknownpos] == card:
                        self.cards_on_board[unknownpos].matched = True
                        card.matched = True
                        matches_remaining -= 1
                        match = True
                        break
                if not match:
                    # Let's wait for the cards to flip back over
                    self.wait_unflip(unknownpos)
                    # Figure out what card flipped back over.
                    for cardnum in range(len(card_positions[self.level])):
                        if self.cards_on_board[cardnum].matched and self.detect_card_back(cardnum)[0] != -1:
                            logging.log(VERBOSE, "Marking card {0} as unmatched.".format(cardnum))
                            self.cards_on_board[cardnum].matched = False
                unknownpos += 1

        self.skipstart = False
        # Click pairs to find cards, and eventually match.
        while matches_remaining > 0:
            # seek past any previously matched cards.
            while self.cards_on_board[unknownpos].name is not None:
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
            self.flip_card(unknownpos, detect=True)

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
                if matches_remaining == 1:
                    # There was only one match left, the last unknown card should be the match we need.
                    # We also won't get a chance to identify it as the level will end.
                    self.flip_card(unknownpos)
                    matches_remaining -= 1
                else:
                    # Detect the card.
                    self.flip_card(unknownpos, detect=True)
                    # Check if this is a match
                    if self.cards_on_board[unknownpos] == self.cards_on_board[unknownpos - 1]:
                        self.cards_on_board[unknownpos].matched = True
                        self.cards_on_board[unknownpos - 1].matched = True
                        matches_remaining -= 1
                    else:
                        # Let's wait for the cards to flip back over
                        self.wait_unflip(unknownpos)
                    unknownpos += 1

    def play(self):
        self.parse_flips()
        while self.level < len(card_positions):
            max_flips = int(len(card_positions[self.level]) * 1.75)
            if max_flips > self.flips_left:
                logging.warning("Not enough flips remaining. Bad case flips for next level: {0}".format(max_flips))
                if not args.force:
                    answer = input("Do you wish to continue? (y/n): ")
                    if answer != 'y':
                        sys.exit(1)
                    else:
                        Mouse.click(*self.safeclick)
                        time.sleep(0.1)
                        # Check if flips were added
                        self.parse_flips()
            self.play_level()
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


tarot = TarotCards(learn=args.learn)

tarot.orient()

if args.guessflips:
    tarot.parse_flips()
    print("Guessed {0} flips left.".format(tarot.flips_left))
    sys.exit(0)

for i in range(args.attempts):
    tarot.play()
    tarot.level = 0
    time.sleep(1.0)

