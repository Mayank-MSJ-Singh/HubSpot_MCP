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
import json
from hubspot import HubSpot
import logging

from hubspot.crm.contacts import Filter, FilterGroup, PublicObjectSearchRequest
from hubspot.crm.properties import PropertyCreate
from hubspot.crm.contacts import SimplePublicObjectInputForCreate, SimplePublicObjectInput


from hubspot.crm.companies import SimplePublicObjectInputForCreate
from hubspot.crm.companies import SimplePublicObjectInput




# ====== MCP Setup ======
mcp = FastMCP("HubSpot")

@mcp.tool()
async def hubspot_list_properties(object_type: str) -> list[dict]:
    """
    List all properties for a given object type.

    Parameters:
    - object_type: One of "contacts", "companies", "deals", or "tickets"

    Returns:
    - List of property metadata
    """
    client = HubSpot(
        access_token="COiA95T5MhIbQlNQMl8kQEwrAg4ACAkIDhIJBB4BAQEBAQEBGO-Q83Mg58rJJijD9O0GMhRNzR7nfwFdxlF8fk3tzWXFgP5i2To6QlNQMl8kQEwrAi0ACBkGKAEBAQFFOwESHAEBEgEBAQQyBAEBAQEBAQEBAQEBAQEBAQEBARgBAQEBAUIUa-dlneDVHDKyFftg0P0Cb182r4NKA25hMlIAWgBgAGjnyskmcAA")

    props = client.crm.properties.core_api.get_all(object_type)
    return [
        {
            "name": p.name,
            "label": p.label,
            "type": p.type,
            "field_type": p.field_type
        }
        for p in props.results
    ]

# <-------------------------- Contacts -------------------------->

@mcp.tool()
async def get_HubSpot_contacts(limit: int = 10):
    """
    Fetch a list of contacts from HubSpot.

    Parameters:
    - limit: Number of contacts to retrieve

    Returns:
    - Paginated contacts response
    """
    client = HubSpot(access_token="CK2_9pP5MhIbQlNQMl8kQEwrAg4ACAkIDhIJBB4BAQEBAQEBGO-Q83Mg58rJJijD9O0GMhSS_GLiPXDQyFG3Q0XF7vRiKzZqrTo6QlNQMl8kQEwrAi0ACBkGKAEBAQFFOwESHAEBEgEBAQQyBAEBAQEBAQEBAQEBAQEBAQEBARgBAQEBAUIUDwxNBrxS8HdHqt1Hx6SIQmAZY61KA25hMlIAWgBgAGjnyskmcAA")

    return client.crm.contacts.basic_api.get_page(limit=limit)


@mcp.tool()
async def get_HubSpot_contact_by_id(contact_id: str):
    """
    Get a specific contact by ID.

    Parameters:
    - contact_id: ID of the contact to retrieve

    Returns:
    - Contact object
    """
    client = HubSpot(access_token="CK2_9pP5MhIbQlNQMl8kQEwrAg4ACAkIDhIJBB4BAQEBAQEBGO-Q83Mg58rJJijD9O0GMhSS_GLiPXDQyFG3Q0XF7vRiKzZqrTo6QlNQMl8kQEwrAi0ACBkGKAEBAQFFOwESHAEBEgEBAQQyBAEBAQEBAQEBAQEBAQEBAQEBARgBAQEBAUIUDwxNBrxS8HdHqt1Hx6SIQmAZY61KA25hMlIAWgBgAGjnyskmcAA")

    return client.crm.contacts.basic_api.get_by_id(contact_id)


