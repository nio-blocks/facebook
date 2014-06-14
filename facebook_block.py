import requests
import json
import re
from datetime import datetime
from math import ceil
from urllib.request import quote
from .http_blocks.rest.rest_block import RESTPolling
from nio.metadata.properties.string import StringProperty
from nio.metadata.properties.int import IntProperty
from nio.metadata.properties.bool import BoolProperty
from nio.metadata.properties.timedelta import TimeDeltaProperty
from nio.common.signal.base import Signal


class FacebookSignal(Signal):
    
    def __init__(self, data):
        for k in data:
            setattr(self, k, data[k])

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

    phrase = StringProperty(default='')
    limit = IntProperty(default=100)
    lookback = TimeDeltaProperty()

    def __init__(self):
        super().__init__()
        self._url = None
        self._paging_field = "paging"
        self._access_token = None
        self._freshest = None
        self._prev_freshest = None
        self._prev_stalest = None

    def configure(self, context):
        super().configure(context)
        self._freshest = self._unix_time(datetime.utcnow() - self.lookback)

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
        posts = resp['data']
        paging = resp.get(self._paging_field) is not None
        self._logger.debug("Facebook response contains %d posts" % len(posts))

        # we shouldn't see empty responses, but we'll protect our necks.
        if len(posts) > 0:

            # timestamps for the most and least recent posts on the
            # current page, respectively.
            freshest = self._created_epoch(posts[0])
            stalest = self._created_epoch(posts[-1])

            # if the most recent post on the current page is more recent
            # than the most recent post notified so far, set self._freshest
            # accordingly and store its previous value. Now the window of
            # fresh (i.e. desirable) are defined as having timestamps btwn
            # self._prev_freshest and self._freshest.
            if freshest > self._freshest:
                self._prev_freshest = self._freshest
                self._freshest = freshest

            # if the current page is not full or the least recent post on
            # the page is outside of the window defined above, we don't
            # need to do any more paging.
            if len(posts) < self.limit or self._prev_freshest > stalest:
                paging = False

                # filter out stale posts
                posts = self._find_fresh_posts(posts)

        signals = [FacebookSignal(p) for p in posts]
        self._logger.debug("Found %d fresh posts" % len(signals))
        
        # record the unix timestamp for the least recent post on the
        # current page. this is used to fill the 'until' parameter
        # while paging through results.
        self._prev_stalest = self._created_epoch(posts[-1])
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

    def _find_fresh_posts(self, posts):
        """ Return only those posts which are guaranteed to be fresh.
        
        Args:
            posts (list(dict))

        Returns:
            posts (list(dict)): Stale posts are filtered out.

        """
        # filter out those posts which are less recent than the
        # self._prev_freshest.
        posts = [p for p in posts \
                 if self._created_epoch(p) > self._prev_freshest]
        return posts
        
    def _prepare_url(self, paging=False):
        """ Overridden from RESTPolling block.

        Appends the access token to the format string. If paging, we do some
        string interpolation to get our arguments into the request url.
        Otherwise, we append the until parameter to the end.

        Args:
            paging (bool): Are we paging?

        Returns:
            None

        """
        fmt = "%s&access_token=%s" % (self.URL_FORMAT, self._access_token)
        if not paging:
            self._url = fmt.format(self._freshest - 2, 
                                   quote(self.phrase), 
                                   self.limit)
        else:
            self._url = "%s&until=%d" % \
                               (self._url, self._prev_stalest)

    def _created_epoch(self, post):
        """ Helper function to return the second since the epoch
        for the given post's 'created_time.

        Args:
            post (dict): Should contain a 'created_time' key.
        
        Returns:
            seconds (int): post[created_time] in seconds since epoch.
        
        """
        dt = self._parse_date(post.get('created_time', ''))
        return self._unix_time(dt)
        
    def _parse_date(self, date):
        """ Parse facebook's date string into a datetime.datetime.

        """
        exp = r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})"
        m = re.match(exp, date)
        return datetime(*[int(n) for n in m.groups(0)])

    def _unix_time(self, dt):
        epoch = datetime.utcfromtimestamp(0)
        delta = dt - epoch
        return int(delta.total_seconds())
        
