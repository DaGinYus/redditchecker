"""the main bot."""
import asyncio
import configparser
import logging
from os.path import dirname, realpath

import discord
import reddit

def read_from_config(filename="config.ini"):
    """Reads configuration file and returns ConfigParser object which contains
    the settings."""
    config = configparser.ConfigParser()
    config.read(dirname(realpath(__file__)) + '/' + filename)
    return config

def check_config(config, filename="config.ini"):
    """Parses through the config file for any NULL values and asks for user
    input to set the value."""
    for section in config.sections():
        for key in config[section]:
            if config[section][key] == "NULL":
                config[section][key] = set_config(section, key)
                with open(dirname(realpath(__file__)) + '/' + filename, 'w') as configfile:
                    config.write(configfile)
                print(f"Wrote {dirname(realpath(__file__)) + '/' + filename} successfully")
                
def set_config(section, key):
    """Asks the user to input a value."""
    print(f"No value found for '{key}' in '{section}'. "
          f"Enter a new value here (this will be saved for future use):")
    return input()

def start_reddit_session_from_config(config):
    """Returns reddit.RedditSession object initialized from config file."""
    redditconf = config["reddit"]
    client_id = redditconf["client_id"]
    client_secret = redditconf["client_secret"]
    user_agent = redditconf["user_agent"]
    return reddit.RedditSession(client_id, client_secret, user_agent)

def compare_dictionaries(new_dict, old_dict):
    """Compares an updated dictionary with the old one to check for differences.
    Returns a dictionary containing values that are in the new dictionary
    but not the old one."""
    output_dict = {}
    for key, val in new_dict.items():
        if key not in old_dict:
            output_dict.update({key : val})
    return output_dict    


class DiscordClient(discord.Client):
    def __init__(self, reddit_session, subreddit, channel_id, *args, **kwargs):
        """The Discord client class inherits from discord.Client to 
        interact with the Discord API. It takes a RedditSession object
        and the name of the subreddit to check posts from, the channel ID
        in Discord to send messages to, as well as other arguments
        as required by discord.py"""
        
        super().__init__(*args, **kwargs)

        self.reddit_session = reddit_session
        self.subreddit = subreddit
        self.channel_id = int(channel_id)
        
        # flag for Reddit authentication
        self.reddit_authenticated = asyncio.Event()
        
        # create background tasks
        self.auth_loop = self.loop.create_task(self.reddit_auth_loop())
        self.check_loop = self.loop.create_task(self.reddit_check_loop())

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

    async def reddit_auth_loop(self):
        """Authenticate every hour."""
        await self.wait_until_ready()
        buffer_time = 100 # seconds
        
        while not self.is_closed():
            if await self.reddit_session.client_cred_grant():
                self.reddit_authenticated.set()
                await asyncio.sleep(self.reddit_session.expires_in - buffer_time)
                # unsets when time is up so it can re-authenticate
            self.reddit_authenticated.clear()
        
    async def reddit_check_loop(self):
        """Check for posts every 5 seconds and sends a message if there is a 
        new post."""
        while not self.is_closed():
            await self.reddit_authenticated.wait()
            print(f"Checking for new posts in r/{self.subreddit}")
            check_interval = 5 # seconds
            temp_posts = await self.reddit_session.sub_get_new(self.subreddit)
            await asyncio.sleep(check_interval)
            updated_posts = await self.reddit_session.sub_get_new(self.subreddit)
            new_posts = compare_dictionaries(updated_posts, temp_posts)
            if new_posts:
                await self.discord_notify(new_posts)

    async def discord_notify(self, new_posts):
        """Takes a dictionary of new posts, formats them and sends notifications
        in Discord."""
        for title, url in new_posts.items():
            # truncate to Discord's length limit for an embed title
            if len(title) > 256:
                title = title[:253] + "..."
            url = "https://reddit.com" + url
            print(f"New post found: {title} at {url}")
            
            # just some stuff to make it look fancy
            thumbnail_url = ("https://assets.stickpng.com/"
                             "images/580b57fcd9996e24bc43c531.png")
            color = 0x8a28ad
            
            msg = discord.Embed(title=title, url=url, color=color)
            msg.set_thumbnail(url=thumbnail_url)

            channel = self.get_channel(self.channel_id)
            await channel.send(embed=msg)
            await asyncio.sleep(1) # ensure the bot does not spam
                
def main():
    """Reads config and starts the bot."""
    logging.basicConfig(level=logging.DEBUG)
    
    config = read_from_config()
    check_config(config)

    reddit_session = start_reddit_session_from_config(config)
    subreddit = config["reddit"]["subreddit"]

    discord_token = config["discord"]["token"]
    discord_channel = config["discord"]["channel_id"]

    client = DiscordClient(reddit_session, subreddit, discord_channel)
    client.run(discord_token)

if __name__ == "__main__":
    main()
