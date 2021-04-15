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

def get_client_auth(client_id, client_secret):
    """Common authentication to code grant and refresh grant flows
    using HTTPBasicAuth."""
    return requests.auth.HTTPBasicAuth(client_id, client_secret)

def code_grant(client_auth, code, user_agent, redirect_uri):
    """Uses code flow grant to retrieve access and refresh tokens."""
    url = "https://www.reddit.com/api/v1/access_token"
    payload = {"grant_type" : "authorization_code",
               "code" : code,
               "redirect_uri" : redirect_uri}
    response = requests.post(url, data=payload, auth=client_auth,
                             headers={"user-agent" : user_agent})
    check_response(response)
    data = response.json()

    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    return access_token, refresh_token

def refresh_grant(client_auth, user_agent, refresh_token):
    """Uses the refresh token to obtain a new access token."""
    url = "https://www.reddit.com/api/v1/access_token"
    payload = {"grant_type" : "refresh_token",
               "refresh_token" : refresh_token}
    response = requests.post(url, data=payload,
                                auth=client_auth,
                                headers={"user-agent" : user_agent})
    check_response(response)
    data = response.json()

    access_token = data["access_token"]
    return access_token

def init_auth(client_auth, user_agent, client_id, redirect_uri):
    """Points the user to a web browser to authenticate and receive
    a refresh token. This is run if there is no existing refresh token
    in the config. Returns refresh token and a bearer access token."""
    state = random_string()
    auth_url = "https://www.reddit.com/api/v1/authorize"
    url = (f"{auth_url}?client_id={client_id}"
           f"&response_type=code"
           f"&state={state}"
           f"&redirect_uri={redirect_uri}"
           f"&duration=permanent"
           f"&scope=read")
    webbrowser.open(url) # user authorizes from browser

    auth_data = handle_reddit_response(state)
    code = auth_data["code"]
    return code_grant(client_auth, code, user_agent,
                      redirect_uri)

def revoke_token(client_auth, user_agent, token, token_type):
    """Tells reddit to revoke the token. Note that revoking a refresh
    token will revoke its related access tokens as well."""
    url = "https://www.reddit.com/api/v1/revoke_token"
    payload = {"token" : token,
               "token_type_hint" : token_type}
    response = requests.post(url, data=payload, auth=client_auth,
                             headers={"user-agent" : user_agent})
    check_response(response)
