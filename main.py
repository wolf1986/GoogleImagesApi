import os

from GoogleImageSearch import Crawler

QUERIES = ['Knife', 'Selfie Stick', 'Umbrella', 'Baguette', 'Nunchaku']
DIR_ROOT = r'D:\Temp\images'
AMOUNT_THREADS = 20

for query in QUERIES:
    dir_root_query = os.path.join(DIR_ROOT, query)
    list_bytes_written = Crawler.retrieve_all(
        query,
        dir_root_query,
        AMOUNT_THREADS
    )
