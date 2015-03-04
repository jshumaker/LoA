__author__ = 'Jody Shumaker'

from utility.mouse import *
from utility.screen import *
from utility.logconfig import *
import argparse
import os.path
from loa import *

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


game = LeagueOfAngels()


# Return to the home screen.
game.goto_homepage()

# Let's orient the first icon.
logging.log(VERBOSE, "Searching for first icon.")
screenshot = game.capture_screenshot()
first_icon_pos = game.image_find(icon_corner_image, 299, 8, xorient=Orient.Right, screenshot=screenshot,
                                 radius=20, great_threshold=1000.0)

if first_icon_pos.x == -1:
    logging.error("Failed to find first icon.")
    sys.exit(1)
logging.log(VERBOSE, "First icon found, offset from expected: {0},{1}".format(first_icon_pos.xoffset,
                                                                              first_icon_pos.yoffset))
# Find the daily tasks button.
logging.log(VERBOSE, "Searching for daily tasks button.")
found = False
for i in range(12):
    x, y = first_icon_pos.x, first_icon_pos.y
    icon_count = 0
    while not found and icon_count < 40:
        if game.image_find(daily_tasks_image, x, y, radius=0, threshold=120000, screenshot=screenshot)[0] != -1:
            logging.log(VERBOSE, "Daily tasks button found, {0},{1}".format(x, y))
            found = True
        else:
            x -= 62
            if x < 310:
                x = first_icon_pos.x + 62
                y += 70
        icon_count += 1
    if found:
        break
    else:
        time.sleep(10)
        screenshot = game.capture_screenshot()

if not found:
    logging.error("Failed to find daily tasks icon.")
    sys.exit(1)

# Enter Daily Tasks
game.click(x + 25, y + 25)
time.sleep(0.500)

# Wait for Join button.
logging.log(VERBOSE, "Searching for join button.")
timeout = time.time() + 90.0
reenter_timeout = time.time() + 9.5
click_count = 0
while time.time() < timeout:
    join_pos = game.image_find(join_image, 161, -150, xorient=Orient.Center, yorient=Orient.Center,
                               radius=2, threshold=15000, great_threshold=2000)
    if join_pos.x != -1:
        logging.log(VERBOSE, "Join button found, offset {0},{1}".format(join_pos.xoffset, join_pos.yoffset))
        break
    if time.time() > reenter_timeout:
        # We possibly brought up daily tasks too early, let's re-open it.
        # We also possibly closed it instead of opening it, so let's click just once to cycle between open and closed.
        reenter_timeout = time.time() + 4.5
        game.click(x + 25, y + 25)
        click_count += 1
        time.sleep(1.500)
    time.sleep(0.200)
if time.time() > timeout:
    logging.error("Timed out waiting for Join button.")
    if click_count % 2 == 1:
        game.click(x + 25, y + 25)
        time.sleep(1.500)
    game.capture_screenshot().save("failed_join.png")
    sys.exit(1)

# Join
logging.info("Joining World Boss.")
game.click(join_pos.x, join_pos.y)
time.sleep(2.000)


logging.info("Searching for Morale button...")
timeout = time.time() + 20.0
while time.time() < timeout:
    game.mouse_move(0, 0)
    morale_pos = game.image_find(morale_image, -95, 121, xorient=Orient.Center, yorient=Orient.Bottom,
                                 radius=5)
    if morale_pos.x != -1:
        logging.info("Found Morale button at {},{}".format(morale_pos.xoffset, morale_pos.yoffset))
        break

# Hide players
logging.info("Hiding other players.")
game.click(137, -111, xorient=Orient.Right, yorient=Orient.Center)
time.sleep(0.500)
# Run up to line.
logging.info("Running up to line.")
game.click(280, 170, xorient=Orient.Right)
time.sleep(1.000)
# Auto attack
logging.info("Enabling auto attack.")
game.click(117, 97, xorient=Orient.Center, yorient=Orient.Bottom)

logging.info('Monitoring for morale boost.')
# Morale boost
for i in range(6):
    timeout = time.time() + 30.0
    while time.time() < timeout:
        game.mouse_move(0, 0)
        pos = game.image_find(morale_image, morale_pos.x, morale_pos.y, radius=0)
        if pos.x != -1:
            break
        time.sleep(0.500)
    if pos.x == -1:
        logging.info("Morale button did not appear as expected, assuming world boss is over.")
        break
    # Keep clicking till it seems to take.
    timeout = time.time() + 10
    while time.time() < timeout and game.image_find(morale_inactive_image,
                                                    morale_pos.x, morale_pos.y, radius=0).x == -1:
        game.click(morale_pos.x, morale_pos.y)
        time.sleep(1.0)
    logging.info('Morale boosted.')
    time.sleep(179.0)