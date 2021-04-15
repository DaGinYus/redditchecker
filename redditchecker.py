import asyncio
import configparser
import logging
from os.path import dirname, realpath

import discord
import requests



class DiscordClient(discord.Client):
    async def set_channel(self, channel):
        # get the channel to send messages in at the start
        # THIS IS HARDCODED RIGHT NOW, MIGHT CHANGE TO BE DYNAMIC
        await self.wait_until_ready()
        self.channel = await self.fetch_channel(channel)

    async def on_ready(self):
        # send a ready message
        print(f"\nLogged in as:"
              f"\n{self.user.name}"
              f"\n{self.user.id}\n")

    async def send_notification(self, subreddit, title, url):
        # truncate to length limit on embed title
        if len(title) > 256:
            title = title[0:253] + "..."
        url = "https://reddit.com" + url
        thumbnail_url = ("https://external-preview.redd.it/"
                         "iDdntscPf-nfWKqzHRGFmhVxZm4hZgaKe5oyFws-yzA.png")
        thumbnail_url2 = ("https://assets.stickpng.com/"
                          "images/580b57fcd9996e24bc43c531.png")
        msg = discord.Embed(title=title, url=url, color=0x8a28ad)
        msg.set_thumbnail(url=thumbnail_url2)
        await self.channel.send(embed=msg)

        
async def auth_reddit(config, agent):
    """Authenticates to reddit via OAuth2 and returns a token"""

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

async def check_reddit(access_token, config, agent, subreddit):
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
    elif response.status_code == 401:
        # most likely the token expired, try to reauthenticate
        try:
            refresh_token = await asyncio.wait_for(auth_reddit(config, agent), 5)
        except asyncio.TimeoutError: # try again
            asyncio.sleep(5)
            refresh_token = await asyncio.wait_for(auth_reddit(config, agent), 5)
        await check_reddit(refresh_token, config, agent, subreddit)
    else:
        # something bad happened
        raise Exception("invalid response")
            
async def main():
    # setting config variables
    logging.basicConfig(level=logging.DEBUG)
    config = configparser.ConfigParser()
    config.read(dirname(realpath(__file__)) + "/config.ini")
    useragent = config["reddit"]["user_agent"]
    subreddit = config["reddit"]["subreddit"]
    channel = config["discord"]["channel_id"]
    delay = config["defaults"]["update_interval"]

    # get tokens for authentication
    reddit_token = await auth_reddit(config, useragent)
    discord_token = config["discord"]["token"]

    # start the discord bot and wait for it to prepare
    client = DiscordClient()
    start_discord = asyncio.ensure_future(client.start(discord_token))
    await client.set_channel(channel)

    # check for new posts every 'delay' seconds
    # and send a discord message if there is a new post
    recent_posts = []
    new_post = ("", "")
    while True:
        try:
            new_post = await check_reddit(reddit_token,
                                             config, useragent, subreddit)
            if new_post in recent_posts:
                pass
            elif (new_post not in recent_posts):
                # store the last 10 posts to guarantee no duplicates
                if len(recent_posts) < 10:
                    recent_posts.append(new_post)
                elif len(recent_posts) == 10:
                    recent_posts.pop(0)
                    recent_posts.append(new_post)
                elif new_post is None:
                    print("RETURNED NONE")
                    print(new_post)
                    break
                    
                await client.send_notification(subreddit, *recent_posts[-1])
        except Exception as err:
            print(err)
            break # exit loop and close the bot
        await asyncio.sleep(int(delay))
    
    await client.close()
    
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
