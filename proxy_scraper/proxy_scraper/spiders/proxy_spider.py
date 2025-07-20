# proxy_scraper/proxy_scraper/spiders/proxy_spider.py

import scrapy
import base64  # Module for decoding base64 encoded strings
from ..items import ProxyItem

class ProxySpider(scrapy.Spider):
    name = "proxy_spider"
    allowed_domains = ["advanced.name"]
    start_urls = ["https://advanced.name/freeproxy"]

    collected_proxies_count = 0
    MAX_PROXIES_TO_COLLECT = 150

    def parse(self, response):
        """
        This method is called for each URL in start_urls and for subsequent pages.
        It's responsible for parsing the downloaded HTML response and extracting data from the table.
        """
        # self.logger.info(f"Processing URL: {response.url}")

        # Target the table rows containing proxies: type#id, follow to its attributes (tbody and then tr elements)
        proxy_rows = response.css('table#table_proxies tbody tr')

        if not proxy_rows:
            # self.logger.warning(f"No proxy rows found on {response.url}. Check HTML structure or if page is empty.")
            return  # Stop processing this page if no rows are found

        for i, row in enumerate(proxy_rows):
            if self.collected_proxies_count >= self.MAX_PROXIES_TO_COLLECT:
                self.logger.info(f"Collected {self.MAX_PROXIES_TO_COLLECT} proxies. Stopping processing current page rows.")
                break  # Stop processing rows on the current page if we have enough
            
            # Parse
            encoded_ip = row.css('td:nth-child(2)::attr(data-ip)').get()
            encoded_port = row.css('td:nth-child(3)::attr(data-port)').get()
            protocols_raw = row.css('td:nth-child(4) a::text').getall()
            protocols = [p.strip() for p in protocols_raw if p.strip()]
            protocols = list(dict.fromkeys(protocols))  # Remove duplicates while preserving order

            ip = None
            port = None

            # Decode base64 encoded IP and port
            if encoded_ip:
                try:
                    ip = base64.b64decode(encoded_ip).decode('utf-8').strip()
                except Exception as e:
                    self.logger.warning(f"Could not base64 decode IP '{encoded_ip}': {e}. Skipping this row.")
                    continue  # Skip this row if IP decoding fails

            if encoded_port:
                try:
                    port = int(base64.b64decode(encoded_port).decode('utf-8').strip())
                except Exception as e:
                    self.logger.warning(f"Could not base64 decode or convert port '{encoded_port}': {e}. Skipping this row.")
                    continue  # Skip this row if IP decoding fails

            # Yield a ProxyItem
            if ip and port is not None and protocols:
                proxy_item = ProxyItem(
                    ip=ip,
                    port=port,
                    protocols=protocols
                )
                yield proxy_item
                self.collected_proxies_count += 1
            else:
                self.logger.warning(f"Skipping row {i+1} due to missing data: IP={ip}, Port={port}, Protocols={protocols}")

        # Pagination: target the '»' link if not enough proxies collected
        next_page_url = response.xpath("//ul[@class='pagination pagination-lg']//a[contains(text(), '»')]/@href").get()
        
        if next_page_url is not None and self.collected_proxies_count < self.MAX_PROXIES_TO_COLLECT:
            self.logger.info(f"Following next page link: {next_page_url}")
            yield response.follow(next_page_url, callback=self.parse)
        elif self.collected_proxies_count >= self.MAX_PROXIES_TO_COLLECT:
            self.logger.info(f"Reached {self.MAX_PROXIES_TO_COLLECT} proxies. Not following next page.")
        else:
            self.logger.info("No more '»' page links found (or on last page).")
            