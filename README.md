# redditchecker
A bot to check reddit for posts and notify the user via discord message. It simply queries the reddit API at set intervals and sends a message if there is a new post. Modules will make it expandable in the future. 

## Why not just use PRAW?
I wanted to learn how to do web requests and asynchronous I/O on my own, so I decided to try implementing my own solution. Also, I am only scraping for one specific thing so the implementation is a lot simpler

## Usage
Create developer accounts in Discord and Reddit, and fill in the corresponding token and client id fields. Authenticate to reddit using username and password for the developer account.
