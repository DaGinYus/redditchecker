"""Handles authentication with reddit API."""
import asyncio
import random
import string
import socket
import webbrowser
import requests

def check_response(response):
    """Checks if a response returned any error codes."""
    if response.ok:
        return
    # raise error if bad response
    response.raise_for_status()

def random_string(length=32):
    """Generates a pseudo-random string."""
    charset = string.ascii_letters + string.digits
    return "".join(random.choice(charset) for _ in range(length))

def receive_connection():
    """Waits for a single client on port 8080 and returns a socket
    object which is the connection."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("localhost", 8080))
        server.listen(1) # stop listening after 1 connection
        conn = server.accept()[0]
        return conn

def return_message(client, msg):
    """Returns a message to the connected client."""
    html_headers = "HTTP/1.0 200 OK\nContent-Type: text/html\n\n"
    html_content = (f"<html>"
                    f"<body>{msg}</body>"
                    f"</html>")
    # send HTTP headers
    client.send(html_headers.encode("utf-8"))
    client.send(html_content.encode("utf-8"))

def handle_reddit_response(state):
    """Create a server at "http://localhost:8080" to handle the
    redirect_uri response from reddit, then close the connection."""
    client = receive_connection()
    data = client.recv(1024).decode("utf-8")
    # returns a list containing the request parameters
    # e.g ["state=RETURNED_STATE", "code=SOME_CODE"]
    param_tokens = data.split(" ")[1].split("?")[1].split("&")
    # unpack into a dictionary
    params = dict(token.split("=") for token in param_tokens)

    if state != params["state"]:
        return_message(client, "Error: Invalid state returned")
        client.close()
        raise Exception("Invalid state returned")

    return_message(client, "Success. (you may now close this page)")
    client.close()
    return params


class RedditAuthenticator:
    def __init__(client_id, client_secret, user_agent, redirect_uri):
        """Initialize with predetermined client details, user agent,
        and redirect URI. Generate a refresh token and bearer access
        token."""
        self.user_agent = user_agent
        self.redirect_uri = redirect_uri
        self.base_url = "https://www.reddit.com/api/v1/"
        # generate HTTPBasicAuth
        self.client_auth = requests.auth.HTTPBasicAuth(client_id,
                                                       client_secret)

        # open web browser for user consent
        state = random_string()
        url = (f"{auth_url + 'authorize'}"
               f"?client_id={client_id}"
               f"&response_type=code"
               f"&state={state}"
               f"&redirect_uri={self.redirect_uri}"
               #f"&duration=permanent"
               f"scope=read")
        webbrowser.open(url)

        auth_data = handle_reddit_response(state)
        code = auth_data["code"]
        self.code_grant(code)
        
    def code_grant(code):
        """Uses code flow grant to retrieve access and refresh tokens."""
        url = self.base_url + "access_token"
        payload = {"grant_type" : "authorization_code",
                   "code" : code,
                   "redirect_uri" : self.redirect_uri}
        response = requests.post(url, data=payload,
                                 auth=self.client_auth,
                                 headers={"user-agent" : self.user_agent})
        check_response(response)
        data = response.json()
        
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]

    def refresh_grant(refresh_token):
        """Uses the refresh token to obtain a new access token."""
        url = self.base_url + "access_token"
        payload = {"grant_type" : "refresh_token",
                   "refresh_token" : refresh_token}
        response = requests.post(url, data=payload,
                                 auth=self.client_auth,
                                 headers={"user-agent" : self.user_agent})
        check_response(response)
        data = response.json()
        
        self.access_token = data["access_token"]

    def revoke_token(token, token_type):
        """Tells reddit to revoke the token. Note that revoking a refresh
        token will revoke its related access tokens as well."""
        url = self.base_url +  "revoke_token"
        payload = {"token" : token,
                   "token_type_hint" : token_type}
        response = requests.post(url, data=payload,
                                 auth=self.client_auth,
                                 headers={"user-agent" : self.user_agent})
        check_response(response)
