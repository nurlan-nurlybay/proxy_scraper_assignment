# proxy_scraper/proxy_scraper/items.py

import scrapy


class ProxyItem(scrapy.Item):
    ip = scrapy.Field()
    port = scrapy.Field()
    protocols = scrapy.Field()


class UploadResultItem(scrapy.Item):
    save_id = scrapy.Field()
    uploaded_proxies = scrapy.Field()
