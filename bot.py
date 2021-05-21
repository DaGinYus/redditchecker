"""the main bot."""
import asyncio
import configparser
import logging
import shutil
import sys
import time
from os.path import dirname, realpath

import discord
import reddit

def read_from_config(filename="config.ini"):
    """Reads configuration file and returns ConfigParser object which contains
    the settings."""
    config = configparser.ConfigParser()
    currentdir = dirname(realpath(__file__)) + '/'
    filepath = currentdir + filename
    try:
        with open(filepath) as config_file:
            config.read_file(config_file)
    except FileNotFoundError:
        # if config doesn't exist, ask to copy SAMPLE_CONFIG.ini
        usrinput = input(f"{filepath} does not exist. "
                         f"Copy config from SAMPLE_CONFIG? (y/n): ")
        if usrinput.lower() == 'y':
            dest_file = currentdir + "config.ini"
            shutil.copy(currentdir + "SAMPLE_CONFIG.ini", dest_file)
            with open(dest_file) as config_file:
                config.read_file(config_file)
                return config

        logging.error("Config file not found. EXITING")
        return None

    return config

def check_config(config, filename="config.ini"):
    """Parses through the config file for any NULL values and asks for user
    input to set the value."""
    filepath = dirname(realpath(__file__)) + '/' + filename
    edited = False
    for section in config.sections():
        for key in config[section]:
            if config[section][key] == "NULL":
                config[section][key] = set_config(section, key)
                with open(filepath, 'w') as configfile:
                    config.write(configfile)
                    edited = True
    if edited:
        logging.info(f"Wrote {filepath}")

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

def format_post(post):
    """Formats the Reddit post data into strings."""
    title = post["title"]
    author = post["author"]
    url = f"https://redd.it/{post['post_id']}"

    # prepend the post flair if it exists
    if post["flair"]:
        title = f"({post['flair']}){title}"
    # append author flair if it exists
    if post["author_flair"]:
        author = f"{author}({post['author_flair']})"

    return title, url, author

def compare(temp_dict, new_dict):
    """Checks for keys in new_dict that are not in temp_dict
    and returns the values associated with those keys."""
    output_list = []
    if new_dict and temp_dict:
        for key in new_dict:
            if key not in temp_dict:
                output_list.append(new_dict[key])
    return output_list


class DiscordClient(discord.Client):
    """A class to modify discord.Client behavior."""
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

    async def close(self, *args, **kwargs):
        """Extend client.close() to perform additional cleanup duties."""
        await self.reddit_session.revoke_token()
        await self.reddit_session.client_session.close()
        await super().close(*args, **kwargs)

    async def on_ready(self):
        """Status message when bot is ready."""
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")

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
        """Check for posts every 5 seconds and sends a message if a post from
        r/subreddit/new has been posted within the last check interval."""

        check_interval = 5 # seconds
        
        # populate a cache that is checked against new posts
        await self.reddit_authenticated.wait()
        temp_posts = await self.reddit_session.sub_get_new(self.subreddit)
        
        while not self.is_closed():
            await self.reddit_authenticated.wait()
            logging.debug(f"Checking for new posts in r/{self.subreddit}")
            updated_posts = await self.reddit_session.sub_get_new(self.subreddit)
            new_posts = compare(temp_posts, updated_posts)
            if new_posts:
                temp_posts = updated_posts
                for post in new_posts:
                    logging.info(f"New post found: {post['title']}")
                    await self.discord_notify(post)
            await asyncio.sleep(check_interval)

    async def discord_notify(self, post):
        """Takes a post containing data in dictionary form, formats it, and
        sends notifications in Discord."""
        title, url, author = format_post(post)

        channel = self.get_channel(self.channel_id)
        await channel.send(f"{title}\n{url} by {author}")
        logging.debug(f"Notification for '{title}' sent")
        await asyncio.sleep(0.5) # ensure the bot does not spam


def main():
    """Reads config and starts the bot."""
    debug_level = logging.INFO
    # command line argument to set verbosity
    if len(sys.argv) == 2:
        if sys.argv[1] == "-v":
            debug_level = logging.DEBUG
    
    logging.basicConfig(
        level=debug_level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler("debug.log", 'w'),
                  logging.StreamHandler()]
    )

    config = read_from_config()
    if not config:
        return
    check_config(config)

    reddit_session = start_reddit_session_from_config(config)
    subreddit = config["reddit"]["subreddit"]

    discord_token = config["discord"]["token"]
    discord_channel = config["discord"]["channel_id"]

    client = DiscordClient(reddit_session, subreddit, discord_channel)
    client.run(discord_token)

if __name__ == "__main__":
    main()
