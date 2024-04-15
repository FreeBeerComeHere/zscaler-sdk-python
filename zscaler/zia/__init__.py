import re
import logging
import os
import time
import datetime
import uuid
from time import sleep
import requests
from box import Box, BoxList
from zscaler import __version__
from zscaler.cache.no_op_cache import NoOpCache
from zscaler.errors.http_error import ZscalerAPIError, HTTPError
from zscaler.exceptions.exceptions import ZscalerAPIException, HTTPException
from zscaler.cache.zscaler_cache import ZscalerCache
from zscaler.logger import setup_logging
from zscaler.utils import obfuscate_api_key
from zscaler.user_agent import UserAgent
from zscaler.ratelimiter.ratelimiter import RateLimiter
from zscaler.utils import (
    convert_keys_to_snake,
    snake_to_camel,
    format_json_response,
    retry_with_backoff,
    dump_request,
    dump_response,
)

from zscaler.zia.client import ZIAClient
from zscaler.zia.admin_and_role_management import AdminAndRoleManagementAPI
from zscaler.zia.apptotal import AppTotalAPI
from zscaler.zia.audit_logs import AuditLogsAPI
from zscaler.zia.authentication_settings import AuthenticationSettingsAPI
from zscaler.zia.activate import ActivationAPI
from zscaler.zia.device import DeviceAPI
from zscaler.zia.dlp import DLPAPI
from zscaler.zia.firewall import FirewallPolicyAPI
from zscaler.zia.forwarding_control import ForwardingControlAPI
from zscaler.zia.labels import RuleLabelsAPI
from zscaler.zia.locations import LocationsAPI
from zscaler.zia.sandbox import CloudSandboxAPI
from zscaler.zia.security import SecurityPolicyAPI
from zscaler.zia.ssl_inspection import SSLInspectionAPI
from zscaler.zia.traffic import TrafficForwardingAPI
from zscaler.zia.url_categories import URLCategoriesAPI
from zscaler.zia.url_filtering import URLFilteringAPI
from zscaler.zia.users import UserManagementAPI
from zscaler.zia.web_dlp import WebDLPAPI
from zscaler.zia.zpa_gateway import ZPAGatewayAPI
from zscaler.zia.isolation_profile import IsolationProfileAPI
from zscaler.zia.workload_groups import WorkloadGroupsAPI

# Setup the logger
setup_logging(logger_name="zscaler-sdk-python")
logger = logging.getLogger("zscaler-sdk-python")


