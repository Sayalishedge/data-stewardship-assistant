import json
import time
from openai import OpenAI
import requests
import streamlit as st
from typing import Dict, List, Tuple, Any


def get_affiliation_priorities_from_cortex_llm(
    session,
    selected_entity_data: Dict[str, Any],
    affiliations: List[Tuple[str, Dict[str, Any]]],
    entity_type: str = "HCP"
) -> Dict[str, Dict[str, Any]]:
    """
    Calls Snowflake Cortex REST API with structured JSON output to rank affiliations by priority.

    Args:
        session: Snowflake session
        selected_entity_data: Dictionary with the selected entity's data
        affiliations: List of (key, affiliation_data) tuples
        entity_type: "HCP" or "HCO"

    Returns:
        Dict mapping affiliation key to {"priority": int, "reason": str}
    """
    if not affiliations:
        return {}

    # Build the prompt for the LLM
    entity_label = "Healthcare Provider" if entity_type == "HCP" else "Healthcare Organization"

    selected_info = f"""
Selected {entity_label}:
- Name: {selected_entity_data.get('Name', selected_entity_data.get('NAME', 'N/A'))}
- Address: {selected_entity_data.get('Address Line1', selected_entity_data.get('ADDRESS1', ''))} {selected_entity_data.get('Address Line2', selected_entity_data.get('ADDRESS2', ''))}
- City: {selected_entity_data.get('City', selected_entity_data.get('CITY', 'N/A'))}
- State: {selected_entity_data.get('State', selected_entity_data.get('STATE', 'N/A'))}
- ZIP: {selected_entity_data.get('ZIP', 'N/A')}
"""

    affiliations_info = "Affiliations to rank:\n"
    for idx, (key, aff) in enumerate(affiliations):
        affiliations_info += f"""
Affiliation {idx + 1} (Key: {key}):
- HCO Name: {aff.get('HCO NAME', 'N/A')}
- HCO Address: {aff.get('HCO ADDRESS', 'N/A')}
- HCO City: {aff.get('HCO CITY', 'N/A')}
- HCO State: {aff.get('HCO STATE', 'N/A')}
- HCO ZIP: {aff.get('HCO ZIP', 'N/A')}
- Source: {aff.get('SOURCE', 'N/A')}
"""

    prompt = f"""You are a healthcare data analyst. Analyze the following selected {entity_label.lower()} and its potential affiliations.
Rank each affiliation by priority (1 being highest priority/best match) based on:
1. Geographic proximity (same city, state, ZIP code area)
2. Name similarity or relationship (parent organization, same health system)
3. Address proximity

{selected_info}

{affiliations_info}

Return your response as a valid JSON object with this exact structure:
{{
    "rankings": [
        {{"key": "affiliation_key", "priority": 1, "reason": "Brief explanation of why this is priority 1"}},
        {{"key": "affiliation_key", "priority": 2, "reason": "Brief explanation of why this is priority 2"}}
    ]
}}

Only return the JSON object, no other text. Use the exact keys provided for each affiliation."""

    try:
        # Use Snowflake Cortex REST API with structured JSON output
        account = st.secrets["snowflake"]["account"]
        account_url = account.replace("_", "-").replace(".", "-")
        api_url = f"https://{account_url}.snowflakecomputing.com/api/v2/cortex/inference:complete"

        # Get token from session
        token = session.connection.rest.token

        headers = {
            "Authorization": f"Snowflake Token=\"{token}\"",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Define JSON schema for structured output
        json_schema = {
            "type": "object",
            "properties": {
                "rankings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "priority": {"type": "number"},
                            "reason": {"type": "string"}
                        },
                        "required": ["key", "priority", "reason"]
                    }
                }
            },
            "required": ["rankings"]
        }

        request_body = {
            "model": "claude-3-5-sonnet",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "response_format": {
                "type": "json",
                "schema": json_schema
            }
        }

        resp = requests.post(api_url, headers=headers, json=request_body, timeout=60)

        if resp.status_code >= 400:
            raise Exception(f"API request failed with status {resp.status_code}: {resp.text}")

        # Parse streaming response - collect all content
        response_text = ""
        for line in resp.text.strip().split("\n"):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        response_text += content
                except json.JSONDecodeError:
                    continue

        # Parse the structured JSON response
        result = json.loads(response_text.strip())

        # Convert to a dictionary keyed by affiliation key
        priority_map = {}
        for ranking in result.get("rankings", []):
            priority_map[str(ranking["key"])] = {
                "priority": ranking["priority"],
                "reason": ranking["reason"]
            }
        return priority_map

    except Exception as e:
        st.warning(f"Could not get LLM priority ranking: {e}")
        # Return default priorities if LLM fails
        return {str(key): {"priority": idx + 1, "reason": "Default ordering (LLM unavailable)"}
                for idx, (key, _) in enumerate(affiliations)}

