import os
import json
from typing import Dict, Any

import streamlit as st
from perplexity import Perplexity

from models.hcp import HCPSearchResponse
from models.hco import HCOSearchResponse


@st.cache_resource
def get_perplexity_client() -> Perplexity:
    os.environ["PERPLEXITY_API_KEY"] = st.secrets["perplexity"]["api_key"]
    return Perplexity()


def get_consolidated_data_for_hcp(
    client: Perplexity,
    hcp_data: Dict[str, Any],
    model_name: str = "sonar",
    use_pro_search: bool = False,
    search_query: str = None
) -> Dict[str, Any]:
    """
    Fetch consolidated HCP data and affiliations from web search via Perplexity.
    
    Args:
        client: Perplexity client instance
        hcp_data: Dictionary or pandas Series containing HCP data
        model_name: Perplexity model to use
        use_pro_search: Whether to use pro search mode
        search_query: Optional search query override for name
        
    Returns:
        Dictionary with hcp_data and hcp_affiliation_data
    """
    if hasattr(hcp_data, 'to_dict'):
        hcp_data = hcp_data.to_dict()
    
    def get_val(key):
        if isinstance(hcp_data, dict):
            return hcp_data.get(key, '')
        return str(hcp_data)
    
    hcp_name = get_val('NAME') or search_query or ''
    hcp_npi = get_val('NPI')
    hcp_address1 = get_val('ADDRESS1')
    hcp_city = get_val('CITY')
    hcp_state = get_val('STATE')
    hcp_zip = get_val('ZIP')
    
    user_query = f"""
    You are a US healthcare data research specialist. Search the web thoroughly for information about this US healthcare provider:
    
    **Health Care Provider to Research:**
    - Name: {hcp_name}
    - NPI: {hcp_npi}
    - Address Line 1: {hcp_address1}
    - City: {hcp_city}
    - State: {hcp_state}
    - ZIP: {hcp_zip}

    **IMPORTANT INSTRUCTIONS:**
    1. You MUST search the web and find COMPLETE information for ALL fields requested below
    2. Do NOT return "N/A" for address fields if the provider exists - search harder to find the actual address
    3. For affiliated organizations, search their official website, NPI Registry, or healthcare directories to find their complete address
    4. If you find an affiliated HCO name, you MUST also find and return their complete address

    **Part 1 - Provider Demographics (verify/update from web sources):**
    Search for the current, verified information about "{hcp_name}":
    - Name: Full name of the doctor/provider
    - First Name: First name of the doctor/provider
    - Last Name: Last name of the doctor/provider
    - NPI: The HCP's NPI number (10 digits). Use the provided {hcp_npi} if available else search for it in NPI Registry, NPIDB.org or healthcare sites and directories
    - Degree: The HCP's degree (e.g., MD, DO, RN)
    - Address Line 1: Current practice street address (e.g., "123 Main Street")
    - Address Line 2: Suite/unit number (or empty string if none)
    - City: City name in ALL CAPS (e.g., "CHARLOTTE")
    - State: 2-letter US state code (e.g., TX, CA, NY)
    - ZIP: 5-digit zipcode (e.g., "28202")

    **Part 2 - Practice/Hospital Affiliation Details:**
    Search for the healthcare organization(s) for the demographics for: {hcp_name}, NPI: {hcp_npi}, at {hcp_address1}, {hcp_city},{hcp_state},{hcp_zip}.
    
    Using the verified Name, NPI, and Address details found in Part 1, search the web 
    (NPI Registry, Hospital Directories, etc.) to find ALL Healthcare Organizations (HCOs) 
    where this specific provider currently practices.

    For each affiliated organization, you MUST provide:
    - NPI: The HCP's NPI number (10 digits). Use the provided {hcp_npi} if available
    - HCO_ID: The organization's NPI number (10 digits). Use "N/A" only if truly not findable.
    - HCO_Name: Full name of the hospital, medical group, health system, or clinic
    - HCO_Address1: REQUIRED - Street address of the practice/hospital location
    - HCO_City: REQUIRED - City in ALL CAPS
    - HCO_State: REQUIRED - 2-letter state code
    - HCO_ZIP: REQUIRED - 5-digit zipcode

    **CRITICAL:** 
    - Ensure the affiliations belong to the SPECIFIC provider at the verified address.
    - Return the HCO Name, HCO NPI (as HCO_ID), and the HCO's full street address.
    - If you find an affiliated organization name, you MUST search for their complete address.
    - Do NOT leave address fields as "N/A" if the organization exists.
    - Return actual found data, not "N/A" unless truly not findable after thorough search.
    - Don't return any rows if all the fields are not found.
    """

    completion = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": user_query}],
        web_search_options={
            "search_type": "pro" if use_pro_search else "fast"
        },  
        response_format={
            "type": "json_schema",
            "json_schema": {
                "schema": HCPSearchResponse.model_json_schema()
            }
        }
    )

    return json.loads(completion.choices[0].message.content)


