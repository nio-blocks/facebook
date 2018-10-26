FacebookFeed
============
DEPRECATED - This version of the Facebook API no longer exists - Polls the Facebook graph api ['feed' endpoint](https://developers.facebook.com/docs/graph-api/reference/v2.2/page/feed). To test your *queries* for validity, enter them into the url: `https://www.facebook.com/query/feed`

Properties
----------
- **creds**: Facebook API credentials.
- **feed_type**: Select which enpoint you want. Defaults to the whole 'feed', but can be limited to just 'posts', 'tagged' or 'promotable_posts'.
- **include_query**: Whether to include queries in request to facebook.
- **limit**: Number of posts to come back on each url request to Facebook.
- **lookback**: On block start, look back this amount of time to grab old posts.
- **polling_interval**: How often Facebook is polled. When using more than one query. Each query will be polled at a period equal to the *polling interval* times the number of queries.
- **queries**: Queries to include on request to facebook
- **retry_interval**: When a url request fails, how long to wait before attempting to try again.
- **retry_limit**: Number of times to retry on a poll.

Inputs
------
- **default**: Any list of signals

Outputs
-------
- **default**: Creates a new signal for each Facebook Post. Every field on the Post will become a signal attribute. Details about the Facebook Posts can be found [here](https://developers.facebook.com/docs/graph-api/reference/v2.2/post). The following is a list of commonly include attributes, but note that not all will be included on every signal: type, id, message, description, link, from['name'], created_time

Commands
--------
None

Dependencies
------------
- requests

