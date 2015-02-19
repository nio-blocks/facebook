from ..facebook_feed_block import FacebookFeed, FeedType
from ..http_blocks.rest.rest_block import RESTPolling
from unittest.mock import patch, MagicMock
from requests import Response
from nio.util.support.block_test_case import NIOBlockTestCase
from nio.modules.threading import Event


class FBTestBlk(FacebookFeed):

    def __init__(self, event):
        super().__init__()
        self._event = event

    def poll(self, paging=False):
        super().poll(paging)
        self._event.set()


class TestFacebookFeed(NIOBlockTestCase):

    @patch("requests.get")
    @patch("requests.Response.json")
    @patch.object(FacebookFeed, "created_epoch")
    def test_process_responses(self, mock_epoch, mock_json, mock_get):
        mock_get.return_value = Response()
        mock_get.return_value.status_code = 200
        mock_epoch.return_value = 23
        mock_json.return_value = {
            'data': [
                {'key': 'val'}
            ]
        }
        e = Event()
        blk = FBTestBlk(e)
        blk._authenticate = MagicMock()
        self.configure_block(blk, {
            "log_level": "DEBUG",
            "polling_interval": {
                "seconds": 1
            },
            "retry_interval": {
                "seconds": 1
            },
            "queries": [
                "foobar"
            ],
            "limit": 2,
        })
        blk._freshest = [22]
        blk.start()
        e.wait(2)
        self.assertEqual(blk._freshest, [23])
        self.assert_num_signals_notified(1)
        blk.stop()

    def test_prepare_url(self):
        blk = FacebookFeed()
        self.configure_block(blk, {
            "queries": ["foobar"]
        })

        def prepare_url(blk, feed_type):
            return blk.URL_FORMAT.format(blk.queries[0],
                                         feed_type,
                                         blk.freshest - 2,
                                         blk.limit) + \
                "&access_token={}".format(blk._access_token)
        # default feed type
        blk._prepare_url()
        self.assertEqual(blk.url, prepare_url(blk, 'feed'))
        # posts
        blk.feed_type = FeedType.POSTS
        blk._prepare_url()
        self.assertEqual(blk.url, prepare_url(blk, 'posts'))
        # posts
        blk.feed_type = FeedType.TAGGED
        blk._prepare_url()
        self.assertEqual(blk.url, prepare_url(blk, 'tagged'))
        # posts
        blk.feed_type = FeedType.PROMOTABLE_POSTS
        blk._prepare_url()
        self.assertEqual(blk.url, prepare_url(blk, 'promotable_posts'))

    @patch.object(RESTPolling, "_retry")
    @patch.object(RESTPolling, "_authenticate")
    @patch("requests.get")
    def test_username_query(self, mock_get, mock_auth, mock_retry):
        """ username queries get a 404 from Facebook """
        blk = FacebookFeed()
        self.configure_block(blk, {
            "queries": [
                "username1",
                "username2"
            ]
        })
        mock_get.return_value = MagicMock()
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = \
            {'error':
             {'message':
              '(#803) Cannot query users by their username (username1)',
              'code': 803,
              'type': 'OAuthException'
              }
             }
        self.assertEqual(0, blk._idx)
        blk.poll()
        # skip to next idx because we are not retrying.
        self.assertEqual(1, blk._idx)

    @patch.object(RESTPolling, "_retry")
    @patch.object(RESTPolling, "_authenticate")
    @patch("requests.get")
    def test_retry(self, mock_get, mock_auth, mock_retry):
        """ username queries get a 404 from Facebook """
        blk = FacebookFeed()
        self.configure_block(blk, {
            "queries": [
                "username1",
                "username2"
            ]
        })
        mock_get.return_value = MagicMock()
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = \
            {'error':
             {'message': 'This is baaaaad',
              'code': 666,
              'type': 'OAuthException'
              }
             }
        self.assertEqual(0, blk._idx)
        blk.poll()
        # don't skip to next idx because we are retrying.
        self.assertEqual(0, blk._idx)
