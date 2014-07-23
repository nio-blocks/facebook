from unittest.mock import patch, MagicMock
from requests import Response
from datetime import datetime, timedelta
from facebook.facebook_block import FacebookBlock
from nio.util.support.block_test_case import NIOBlockTestCase
from nio.modules.threading import Event



class FBTestBlk(FacebookBlock):
    def __init__(self, event):
        super().__init__()
        self._event = event

    def poll(self, paging=False):
        super().poll(paging)
        self._event.set()

class TestFacebook(NIOBlockTestCase):
    
    @patch("requests.get")
    @patch("requests.Response.json")
    @patch("facebook.facebook_block.FacebookBlock.created_epoch")
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
        

    
