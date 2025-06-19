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
    phone: str | None = None
) -> None:
    """
    Creates a new contact in HubSpot.

    Parameters:
    - firstname: Contact's first name
    - lastname: Contact's last name
    - email: Contact's email address
    - phone: (Optional) Contact's phone number

    This will create a contact with the given details and print the new contact's ID.
    """
    client = await ensure_creds()
    properties = {
        "firstname": firstname,
        "email": email
    }
    if phone:
        properties["phone"] = phone
    if lastname:
        properties["lastname"] = lastname

    data = SimplePublicObjectInputForCreate(properties=properties)

    try:
        contact = client.crm.contacts.basic_api.create(data)
        print(f"Created contact: {firstname} {lastname}, ID: {contact.id}")
    except Exception as e:
        print("Error creating contact:", e)


@mcp.tool()
async def search_contacts(
    firstname: str | None = None,
    lastname: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    limit: int | None = None
) -> None:
    """
    Searches for contacts in HubSpot CRM based on optional filters.

    Parameters:
    - firstname: (Optional) First name of the contact to search.
    - lastname: (Optional) Last name of the contact to search.
    - email: (Optional) Email of the contact to search.
    - phone: (Optional) Phone number of the contact to search.
    - limit: (Optional) Max number of contacts to return. If not provided, all matching contacts are returned.

    If one or more filters are provided, it returns matching contacts.
    If no filters are provided, it returns the first `limit` contacts (or all, if `limit` is None).

    For each contact, the function prints:
    - Contact ID
    - Name (first and last)
    - Email
    - Phone number
    - Associated company
    - Contact owner
    - Lead status
    """
    client = await ensure_creds()
    filters = []
    for field, value in {
        "firstname": firstname,
        "lastname": lastname,
        "email": email,
        "phone": phone
    }.items():
        if value:
            filters.append(Filter(property_name=field, operator="EQ", value=value))

    try:
        results = []
        if filters:
            filter_group = FilterGroup(filters=filters)
            search_request = PublicObjectSearchRequest(
                filter_groups=[filter_group],
                properties=[
                    "firstname", "lastname", "email", "phone",
                    "company", "contact_owner", "hs_lead_status"
                ],
                limit=limit or 100  # HubSpot max page size is 100
            )
            page = client.crm.contacts.search_api.do_search(public_object_search_request=search_request)
            results.extend(page.results)
        else:
            after = None
            fetched = 0
            while True:
                page = client.crm.contacts.basic_api.get_page(
                    limit=100,
                    after=after,
                    properties=[
                        "firstname", "lastname", "email", "phone",
                        "company", "contact_owner", "hs_lead_status"
                    ]
                )
                results.extend(page.results)
                fetched += len(page.results)
                after = page.paging.next.after if page.paging and page.paging.next else None
                if not after or (limit and fetched >= limit):
                    break

            if limit:
                results = results[:limit]

        if not results:
            print("No contacts found.")
            return

        for contact in results:
            props = contact.properties
            print("Contact:")
            print(f"  ID: {contact.id}")
            print(f"  Name: {props.get('firstname')} {props.get('lastname')}")
            print(f"  Email: {props.get('email')}")
            print(f"  Phone: {props.get('phone')}")
            print(f"  Company: {props.get('company')}")
            print(f"  Contact Owner: {props.get('hubspot_owner_id')}")
            print(f"  Lead Status: {props.get('hs_lead_status')}")
            print("  -------------------")

    except Exception as e:
        print("Error searching contacts:", e)



@mcp.tool()
async def update_contact_by_id(
    contact_id: str,
    updates: dict[str, str]
) -> None:
    """
    Updates a HubSpot contact by ID.

    Parameters:
    - contact_id: ID of the contact to update
    - updates: Dictionary of fields to update (e.g., {"email": "new@email.com"})

    Applies the updates and prints the modified fields.
    """
    client = await ensure_creds()
    data = SimplePublicObjectInput(properties=updates)

    try:
        updated_contact = client.crm.contacts.basic_api.update(contact_id, data)
        print(f"Updated contact ID: {contact_id}")
        for key, value in updates.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print("Failed to update contact:", e)


@mcp.tool()
async def delete_contact_by_id(contact_id: str) -> None:
    """
    Deletes (archives) a contact in HubSpot.

    Parameters:
    - contact_id: ID of the contact to delete

    Archives the contact and confirms the deletion.
    """
    client = await ensure_creds()
    try:
        client.crm.contacts.basic_api.archive(contact_id)
        print(f"Deleted contact ID: {contact_id}")
    except Exception as e:
        print("Failed to delete contact:", e)

if __name__ == "__main__":
    async def main() -> None:
        await ensure_creds()
        await search_contacts()


    asyncio.run(main())
