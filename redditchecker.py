import asyncio
import configparser
import discord
import requests
from os.path import dirname, realpath


class RedditClient(discord.Client):
    async def on_ready(self):
        print(f"Logged in as:"
              f"\n{self.user.name}"
              f"\n{self.user.id}"
              f"\n------")
        channel = self.get_channel(467375306576101399)
        await channel.send("Bot ready")

    async def send_message(self, subreddit, title, url):
        channel = self.get_channel(467375306576101399)
        await channel.send(f"New Post in r/{subreddit}:\n"
                           f"{title}"
                           f"{url}")

async def auth_reddit(config, agent):
    """Authenticates to reddit via OAuth2"""

    rc = config["reddit"]
    authurl = "https://www.reddit.com/api/v1/access_token"
    payload = {"grant_type": "password", "username": rc["username"],
               "password": rc["password"]}
    auth = requests.auth.HTTPBasicAuth(rc["client_id"], rc["client_secret"])
    r = requests.post(authurl, data=payload,
                      headers={"user-agent": agent},
                      auth=auth)
    d = r.json()
    return d["access_token"]

async def check_reddit(access_token, agent, subreddit, refresh, disc_client):
    """Checks the defined subreddit for the most recent post and sends a
    discord message if it is new."""

    token = "bearer " + access_token
    url = "https://oauth.reddit.com/r/" + subreddit + "/new"
    headers = {"Authorization": token, "User-Agent": agent}
    payload = {"limit": "1", "sort": "new"} # only get the most recent post

    recent_post = ""
    while True:
        response = requests.get(url, params=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            post = data["data"]["children"][0]["data"]
            title = post["title"]
            url = post["permalink"]
            print(title, permalink)
            if recent_post is not title:
                await client.send_message(subreddit, title, url)
                recent_post = title
            await asyncio.sleep(5)
        else:
            break
            
    
async def main():
    config = configparser.ConfigParser()
    config.read(dirname(realpath(__file__)) + "/config.ini")
    useragent = config["reddit"]["user_agent"]
    subreddit = config["reddit"]["subreddit"]
    delay = config["defaults"]["update_interval"]

    reddit_token = await auth_reddit(config, useragent)
    discord_token = config["defaults"]["token"]
    client = RedditClient()
    client.run(discord_token)
    loop = asyncio.get_event_loop()
    task = loop.create_task(check_reddit(reddit_token, useragent, subreddit, delay, client))
    await loop.run_until_complete(main())
    
    
if __name__ == "__main__":
    asyncio.run(main())
