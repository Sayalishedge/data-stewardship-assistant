import os
import json
from typing import Dict, Any

import streamlit as st
from openai import OpenAI

from models.hcp import HCPSearchResponse
from models.hco import HCOSearchResponse

@st.cache_resource
def get_openai_client() -> OpenAI:
    # Safely retrieve key from Streamlit secrets
    api_key = st.secrets.get("openai", {}).get("api_key")
    if not api_key:
        st.error("OpenAI API key not found in secrets.")
    return OpenAI(api_key=api_key)

def get_consolidated_data_for_hcp(
    client: OpenAI,
    hcp_data: Dict[str, Any],
    # Updated to use the search-capable model for real-time web research
    model_name: str = "gpt-4o-search-preview", 
    search_query: str = None
) -> Dict[str, Any]:
    """
    Research HCP data using OpenAI's search-enabled model with Structured Outputs.
    """
    if hasattr(hcp_data, 'to_dict'):
        hcp_data = hcp_data.to_dict()
    
    def get_val(key):
        return hcp_data.get(key, '') if isinstance(hcp_data, dict) else ''

    hcp_name = get_val('NAME') or search_query or 'Unknown Provider'
    hcp_npi = get_val('NPI')
    hcp_loc = f"{get_val('ADDRESS1')}, {get_val('CITY')}, {get_val('STATE')} {get_val('ZIP')}"

    # Same prompt logic as Perplexity to maintain data quality
    user_query = f"""
    Perform a live web search for this US Healthcare Provider:
    Name: {hcp_name}
    NPI: {hcp_npi}
    Address: {hcp_loc}

    Task:
    1. Verify the primary work address and contact details.
    2. Identify all current hospital and medical group affiliations.
    3. Ensure every organization has a complete, verified address.
    """

    # Using Structured Outputs (Strict JSON Schema)
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a professional medical data researcher. Search the web and return verified data in structured JSON."},
            {"role": "user", "content": user_query}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "hcp_research_response",
                "strict": True,
                "schema": HCPSearchResponse.model_json_schema()
            }
        }
    )

    return json.loads(completion.choices[0].message.content)

def get_consolidated_data_for_hco(
    client: OpenAI,
    hco_data: Dict[str, Any],
    model_name: str = "gpt-4o-search-preview",
    search_query: str = None
) -> Dict[str, Any]:
    """
    Research HCO data using OpenAI's search-enabled model with Structured Outputs.
    """
    if hasattr(hco_data, 'to_dict'):
        hco_data = hco_data.to_dict()

    def get_val(key):
        return hco_data.get(key, '') if isinstance(hco_data, dict) else ''

    hco_name = get_val('NAME') or search_query or 'Unknown Organization'
    hco_npi = get_val('NPI')
    hco_loc = f"{get_val('ADDRESS1')}, {get_val('CITY')}, {get_val('STATE')} {get_val('ZIP')}"

    user_query = f"""
    Perform a live web search for this US Healthcare Organization:
    Name: {hco_name}
    NPI: {hco_npi}
    Address: {hco_loc}

    Task:
    1. Verify current demographic details (Address, Phone, Taxonomy).
    2. Identify the parent organization, health system, or corporate owner.
    """

    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a healthcare organizational researcher. Search the web and return verified data in structured JSON."},
            {"role": "user", "content": user_query}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "hco_research_response",
                "strict": True,
                "schema": HCOSearchResponse.model_json_schema()
            }
        }
    )

    return json.loads(completion.choices[0].message.content)

def standardize_value_lengths(dictionary: Dict[str, Any]) -> Dict[str, Any]:
    # Logic for padding lists to match UI table rows
    valid_lists = [v for v in dictionary.values() if isinstance(v, list) and len(v) > 0]
    if not valid_lists:
        return dictionary

    max_length = max(len(v) for v in valid_lists)

    for key, value in dictionary.items():
        if isinstance(value, list):
            if len(value) == 0:
                dictionary[key] = [None] * max_length
            elif len(value) < max_length:
                dictionary[key].extend([value[0]] * (max_length - len(value)))

    return dictionary