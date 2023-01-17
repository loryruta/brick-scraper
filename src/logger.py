import logging

logger = logging.getLogger('brick-scraper')
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
stream_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