def get_consolidated_data_for_hco(
    client: Perplexity,
    hco_data: Dict[str, Any],
    model_name: str = "sonar",
    use_pro_search: bool = False,
    search_query: str = None
) -> Dict[str, Any]:
    """
    Fetch consolidated HCO data and affiliations from web search via Perplexity.
    
    Args:
        client: Perplexity client instance
        hco_data: Dictionary or pandas Series containing HCO data
        model_name: Perplexity model to use
        use_pro_search: Whether to use pro search mode
        search_query: Optional search query override for name
        
    Returns:
        Dictionary with hco_data and hco_affiliation_data
    """
    if hasattr(hco_data, 'to_dict'):
        hco_data = hco_data.to_dict()
    
    def get_val(key):
        if isinstance(hco_data, dict):
            return hco_data.get(key, '')
        return str(hco_data)
    
    hco_name = get_val('NAME') or search_query or ''
    hco_npi = get_val('NPI')
    hco_address1 = get_val('ADDRESS1')
    hco_city = get_val('CITY')
    hco_state = get_val('STATE')
    hco_zip = get_val('ZIP')
    
    user_query = f"""
    You are a US healthcare data research specialist. Search the web thoroughly for information about this US healthcare organization:
    
    **Organization to Research:**
    - Name: {hco_name}
    - NPI: {hco_npi}
    - Address Line 1: {hco_address1}
    - City: {hco_city}
    - State: {hco_state}
    - ZIP: {hco_zip}

    **IMPORTANT INSTRUCTIONS:**
    1. You MUST search the web and find COMPLETE information for ALL fields requested below
    2. Do NOT return "N/A" for address fields if the organization exists
    3. For parent/affiliated organizations, search their official website to find their complete address

    **Part 1 - Organization Demographics (verify/update from web sources):**
    Search for the current, verified information about "{hco_name}":
    - Name: Full name of the healthcare organization
    - Address Line 1: Current street address (e.g., "123 Main Street")
    - Address Line 2: Suite/unit number (or empty string if none)
    - City: City name in ALL CAPS (e.g., "CHARLOTTE")
    - State: 2-letter US state code (e.g., TX, CA, NY)
    - ZIP: 5-digit zipcode (e.g., "28202")
    - Country: 2-letter country code (e.g., "US")

    **Part 2 - Parent/Affiliated Organization Details:**
    Search for the parent organization or health system that "{hco_name}" belongs to.
    
    For each affiliated organization, you MUST provide:
    - HCO_ID: The organization's NPI number (10 digits). Use "N/A" only if truly not findable.
    - HCO_Name: Full name of the parent hospital, health system
    - HCO_Address1: REQUIRED - Street address of the organization
    - HCO_City: REQUIRED - City in ALL CAPS
    - HCO_State: REQUIRED - 2-letter state code
    - HCO_ZIP: REQUIRED - 5-digit zipcode

    **CRITICAL:** 
    - Return actual found data, not "N/A" unless truly not findable after thorough search.
    - Return the results only for the organizations in the US and no other countries.
    - Don't return any rows if all the fields are not found.
    """

    completion = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": user_query}],
        web_search_options={
            "search_type": "pro" if use_pro_search else "fast"
        },  
        response_format={
            "type": "json_schema",
            "json_schema": {
                "schema": HCOSearchResponse.model_json_schema()
            }
        }
    )

    return json.loads(completion.choices[0].message.content)


def standardize_value_lengths(dictionary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardize list lengths in a dictionary by padding shorter lists.
    
    Args:
        dictionary: Dictionary with list values of varying lengths
        
    Returns:
        Dictionary with all lists padded to the same length
    """
    valid_lists = [v for v in dictionary.values() if isinstance(v, list) and len(v) > 0]
    if not valid_lists:
        return dictionary

    max_length = max(len(v) for v in valid_lists)

    for key, value in dictionary.items():
        if not isinstance(value, list):
            continue
        if len(value) == 0:
            dictionary[key] = [None] * max_length
        elif len(value) < max_length:
            dictionary[key].extend([value[0]] * (max_length - len(value)))

    return dictionary