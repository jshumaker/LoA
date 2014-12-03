__author__ = 'Jody Shumaker'

from utility.mouse import *
from utility.screen import *
from utility.logconfig import *
import argparse
from PIL import ImageGrab, Image
import os.path

script_dir = os.path.dirname(os.path.realpath(__file__))

parser = argparse.ArgumentParser(description='Automatically join world boss.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--debug', action='store_true', help="""
Enable debug mode, extra details will be added to log file.
""")
args = parser.parse_args()

loglevel = VERBOSE
if args.debug:
    loglevel = logging.DEBUG
logconfig('worldboss', loglevel)


# Resources.
icon_corner_image = Image.open(os.path.join(script_dir, "misc/IconCorner.png"))
daily_tasks_image = Image.open(os.path.join(script_dir, "misc/DailyTasks.png"))
join_image = Image.open(os.path.join(script_dir, "misc/Join.png"))
morale_image = Image.open(os.path.join(script_dir, "misc/Morale.png"))
morale_inactive_image = Image.open(os.path.join(script_dir, "misc/MoraleInactive.png"))

game_window = get_game_window(auto=True)

game_center = (int((game_window[2] - game_window[0]) / 2) + game_window[0],
               int((game_window[3] - game_window[1]) / 2) + game_window[1])

# Give the game focus.
safe_click_pos = (max(0, game_window[0] - 1), max(0, game_window[1]))
Mouse.click(*safe_click_pos)
time.sleep(0.050)

# Let's orient the first icon.
logging.log(VERBOSE, "Searching for first icon.")
screengrab = ImageGrab.grab()
searchpos = (game_window[2] - 242, game_window[1] + 8)
first_icon_pos = image_search(screengrab, icon_corner_image, *searchpos, radius=20, great_threshold=1000.0)

if first_icon_pos[0] == -1:
    logging.error("Failed to find first icon.")
    sys.exit(1)
logging.log(VERBOSE, "First icon found, offset from expected: {0},{1}".format(first_icon_pos[0] - searchpos[0],
                                                                              first_icon_pos[1] - searchpos[1]))
# Find the daily tasks button.
logging.log(VERBOSE, "Searching for daily tasks button.")
found = False
x, y = first_icon_pos
icon_count = 0
while not found and icon_count < 40:
    if image_search(screengrab, daily_tasks_image, x, y, radius=0, threshold=120000)[0] != -1:
        logging.log(VERBOSE, "Daily tasks button found, {0},{1}".format(x, y))
        found = True
    else:
        x -= 62
        if x - game_window[0] < 310:
            x = first_icon_pos[0]
            y += 70
    icon_count += 1

if not found:
    logging.error("Failed to find daily tasks icon.")
    sys.exit(1)

# Enter Daily Tasks
Mouse.click(x + 25, y + 25)
time.sleep(0.010)

# Wait for Join button.
logging.log(VERBOSE, "Waiting for join button.")
timeout = time.time() + 30.0
while time.time() < timeout:
    searchx = game_center[0] + 161
    searchy = game_center[1] - 152
    posx, posy = image_search(ImageGrab.grab(), join_image, searchx, searchy, radius=5, great_threshold=2000)
    if posx != -1:
        logging.log(VERBOSE, "Join button found, offset {0},{1}".format(posx - searchx, posy - searchy))
        break
    time.sleep(0.200)
if time.time() > timeout:
    logging.error("Timed out waiting for Join button.")
    sys.exit(1)

# Join
Mouse.click(game_center[0] + 176, game_center[1] - 143)
time.sleep(4.000)

# Run up to line.
Mouse.click(game_center[2] - 280, game_window[1] + 170)
time.sleep(0.100)
# Auto attack
Mouse.click(game_center[0] + 119, game_window[3] - 97)

timeout = time.time() + 15.0
while time.time() < timeout:
    morale_x, morale_y = image_search(ImageGrab.grab(), morale_image, game_center[0] - 128, game_window[3] - 112,
                                      radius=5)
    if morale_x != -1:
        logging.info("Found Morale button at {0},{1}")
        break

# Morale boost
for i in range(4):
    timeout = time.time() + 5.0
    while time.time() < timeout:
        x, y = image_search(ImageGrab.grab(), morale_image, morale_x, morale_y, radius=0)
        if x != -1:
            break
        time.sleep(0.500)
    if x == -1:
        logging.info("Morale button did not appear as expected, assuming world boss is over.")
        break
    Mouse.click(morale_x, morale_y)
    time.sleep(180.0)