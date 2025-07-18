# Proxy Scraper Project

This project is a Scrapy-based web scraper designed to extract proxy information from `https://advanced.name/freeproxy` and then attempt to upload this data to a specific API endpoint at `https://test-rg8.ddns.net/api/post_proxies`.

## Project Overview

The project is structured into a Scrapy Spider for data extraction and two Pipelines for processing the scraped data:
1.  **Scraping:** The `ProxySpider` visits `https://advanced.name/freeproxy`, parses the HTML, decodes base64-encoded IP addresses and ports, and extracts associated protocols.
2.  **Local Storage:** The `JsonWriterPipeline` takes the scraped proxy data and saves it to a `proxies.json` file in a specified compact JSON format.
3.  **API Upload (Challenged):** The `UploadPipeline` is designed to send the scraped proxies in batches to `https://test-rg8.ddns.net/api/post_proxies` and record the API's response (`save_id`) in `results.json`, along with the total execution time in `time.txt`.

## Features Implemented & Working

* **Proxy Scraping:** Successfully extracts IP addresses, ports, and protocols from `https://advanced.name/freeproxy`.
* **Base64 Decoding:** Correctly decodes the base64-encoded IP and port values from the source website.
* **Local JSON Output:** Generates `proxies.json` in the specified compact, line-by-line JSON array format.
* **Time Logging:** Records the total execution time of the spider in `time.txt`.
* **Batch Processing (Internal):** Proxies are correctly batched into groups of 10 for potential API submission.

## Upload Functionality: The Persistent "Bad Session" Challenge

The primary challenge encountered during this project has been the inability to successfully upload proxies to the `https://test-rg8.ddns.net/api/post_proxies` endpoint. Despite numerous attempts to correctly format the request, the server consistently responds with a `403 Client Error: Forbidden` and the message `{"detail":"Bad session"}`.

### Debugging Attempts & Server Responses:

We meticulously debugged the `UploadPipeline`'s interaction with the target API, guided by the server's error messages:

1.  **Initial Payload Format:** We initially attempted to send the `proxies` field as a list of strings (`["ip:port", ...]`).
    * **Server Response:** `{"detail":[{"type":"string_type","loc":["body","proxies"],"msg":"Input should be a valid string", ...}]}`
    * **Action:** Changed `proxies` to a single comma-separated string (`"ip1:port1,ip2:port2,..."`).

2.  **Missing Fields:** The server indicated `user_id` was a required field.
    * **Server Response:** `{"detail":[{"type":"missing","loc":["body","user_id"],"msg":"Field required", ...}]}`
    * **Action:** Included `user_id` in the JSON payload, set to the `PERSONAL_TOKEN`. `token` and `len` fields were also included based on form structure and common API practices.

3.  **Session Management (Cookies & Headers):**
    * **Observation:** Our `requests.Session()` object consistently showed an empty cookie jar after the initial `GET` request to `https://test-rg8.ddns.net/task`. This is unusual, as servers typically set session cookies via `Set-Cookie` headers.
    * **Workaround Attempt 1:** Manually injected the `x-user_id` cookie (value: `PERSONAL_TOKEN`) into the `requests.Session`'s cookie jar, as browser inspection revealed this cookie was being sent.
    * **Workaround Attempt 2:** Ensured `Referer`, `Content-Type: application/json`, and a realistic `User-Agent` header were always sent.
    * **Result:** Despite all these efforts, the `POST` request continued to fail with `{"detail":"Bad session"}`.

### The Root Cause: Client-Side JavaScript Dependency

Through detailed browser network inspection (specifically the `Request Headers` of the `GET /task` request itself), we discovered the definitive reason for the "Bad session" error:

* **Dynamic Cookie Generation:** The browser's initial `GET /task` request sends a `Cookie` header that includes `form_token_` (e.g., `form_token_=bf7d7538-...`).
* **Server's Missing `Set-Cookie`:** Crucially, the server's *response* to this `GET` request *does not* contain a `Set-Cookie` header for `form_token_` (or `x-user_id`).
* **Conclusion:** This strongly indicates that the `x-user_id` and `form_token_` cookies are **generated and set by client-side JavaScript** that runs when the `https://test-rg8.ddns.net/task` page loads in a real browser. The server then validates the presence and value of these JavaScript-generated cookies in subsequent requests (including the initial GET if the browser has previously executed the JS).

Since `requests` (and Scrapy's default downloader) **do not execute JavaScript**, they cannot generate these dynamic cookies or replicate the full client-side environment that the server expects for a valid session.

## Limitations Faced

The primary limitation is the inability of `requests` and standard Scrapy HTTP requests to execute client-side JavaScript. This prevents us from:

* Generating the `form_token_` cookie (and potentially `x-user_id` if it's also JS-generated).
* Replicating the full browser environment that the server's session validation mechanism relies upon.

## Next Steps (Proposed Solution)

To successfully upload the proxies, the project would need to integrate a **headless browser** (such as Playwright or Selenium). A headless browser can execute JavaScript, maintain a full browser context (including all dynamically set cookies), and thus accurately mimic a real user's interaction with the web form.

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
    * Scrape 10 proxies from `advanced.name`.
    * Attempt to upload the first batch of 10 proxies to `test-rg8.ddns.net`.
    * Save the scraped proxies to `proxies.json`.
    * Save upload results (will be empty due to "Bad session") to `results.json`.
    * Save the execution time to `time.txt`.