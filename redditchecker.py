import asyncio
import configparser
import discord
import logging
import requests
from os.path import dirname, realpath


class DiscordClient(discord.Client):
    async def set_channel(self, channel):
        await self.wait_until_ready()
        self.channel = await self.fetch_channel(channel)
        
    async def on_ready(self):
        print(f"\nLogged in as:"
              f"\n{self.user.name}"
              f"\n{self.user.id}\n")

    async def send_notification(self, subreddit, title, url):
        url = "https://reddit.com" + url
        thumbnail_url = "https://external-preview.redd.it/iDdntscPf-nfWKqzHRGFmhVxZm4hZgaKe5oyFws-yzA.png"
        thumbnail_url2 = "https://assets.stickpng.com/images/580b57fcd9996e24bc43c531.png"
        msg = discord.Embed(title=title, url=url, color=0x8a28ad)
        msg.set_thumbnail(url=thumbnail_url2)
        await self.channel.send(embed=msg)

        
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
    token = d["access_token"]
    print(f"\nAuthenticated with token: {token}\n")
    return token

async def check_reddit(access_token, agent, subreddit):
    """Checks the defined subreddit for the most recent post and returns a
    tuple containing the post title and permalink."""

    token = "bearer " + access_token
    url = "https://oauth.reddit.com/r/" + subreddit + "/new"
    headers = {"Authorization": token, "User-Agent": agent}
    payload = {"limit": "10", "sort": "new"} # only get the most recent post

    response = requests.get(url, params=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        post = data["data"]["children"][0]["data"]
        title = post["title"]
        permalink = post["permalink"]
        print(title, permalink)
        return (title, permalink)
    else:
        return None
            
async def main():
    logging.basicConfig(level=logging.DEBUG)
    config = configparser.ConfigParser()
    config.read(dirname(realpath(__file__)) + "/config.ini")
    useragent = config["reddit"]["user_agent"]
    subreddit = config["reddit"]["subreddit"]
    channel = config["discord"]["channel_id"]
    delay = config["defaults"]["update_interval"]

    reddit_token = await auth_reddit(config, useragent)
    discord_token = config["discord"]["token"]

    client = DiscordClient()
    start_discord = asyncio.ensure_future(client.start(discord_token))
    await client.set_channel(channel)

    last_post = ("", "")
    recent_post = ("", "")
    while recent_post != None:
        recent_post = await check_reddit(reddit_token, useragent, subreddit)
        if last_post == recent_post:
            pass
        elif last_post != recent_post:
            await client.send_notification(subreddit, *recent_post)
            last_post = recent_post
        else:
            break
        await asyncio.sleep(int(delay))
    await client.close()
    
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
