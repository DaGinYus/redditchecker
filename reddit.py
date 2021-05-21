import logging
import random
import string
import aiohttp

def check_response(response):
    """Checks if a response returned any error codes and raises an error if
    it's a bad response."""
    if response.ok:
        return
    response.raise_for_status()

def random_string(length=20):
    """Generates a pseudo-random string."""
    charset = string.ascii_letters + string.digits
    return "".join(random.choice(charset) for _ in range(length))

def sub_parse_to_list(data):
    """Parses relevant JSON data and returns a dictionary 
    with post id as the keys and post information as the values:
      
      { post_id : {
            "title" : title,
            "author" : author,
            "flair" : flair_text,
            "author_flair" : author_flair_text,
        },
        post_id_2 ...,
        post_id_3 ...,
      }
        
    """
    # follows the JSON format returned by reddit
    # list of posts containing info
    posts = data["data"]["children"]
    posts_dict = {}
    # the locations of post data values within the JSON
    post_template = {"post_id" : "id",
                     "title" : "title",
                     "author" : "author",
                     "flair" : "link_flair_text",
                     "author_flair" : "author_flair_text"}
    
    # parse the posts and put in dictionary
    for post in posts:
        temp_dict = {}
        for var_name, json_loc in post_template.items():
            temp_dict[var_name] = post["data"][json_loc]
        posts_dict.update({post["data"]["id"] : temp_dict})
    return posts_dict

class RedditSession:
    """A class to keep track of shared instance variables required for
    Reddit authentication."""
    def __init__(self, client_id, client_secret, user_agent):
        """Initialized with client details and user agent."""
        
        self.user_agent = user_agent
        self.base_url = "https://www.reddit.com/api/v1/"
        
        # generate HTTPBasicAuth
        self.client_auth = aiohttp.BasicAuth(client_id, client_secret)

        # start aiohttp session
        headers = {"user-agent" : user_agent}
        self.client_session = aiohttp.ClientSession(headers=headers)
        
        self.access_token = ""

    async def client_cred_grant(self):
        """Authenticates with Reddit using client credentials. See 
        'Application Only OAuth' under 
        https://github.com/reddit-archive/reddit/wiki/oauth2.
        This function sets the access token and returns True on success"""
        
        url = self.base_url + "access_token"
        device_id = random_string()
        payload = {"grant_type" : "client_credentials",
                   "device_id" : device_id}
        try:
            async with self.client_session.post(url, data=payload,
                    auth=self.client_auth) as response:
                check_response(response)
                response_data = await response.json()
                self.access_token = response_data["access_token"]
                self.expires_in = int(response_data["expires_in"])
                
                logging.info(f"Authenticated to Reddit "
                             f"(token: {self.access_token})")
                return True
        except aiohttp.ClientResponseError as err:
            logging.error(f"Request failed with error code {err.status}")
            return False

    async def revoke_token(self, token="", token_type="access_token"):
        """Tells reddit to revoke the token."""
        # default is to revoke the instance token
        if token == "":
            token = self.access_token
        
        url = self.base_url + "revoke_token"
        payload = {"token" : token,
                   "token_type_hint" : token_type}
        try:
            async with self.client_session.post(url, data=payload,
                    auth=self.client_auth) as response:
                check_response(response)
                logging.info(f"Reddit access token revoked (token: {self.access_token})")
        except aiohttp.ClientResponseError as err:
            logging.error(f"Request failed with error code {err.status}")

    async def sub_get_new(self, subreddit, num_posts=10):
        """Retrieves the most recent posts from a subreddit and returns the data
        in dictionary format"""
        
        num_posts = str(num_posts)
        token = "bearer " + self.access_token
        url = "https://oauth.reddit.com/r/" + subreddit + "/new"
        payload = {"limit" : num_posts, "sort" : "new"}
        headers = {"Authorization" : token, "User-Agent" : self.user_agent}
        try:
            async with self.client_session.get(url, params=payload,
                    headers=headers) as response:
                check_response(response)
                sub_data = await response.json()

                return sub_parse_to_list(sub_data)
        except aiohttp.ClientResponseError as err:
            logging.error(f"Request failed with error code {err.status}")
        return
