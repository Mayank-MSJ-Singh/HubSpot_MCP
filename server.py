import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from hubspot import HubSpot
from hubspot.oauth import ApiException
from mcp.server.fastmcp import FastMCP

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

client = HubSpot()
try:
    tokens = client.oauth.tokens_api.create(
        grant_type="authorization_code",
        redirect_uri=REDIRECT_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        code=auth_code
    )
except ApiException as e:
    print("❌ Failed to get tokens:", e)
    exit()

access_token = tokens.access_token
print("✅ Got access token")

# ====== Fetch and Send Contacts ======
client = HubSpot(access_token=access_token)
response = client.crm.contacts.basic_api.get_page(limit=5)
context_chunks = []

for contact in response.results:
    props = contact.properties
    name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
    email = props.get("email", "")
    context_chunks.append(f"Contact: {name}, Email: {email}")

payload = {
    "session_id": "hubspot-session",
    "role": "user",
    "messages": [{"type": "text", "content": chunk} for chunk in context_chunks]
}

print(payload)
