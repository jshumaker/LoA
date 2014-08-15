League of Angels utility scripts
===
All scripts are generally tested to work with Python 3.x

tt.py
-----
Attempts to simulate Team Tournament battles. Requires manually editing the code currently to setup what to simulate.

gemology.py
-----------
Recognizes a gemology board, calculates and performs best move.

Requires pywin32, download tha appropriate version for your version of python:
http://sourceforge.net/projects/pywin32/files/pywin32/

Also requires Pillow which can be installed via:
easy_install Pillow

Can run with --help parameter to get list of options.  In normal mode after starting it will ask how much energy you have left. Then it will ask you to place your mouse over the top left gem and press enter.  To do this, have both command line window and browser window open side by side with the gems visible and the command window in focus. Place mouse over top left gem but keep focus on command line window, then press enter.  Script will then home in on exact coordinates for the gemology grid, it will then repeat the following:

1. Scan what colors the gems are.
2. Calculate best move based upon current configuration.
3. Perform the gem swap move.
4. Wait for the move to resolve itself.
5. Back to 1, until out of energy.

The script recognizes when it gets to the end of the energy and stops trying to setup 2 or 3 move combos when there is not enough energy left to do so.

To quit the script in the middle of operation, press ctrl + c. Do not move the browser window, or hide the view of the gems.  If the script fails to recognize the gem colors, it will stop running.