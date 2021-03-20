"""Reddit class for API interaction. Basically bootleg PRAW."""
import requests


def handle_response(response):
    """Handles a web response and returns the data if response
       is good. Input is requests.Response object.
    """
    if response.ok:
        # good response
        return response.json()
    # raise an error if response is not ok
    response.raise_for_status()
    # something bad happened
    return None

class Reddit:
    """A class to represent a Reddit session.
    Responsible for handling web requests to Reddit API and
    authenticating. Works asynchronously so it is compatibile with
    discord.py

    Initialization:
        myreddit = reddit.Reddit((client_id, client_secret),
                                 (username, password),
                                  user_agent)

    """

    def __init__(self, client_details, auth_details, user_agent):
        """Initialize Reddit session.

        client_details: a tuple of the form (client_id, client_secret)
        auth_details: a tuple of the form (username, password)
        user_agent: a string containing the user agent
        """
        # unpack arguments with tuple comprehension
        self._client_id, self._client_secret = client_details
        self._username, self._password = auth_details
        self._user_agent = user_agent

        self._url = "https://www.reddit.com/"
        self._oauthurl = "https://oauth.reddit.com/"

        self.token = None
        self.headers = None
        self.subreddit = None

    def sub_search(self, name, limit, timeframe):
        """Looks for subreddit matching name and creates Subreddit
        class with corresponding details.
        """
        self.set_headers()
        search_url = self._oauthurl + "search"
        payload = {"q" : name,
                   "t" : timeframe,
                   "limit" : limit,
                   "type" : "sr"}
        result = requests.get(search_url, params=payload,
                              headers=self.headers)
        data = handle_response(result)
        print(data)

    def auth(self):
        """Authenticate with reddit API. Sets a variable that
        contains the token.
        """
        authurl = self._url + "api/v1/access_token"
        payload = {"grant_type": "password", "username": self._username,
                   "password": self._password}
        auth = requests.auth.HTTPBasicAuth(self._client_id, self._client_secret)
        response = requests.post(authurl, data=payload,
                                 headers={"user-agent": self._user_agent},
                                 auth=auth)
        data = handle_response(response)
        if data:
            self.token = data["access_token"]
        else:
            raise Exception("bad data")

    def set_headers(self):
        """Sets default headers for OAuth requests."""
        self.headers = {"Authorization" : "bearer " + self.token,
                        "User-Agent" : self._user_agent}

class Subreddit:
    """A class to represent a subreddit. It is a container for
    RedditPost objects.
    """

    def __init__(self, name, id_):
        """Initialize Subreddit object."""
        self.type_prefix = "t5_"
        self.id_ = id_
        # from the reddit API, fullnames are the combination of its
        # type and unique ID, e.g. t3_15bfi0
        self.fullname = self.type_prefix + self.id_