def get_affiliation_priorities_from_llm(
    session,
    selected_entity_data: Dict[str, Any],
    affiliations: List[Tuple[str, Dict[str, Any]]],
    entity_type: str = "HCP"
) -> Dict[str, Dict[str, Any]]:
    """
    Calls OpenAI Chat Completions API with structured JSON output
    to rank affiliations by priority.
    """
    if not affiliations:
        return {}

    entity_label = "Healthcare Provider" if entity_type == "HCP" else "Healthcare Organization"

    selected_info = f"""
Selected {entity_label}:
- Name: {selected_entity_data.get('Name', selected_entity_data.get('NAME', 'N/A'))}
- Address: {selected_entity_data.get('Address Line1', selected_entity_data.get('ADDRESS1', ''))} {selected_entity_data.get('Address Line2', selected_entity_data.get('ADDRESS2', ''))}
- City: {selected_entity_data.get('City', selected_entity_data.get('CITY', 'N/A'))}
- State: {selected_entity_data.get('State', selected_entity_data.get('STATE', 'N/A'))}
- ZIP: {selected_entity_data.get('ZIP', 'N/A')}
"""

    affiliations_info = "Affiliations to rank:\n"
    for idx, (key, aff) in enumerate(affiliations):
        affiliations_info += f"""
Affiliation {idx + 1} (Key: {key}):
- HCO Name: {aff.get('HCO NAME', 'N/A')}
- HCO Address: {aff.get('HCO ADDRESS', 'N/A')}
- HCO City: {aff.get('HCO CITY', 'N/A')}
- HCO State: {aff.get('HCO STATE', 'N/A')}
- HCO ZIP: {aff.get('HCO ZIP', 'N/A')}
- Source: {aff.get('SOURCE', 'N/A')}
"""

    prompt = f"""You are a healthcare data analyst. Analyze the following selected {entity_label.lower()} and its potential affiliations.
Rank each affiliation by priority (1 being highest priority/best match) based on:
1. Geographic proximity (same city, state, ZIP code area)
2. Name similarity or relationship (parent organization, same health system)
3. Address proximity

{selected_info}

{affiliations_info}

Return your response as a valid JSON object with this exact structure:
{{
    "rankings": [
        {{"key": "affiliation_key", "priority": 1, "reason": "Brief explanation of why this is priority 1"}},
        {{"key": "affiliation_key", "priority": 2, "reason": "Brief explanation of why this is priority 2"}}
    ]
}}

Only return the JSON object, no other text. Use the exact keys provided for each affiliation.
"""

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "affiliation_rankings",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "rankings": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "key": {"type": "string"},
                                        "priority": {"type": "number"},
                                        "reason": {"type": "string"}
                                    },
                                    "required": ["key", "priority", "reason"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["rankings"],
                        "additionalProperties": False
                    }
                }
            },
            max_tokens=4096,
        )

        # Structured output is returned as a JSON string
        content = response.choices[0].message.content
        result = json.loads(content)

        priority_map = {}
        for ranking in result.get("rankings", []):
            priority_map[str(ranking["key"])] = {
                "priority": ranking["priority"],
                "reason": ranking["reason"]
            }

        return priority_map

    except Exception as e:
        st.warning(f"Could not get LLM priority ranking: {e}")
        time.sleep(100)
        return {
            str(key): {
                "priority": idx + 1,
                "reason": "Default ordering (LLM unavailable)"
            }
            for idx, (key, _) in enumerate(affiliations)
        }