@mcp.tool()
async def hubspot_create_property(name: str, label: str, description: str) -> str:
    """
    Create a new custom property for contacts.

    Parameters:
    - name: Internal property name
    - label: Display label for the property
    - description: Description of the property

    Returns:
    - Confirmation message
    """
    client = HubSpot(access_token="CK2_9pP5MhIbQlNQMl8kQEwrAg4ACAkIDhIJBB4BAQEBAQEBGO-Q83Mg58rJJijD9O0GMhSS_GLiPXDQyFG3Q0XF7vRiKzZqrTo6QlNQMl8kQEwrAi0ACBkGKAEBAQFFOwESHAEBEgEBAQQyBAEBAQEBAQEBAQEBAQEBAQEBARgBAQEBAUIUDwxNBrxS8HdHqt1Hx6SIQmAZY61KA25hMlIAWgBgAGjnyskmcAA")

    property = PropertyCreate(
        name=name,
        label=label,
        group_name="contactinformation",
        type="string",
        description=description
    )
    client.crm.properties.core_api.create(
        object_type="contacts",
        property_create=property
    )
    return "Property Created"


@mcp.tool()
async def hubspot_delete_contant_by_id(contact_id: str) -> str:
    """
    Delete a contact by ID.

    Parameters:
    - contact_id: ID of the contact to delete

    Returns:
    - Status message
    """
    client = HubSpot(access_token="CK2_9pP5MhIbQlNQMl8kQEwrAg4ACAkIDhIJBB4BAQEBAQEBGO-Q83Mg58rJJijD9O0GMhSS_GLiPXDQyFG3Q0XF7vRiKzZqrTo6QlNQMl8kQEwrAi0ACBkGKAEBAQFFOwESHAEBEgEBAQQyBAEBAQEBAQEBAQEBAQEBAQEBARgBAQEBAUIUDwxNBrxS8HdHqt1Hx6SIQmAZY61KA25hMlIAWgBgAGjnyskmcAA")

    client.crm.contacts.basic_api.archive(contact_id)
    return "Deleted"


@mcp.tool()
async def hubspot_create_contact(properties: str) -> str:
    """
    Create a new contact using JSON string of properties.

    Parameters:
    - properties: JSON string containing contact fields

    Returns:
    - Status message
    """
    client = HubSpot(access_token="CK2_9pP5MhIbQlNQMl8kQEwrAg4ACAkIDhIJBB4BAQEBAQEBGO-Q83Mg58rJJijD9O0GMhSS_GLiPXDQyFG3Q0XF7vRiKzZqrTo6QlNQMl8kQEwrAi0ACBkGKAEBAQFFOwESHAEBEgEBAQQyBAEBAQEBAQEBAQEBAQEBAQEBARgBAQEBAUIUDwxNBrxS8HdHqt1Hx6SIQmAZY61KA25hMlIAWgBgAGjnyskmcAA")

    properties = json.loads(properties)
    data = SimplePublicObjectInputForCreate(properties=properties)
    client.crm.contacts.basic_api.create(simple_public_object_input_for_create=data)
    return "Created"


@mcp.tool()
async def hubspot_update_contact_by_id(contact_id: str, updates: str) -> str:
    """
    Update a contact by ID.

    Parameters:
    - contact_id: ID of the contact to update
    - updates: JSON string of properties to update

    Returns:
    - Status message
    """
    updates = json.loads(updates)
    data = SimplePublicObjectInput(properties=updates)
    client = HubSpot(access_token="CK2_9pP5MhIbQlNQMl8kQEwrAg4ACAkIDhIJBB4BAQEBAQEBGO-Q83Mg58rJJijD9O0GMhSS_GLiPXDQyFG3Q0XF7vRiKzZqrTo6QlNQMl8kQEwrAi0ACBkGKAEBAQFFOwESHAEBEgEBAQQyBAEBAQEBAQEBAQEBAQEBAQEBARgBAQEBAUIUDwxNBrxS8HdHqt1Hx6SIQmAZY61KA25hMlIAWgBgAGjnyskmcAA")

    try:
        client.crm.contacts.basic_api.update(contact_id, data)
        return "Done"
    except Exception as e:
        return f"Error occurred: {e}"





#if __name__ == "__main__":
#    mcp.run(transport="stdio")
