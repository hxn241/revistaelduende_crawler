import pandas as pd

from modules.article import scraping_session
from modules.links import get_urls_from_sitemap, get_differences, read_pickle, write_pickle
from settings import config

# LINKS = {'https://revistaelduende.com/revista/194/dale-la-vuelta-a-el-aguila-sin-filtrar/': '2022-04-05T08:11:36+00:00'}
# links = 'https://revistaelduende.com/planes/tendencias/para-mama-todo-lo-que-ella-necesita'


def test_get_new_links():
    links = get_urls_from_sitemap(config['elduende']['sitemap_url'], period=config['period_update'])
    print(links)


def test_modify_pickle():
    links = read_pickle()
    print(links)
    # mod_links = [link_d for link_d in links if link_d.keys()[0] != 'https://revistaelduende.com/planes/tendencias/para-mama-todo-lo-que-ella-necesita/']
    mod_links=links
    del mod_links['https://revistaelduende.com/planes/tendencias/para-mama-todo-lo-que-ella-necesita/']
    write_pickle(mod_links)
    print(f'linkd: {len(links)} --> mod_linkds: {len(mod_links)}')


def test_compare_dicts():
    original = {'google.es':'6','yahoo.com':'1'}
    new = {'google.es':'6','yahoo.com':'3','facebook.com':'9'}
    new_diff = get_differences(original, new)
    print(new_diff)


def test_links_fetch():
    try:
        checked_link = 'https://revistaelduende.com/articulo/fritz-kola-la-aktitud-importa/'
        links = get_urls_from_sitemap(config['elduende']['sitemap_url'], period=config['period_update'])
        assert checked_link in links.keys()
    except:
        print(links)


def articles_to_xlsx(articles):
    df = pd.DataFrame.from_records([article.get_json_body() for article in articles])
    df.to_excel('test/data/articles.xlsx', index=False)


if __name__ == "__main__":
    # test_links_fetch()
    # test_compare_dicts()
    # test_get_new_links()
    # test_modify_pickle()

    # dict_1 = {'https://revistaelduende.com/planes/tendencias/polo-ralph-lauren-lanza-su-coleccion-pride':'333'}
    # links = get_urls_from_sitemap(config['elduende']['sitemap_url'],period=24)
    url = config['elduende']['sitemap_url']
    links = get_urls_from_sitemap(url, period=config['period_update'])
    articles = scraping_session(links, headless=False)
    # print(*(f"TITLE: {article.title}\nAUTHOR: {article.author}" for article in articles))
#