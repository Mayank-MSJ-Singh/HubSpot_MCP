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
    print("👉 Opening browser for auth...")
    webbrowser.open(auth_url)

    while 'code' not in code_holder:
        pass

    return code_holder['code']


# ====== Ensure Tokens ======
async def ensure_creds():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            tokens = json.load(f)
        return HubSpot(access_token=tokens['access_token'])

    code = get_auth_code()
    print("✅ Got auth code")

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
        with open(TOKEN_FILE, "w") as f:
            json.dump({"access_token": access_token}, f)
        os.chmod(TOKEN_FILE, 0o600)
        print("✅ Access token saved")
        return HubSpot(access_token=access_token)
    except ApiException as e:
        print("❌ Failed to fetch tokens:", e)
        exit()

@mcp.tool()
async def create_contact(client, firstname, lastname, email, phone=None):

    await ensure_creds()
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


@mcp.tool()
async def search_contacts(client, **kwargs):

    await ensure_creds()
    filters = []
    for field, value in kwargs.items():
        if value:
            filters.append(Filter(property_name=field, operator="EQ", value=value))

    if filters:
        filter_group = FilterGroup(filters=filters)
        search_request = PublicObjectSearchRequest(filter_groups=[filter_group], properties=["firstname", "lastname", "email", "phone", "company", "contact_owner", "hs_lead_status"])
        results = client.crm.contacts.search_api.do_search(public_object_search_request=search_request)
    else:
        # If no filters, return all contacts (basic listing)
        results = client.crm.contacts.basic_api.get_page(limit=10)

    for contact in results.results:
        props = contact.properties
        print("🧾 Contact:")
        print(f"  ID: {contact.id}")
        print(f"  Name: {props.get('firstname')} {props.get('lastname')}")
        print(f"  Email: {props.get('email')}")
        print(f"  Phone: {props.get('phone')}")
        print(f"  Company: {props.get('company')}")
        print(f"  Contact Owner: {props.get('hubspot_owner_id')}")
        print(f"  Lead Status: {props.get('hs_lead_status')}")
        print("  -------------------")


@mcp.tool()
async def update_contact_by_id(client, contact_id, updates: dict):

    await ensure_creds()

    data = SimplePublicObjectInput(properties=updates)

    try:
        updated_contact = client.crm.contacts.basic_api.update(contact_id, data)
        print(f"✅ Updated contact ID: {contact_id}")
        for key, value in updates.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print("❌ Failed to update contact:", e)


@mcp.tool()
async def delete_contact_by_id(client, contact_id):

    await ensure_creds()
    try:
        client.crm.contacts.basic_api.archive(contact_id)
        print(f"✅ Deleted contact ID: {contact_id}")
    except Exception as e:
        print("❌ Failed to delete contact:", e)


if __name__ == "__main__":
        async def main():
            client = await ensure_creds()
            #await search_contacts(client, email="anironman@starkindustries.com")
            #await create_contact(client, "Antony", "Stark", "anironman@starkindustries.com", "+91-9876543210")
            # await delete_contact_by_id(client, '147129159386')
            '''
            contact_id = "146083150549"
            updates = {
                "firstname": "Bruce",
                "lastname": "Wayne",
                "email": "batman@wayneenterprises.com",
                "phone": "+91-1112223334"
            }
            await update_contact_by_id(client, contact_id, updates)
            '''


        asyncio.run(main())


