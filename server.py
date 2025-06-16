import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from hubspot import HubSpot
from hubspot.oauth import ApiException
from mcp.server.fastmcp import FastMCP
from hubspot.crm.contacts import SimplePublicObjectInputForCreate

# ====== Credentials ======
CLIENT_ID = "930200dd-a49b-4e00-b6db-194c506de7df"
CLIENT_SECRET = "f3463abf-8286-4ed7-96d5-437620aa399c"
REDIRECT_URI = "http://localhost:9999/callback"
SCOPES = "crm.objects.contacts.read crm.objects.contacts.write crm.schemas.contacts.read crm.schemas.contacts.write oauth"

# MCP server
mcp = FastMCP("HubSpot")

# ====== Auto-capture code ======
def get_auth_code():
    auth_code_holder = {}

    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_url = urlparse(self.path)
            query = parse_qs(parsed_url.query)
            if "code" in query:
                auth_code_holder['code'] = query["code"][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Authorization successful! You can close this window.")
            else:
                self.send_error(400, "Missing code")

    def run_server():
        httpd = HTTPServer(('localhost', 9999), OAuthHandler)
        httpd.handle_request()

    threading.Thread(target=run_server, daemon=True).start()

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code"
    }
    auth_url = f"https://app.hubspot.com/oauth/authorize?{urlencode(params)}"
    print("👉 Opening browser to authorize...")
    webbrowser.open(auth_url)

    while 'code' not in auth_code_holder:
        pass

    return auth_code_holder['code']


# ====== Main Auth Flow ======
auth_code = get_auth_code()
print("✅ Got auth code:", auth_code)

try:
    temp_client = HubSpot()
    tokens = temp_client.oauth.tokens_api.create(
        grant_type="authorization_code",
        redirect_uri=REDIRECT_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        code=auth_code
    )
    access_token = tokens.access_token
    client = HubSpot(access_token=access_token)
    print("✅ Got access token")
except ApiException as e:
    print("❌ Failed to get tokens:", e)
    exit()


def create_contact(client, firstname, lastname, email, phone=None):
    properties = {
        "firstname": firstname,
        "lastname": lastname,
        "email": email
    }
    if phone:
        properties["phone"] = phone

    data = SimplePublicObjectInputForCreate(properties=properties)

    try:
        contact = client.crm.contacts.basic_api.create(data)
        print(f"✅ Created contact: {firstname} {lastname}, ID: {contact.id}")
    except Exception as e:
        print("❌ Error creating contact:", e)


if __name__ == "__main__":
    create_contact(client, "Tony", "Stark", "ironman@starkindustries.com", "+91-9876543210")