class ZIAClientHelper(ZIAClient):
    """
    A Controller to access Endpoints in the Zscaler Internet Access (ZIA) API.

    The ZIA object stores the session token and simplifies access to CRUD options within the ZIA platform.

    Attributes:
        api_key (str): The ZIA API key generated from the ZIA console.
        username (str): The ZIA administrator username.
        password (str): The ZIA administrator password.
        cloud (str): The Zscaler cloud for your tenancy, accepted values are:

            * ``zscaler``
            * ``zscloud``
            * ``zscalerbeta``
            * ``zspreview``
            * ``zscalerone``
            * ``zscalertwo``
            * ``zscalerthree``
            * ``zscalergov``
            * ``zscalerten``

        override_url (str):
            If supplied, this attribute can be used to override the production URL that is derived
            from supplying the `cloud` attribute. Use this attribute if you have a non-standard tenant URL
            (e.g. internal test instance etc). When using this attribute, there is no need to supply the `cloud`
            attribute. The override URL will be prepended to the API endpoint suffixes. The protocol must be included
            i.e. http:// or https://.

    """

    _vendor = "Zscaler"
    _product = "Zscaler Internet Access"
    _build = __version__
    _env_base = "ZIA"
    url = "https://zsapi.zscaler.net/api/v1"
    env_cloud = "zscaler"

    def __init__(self, cloud, timeout=240, cache=None, fail_safe=False, **kw):
        self.api_key = kw.get("api_key", os.getenv(f"{self._env_base}_API_KEY"))
        self.username = kw.get("username", os.getenv(f"{self._env_base}_USERNAME"))
        self.password = kw.get("password", os.getenv(f"{self._env_base}_PASSWORD"))
        # The 'cloud' parameter should have precedence over environment variables
        self.env_cloud = (
            cloud or kw.get("cloud") or os.getenv(f"{self._env_base}_CLOUD")
        )
        if not self.env_cloud:
            raise ValueError(
                f"Cloud environment must be set via the 'cloud' argument or the {self._env_base}_CLOUD environment variable."
            )

        # URL construction
        if cloud == "zspreview":
            self.url = f"https://admin.{self.env_cloud}.net/api/v1"
        else:
            # Use override URL if provided, else construct the URL
            self.url = (
                kw.get("override_url")
                or os.getenv(f"{self._env_base}_OVERRIDE_URL")
                or f"https://zsapi.{self.env_cloud}.net/api/v1"
            )

        self.conv_box = True
        self.sandbox_token = kw.get("sandbox_token") or os.getenv(
            f"{self._env_base}_SANDBOX_TOKEN"
        )
        self.timeout = timeout
        self.fail_safe = fail_safe
        cache_enabled = (
            os.environ.get("ZSCALER_CLIENT_CACHE_ENABLED", "true").lower() == "true"
        )
        if cache is None:
            if cache_enabled:
                ttl = int(os.environ.get("ZSCALER_CLIENT_CACHE_DEFAULT_TTL", 3600))
                tti = int(os.environ.get("ZSCALER_CLIENT_CACHE_DEFAULT_TTI", 1800))
                self.cache = ZscalerCache(ttl=ttl, tti=tti)
            else:
                self.cache = NoOpCache()
        else:
            self.cache = cache
        # Initialize user-agent
        ua = UserAgent()
        self.user_agent = ua.get_user_agent_string()
        # Initialize rate limiter
        # You may want to adjust these parameters as per your rate limit configuration
        self.rate_limiter = RateLimiter(
            get_limit=2,  # Adjust as per actual limit
            post_put_delete_limit=2,  # Adjust as per actual limit
            get_freq=2,  # Adjust as per actual frequency (in seconds)
            post_put_delete_freq=2,  # Adjust as per actual frequency (in seconds)
        )
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        self.session_timeout_offset = datetime.timedelta(minutes=5)
        self.session_refreshed = None
        self.auth_details = None
        self.session_id = None
        self.authenticate()

    def extractJSessionIDFromHeaders(self, header):
        session_id_str = header.get("Set-Cookie", "")

        if not session_id_str:
            raise ValueError("no Set-Cookie header received")

        regex = re.compile(r"JSESSIONID=(.*?);")
        result = regex.search(session_id_str)

        if not result:
            raise ValueError("couldn't find JSESSIONID in header value")

        return result.group(1)

    def is_session_expired(self):
        if self.auth_details is None:
            return True
        now = datetime.datetime.now()
        if self.auth_details["passwordExpiryTime"] > 0 and (
            self.session_refreshed
            + datetime.timedelta(seconds=-self.session_timeout_offset)
            < now
        ):
            return True
        return False

    @retry_with_backoff(retries=5)
    def authenticate(self) -> Box:
        """
        Creates a ZIA authentication session.
        """
        api_key_chars = list(self.api_key)
        api_obf = obfuscate_api_key(api_key_chars)

        payload = {
            "apiKey": api_obf["key"],
            "username": self.username,
            "password": self.password,
            "timestamp": api_obf["timestamp"],
        }
        resp = requests.request(
            "POST",
            self.url + "/authenticatedSession",
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        if resp.status_code > 299:
            return resp
        self.session_refreshed = datetime.datetime.now()
        self.session_id = self.extractJSessionIDFromHeaders(resp.headers)
        self.auth_details = resp.json()
        return resp

    def deauthenticate(self):
        """
        Ends the ZIA authentication session.
        """
        logout_url = self.url + "/authenticatedSession"

        headers = self.headers.copy()
        headers.update({"Cookie": f"JSESSIONID={self.session_id}"})

        try:
            response = requests.delete(
                logout_url, headers=headers, timeout=self.timeout
            )
            if response.status_code == 204:
                self.session_id = None
                self.auth_details = None
                return True
            else:
                return False
        except requests.RequestException as e:
            return False
        
    def send(self, method, path, json=None, params=None, data=None, headers=None):
        """
        Send a request to the ZIA API.

        Parameters:
        - method (str): The HTTP method.
        - path (str): API endpoint path.
        - json (dict, optional): Request payload. Defaults to None.
        Returns:
        - Response: Response object from the request.
        """
        is_sandbox = "zscsb" in path
        api = self.url
        if is_sandbox:
            api = f"https://csbapi.{self.env_cloud}.net"
        url = f"{api}/{path.lstrip('/')}"
        start_time = time.time()
        # Update headers to include the user agent
        headers_with_user_agent = self.headers.copy()
        headers_with_user_agent["User-Agent"] = self.user_agent
        # Generate a unique UUID for this request
        request_uuid = uuid.uuid4()
        if headers is not None:
            headers_with_user_agent.update(headers)
        dump_request(
            logger,
            url,
            method,
            json,
            params,
            headers_with_user_agent,
            request_uuid,
            body=not is_sandbox,
        )
        # Check cache before sending request
        cache_key = self.cache.create_key(url, params)
        if method == "GET" and self.cache.contains(cache_key):
            resp = self.cache.get(cache_key)
            dump_response(
                logger=logger,
                url=url,
                method=method,
                params=params,
                resp=resp,
                request_uuid=request_uuid,
                start_time=start_time,
                from_cache=True,
            )
            return resp

        attempts = 0
        while attempts < 5:  # Trying a maximum of 5 times
            try:
                # If the token is None or expired, fetch a new token
                if self.is_session_expired():
                    logger.warning("The provided sesion expired. Refreshing...")
                    self.authenticate()
                resp = requests.request(
                    method=method,
                    url=url,
                    json=json,
                    data=data,
                    params=params,
                    headers=headers_with_user_agent,
                    timeout=self.timeout,
                    cookies={"JSESSIONID": self.session_id},
                )
                dump_response(
                    logger=logger,
                    url=url,
                    params=params,
                    method=method,
                    resp=resp,
                    request_uuid=request_uuid,
                    start_time=start_time,
                )
                if (
                    resp.status_code == 429
                ):  # HTTP Status code 429 indicates "Too Many Requests"
                    sleep_time = int(
                        resp.headers.get("Retry-After", 2)
                    )  # Default to 60 seconds if 'Retry-After' header is missing
                    logger.warning(
                        f"Rate limit exceeded. Retrying in {sleep_time} seconds."
                    )
                    sleep(sleep_time)
                    attempts += 1
                    continue
                else:
                    break
            except requests.RequestException as e:
                if attempts == 4:  # If it's the last attempt, raise the exception
                    logger.error(
                        f"Failed to send {method} request to {url} after 5 attempts. Error: {str(e)}"
                    )
                    raise e
                else:
                    logger.warning(
                        f"Failed to send {method} request to {url}. Retrying... Error: {str(e)}"
                    )
                    attempts += 1
                    sleep(5)  # Sleep for 5 seconds before retrying

        # If Non-GET call, clear the
        if method != "GET":
            self.cache.delete(cache_key)

        # Detailed logging for request and response
        try:
            response_data = resp.json()
        except ValueError:  # Using ValueError for JSON decoding errors
            response_data = resp.text
        # check if call was succesful
        if 200 > resp.status_code or resp.status_code > 299:
            # create errors
            try:
                error = ZscalerAPIError(url, resp, response_data)
                if self.fail_safe:
                    raise ZscalerAPIException(url, resp, response_data)
            except ZscalerAPIException:
                raise
            except Exception:
                error = HTTPError(url, resp, response_data)
                if self.fail_safe:
                    logger.error(response_data)
                    raise HTTPException(url, resp, response_data)
            logger.error(error)
        # Cache the response if it's a successful GET request
        if method == "GET" and resp.status_code == 200:
            self.cache.add(cache_key, resp)
        return resp

    def get(self, path, json=None, params=None):
        """
        Send a GET request to the ZIA API.

        Parameters:
        - path (str): API endpoint path.
        - data (dict, optional): Request payload. Defaults to None.
        Returns:
        - Response: Response object from the request.
        """

        # Use rate limiter before making a request
        should_wait, delay = self.rate_limiter.wait("GET")
        if should_wait:
            time.sleep(delay)

        # Now proceed with sending the request
        resp = self.send("GET", path, json, params)
        formatted_resp = format_json_response(resp, box_attrs=dict())
        return formatted_resp

    def put(self, path, json=None, params=None):
        should_wait, delay = self.rate_limiter.wait("PUT")
        if should_wait:
            time.sleep(delay)
        resp = self.send("PUT", path, json, params)
        formatted_resp = format_json_response(resp, box_attrs=dict())
        return formatted_resp

    def post(self, path, json=None, params=None, data=None, headers=None):
        should_wait, delay = self.rate_limiter.wait("POST")
        if should_wait:
            time.sleep(delay)
        resp = self.send("POST", path, json, params, data=data, headers=headers)
        formatted_resp = format_json_response(resp, box_attrs=dict())
        return formatted_resp

    def delete(self, path, json=None, params=None):
        should_wait, delay = self.rate_limiter.wait("DELETE")
        if should_wait:
            time.sleep(delay)
        return self.send("DELETE", path, json, params)

    def get_paginated_data(
        self,
        path=None,
        params=None,
        expected_status_code=200,
        page=None,
        page_size=100,  # Default value
        search=None
    ):
        """
        Fetch paginated data from the ZIA API based on specified parameters.

        Args:
            path (str): The API endpoint path to send requests to.
            params (dict): Additional query parameters for the API request.
            expected_status_code (int): The expected HTTP status code for a successful request.
            page (int): Specifies the page offset, defaults to starting from the first page if pagination is supported.
            page_size (int): Specifies the page size, default is 100 with a maximum of 1000.
            search (str): Search query string to filter the results, applicable if supported by the endpoint.

        Returns:
            list: A list of fetched items.
            str: An error message if any occurred during the data fetching process.
        """
        logger = logging.getLogger(__name__)
        ERROR_MESSAGES = {
            "UNEXPECTED_STATUS": "Unexpected status code {status_code} received on page {page}.",
            "EMPTY_RESULTS": "No results found on page {page}.",
        }

        if params is None:
            params = {}

        # Add page and search parameters to local params dictionary, not overriding input params
        local_params = {
            'page': page or 1,
            'pageSize': page_size,  # Adjusting the name to API specification
            'search': search
        }
        # Merge with additional params provided by the user
        local_params.update(params)

        # Convert all params keys to CamelCase for API compliance
        camel_case_params = {snake_to_camel(key): value for key, value in local_params.items() if value is not None}

        ret_data = []
        current_page = camel_case_params.get('page', 1)

        while True:
            # Construct the URL with parameters
            url_params = "&".join(f"{key}={value}" for key, value in camel_case_params.items())
            required_url = f"{path}?{url_params}"

            should_wait, delay = self.rate_limiter.wait("GET")
            if should_wait:
                time.sleep(delay)

            response = self.send("GET", required_url)
            if response.status_code != expected_status_code:
                error_message = ERROR_MESSAGES["UNEXPECTED_STATUS"].format(status_code=response.status_code, page=current_page)
                logger.error(error_message)
                return [], error_message

            data = response.json()
            if not data:  # Handles empty list or non-paginated endpoints
                logger.info(ERROR_MESSAGES["EMPTY_RESULTS"].format(page=current_page))
                break

            ret_data.extend(convert_keys_to_snake(data))

            # Check data size for stopping condition
            if len(data) < camel_case_params['pageSize']:
                break  # Stop if data returned is less than pageSize

            current_page += 1
            camel_case_params['page'] = current_page
            time.sleep(1)  # Sleep to handle rate limiting

        return ret_data, None

    @property
    def admin_and_role_management(self):
        """
        The interface object for the :ref:`ZIA Admin and Role Management interface <zia-admin_and_role_management>`.

        """
        return AdminAndRoleManagementAPI(self)

    @property
    def apptotal(self):
        """
        The interface object for the :ref:`ZIA AppTotal interface <zia-apptotal>`.

        """
        return AppTotalAPI(self)

    @property
    def audit_logs(self):
        """
        The interface object for the :ref:`ZIA Admin Audit Logs interface <zia-audit_logs>`.

        """
        return AuditLogsAPI(self)

    @property
    def activate(self):
        """
        The interface object for the :ref:`ZIA Activation interface <zia-config>`.

        """
        return ActivationAPI(self)

    @property
    def dlp(self):
        """
        The interface object for the :ref:`ZIA DLP Dictionaries interface <zia-dlp>`.


        """
        return DLPAPI(self)

    @property
    def firewall(self):
        """
        The interface object for the :ref:`ZIA Firewall Policies interface <zia-firewall>`.

        """
        return FirewallPolicyAPI(self)

    @property
    def forwarding_control(self):
        """
        The interface object for the :ref:`ZIA Forwarding Control Policies interface <zia-forwarding>`.

        """
        return ForwardingControlAPI(self)

    @property
    def labels(self):
        """
        The interface object for the :ref:`ZIA Rule Labels interface <zia-labels>`.

        """
        return RuleLabelsAPI(self)

    @property
    def device(self):
        """
        The interface object for the :ref:`ZIA device interface <zia-device>`.

        """
        return DeviceAPI(self)

    @property
    def locations(self):
        """
        The interface object for the :ref:`ZIA Locations interface <zia-locations>`.

        """
        return LocationsAPI(self)

    @property
    def sandbox(self):
        """
        The interface object for the :ref:`ZIA Cloud Sandbox interface <zia-sandbox>`.

        """
        return CloudSandboxAPI(self)

    @property
    def security(self):
        """
        The interface object for the :ref:`ZIA Security Policy Settings interface <zia-security>`.

        """
        return SecurityPolicyAPI(self)

    @property
    def authentication_settings(self):
        """
        The interface object for the :ref:`ZIA Authentication Security Settings interface <zia-auth-settings>`.

        """
        return AuthenticationSettingsAPI(self)

    @property
    def ssl(self):
        """
        The interface object for the :ref:`ZIA SSL Inspection interface <zia-ssl_inspection>`.

        """
        return SSLInspectionAPI(self)

    @property
    def traffic(self):
        """
        The interface object for the :ref:`ZIA Traffic Forwarding interface <zia-traffic>`.

        """
        return TrafficForwardingAPI(self)

    @property
    def url_categories(self):
        """
        The interface object for the :ref:`ZIA URL Categories interface <zia-url_categories>`.

        """
        return URLCategoriesAPI(self)

    @property
    def url_filtering(self):
        """
        The interface object for the :ref:`ZIA URL Filtering interface <zia-url_filtering>`.

        """
        return URLFilteringAPI(self)

    @property
    def users(self):
        """
        The interface object for the :ref:`ZIA User Management interface <zia-users>`.

        """
        return UserManagementAPI(self)

    @property
    def web_dlp(self):
        """
        The interface object for the :ref: `ZIA Data-Loss-Prevention Web DLP Rules`.

        """
        return WebDLPAPI(self)

    @property
    def zpa_gateway(self):
        """
        The interface object for the :ref: `ZIA Data-Loss-Prevention Web DLP Rules`.

        """
        return ZPAGatewayAPI(self)

    @property
    def isolation_profile(self):
        """
        The interface object for the :ref: `ZIA Cloud Browser Isolation Profile`.

        """
        return IsolationProfileAPI(self)

    @property
    def workload_groups(self):
        """
        The interface object for the :ref: `ZIA Workload Groups`.

        """
        return WorkloadGroupsAPI(self)
