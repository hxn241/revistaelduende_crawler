import datetime as dt
import os

from modules.core import CoreMultithread
from modules.utils import setup_logger
from settings import config, ROOT_DIR
from modules.links import get_urls_from_sitemap
from modules.article import scraping_session


if __name__ == '__main__':
    logger = setup_logger(
        log_filename=f"{dt.datetime.now():%Y%m%d}_elduende.log",
        src_path=os.path.join(ROOT_DIR, "data")
    )
    logger.info("ELDUENDE. Process started")
    url = config['elduende']['sitemap_url']
    links = get_urls_from_sitemap(url, period=config['period_update'])
    articles = scraping_session(links, headless=True)
    if articles:
        core_api = CoreMultithread(config['core'])
        created_items = core_api.create_items(articles)
        logger.info(f'Total items created: {[r[1] for r in created_items].count(200)}/{len(created_items)}')
    else:
        logger.info("No new articles to upload")
    logger.info(
        "Process finished\n"
        "===================================================================\n\n"
    )
