import random
import logging
import datetime as dt
import re
import time
from urllib.parse import urlparse
from lxml import etree
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from webdriver_manager.chrome import ChromeDriverManager

from modules.utils import is_current_period, parse_date_from_str, retry
from settings import config

logger = logging.getLogger(__name__)


class Article:

    def __init__(self, fields):
        self.url = fields.get('url')
        self.title = fields.get("title")
        self.content = fields.get('content')
        self.author = fields.get('author')
        self.images = fields.get('images')
        self.publication_date = self.format_date(fields.get('publicationdate'))

    @staticmethod
    def format_date(original_date):
        return int(original_date.timestamp() * 1000)

    def get_json_body(self):
        return {
            "sourceUri": "/s/a/209fef11ccc9e527309955c8694b6635",
            "typology": 'news',
            "availability": "free",
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "publicationDate": self.publication_date,
            "author": self.author,
            "imageURL": self.images
        }


def clean_text(field_list):
    """ clean content """
    return " ".join((" ".join(field_list).split()))


def scrape_image(img_class, images):
    if img_class == 'header':
        url_images = re.findall(r'url\([\"]?(.*?[^\"])[\"]?\)', images[0])
    else:
        url_images = [re.sub(r'^.*url\([\"]?(.*?[^\"])[\"]?\).*$', r'\g<1>', image) for image in images]
    return url_images


def get_fields_from_html(html, article_type, xpath_settings):
    """
    Get article fields from html
    :param article_type: routes, plans or magazine
    :param xpath_settings: article type xpath
    :param html: html string format
    :return:
    """
    scope = xpath_settings.get('scope').get(article_type)
    fields_xpath = xpath_settings.get('fields_xpath')
    tree = etree.fromstring(html, parser=etree.HTMLParser())
    title = clean_text(tree.xpath(fields_xpath.get('title').replace("{scope}", scope))).split(" - ")[0]
    intro = clean_text(tree.xpath(fields_xpath.get('intro').replace("{scope}", scope)))
    content = clean_text(tree.xpath(fields_xpath.get('content').replace("{scope}", scope)))
    pdate = parse_date_from_html(tree, fields_xpath)
    content_images = scrape_image(
        'content',
        tree.xpath(fields_xpath.get('content_images').replace("{scope}", scope))
    )
    header_image = scrape_image(
        'header',
        tree.xpath(fields_xpath.get('header_image').replace("{scope}", scope))
    )
    author = clean_text(
        tree.xpath(fields_xpath.get('author').replace("{scope}", scope))
    ).replace("Por ", "").replace("POR ", "")

    fields_dict = {
        'title': title,
        'content': f'{intro}\n{content}',
        'images': ",".join(header_image + content_images),
        'author': author,
        'publicationdate': pdate,
    }
    return fields_dict


def open_browser_session(headless):
    chrome_options = Options()
    chrome_options.add_argument(f'user-agent={config.get("user-agent")}')
    if headless:
        chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(
        executable_path=ChromeDriverManager().install(),
        options=chrome_options
    )
    driver.maximize_window()
    return driver


def parse_date_from_html(html_tree, fields_xpath):
    pdate = dt.datetime.now()
    try:
        elems = html_tree.xpath(fields_xpath.get('publicationdatetime'))
        if elems:
            aux_date = re.search(r'\"datePublished\":[\s]?\"(.*?[^\"])\"', elems[0]).group(1)
        else:
            aux_date = clean_text(html_tree.xpath(fields_xpath.get('publicationdate')))
        pdate = parse_date_from_str(aux_date)
    finally:
        return pdate


@retry(max_retries=3)
def scrape_article(article_url, driver):
    fields_data = {}
    try:
        driver.get(article_url)
        article_type = urlparse(article_url).path.split("/")[1]
        content_xpath = config['elduende']['fields_xpath']['content'] \
            .replace("//text()", "") \
            .replace("{scope}", config['elduende']['scope'][article_type])
        WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.XPATH, content_xpath)))
        fields_data = get_fields_from_html(driver.page_source, article_type, config['elduende'])
        fields_data.update({'url': article_url})
    except Exception as e:
        logger.error(f'impossible to get articles content from:{article_url}', e)
        raise Exception("Unknown error scraping article")
    finally:
        time.sleep(random.uniform(1, 3))
        return fields_data


def scraping_session(links, headless=True):
    driver = open_browser_session(headless)
    articles = []
    total_articles = len(links.keys())
    for i, article_url in enumerate(links.keys()):
        logger.info(f"scraping article: {i}/{total_articles}")
        fields_data = scrape_article(article_url, driver)
        if is_current_period(fields_data.get('publicationdate'), period=24):
            articles.append(Article(fields_data))
        else:
            logger.info(f'Article older than last 24h: {article_url}')

    driver.quit()
    return articles
