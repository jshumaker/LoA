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
parser.add_argument('--recognize_file', '-r', help="""
Parse a given file, giving card values for each position and outputting png's for unrecognized cards.
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

flips_offsetx = 745
flips_offsety = 20
level_offsetx = 350
level_offsety = 52
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
    def __init__(self):
        self.flips_left = 0
        self.xoffset = 0
        self.yoffset = 0
        self.level = -1
        self.cards_on_board = None
        self.gamepos = None
        self.gamesize = None

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
            logging.debug("Loaded digit: {0}".format(name))

    def orient(self):
        # Get the game window
        self.gamepos = get_game_window()
        self.gamesize = (self.gamepos[2] - self.gamepos[0] + 1, self.gamepos[3] - self.gamepos[1] + 1)
        logging.debug("Game Window position: {0},{1},{2},{3}".format(*self.gamepos))

        Mouse.click(self.gamepos[0] + 2, self.gamepos[1] + 2)

        # Search for start button to center.
        logging.debug("Searching for start button...")
        start_image = Image.open("tarot/start.png")
        searchx = int(self.gamepos[0] + (self.gamesize[0] / 2) - 31)
        searchy = int(self.gamepos[1] + (self.gamesize[1] / 2) + 97)
        best_x, best_y = image_search(ImageGrab.grab(), start_image, searchx, searchy)
        start_image.close()

        if best_x != -1:
            center_x = best_x + 31
            center_y = best_y - 97
            self.level = 0
            logging.debug("Start button found, offset from expected: {0}, {1}".format(best_x - searchx, best_y - searchy))
        else:
            # Search for next button.
            logging.debug("Searching for next button...")
            next_image = Image.open("tarot/next.png")
            searchx = int(self.gamepos[0] + (self.gamesize[0] / 2) - 45)
            searchy = int(self.gamepos[1] + (self.gamesize[1] / 2) + 65)
            best_x, best_y = image_search(ImageGrab.grab(), next_image, searchx, searchy)
            next_image.close()
            if best_x != -1:
                center_x = best_x + 45
                center_y = best_y - 70
                self.level = self.parse_level() - 1
                logging.debug("Next button found, offset from expected: {0}, {1}".format(best_x - searchx, best_y - searchy))
            else:
                logging.error("Failed to find origin!")
                sys.exit(1)

        logging.info("Center found at {0},{1}".format(center_x, center_y))
        logging.info("Starting play at level {0}".format(self.level + 1))

        self.xoffset = center_x - 543
        self.yoffset = center_y - 306

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
        logging.debug("Calibrating via card 0")
        searchx, searchy = card_positions[self.level][0]
        searchx += self.xoffset - 6
        searchy += self.yoffset - 6
        newx, newy = image_search(screengrab, card_corner, searchx, searchy, radius=20)
        if newx == -1:
            logging.error("Failed to calibrate")
            sys.exit(1)
        logging.info("Card offset: {0},{1}".format(newx - searchx, newy - searchy))
        self.xoffset += newx - searchx
        self.yoffset += newx - searchx
        card_corner.close()

        logging.info("Origin at {0},{1}".format(self.xoffset, self.yoffset))
        Mouse.click(self.xoffset, self.yoffset)

        time.sleep(0.2)

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
        logging.debug("Parsing flips...")
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
                    logging.debug("Digit found, offset from expected: {0},{1}".format(
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
        logging.debug("Parsing level...")
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
                    logging.debug("Digit found, offset from expected: {0},{1}".format(
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
        cardpos = (self.xoffset + card_positions[self.level][cardnum][0] + int(card_width / 2),
                   self.yoffset + card_positions[self.level][cardnum][1] + 15)
        logging.debug("Flipping level {0} card {1} at position {2}".format(self.level, cardnum, cardpos))
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
        logging.debug("Flips left: {0}".format(self.flips_left))

    def detect_card(self, cardnum, dumb=False):
        retries = 0
        if dumb:
            retry_max = 1
        else:
            retry_max = 30
        while retries < retry_max:
            retries += 1
            searchx = self.xoffset + card_positions[self.level][cardnum][0]
            searchy = self.yoffset + card_positions[self.level][cardnum][1]
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
        return False

    def wait_unflip(self, cardnum):
        cardpos = (self.xoffset + card_positions[self.level][cardnum][0] + int(card_width / 2),
                   self.yoffset + card_positions[self.level][cardnum][1] + 15)
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
        #for cardnum in range(len(card_positions[self.level])):
        #    logging.debug("Check if level has already been started, scan if any cards can be detected.")
        #    self.detect_card(cardnum, dumb=True)
        #    if self.cards_on_board[cardnum].name is not None:
        #        self.cards_on_board[cardnum].matched = True
        #        cards_flipped += 1

        unknownpos = 0
        matches_remaining = len(card_positions[self.level]) / 2
        if cards_flipped == 0:
            if not skip_start:
                # Click start.
                start_pos = (545 + self.xoffset, 415 + self.yoffset)
                next_pos = (540 + self.xoffset, 380 + self.yoffset)
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
            for i in range(len(card_positions[self.level])):
                logging.debug("Calibrating card {0}".format(i))
                searchx, searchy = card_positions[self.level][i]
                searchx += self.xoffset - 6
                searchy += self.yoffset - 6
                newx, newy = image_search(screengrab, card_corner, searchx, searchy, radius=10)
                if newx == -1:
                    logging.warning("Failed to calibrate card position {0}".format(i))
                card_positions[self.level][i] = (newx + 6 - self.xoffset, newy + 6 - self.yoffset)
                logging.debug("Card {0} offset: {1},{2}".format(i, newx - searchx, newy - searchy))
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


tarot = TarotCards()
if args.recognize_file:
    tarot.recognize_file()

tarot.orient()

if args.guessflips:
    tarot.parse_flips()
    print("Guessed {0} flips left.".format(tarot.flips_left))
    sys.exit(0)

if args.skipstart:
    # Let's autodetect the level
    logging.error("Skipping the start is unfortunately unsupported at this time.")
    sys.exit(1)

for i in range(args.attempts):
    tarot.play(args.skipstart)
    args.skipstart = False
    tarot.level = 0
    time.sleep(1.0)

