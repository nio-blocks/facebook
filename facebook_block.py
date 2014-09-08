import requests
from datetime import datetime
from nio.common.discovery import Discoverable, DiscoverableType
from nio.metadata.properties.string import StringProperty
from nio.metadata.properties.object import ObjectProperty
from nio.metadata.properties.holder import PropertyHolder
from nio.metadata.properties.timedelta import TimeDeltaProperty
from nio.metadata.properties.int import IntProperty
from nio.common.signal.base import Signal
from http_blocks.rest.rest_block import RESTPolling


class OAuthCreds(PropertyHolder):
    """ Property holder for Twitter OAuth credentials.

    """
    consumer_key = StringProperty(title='Consumer Key', )
    app_secret = StringProperty(title='App Secret', )
    oauth_token = StringProperty(title='OAuth Token', )
    oauth_token_secret = StringProperty(title='OAuth Secret', )


class FacebookSignal(Signal):
    def __init__(self, data):
        super().__init__()
        for k in data:
            setattr(self, k, data[k])

@Discoverable(DiscoverableType.block)
class FacebookBlock(RESTPolling):
    """ This block polls the Facebook Graph API, searching for posts 
    matching a configurable phrase. 

    Params:
        phrase (str): The phrase with which to search posts. Need not be
            url-quoted.
        limit (int): Maximum number of posts contained in each response.
        lookback (timedelta): Initial window of desirable posts (for the 
            very first request.

    """
    URL_FORMAT = ("https://graph.facebook.com/v1.0/"
                  "search?since={0}&q={1}&type=post&limit={2}")

    TOKEN_URL_FORMAT = ("https://graph.facebook.com/oauth"
                        "/access_token?client_id={0}&client_secret={1}"
                        "&grant_type=client_credentials")

    creds = ObjectProperty(OAuthCreds, title='Credentials')
    lookback = TimeDeltaProperty(title='Lookback')
    limit = IntProperty(title='Limit (per poll)', default=10)

    def __init__(self):
        super().__init__()
        self._url = None
        self._paging_field = "paging"
        self._created_field = "created_time"
        self._access_token = None

    def configure(self, context):
        super().configure(context)
        lb = self._unix_time(datetime.utcnow() - self.lookback)
        self._freshest = [lb] * self._n_queries


    def _authenticate(self):
        """ Overridden from the RESTPolling block.

        Generates and records the access token for pending requests.

        """
        if self.creds.consumer_key is None or self.creds.app_secret is None:
            self._logger.error("You need a consumer key and app secret, yo")
        else:
            self._access_token = self._request_access_token()
        
    def _process_response(self, resp):
        """ Extract fresh posts from the Facebook graph api response object.

        Args:
            resp (Response)
        
        Returns:
            signals (list(Signal)): The list of signals to notify, each of
                which corresponds to a fresh FB post.
            paging (bool): Denotes whether or not paging requests are
                necessary.

        """
        signals = []
        resp = resp.json()
        fresh_posts = posts = resp['data']
        paging = resp.get(self._paging_field) is not None
        self._logger.debug("Facebook response contains %d posts" % len(posts))

        # we shouldn't see empty responses, but we'll protect our necks.
        if len(posts) > 0:
            self.update_freshness(posts)
            fresh_posts = self.find_fresh_posts(posts)
            paging = len(fresh_posts) == self.limit

            # store the timestamp of the oldest fresh post for use in url
            # preparation later.
            if len(fresh_posts) > 0:
                self.prev_stalest = self.created_epoch(fresh_posts[-1])

        signals = [FacebookSignal(p) for p in fresh_posts]
        self._logger.debug("Found %d fresh posts" % len(signals))
        
        return signals, paging

    def _request_access_token(self):
        """ Request an access token directly from facebook.

        Args:
            None

        Returns:
            token (str): The access token, which goes on the end of a request.

        """
        resp = requests.get(self.TOKEN_URL_FORMAT.format(
            self.creds.consumer_key, self.creds.app_secret)
        )
        status = resp.status_code

        # If the token request fails, try to use the configured app id
        # and secret. This probably won't work, but the docs say that it
        # should. for more info, see:
        # https://developers.facebook.com/docs/facebook-login/access-tokens
        token = "%s|%s" % (self.creds.consumer_key, self.creds.app_secret)
        if status == 200:
            token = resp.text.split('access_token=')[1]
        else:
            self._logger.error(
                "Facebook token request failed with status %d" % status
            )
        return token
        
    def _prepare_url(self, paging=False):
        """ Overridden from RESTPolling block.

        Appends the access token to the format string and builds the headers
        dictionary. If paging, we do some string interpolation to get our
        arguments into the request url. Otherwise, we append the until parameter 
        to the end.

        Args:
            paging (bool): Are we paging?

        Returns:
            headers (dict): Contains the (case sensitive) http headers.

        """
        headers = {"Content-Type": "application/json"}
        fmt = "%s&access_token=%s" % (self.URL_FORMAT, self._access_token)
        if not paging:
            self.paging_url = None
            self.url = fmt.format(self.freshest - 2, 
                                  self.current_query, 
                                  self.limit)
        else:
            self.paging_url = "%s&until=%d" % (self.url, self.prev_stalest)

        return headers
