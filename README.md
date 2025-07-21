# Proxy Scraper Project

This project is a Scrapy-based web scraper designed to extract proxy information from `https://advanced.name/freeproxy` and then successfully upload this data to a specific API endpoint at `https://test-rg8.ddns.net/api/post_proxies`.

## Project Overview

The project is structured into a Scrapy Spider for data extraction and two Pipelines for processing the scraped data:

1.  **Scraping:** The `ProxySpider` visits `https://advanced.name/freeproxy`, parses the HTML, decodes base64-encoded IP addresses and ports, and extracts associated protocols. It is configured to collect a specified number of proxies (e.g., 150).

2.  **Local Storage:** The `JsonWriterPipeline` takes the scraped proxy data and saves it to a `proxies.json` file in a specified compact JSON format.

3.  **API Upload:** The `UploadPipeline` is designed to send *all* collected proxies in batches to `https://test-rg8.ddns.net/api/post_proxies`. It incorporates robust retry logic with exponential backoff to handle transient network issues and server-side rate limiting. It records the API's response (`save_id`) for successfully uploaded batches in `results.json`, along with the total execution time in `time.txt`.

## Features Implemented & Working

* **Proxy Scraping:** Successfully extracts IP addresses, ports, and protocols from `https://advanced.name/freeproxy`, including decoding base64-encoded values.

* **Local JSON Output:** Generates `proxies.json` in the specified compact, line-by-line JSON array format.

* **Time Logging:** Records the total execution time of the spider in `time.txt`.

* **Batch Processing:** Proxies are correctly batched into groups of 10 for API submission.

* **Robust API Uploads:** The `UploadPipeline` now successfully handles the server's session requirements and rate limits, allowing for the complete upload of all collected proxies.

## Overcoming the "Bad Session" and "Too Many Requests" Challenges

The primary challenge involved understanding and overcoming the server's session validation and rate-limiting mechanisms.

### Initial "Bad Session" Debugging & Resolution:

* **Initial Observation:** Our `requests.Session()` object showed an empty cookie jar after the initial `GET` request to `https://test-rg8.ddns.net/task`. This led to the `{"detail":"Bad session"}` error.

* **Key Discovery:** Through detailed browser network inspection and confirmation from the instructor, it was determined that the `form_token` cookie is **set by the server** in response to a *subsequent* API call (`GET /api/get_token`), which is typically initiated by client-side JavaScript in a real browser. The `x-user_id` cookie was also observed to be sent by the browser.

* **Solution Implemented:** The `UploadPipeline` was updated to perform a two-step process for each batch:

    1.  Make a `GET` request to `https://test-rg8.ddns.net/task` to establish a base session.

    2.  Immediately follow with a `GET` request to `https://test-rg8.ddns.net/api/get_token`. The server's response to this specific endpoint contains the `Set-Cookie` header for the `form_token`, which `requests.Session()` automatically captures.

    3.  The `x-user_id` cookie is manually set in the session's cookie jar as a robust workaround.

### Overcoming "Too Many Requests":

* **Problem:** After resolving the "Bad session" issue, attempting to upload multiple batches quickly led to `429 Client Error: Too Many Requests` with the detail `"Too Many Requests per IP"`. This indicated server-side rate limiting.

* **Solution Implemented:** A **retry mechanism with exponential backoff** was integrated into the `UploadPipeline`. For each batch upload attempt:

    * The `GET /task` and `GET /api/get_token` requests are performed to ensure a fresh session and `form_token`.

    * The `POST /api/post_proxies` request is then attempted.

    * If a retryable error (like `429`, `500`, `502`, `503`, `504`) occurs, the script pauses for an exponentially increasing duration before retrying the *same batch*.

    * A maximum number of retries (`MAX_RETRIES_PER_BATCH`) is set to prevent infinite loops.

    * A small, fixed delay (`time.sleep(2)`) is also maintained between successful batch uploads to be polite to the server.

## How to Run the Project

1.  **Navigate to the project directory:**

    ```bash
    cd ~/proxy_scraper_assignment/proxy_scraper
    ```

2.  **Run the spider:**

    ```bash
    scrapy crawl proxy_spider
    ```

    This will:

    * Scrape proxies from `advanced.name` (up to `MAX_PROXIES_TO_COLLECT` as defined in `proxy_spider.py`).

    * Save the scraped proxies to `proxies.json`.

    * Attempt to upload *all collected proxies* in batches to `test-rg8.ddns.net`, utilizing the retry mechanism.

    * Save the upload results (including `save_id`s for successful batches) to `results.json`.

    * Save the total execution time to `time.txt`.