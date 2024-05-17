from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests
import logging
import pickle
import os

from modules.utils import is_current_period, parse_date_from_str
from settings import config, ROOT_DIR

logger = logging.getLogger(__name__)


def is_blacklisted(url, blacklisted_urls):
    blacklisted_exact = [url for url, match in blacklisted_urls if match == 'exact']
    blacklisted_part = [url for url, match in blacklisted_urls if match == 'part']
    return any([part_url in url for part_url in blacklisted_part]) or \
           any([exact_url == url for exact_url in blacklisted_exact])


def first_pickle(soup):
    if not os.listdir(os.path.join(ROOT_DIR, "data", "tmp")):
        all_links = extract_all_links(soup)
        with open(os.path.join(ROOT_DIR, "data", "tmp", "tmplinks.pickle"), 'wb') as handle:
            pickle.dump(all_links, handle, protocol=pickle.HIGHEST_PROTOCOL)


def write_pickle(new_links):
    with open(os.path.join(ROOT_DIR, "data", "tmp", "tmplinks.pickle"), 'wb') as handle:
        pickle.dump(new_links, handle, protocol=pickle.HIGHEST_PROTOCOL)


def read_pickle():
    if os.listdir(os.path.join(ROOT_DIR, "data", "tmp")):
        with open(os.path.join(ROOT_DIR, "data", "tmp", "tmplinks.pickle"), 'rb') as handle:
            tmp_links = pickle.load(handle)
            return tmp_links
    return False


def get_differences(old_dict, new_dict):
    result_links = {k: new_dict[k] for k in set(new_dict) - set(old_dict)}
    return result_links


def extract_all_links(soup):                                                # all links
    sitemap_dict = {}
    for item, last_update in zip(soup.find_all('loc'), soup.find_all('lastmod')):
        try:
            # if is_current_period(parse_date_from_str(last_update.text), period) and \
            #         urlparse(item.text).path != '/sitemap-misc.xml':
            if urlparse(item.text).path != '/sitemap-misc.xml':
                if item.text.endswith(".xml"):
                    # Send another GET request to the .xml link
                    r = requests.get(item.text)
                    assert r.ok
                    new_soup = BeautifulSoup(r.text, 'xml')
                    for url, lmod in zip(new_soup.find_all('loc'), new_soup.find_all('lastmod')):
                        # if is_current_period(parse_date_from_str(lmod.text), period):
                        sitemap_dict[url.text] = lmod.text
        except Exception as e:
            logger.error(f"Error while get links from sitemap for: {item}")

    return sitemap_dict


def extract_links(soup, period):
    sitemap_dict = {}
    for item, last_update in zip(soup.find_all('loc'), soup.find_all('lastmod')):
        try:
            if is_current_period(parse_date_from_str(last_update.text), period) and \
                    urlparse(item.text).path != '/sitemap-misc.xml':
                if item.text.endswith(".xml"):
                    # Send another GET request to the .xml link
                    r = requests.get(item.text)
                    assert r.ok
                    new_soup = BeautifulSoup(r.text, 'xml')
                    for url, lmod in zip(new_soup.find_all('loc'), new_soup.find_all('lastmod')):
                        if is_current_period(parse_date_from_str(lmod.text), period):
                            sitemap_dict[url.text] = lmod.text
            # TODO recursivo para xml
        except Exception as e:
            logger.error(f"Error while get links from sitemap for: {item}")
    return sitemap_dict


def get_urls_from_sitemap(url, period):
    clean_dict = {}
    blacklisted_urls = config['elduende']['blacklisted_urls']
    logger.info("fetching links from sitemap")
    # Send our GET requests and parse the response with BS4
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/70.0.3538.77 Safari/537.36 "
    }
    resp = requests.get(url, headers=headers)
    if resp.ok:
        soup = BeautifulSoup(resp.text, 'xml')
        # first_pickle(soup)
        last_exec_links = read_pickle()
        current_exec_links = extract_all_links(soup)
        new_links = get_differences(last_exec_links, current_exec_links)
        write_pickle(current_exec_links)
        # sitemap_dict = extract_links(soup, period) (original)
        logger.info("Total links found: " + str(len(new_links)))
        clean_dict = {key: new_links.get(key, "") for key in new_links.keys() if
                      not is_blacklisted(key, blacklisted_urls)}

    return clean_dict
