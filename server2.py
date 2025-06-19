import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from hubspot import HubSpot
from hubspot.oauth import ApiException
from mcp.server.fastmcp import FastMCP
from hubspot.crm.contacts import SimplePublicObjectInputForCreate, Filter, FilterGroup, PublicObjectSearchRequest, SimplePublicObjectInput
import os
import json
import asyncio




# ====== MCP Setup ======
mcp = FastMCP("HubSpot")

# ====== Config ======
CLIENT_ID = "930200dd-a49b-4e00-b6db-194c506de7df"
CLIENT_SECRET = "f3463abf-8286-4ed7-96d5-437620aa399c"
REDIRECT_URI = "http://localhost:9999/callback"
TOKEN_FILE = "hubspot_token.json"
SCOPES = (
    "crm.objects.companies.read "
    "crm.objects.companies.write "
    "crm.objects.contacts.read "
    "crm.objects.contacts.write "
    "crm.schemas.companies.read "
    "crm.schemas.companies.write "
    "crm.schemas.contacts.read "
    "crm.schemas.contacts.write "
    "oauth"
)

# ====== Handle Redirect Auth ======
def get_auth_code():
    code_holder = {}

    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_url = urlparse(self.path)
            query = parse_qs(parsed_url.query)
            if "code" in query:
                code_holder['code'] = query["code"][0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Auth successful. You can close this tab.")
            else:
                self.send_error(400, "No code in redirect.")

    def run_server():
        server = HTTPServer(('localhost', 9999), OAuthHandler)
        server.handle_request()

    threading.Thread(target=run_server, daemon=True).start()

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code"
    }
    auth_url = f"https://app.hubspot.com/oauth/authorize?{urlencode(params)}"
    print("Opening browser for auth...")
    webbrowser.open(auth_url)

    while 'code' not in code_holder:
        pass

    return code_holder['code']

# ====== Ensure Tokens ======
async def ensure_creds():
    def save_token(access_token):
        with open(TOKEN_FILE, "w") as f:
            json.dump({"access_token": access_token}, f)
        os.chmod(TOKEN_FILE, 0o600)

    def load_token():
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                return json.load(f).get("access_token")
        return None

    def get_new_token():
        code = get_auth_code()
        print("Got auth code")

        try:
            temp_client = HubSpot()
            tokens = temp_client.oauth.tokens_api.create(
                grant_type="authorization_code",
                redirect_uri=REDIRECT_URI,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                code=code
            )
            access_token = tokens.access_token
            save_token(access_token)
            print("Access token saved")
            return access_token
        except ApiException as e:
            print("Failed to fetch tokens:", e)
            exit()

    access_token = load_token() or get_new_token()
    client = HubSpot(access_token=access_token)

    try:
        client.crm.contacts.basic_api.get_page(limit=1)
        return client
    except ApiException as e:
        if e.status == 401:
            print("Token expired or invalid. Getting new one...")
            access_token = get_new_token()
            return HubSpot(access_token=access_token)
        else:
            print("HubSpot API error:", e)
            exit()


@mcp.tool()
async def create_contact(
    firstname: str,
    email: str,
    lastname: str | None = None,
    phone: str | None = None,
    **kwargs
) -> None:
    """
    Creates a new contact in HubSpot.

    Parameters:
    - firstname: Contact's first name
    - email: Contact's email address
    - lastname: (Optional) Contact's last name
    - phone: (Optional) Contact's phone number
    - **kwargs: (Optional) Contact's keyword arguments

    This will create a contact with the given details and print the new contact's ID.
    """

    properties = {
        "firstname": firstname,
        "email": email
    }
    if phone:
        properties["phone"] = phone
    if lastname:
        properties["lastname"] = lastname


















#if __name__ == "__main__":
#    mcp.run(transport="stdio")
