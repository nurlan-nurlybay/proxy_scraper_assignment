import json
import os
import time
from collections import defaultdict
import requests
from .items import ProxyItem

PERSONAL_TOKEN = "t_1a6e35f4"
UPLOAD_URL_MODULE = "https://test-rg8.ddns.net/api/post_proxies"
GET_TOKEN_URL_MODULE = "https://test-rg8.ddns.net/api/get_token"
MAX_PROXIES_PER_UPLOAD_MODULE = 10

MAX_RETRIES_PER_BATCH = 10
INITIAL_RETRY_DELAY_SECONDS = 10
MAX_RETRY_DELAY_SECONDS = 60

class JsonWriterPipeline:
    def __init__(self):
        self.proxies_file_path = os.path.join(os.getcwd(), 'proxies.json')
        self.proxies_data = []

    def process_item(self, item, spider):
        if isinstance(item, ProxyItem):
            self.proxies_data.append(dict(item))
            return item
        return item

    def close_spider(self, spider):
        spider.logger.info(f"Writing {len(self.proxies_data)} proxies to {self.proxies_file_path}")
        try:
            with open(self.proxies_file_path, 'w', encoding='utf-8') as f:
                f.write("[\n")
                formatted_proxies = []
                for i, proxy_dict in enumerate(self.proxies_data):
                    formatted_line = json.dumps(proxy_dict, separators=(',', ':'), ensure_ascii=False)
                    formatted_proxies.append(f"   {formatted_line}")
                f.write(",\n".join(formatted_proxies))
                f.write("\n]\n")
            spider.logger.info(f"Proxies saved to {self.proxies_file_path}")
        except Exception as e:
            spider.logger.error(f"Failed to save proxies to {self.proxies_file_path}: {e}")


