import os
import json
from typing import Dict, Any

import streamlit as st
from google import genai
from google.genai import types

# Note: We keep your model imports for schema consistency
from models.hcp import HCPSearchResponse
from models.hco import HCOSearchResponse

@st.cache_resource
def get_gemini_client():
    """Initializes the Gemini 2.0 Flash client using Streamlit secrets."""
    return genai.Client(api_key=st.secrets["google"]["api_key"])

def get_consolidated_data_for_hcp(
    client, # Now a Gemini client
    hcp_data: Dict[str, Any],
    model_name: str = "gemini-1.5-flash",
    search_query: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Fetch consolidated HCP data using Gemini 2.0 Flash with Google Search Grounding.
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
    
    # We maintain your exact prompt logic to ensure data quality
    user_query = f"""
    Search the web thoroughly using Google Search for information about this US healthcare provider:
    
    **Health Care Provider to Research:**
    - Name: {hcp_name}
    - NPI: {hcp_npi}
    - Address: {hcp_address1}, {hcp_city}, {hcp_state}, {hcp_zip}

    **Instructions:**
    1. Find COMPLETE information. Do NOT return "N/A" if the provider exists.
    2. Search NPI Registry, NPIDB.org, and official hospital sites.
    3. Return data in two parts: Provider Demographics and Practice/Hospital Affiliations.

    Return the result as a JSON object following this schema:
    {json.dumps(HCPSearchResponse.model_json_schema(), indent=2)}
    """

    # Enable Google Search Grounding
    google_search_tool = types.Tool(google_search=types.GoogleSearch())

    response = client.models.generate_content(
        model=model_name,
        contents=user_query,
        config=types.GenerateContentConfig(
            tools=[google_search_tool],
            response_mime_type="application/json",
            # Pass the schema here so Gemini knows exactly how to format the JSON
            response_schema=HCPSearchResponse.model_json_schema(), 
            temperature=0.0
        )
    )

    return json.loads(response.text)


def get_consolidated_data_for_hco(
    client, # Now a Gemini client
    hco_data: Dict[str, Any],
    model_name: str = "gemini-2.0-flash",
    search_query: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Fetch consolidated HCO data using Gemini 2.0 Flash with Google Search Grounding.
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
    Search the web using Google Search for this US healthcare organization:
    - Name: {hco_name}
    - NPI: {hco_npi}
    - Address: {hco_address1}, {hco_city}, {hco_state}, {hco_zip}

    Return Part 1 (Demographics) and Part 2 (Parent/Affiliated systems).
    Return the result as a JSON object following this schema:
    {json.dumps(HCOSearchResponse.model_json_schema(), indent=2)}
    """

    google_search_tool = types.Tool(google_search=types.GoogleSearch())

    response = client.models.generate_content(
        model=model_name,
        contents=user_query,
        config=types.GenerateContentConfig(
            tools=[google_search_tool],
            response_mime_type="application/json",
            temperature=0.0
        )
    )

    return json.loads(response.text)

# Keep your standardization utility unchanged
def standardize_value_lengths(dictionary: Dict[str, Any]) -> Dict[str, Any]:
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