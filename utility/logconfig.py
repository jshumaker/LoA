__author__ = 'Jody Shumaker'

import logging
import os
import os.path
import glob
import datetime


VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")


def logconfig(name, loglevel):
    logger = logging.getLogger('')
    logger.setLevel(loglevel)

    # Rotate logs and create new filename.
    if not os.path.exists('log'):
        os.mkdir('log')
    logfilename = 'log/{0}_{1}.log'.format(name, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, mode='w')
    fh.setLevel(loglevel)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    # Trim old log files.
    logfiles = sorted(glob.glob('log/{0}*.log'.format(name)), reverse=True)
    if len(logfiles) > 5:
        for i in range(5, len(logfiles)):
            os.remove(logfiles[i])