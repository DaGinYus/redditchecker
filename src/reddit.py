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

def auth(auth_url, client_details, login_details, user):
    """Maybe moving auth outside of the class."""


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
    def __init__(self, client_details, login_details, user_agent):
        """Initialize Reddit session.

        client_details: a tuple of the form (client_id, client_secret)
        auth_details: a tuple of the form (username, password)
        user_agent: a string containing the user agent
        """
        # unpack arguments with tuple comprehension
        # pylint: disable=too-many-instance-attributes
        self._client_id, self._client_secret = client_details
        self._username, self._password = login_details
        self._user_agent = user_agent

        self._url = "https://www.reddit.com/"
        self._oauthurl = "https://oauth.reddit.com/"
        self._token = None
        self._headers = None

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
            self._token = data["access_token"]
        else:
            raise Exception("bad data")

    def set_headers(self):
        """Sets default headers for OAuth requests."""
        self._headers = {"Authorization" : "bearer " + self._token,
                        "User-Agent" : self._user_agent}

    def get_subreddit(self, name):
        """Creates Subreddit class with name and url if it exists. If
        not, handle the 404 error.
        """
        self.set_headers()
        sub_url = self._oauthurl + "r/" + name
        try:
            requests.get(sub_url, headers=self._headers)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                print("subreddit not found")
        return Subreddit(name, sub_url)

    def get_subreddit_posts(self, subreddit, sort="new", limit="10",
                            timeframe="hour"):
        """Searches for and updates the posts in a Subreddit
        object. Specified options to edit search parameters.
        """


class Subreddit:
    """A class to represent a subreddit. It is a container for
    RedditPost objects.
    """
    def __init__(self, name, url):
        """Initialize Subreddit object."""
        self.name = name
        self.url = url
        self.posts = []


class RedditPost:
    """A class to represent a reddit post. It keeps track of title, id
    post content, and images.
    """
    def __init__(self, title, content, url):
        """Initialize using id."""