class UploadPipeline:
    def __init__(self):
        self.proxies_to_upload = []
        self.upload_results = defaultdict(list)
        self.results_file_path = os.path.join(os.getcwd(), 'results.json')
        self.time_file_path = os.path.join(os.getcwd(), 'time.txt')
        self.start_time = time.time()
        
        self.PERSONAL_TOKEN = PERSONAL_TOKEN
        self.UPLOAD_URL = UPLOAD_URL_MODULE
        self.GET_TOKEN_URL = GET_TOKEN_URL_MODULE
        self.MAX_PROXIES_PER_UPLOAD = MAX_PROXIES_PER_UPLOAD_MODULE
        self.user_id = self.PERSONAL_TOKEN

        self.session = requests.Session()
        self.uploaded_batches_count = 0

        self.form_page_url = "https://test-rg8.ddns.net/task"

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        if isinstance(item, ProxyItem):
            self.proxies_to_upload.append(dict(item))
            return item
        return item

    def close_spider(self, spider):
        spider.logger.info("Spider closed. Attempting to upload collected proxies.")
        
        if self.proxies_to_upload:
            for i in range(0, len(self.proxies_to_upload), self.MAX_PROXIES_PER_UPLOAD):

                batch = self.proxies_to_upload[i:i + self.MAX_PROXIES_PER_UPLOAD]
                current_batch_number = self.uploaded_batches_count + 1
                
                proxies_comma_separated_string = ",".join([f"{p['ip']}:{p['port']}" for p in batch])

                json_payload_dict = {
                    "token": self.PERSONAL_TOKEN,
                    "user_id": self.user_id,
                    "len": len(batch),
                    "proxies": proxies_comma_separated_string
                }

                formatted_batch_for_results_json = [f"{p['ip']}:{p['port']}" for p in batch]

                headers = {
                    'Referer': self.form_page_url,
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                retries = 0
                upload_successful = False
                while retries < MAX_RETRIES_PER_BATCH:
                    # Re-create session for each attempt to ensure fresh cookies
                    self.session = requests.Session() 

                    # STEP 1: Establish Session with the Server (GET /task)
                    try:
                        # spider.logger.info(f"Batch {current_batch_number}, Attempt {retries + 1}: Establishing session with GET request to {self.form_page_url}")
                        get_response = self.session.get(self.form_page_url)
                        get_response.raise_for_status()
                        # spider.logger.info(f"Batch {current_batch_number}, Attempt {retries + 1}: Session established. Cookies after /task GET: {self.session.cookies.get_dict()}")
                        
                        # CRITICAL WORKAROUND (Still needed for x-user_id as observed)
                        self.session.cookies.set('x-user_id', self.PERSONAL_TOKEN, domain='test-rg8.ddns.net', path='/')
                        # spider.logger.info(f"Batch {current_batch_number}, Attempt {retries + 1}: Manually set x-user_id cookie. Cookies now: {self.session.cookies.get_dict()}")
                        
                    except requests.exceptions.RequestException as e:
                        spider.logger.error(f"Batch {current_batch_number}, Attempt {retries + 1}: Failed to establish session with GET request to {self.form_page_url}: {e}.")
                        retries += 1
                        current_delay = min(INITIAL_RETRY_DELAY_SECONDS * (2 ** (retries - 1)), MAX_RETRY_DELAY_SECONDS)
                        spider.logger.info(f"Retrying batch {current_batch_number} in {current_delay} seconds...")
                        time.sleep(current_delay)
                        continue

                    # STEP 2: Get the fresh form_token (GET /api/get_token)
                    try:
                        # spider.logger.info(f"Batch {current_batch_number}, Attempt {retries + 1}: Fetching fresh form_token from GET request to {self.GET_TOKEN_URL}")
                        token_response = self.session.get(self.GET_TOKEN_URL)
                        token_response.raise_for_status()
                        # spider.logger.info(f"Batch {current_batch_number}, Attempt {retries + 1}: Fresh form_token fetched. Cookies after /get_token GET: {self.session.cookies.get_dict()}")
                    except requests.exceptions.RequestException as e:
                        spider.logger.error(f"Batch {current_batch_number}, Attempt {retries + 1}: Failed to fetch fresh form_token from {self.GET_TOKEN_URL}: {e}.")
                        retries += 1
                        current_delay = min(INITIAL_RETRY_DELAY_SECONDS * (2 ** (retries - 1)), MAX_RETRY_DELAY_SECONDS)
                        spider.logger.info(f"Retrying batch {current_batch_number} in {current_delay} seconds...")
                        time.sleep(current_delay)
                        continue

                    # spider.logger.info(f"DEBUG: UPLOAD_URL: {self.UPLOAD_URL}")
                    # spider.logger.info(f"DEBUG: JSON Payload Dict being sent (type: {type(json_payload_dict)}):")
                    # spider.logger.info(json.dumps(json_payload_dict, indent=4))
                    # spider.logger.info(f"DEBUG: Headers being sent: {headers}")
                    # spider.logger.info(f"DEBUG: Cookies in session before POST: {self.session.cookies.get_dict()}")

                    try:
                        spider.logger.info(f"Submitting batch {current_batch_number}, Attempt {retries + 1} "
                                            f"of {len(batch)} proxies to {self.UPLOAD_URL}")
                        
                        upload_response = self.session.post(
                            self.UPLOAD_URL,
                            json=json_payload_dict,
                            headers=headers,
                            cookies=self.session.cookies
                        )
                        upload_response.raise_for_status()

                        response_json = upload_response.json()
                        save_id = response_json.get('save_id')

                        if save_id:
                            spider.logger.info(f"Successfully uploaded batch {current_batch_number}. Received save_id: {save_id}")
                            self.upload_results[save_id].extend(formatted_batch_for_results_json)
                            upload_successful = True
                            break
                        else:
                            spider.logger.warning(f"Batch {current_batch_number}, Attempt {retries + 1}: Upload successful but no 'save_id' found in response. Response: {response_json}")
                            upload_successful = True
                            break
                            
                    except requests.exceptions.RequestException as e:
                        spider.logger.error(f"Batch {current_batch_number}, Attempt {retries + 1}: Failed to upload: {e}")
                        if hasattr(e, 'response') and e.response is not None:
                            spider.logger.error(f"Response content: {e.response.text}")
                        
                        if hasattr(e, 'response') and e.response is not None and e.response.status_code in [429, 500, 502, 503, 504]:
                            retries += 1
                            current_delay = min(INITIAL_RETRY_DELAY_SECONDS * (2 ** (retries - 1)), MAX_RETRY_DELAY_SECONDS)
                            spider.logger.info(f"Retrying batch {current_batch_number} in {current_delay} seconds...")
                            time.sleep(current_delay)
                            continue
                        else:
                            spider.logger.error(f"Batch {current_batch_number}: Non-retryable error. Skipping batch.")
                            break

                    except json.JSONDecodeError:
                        spider.logger.error(f"Batch {current_batch_number}, Attempt {retries + 1}: Failed to decode JSON response. Response: {upload_response.text}")
                        break 
                    except Exception as e:
                        spider.logger.error(f"Batch {current_batch_number}, Attempt {retries + 1}: An unexpected error occurred: {e}")
                        break 

                if not upload_successful:
                    spider.logger.error(f"Batch {current_batch_number}: Failed to upload after {MAX_RETRIES_PER_BATCH} attempts. Moving to next batch.")
                
                self.uploaded_batches_count += 1
                time.sleep(2)

        else:
            spider.logger.info("No proxies collected to upload.")

        try:
            with open(self.results_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.upload_results, f, indent=4, ensure_ascii=False)
            spider.logger.info(f"Upload results saved to {self.results_file_path}")
        except Exception as e:
            spider.logger.error(f"Failed to save upload results to {self.results_file_path}: {e}")

        end_time = time.time()
        total_time_seconds = end_time - self.start_time
        hours, remainder = divmod(total_time_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_format = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

        try:
            with open(self.time_file_path, 'w') as f:
                f.write(time_format)
            spider.logger.info(f"Spider execution time ({time_format}) saved to {self.time_file_path}")
        except Exception as e:
            spider.logger.error(f"Failed to save execution time to {self.time_file_path}: {e}")
