import requests
import logging
import requests.packages
from json import JSONDecodeError
from typing import List, Dict
from .exceptions import TheCatApiException
from .models import *

class RestAdapter:
    def __init__(self, hostname: str = 'api.thecatapi.com', api_key: str = '', ver: str = 'v1', ssl_verify: bool = True, logger: logging.Logger = None ):
        """
        Constructor for RestAdapter
        :param hostname: Normally, api.thecatapi.com
        :param api_key: (optional) string used for authentication when POSTing or DELETEing
        :param ver: always v1
        :param ssl_verify: Normally set to True, but if having SSL/TLS cert validation issues, can turn off with False
        :param logger: (optional) If your app has a logger, pass it in here.
        """
        self._logger = logger or logging.getLogger(__name__)
        self.url = "https://{}/{}".format(hostname, ver)
        self._api_key = api_key
        self._ssl_verify = ssl_verify
        if not ssl_verify:
            requests.packages.urllib3.disable_warnings()

    def _do(self, http_method: str, endpoint: str, ep_params: Dict = None, data: Dict = None) -> Result:
        """
        Genric method for request methods
        :param http_method: Normally, request method
        :endpoint: endpoint to get the data
        :ep_params: Any other query parameter
        :data: data for POST, DELETE, etc. methods
        """
        full_url = self.url + endpoint
        headers = {'x-api-key': self._api_key}
        log_line_pre = f"method={http_method}, url={full_url}, params={ep_params}"
        log_line_post = ', '.join((log_line_pre, "success={}, status_code={}, message={}"))

        # Log HTTP params and perform an HTTP request, catching and re-raising any exceptions
        try:
            self._logger.debug(msg=log_line_pre)
            response = requests.request(method=http_method, url=full_url, verify=self._ssl_verify, 
                                        headers=headers, params=ep_params, json=data)
        except requests.exceptions.RequestException as e:
            self._logger.error(msg=(str(e)))
            raise TheCatApiException("Request failed") from e

        # Deserialize JSON output to Python object, or return failed Result on exception
        try:
            data_out = response.json()
        except (ValueError, JSONDecodeError) as e:
            self._logger.error(msg=log_line_post.format(False, None, e))
            raise TheCatApiException("Bad JSON in response") from e

        # If status_code in 200-299 range, return success Result with data, otherwise raise exception
        is_success = 299 >= response.status_code >= 200
        log_line = log_line_post.format(is_success, response.status_code, response.reason)
        if is_success:  # OK
            self._logger.debug(msg=log_line)
            return Result(status_code=response.status_code, message=response.reason, data=data_out)
        self._logger.error(msg=log_line)
        raise TheCatApiException(f"{response.status_code}: {response.reason}")

    def fetch_data(self, url: str) -> bytes:
        # GET URL; catching, logging, and re-raising any exceptions
        http_method = 'GET'
        try:
            log_line = f"method={http_method}, url={url}"
            self._logger.debug(msg=log_line)
            response = requests.request(method=http_method, url=url, verify=self._ssl_verify)
        except requests.exceptions.RequestException as e:
            self._logger.error(msg=(str(e)))
            raise TheCatApiException(str(e)) from e

        # If status_code in 200-299 range, return byte stream, otherwise raise exception
        is_success = 299 >= response.status_code >= 200
        log_line = f"success={is_success}, status_code={response.status_code}, message={response.reason}"
        self._logger.debug(msg=log_line)
        if not is_success:
            raise TheCatApiException(response.reason)
        return response.content

    def get(self, endpoint: str, ep_params: Dict = None) -> Result:
        return self._do(http_method='GET', endpoint=endpoint, ep_params=ep_params)
        
    def post(self, endpoint: str, ep_params: Dict = None, data: Dict = None) -> Result:
        return self._do(http_method='POST', endpoint=endpoint, ep_params=ep_params, data=data)

    def delete(self, endpoint: str, ep_params: Dict = None, data: Dict = None) -> Result:
        return self._do(http_method='DELETE', endpoint=endpoint, ep_params=ep_params, data=data)
