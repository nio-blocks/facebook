FacebookBlock
=============

Polls Facebook for public posts via Graph API v1.0.

Properties
--------------

-   **polling_interval**: How often Facebook is polled. When using more than one query. Each query will be polled at a period equal to the *polling\_interval* times the number of queries.
-   **retry_interval**: When a url request fails, how long to wait before attempting to try again.
-   **limit**: Number of posts to come back on each url request to Facebook.
-   **queries**: List of queries to public posts for. Note that multi-word queries will search for posts that have all of the words but not as a single string.
-   **lookback**: On block start, look back this amount of time to grab old posts.
-   **creds**: Facebook API credentials.

Commands
----------------
None

Input
-------
None

Output
---------
Creates a new signal for each Facebook Post. Every field on the Post will become a signal attribute. Details about the Facebook Posts can be found 
[here](https://developers.facebook.com/docs/graph-api/reference/v1.0/post). The following is a list of commonly include attributes, but note that not all will be included on every signal:

-   type
-   id
-   message
-   description
-   link
-   from['name']
-   created_time
