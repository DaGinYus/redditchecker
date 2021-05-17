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

def sub_parse_to_dict(data):
    """Parses JSON data into a dictionary {title : permalink}."""
    # follows the JSON format returned by reddit
    # list of posts containing info
    posts = data["data"]["children"]
    posts_dict = {}
    # parse the posts and put in dictionary
    for post in posts:
        post_data = post["data"]
        posts_dict[post_data["title"]] = post_data["permalink"]
    return posts_dict

class RedditSession:
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
        
        async with self.client_session.post(url, data=payload,
                                            auth=self.client_auth) as response:
            check_response(response)
            response_data = await response.json()
            self.access_token = response_data["access_token"]
            self.expires_in = int(response_data["expires_in"])
            
        print(f"Authenticated to Reddit with token "
              f"{self.access_token}")
        return True

    async def revoke_token(self, token, token_type="access_token"):
        """Tells reddit to revoke the token."""
        
        url = self.base_url + "revoke_token"
        payload = {"token" : token,
                   "token_type_hint" : token_type}

        async with self.client_session.post(url, data=payload,
                                            auth=self.client_auth) as response:
            check_response(response)

    async def sub_get_new(self, subreddit, num_posts=10):
        """Retrieves the most recent posts from a subreddit and returns the data
        in dictionary format"""
        num_posts = str(num_posts)
        token = "bearer " + self.access_token
        url = "https://oauth.reddit.com/r/" + subreddit + "/new"
        payload = {"limit" : num_posts, "sort" : "new"}
        headers = {"Authorization" : token, "User-Agent" : self.user_agent}

        async with self.client_session.get(url, data=payload,
                                           headers=headers) as response:
            check_response(response)
            sub_data = await response.json()

        return sub_parse_to_dict(sub_data)
