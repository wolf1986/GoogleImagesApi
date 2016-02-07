import json
import mimetypes
import os
import urllib.parse
import urllib.request
import jsonpickle

from collections import defaultdict
from multiprocessing.dummy import Pool
from typing import List
from bs4 import BeautifulSoup


class QueryUrls:
    TEMPLATE = \
        "http://www.google.com/search" \
        "?site=&tbm=isch&source=hp&biw=1280&bih=899&q=__QUERY__&__PAGE_DATA__"

    IMAGES_IN_PAGE = 100

    def __init__(self, query: str, amount_queries: int, starting_page=0):
        self.max_requests = amount_queries
        self.query = query
        self.starting_page = starting_page

    def __iter__(self):
        self.current_index = self.starting_page
        return self

    def __next__(self):
        if self.current_index < self.max_requests:
            page_data = ''
            if self.current_index != 0:
                page_data = 'ijn={}&start={}'.format(
                    self.current_index,
                    self.IMAGES_IN_PAGE * self.current_index
                )
            query_encoded = urllib.parse.quote_plus(self.query)

            self.current_index += 1
            return \
                QueryUrls.TEMPLATE \
                    .replace('__QUERY__', query_encoded) \
                    .replace('__PAGE_DATA__', page_data)
        else:
            raise StopIteration


class Record:
    def __init__(self, dic_orig: dict = None, index: int = -1):
        self.Url = ''

        self.WidthThumbnail = 0
        self.HeightThumbnail = 0
        self.WidthOriginal = 0
        self.HeightOriginal = 0

        self.TitlePage = ''
        self.TitleImage = ''

        self.Extension = ''

        if dic_orig:
            self.__dict__.update(self.from_dict(dic_orig).__dict__)

        self.Index = index

    @classmethod
    def from_dict(cls, dic_orig):
        dic = defaultdict(lambda: None, **dic_orig)
        ret = cls()
        ret.Url = dic['tu']

        ret.WidthThumbnail = dic['tw']
        ret.HeightThumbnail = dic['th']
        ret.WidthOriginal = dic['ow']
        ret.HeightOriginal = dic['oh']

        ret.TitlePage = dic['pt']
        ret.TitleImage = dic['s']

        ret.Extension = dic['ity']

        return ret

    def __str__(self):
        return json.dumps(self.__dict__, indent=4)


class Crawler:
    CACHE_SEARCH_QUERY = True
    AMOUNT_FILE_DIGITS = 3
    PAGES_TO_QUERY = 6
    FILENAME_INDEX = '_search_results.json'

    HEADERS = {
        'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36'
    }

    @classmethod
    def query(cls, query: str, pages_to_query: int) -> List[Record]:
        list_meta_records = []  # type: List[Record]
        for url in QueryUrls(query, pages_to_query):
            request = urllib.request.Request(url, headers=cls.HEADERS)

            with urllib.request.urlopen(request) as stream:
                str_html = stream.read().decode('utf-8')

            if not str_html:
                raise Exception('Unable to fetch HTML')

            soup = BeautifulSoup(str_html, 'html.parser')
            list_meta_div = soup.select('.rg_meta')

            # Transform metadata to JSON
            list_meta_dic = [json.loads(div.string) for div in list_meta_div]
            list_meta_records_temp = list(map(Record, list_meta_dic))

            # Remove records without urls
            list_meta_records += [r for r in list_meta_records_temp if r.Url is not None]

        # Enumerate records
        for i in range(len(list_meta_records)):
            record = list_meta_records[i]
            record.Index = i

        return list_meta_records

    @classmethod
    def retrieve_single(cls, record: Record, dir_root: str) -> int:
        # noinspection PyBroadException
        try:
            # Open url
            response = urllib.request.urlopen(record.Url)

            # # Guess extension if wasn't known
            # if record.Extension:
            #     extension = '.{}'.format(record.Extension)
            # else:
            #     content_type = response.headers['content-type']
            #     extension = mimetypes.guess_extension(content_type)

            # Always read extension from mime type
            content_type = response.headers['content-type']
            extension = mimetypes.guess_extension(content_type)

            # Write to disk
            format_str = '{{:0{}d}}{{}}'.format(cls.AMOUNT_FILE_DIGITS)
            filename = format_str.format(record.Index, extension)
            path_image = os.path.join(dir_root, filename)

            with open(path_image, 'wb') as file:
                return file.write(response.read())

        except:
            return -1

    @classmethod
    def retrieve_all(
        cls,
        query: str,
        dir_root: str,
        amount_threads: int = None
    ):
        """
            Note: __main__ must be defined in order to use this function
            :param dir_root: Path to root of download
            :param query: Search string
            :param amount_threads: Number of processes to spawn
        """
        if not os.path.isdir(dir_root):
            os.mkdir(dir_root)

        path_file_index = os.path.join(dir_root, cls.FILENAME_INDEX)

        # Try loading results from cache file
        if os.path.exists(path_file_index):
            with open(path_file_index, 'r', encoding='utf-8') as file:
                list_meta_records = jsonpickle.decode(file.read())
        else:
            list_meta_records = Crawler.query(query, cls.PAGES_TO_QUERY)

            with open(path_file_index, 'w', encoding='utf-8') as file:
                file.write(jsonpickle.encode(list_meta_records))

        def download_record(record: Record):
            return Crawler.retrieve_single(record, dir_root)

        pool = Pool(processes=amount_threads)
        return pool.map(download_record, list_meta_records)
