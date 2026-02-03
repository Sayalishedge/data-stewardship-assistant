import streamlit as st
from snowflake.snowpark import Session
from typing import Dict, Any, Optional, List

# ============================= #
# CORTEX SEARCH SERVICE HELPERS #
# ============================= #

def get_cortex_search_service(
    session: Session,
    database: str,
    schema: str,
    service_name: str
):
    """
    Get a Cortex Search Service instance.

    Args:
        session: Snowflake session
        database: Database name
        schema: Schema name
        service_name: Cortex Search Service name

    Returns:
        Cortex Search Service object
    """
    from snowflake.core import Root

    try:
        root = Root(session)
        return (
            root.databases[database]
            .schemas[schema]
            .cortex_search_services[service_name]
        )
    except Exception as e:
        raise Exception(f"Could not connect to Cortex Search Service: {e}")


def search_cortex(
    service,
    query: str,
    columns: List[str],
    num_results: int = 3,
    filter_dict: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Search using Cortex Search Service.

    Args:
        service: Cortex Search Service instance
        query: Search query
        columns: Columns to retrieve
        num_results: Number of results to return
        filter_dict: Optional filter dictionary

    Returns:
        List of search results
    """
    try:
        search_params = {
            "query": query,
            "columns": columns,
            "limit": num_results
        }

        if filter_dict:
            search_params["filter"] = filter_dict

        response = service.search(**search_params)
        return response.results if hasattr(response, 'results') else []
    except Exception as e:
        print(f"Cortex search error: {e}")
        return []

# ====================== #
# CORTEX ANALYST HELPERS #
# ====================== #

def call_cortex_analyst(
    session: Session,
    prompt: str,
    semantic_model_file: str,
    database: str = None,
    schema: str = None,
    stage: str = None
) -> Dict[str, Any]:
    """
    Call Cortex Analyst to generate SQL from natural language.

    Args:
        session: Snowflake session
        prompt: Natural language prompt
        semantic_model_file: Path to semantic model YAML file
        database: Database name
        schema: Schema name
        stage: Stage name where semantic model is stored

    Returns:
        Dictionary with SQL and other response data
    """
    import json
    import requests

    try:
        account = st.secrets["snowflake"]["account"]
        account_url = account.replace("_", "-").replace(".", "-")
        api_url = f"https://{account_url}.snowflakecomputing.com/api/v2/cortex/analyst/message"

        token = session.connection.rest.token

        headers = {
            "Authorization": f"Snowflake Token=\"{token}\"",
            "Content-Type": "application/json",
        }

        # Build semantic model path
        if database and schema and stage:
            model_path = f"@{database}.{schema}.{stage}/{semantic_model_file}"
        else:
            model_path = semantic_model_file

        request_body = {
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            "semantic_model_file": model_path
        }

        response = requests.post(api_url, headers=headers, json=request_body, timeout=60)

        if response.status_code >= 400:
            raise Exception(f"API error: {response.status_code} - {response.text}")

        return response.json()
    except Exception as e:
        print(f"Cortex Analyst error: {e}")
        return {"error": str(e)}


def parse_analyst_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Cortex Analyst response to extract SQL and text.

    Args:
        response: Raw response from Cortex Analyst

    Returns:
        Dictionary with 'sql', 'text', and 'suggestions' keys
    """
    result = {
        "sql": None,
        "text": None,
        "suggestions": []
    }

    try:
        message = response.get("message", {})
        content = message.get("content", [])

        for item in content:
            item_type = item.get("type", "")

            if item_type == "sql":
                result["sql"] = item.get("statement", "")
            elif item_type == "text":
                result["text"] = item.get("text", "")
            elif item_type == "suggestions":
                result["suggestions"] = item.get("suggestions", [])
    except Exception as e:
        print(f"Error parsing analyst response: {e}")

    return result
