import json
from hubspot import HubSpot
import logging
from mcp.server.fastmcp import FastMCP
import asyncio

from hubspot.crm.contacts import Filter, FilterGroup, PublicObjectSearchRequest
from hubspot.crm.properties import PropertyCreate
from hubspot.crm.contacts import SimplePublicObjectInputForCreate, SimplePublicObjectInput


from hubspot.crm.companies import SimplePublicObjectInputForCreate
from hubspot.crm.companies import SimplePublicObjectInput


logger = logging.getLogger(__name__)

client = HubSpot(access_token="CPujkMT4MhIbQlNQMl8kQEwrAg4ACAkIDhIJBB4BAQEBAQEBGO-Q83Mg58rJJijD9O0GMhQ_lvI-TkHGJoeaHK_2BIe-6PR9qzo6QlNQMl8kQEwrAi0ACBkGKAEBAQFFOwESHAEBEgEBAQQyBAEBAQEBAQEBAQEBAQEBAQEBARgBAQEBAUIUjDgvcYwTnep0RPK3uvJp10JlWClKA25hMlIAWgBgAGjnyskmcAA")



# ====== MCP Setup ======
mcp = FastMCP("HubSpot")


#<--------------------------Properties-------------------------->

def hubspot_list_properties(object_type: str):
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

def hubspot_search_by_property(object_type, property_name, operator, value, properties, limit=10):
    search_request = PublicObjectSearchRequest(
        filter_groups=[
            FilterGroup(filters=[
                Filter(property_name=property_name, operator=operator, value=value)
            ])
        ],
        properties=list(properties),
        limit=limit
    )

    if object_type == "contacts":
        results = client.crm.contacts.search_api.do_search(public_object_search_request=search_request)
    elif object_type == "companies":
        results = client.crm.companies.search_api.do_search(public_object_search_request=search_request)
    elif object_type == "deals":
        results = client.crm.deals.search_api.do_search(public_object_search_request=search_request)
    elif object_type == "tickets":
        results = client.crm.tickets.search_api.do_search(public_object_search_request=search_request)
    else:
        raise ValueError("Unsupported object type")

    return [obj.properties for obj in results.results]



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
    try:
        client.crm.contacts.basic_api.update(contact_id, data)
        logger.info(f"Updated contact ID: {contact_id}")
        return "Done"
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return f"Error occurred: {e}"




#<--------------------------Companies-------------------------->
def hubspot_create_companies(properties):
    properties = json.loads(properties)
    data = SimplePublicObjectInputForCreate(properties=properties)
    client.crm.companies.basic_api.create(simple_public_object_input_for_create=data)

def get_HubSpot_companies(limit=10):
    return client.crm.companies.basic_api.get_page(limit=10)


def get_HubSpot_companies_by_id(company_id):
    return client.crm.companies.basic_api.get_by_id(company_id)

def hubspot_update_company_by_id(company_id, updates):
    updates = json.loads(updates)
    update = SimplePublicObjectInput(properties=updates)
    try:
        client.crm.companies.basic_api.update(company_id, update)
        logger.info(f"Updated company ID: {company_id}")
        return("Done")
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return(f"Error occured: {e}")

def hubspot_delete_company_by_id(company_id):
    client.crm.companies.basic_api.archive(company_id)


# <--------------------------Deals-------------------------->

def get_HubSpot_deals(limit=10):
    return client.crm.deals.basic_api.get_page(limit=limit)

def get_HubSpot_deal_by_id(deal_id):
    return client.crm.deals.basic_api.get_by_id(deal_id)

def hubspot_create_deal(properties):
    properties = json.loads(properties)
    data = SimplePublicObjectInputForCreate(properties=properties)
    client.crm.deals.basic_api.create(simple_public_object_input_for_create=data)

def hubspot_update_deal_by_id(deal_id, updates):
    updates = json.loads(updates)
    data = SimplePublicObjectInput(properties=updates)
    try:
        client.crm.deals.basic_api.update(deal_id, data)
        logger.info(f"Updated deal ID: {deal_id}")
        return "Done"
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return f"Error occurred: {e}"

def hubspot_delete_deal_by_id(deal_id):
    client.crm.deals.basic_api.archive(deal_id)


# <--------------------------Tickets-------------------------->

def get_HubSpot_tickets(limit=10):
    return client.crm.tickets.basic_api.get_page(limit=limit)

def get_HubSpot_ticket_by_id(ticket_id):
    return client.crm.tickets.basic_api.get_by_id(ticket_id)

def hubspot_create_ticket(properties):
    properties = json.loads(properties)
    data = SimplePublicObjectInputForCreate(properties=properties)
    client.crm.tickets.basic_api.create(simple_public_object_input_for_create=data)

def hubspot_update_ticket_by_id(ticket_id, updates):
    updates = json.loads(updates)
    data = SimplePublicObjectInput(properties=updates)
    try:
        client.crm.tickets.basic_api.update(ticket_id, data)
        logger.info(f"Updated ticket ID: {ticket_id}")
        return "Done"
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return (f"Error occurred: {e}")

def hubspot_delete_ticket_by_id(ticket_id):
    client.crm.tickets.basic_api.archive(ticket_id)