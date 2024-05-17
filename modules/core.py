import math
import threading
from itertools import repeat
import concurrent.futures
import requests
import logging

from modules.utils import retry

logger = logging.getLogger(__name__)


class CoreMultithread:

    def __init__(self, core_config):
        self.base_url = core_config['internal_base_url']
        self.user = core_config['user']
        self.max_timeout = core_config['max_timeout']
        self.request_page_size = core_config['request_page_size']
        self.max_iterations = core_config['max_iterations']
        self.thread_local = threading.local()

    def get_thread_session(self):
        if not hasattr(self.thread_local, "session"):
            self.thread_local.session = requests.Session()
        return self.thread_local.session

    @staticmethod
    def is_error(status_code):
        return status_code != 200

    @staticmethod
    def order_params(params):
        params_order = ['user', 'query', 'mediaTypes', 'fields', 'orderBy',
                        'order', 'totalHits', 'pageSize', 'page', 'timeout']
        ordered_params = []
        for i in range(0, len(params_order)):
            key = params_order[i]
            if key in params:
                ordered_params.append((key, params[key]))
        return tuple(ordered_params)

    def fetch_data(self, params, page, media_type=None):
        session = self.get_thread_session()
        status_code = 500
        params['page'] = page
        if media_type is not None:
            params['mediaTypes'] = media_type
        result = []
        data_hits = 0
        ordered_params = self.order_params(params)
        try:
            with session.get(self.base_url, params=ordered_params, verify=False) as response:
                status_code = response.status_code
                if response.status_code == 200:
                    data = response.json()
                    data_hits = data.get('hits', 0)
                    result = [item['headers'] for item in data['items']] if data_hits > 0 else []
                else:
                    logger.error(f"Api response error in core fetch data - Status code: {response.status_code}")
                    data_hits = -1
        except Exception as e:
            logger.error(f"Api call unexpected error on core fetch data.\n {e}")
            status_code = 500
        finally:
            return result, data_hits, status_code

    def get_news_data(self, params, scope="data"):
        """
        Get data from core api given parameters of the call and the scope.
            - params --> dict. Example:
                params = {
                    (str) "query": 'typology:(news newspaper magazine blog) AND 'publicationDate:[{ini_date} TO {end_date}]',
                    (str) "mediaTypes": "i,p",
                    (num) "pageSize": 200,        ** --> overwrites request_page_size from config
                    (str) "totalHits": '',
                    (str) "fields": "uri,title,url,sourceUri,sourceName",
                    (str) "orderBy": 'coreAdmissionDate',
                    (str) "order": "desc"
                }
            - Scope --> str. Can be one of:
                1) data --> Return matched items
                2) totals --> Return total query hits
        """
        try:
            params['timeout'] = self.max_timeout
            if params.get('pageSize') is None:
                params['pageSize'] = self.request_page_size
            params['user'] = self.user
            # Fetch data
            if scope == "data":
                status_codes = []
                result_data, hits, status_code = self.fetch_data(params, 1)
                if self.is_error(status_code):
                    print(f"Error raised core get data: {status_code}")
                    return [], status_code
                num_iter = math.ceil(hits / params['pageSize']) if hits > 0 else 0
                num_iter = num_iter if num_iter <= self.max_iterations else self.max_iterations
                print(f"Core get news --> total hits: {hits}")
                print("Number of iterations: ", num_iter)
                if num_iter > 1:
                    pages = list(range(2, num_iter + 1))
                    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
                        downloaded_data = executor.map(self.fetch_data, repeat(params), pages)

                    for result in downloaded_data:
                        try:
                            result_data.extend(result[0])
                            status_codes.append(result[2])
                        except Exception as e:
                            print(f"ThreadDataFetchError: Error in thread while trying to fetch core data {e}")

                if any([status != 200 for status in status_codes]):
                    return [], 500

                return result_data, 200
            # Fetch total hits
            elif scope == "totals":
                params['pageSize'] = 1
                result_data, hits, status_code = self.fetch_data(params, 1)
                return hits, 200

        except Exception as e:
            print(f"Unknown error raised in get news data from core {e}")

    @retry(max_retries=3, wait_time=5)
    def fetch_news_from_core(self, params, scope="data", retry_status_codes=[500, 503, 504]):
        result, status = self.get_news_data(params, scope)
        if status in retry_status_codes:
            raise Exception(f"APIResponseError. Status code: {status}")
        else:
            return result, status

    def core_update_item(self, item, data):
        """
        Update item
            item: str --> uri of the news in core (i.e: /i/a/0ced8baf0686f553d677f10dbba692e4)
            data: dict --> json body with some mandatory fields as well as the ones to update
                json_body = {
                    (str)       'url': 'https://www.testurl.es/.....html',
                    (str)       'title': 'Título noticia',
                    (str)       'content': 'Contenido de la noticia [...]',
                    (str)       'availability': 'reg',
                    *(list str) 'license': ['accesopaywalls']
                }
                * optional fields
                availability -> One of [earlyaccess, free, prem, reg, sub]. Depends on the source
                licence -> list with possible values [accesopaywalls, newsright]
        """
        response_code = 500
        try:
            session = self.get_thread_session()
            url = f"{self.base_url}{item}"
            params = {'user': self.user, 'custom': 'true'}
            with session.put(url, params=params, json=data) as response:
                if response.status_code != 204:
                    print(
                        f"Api response error - Status code: {response.status_code}",
                        f"It was not possible to update item: {item}. Url: {data['url']}"
                    )
                response_code = response.status_code
        finally:
            return item, response_code

    def update_items(self, news):
        """
        Update already existing items in core given a list of News class objects
            news --> list: list of News class items
        """
        items = [item.uri for item in news]
        bodies_data = [item.get_json_body() for item in news]
        responses = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            response_data = executor.map(self.core_update_item, items, bodies_data)
            for result in response_data:
                try:
                    responses.append(result)
                except Exception as e:
                    print(f"ThreadDataFetchError: Error in thread while trying to put data (update item)\n {e}")
        return responses

    def core_create_new_item(self, data, media_type='i', provider='a'):
        """
        Create new item in core
            data: dict --> json body with some mandatory fields as well as the ones to update
                json_body = {
                    (str)       'sourceUri': '/s/mn/0fee1794763b50bd52b0bffc1671f23a',
                    (str)       'typology': 'news',
                    (str)       'url': 'https://www.testurl.es/.....html',
                    (str)       'title': 'Título de la noticia',
                    (num)       'publicationDate': 1619511910369,
                    (str)       'content': 'Contenido de la noticia [...]',
                    *(str)      'availability': 'sub',
                    *(list str) 'license': ['accesopaywalls'],
                    *(str)      'author': 'J.A. Lopez',
                    *(list str) 'imageURL': ['https://3.bp.blogspot.com/...jpg', 'https://img.difoosion.com/...jpg']
                    *(str)      'contentTypology': 'photogallery',
                    **(num)     'releaseDate': 1619511200000
                }
                * Optional fields
                ** Mandatory iif availability = earlyaccess
                availability -> One of [earlyaccess, free, prem, reg, sub]. Depends on the source
                licence -> list with possible values [accesopaywalls, newsright]
        """
        response_code = 500
        try:
            session = self.get_thread_session()
            url = f"{self.base_url}/{media_type}/{provider}"
            params = {'user': self.user}
            with session.post(url, params=params, json=data) as response:
                if response.status_code != 200:
                    print(
                        f"Api response error - Status code: {response.status_code}",
                        f"It was not possible to create a new item. Url: {data['url']}"
                    )
                response_code = response.status_code
        finally:
            return data['url'], response_code

    def create_items(self, news):
        """
        Create new items in core given a list of News class objects
            news --> list: list of News class items
        """
        bodies_data = [item.get_json_body() for item in news]
        responses = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            response_data = executor.map(self.core_create_new_item, bodies_data)
            for result in response_data:
                try:
                    responses.append(result)
                except Exception as e:
                    print(f"ThreadDataFetchError: Error in thread while trying to post data (new item)\n{e}")
        return responses
