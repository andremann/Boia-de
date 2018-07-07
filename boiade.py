import re
import numpy as np
import random
import logging
import logging.handlers
from apscheduler.schedulers.blocking import BlockingScheduler
from twython import Twython, TwythonError
from secrets import *

LOGGER = logging.getLogger('boiade_service')
LOGGER.setLevel(logging.DEBUG)
# rotating file handler
FH = logging.handlers.RotatingFileHandler('boiade.log', maxBytes=10000000, backupCount=5)
FH.setLevel(logging.INFO)
# console handler
CH = logging.StreamHandler()
CH.setLevel(logging.INFO)
# add the handlers to the logger
LOGGER.addHandler(FH)
LOGGER.addHandler(CH)

STATES = ['<START>', 'dé', 'ma', 'allora', 'certo', 'però', 'comunque', 'boia', '<EOM>']

MARKOV = [[0, 1/7, 1/7, 1/7, 1/7, 1/7, 1/7, 1/7, 0], # <START>
          [0, 0, 0.7/7, 0.8/7, 0.7/7, 0.4/7, 0.7/7, 0.7/7, 3/7], # dé
          [0, 6/25, 0, 6/25, 3/25, 6/25, 0, 4/25, 0], # ma
          [0, 1.4/4, 0, 0, 0, 1.2/4, 0, 1.2/4, 0.2/4], # allora
          [0, 11/25, 2/25, 2/25, 0, 5/25, 0, 3/25, 2/25], # certo
          [0, 14/20, 0, 2/20, 2/20, 0, 0, 2/20, 0], # però
          [0, 12/25, 0, 1/25, 1/25, 1/25, 0, 10/25, 0], # comunque
          [0, 1/7, 0.7/7, 0.6/7, 0.6/7, 0.6/7, 0.5/7, 0, 3/7]] # boia

TWITTER_API = Twython(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
SCHEDULER = BlockingScheduler()


def generate_next_token(last_token):
    row_index = STATES.index(last_token)
    next_token = np.random.choice(STATES, 1, p=MARKOV[row_index])
    return next_token[0]


def generate_status():
    generated_sequence = []
    last_token = '<START>'
    while True:
        next_token = generate_next_token(last_token)
        if next_token == '<EOM>':
            status = ''
            for token in generated_sequence:
                status += token + ' '
            # status = status[:-1] + '.'
            status = re.sub(r'(boia dé|dé|boia)', r'\1,', status)
            status = re.sub(r',\s$|.$', '.', status)
            return status.capitalize()
        generated_sequence.append(next_token)
        last_token = next_token


def tweet():
    status = generate_status()
    
    try:
        TWITTER_API.update_status(status=status, lat=43.5519, long=10.308)
        LOGGER.info('Tweeted status: %s', status.encode())
    except TwythonError as err:
        LOGGER.error(err)
        fallback = status[:-1] + '!'
        LOGGER.info('Tweeted status: %s', fallback)
        TWITTER_API.update_status(status=fallback)
    SCHEDULER.remove_job('boiade')
    next_run = random.randint(10, 60)
    LOGGER.info('Next tweet scheduled in %s minutes', next_run)
    SCHEDULER.add_job(tweet, 'interval', minutes=next_run, id='boiade')


SCHEDULER.add_job(tweet, 'interval', seconds=0, id='boiade')
try:
    SCHEDULER.start()
except (KeyboardInterrupt, SystemExit, TwythonError) as err:
    LOGGER.error(err)