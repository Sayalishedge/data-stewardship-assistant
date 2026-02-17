"""
session_helpers.py

Reusable Streamlit session state management helpers.
Provides functions for initializing, getting, and setting session state variables.

Designed to be reusable across HCP and HCO applications.
"""

import streamlit as st
from typing import Any, Dict, List, Optional


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state(
    defaults: Dict[str, Any],
    force: bool = False
):
    """
    Initialize multiple session state variables with default values.

    Args:
        defaults: Dictionary of {key: default_value} pairs
        force: If True, overwrite existing values
    """
    for key, default_value in defaults.items():
        if force or key not in st.session_state:
            st.session_state[key] = default_value


def init_common_session_state(entity_type: str = "HCP"):
    """
    Initialize common session state variables for data steward apps.

    Args:
        entity_type: "HCP" or "HCO" - determines key naming
    """
    # Determine the selected ID key based on entity type
    selected_id_key = f"selected_{entity_type.lower()}_id"

    defaults = {
        "messages": [],
        "results_df": None,
        selected_id_key: None,
        "current_view": "main",
        "last_prompt": None,
        "show_popup": False,
        "popup_message_info": None,
        "show_confirm_dialog": False,
        "show_primary_confirm_dialog": False,
        "show_reason_popup": False,
        "reason_popup_data": None,
        "priority_rankings_cache": {},
        "approved_cols": [],
        "proposed_record": None,
        "primary_hco_id": None,
        "primary_hco_data": None,
        "empty_record_for_enrichment": None,
        "web_search_query": None,
    }

    init_session_state(defaults)


def init_hcp_session_state():
    """Initialize session state for HCP (Healthcare Provider) applications."""
    init_common_session_state("HCP")


def init_hco_session_state():
    """Initialize session state for HCO (Healthcare Organization) applications."""
    init_common_session_state("HCO")


def init_data_steward_session_state(entity_type: str = "HCP", force_reset: bool = False):
    """
    Initialize session state for the data steward apps while reusing common defaults.

    Args:
        entity_type: "HCP" or "HCO"
        force_reset: If True, forces reset of all session state variables
    """
    # Determine the selected ID key based on entity type
    selected_id_key = f"selected_{entity_type.lower()}_id"

    # Clear the other entity's selected ID when switching
    other_entity = "hco" if entity_type == "HCP" else "hcp"
    other_selected_key = f"selected_{other_entity}_id"
    if other_selected_key in st.session_state:
        st.session_state[other_selected_key] = None

    defaults = {
        "messages": [],
        "results_df": None,
        selected_id_key: None,
        "selected_record_df": None,  # Stores the selected record after insert for affiliation operations
        "current_view": "main",
        "last_prompt": None,
        "show_popup": False,
        "popup_message_info": None,
        "show_confirm_dialog": False,
        "show_primary_confirm_dialog": False,
        "show_reason_popup": False,
        "reason_popup_data": None,
        "priority_rankings_cache": {},
        "approved_cols": [],
        "proposed_record": None,
        "primary_hco_id": None,
        "primary_hco_data": None,
        "empty_record_for_enrichment": None,
        "web_search_query": None,
        "priority_reasons": {},
        "demographic_expander_state": False,
        "provider_info_change": False,
        "semantic_model_file": "HCP.yaml" if entity_type == "HCP" else "HCO.yaml",
        "search_query": None,          # What user typed in search
        "enrichment_query": None,      # What web enrichment should use
    }

    # Force reset all values when switching assistant types
    init_session_state(defaults, force=force_reset)

    # Clear any cached Perplexity responses when switching
    if force_reset:
        keys_to_clear = [k for k in st.session_state.keys() if k.startswith("perplexity_response_")]
        for key in keys_to_clear:
            del st.session_state[key]


# ============================================================================
# SESSION STATE GETTERS
# ============================================================================

def get_session_value(key: str, default: Any = None) -> Any:
    """
    Get a value from session state with optional default.

    Args:
        key: Session state key
        default: Default value if key doesn't exist

    Returns:
        Session state value or default
    """
    return st.session_state.get(key, default)


def get_selected_id(entity_type: str = "HCP") -> Optional[Any]:
    """
    Get the currently selected entity ID.

    Args:
        entity_type: "HCP" or "HCO"

    Returns:
        Selected ID or None
    """
    key = f"selected_{entity_type.lower()}_id"
    return st.session_state.get(key)


def get_current_view() -> str:
    """
    Get the current view name.

    Returns:
        Current view name (default: "main")
    """
    return st.session_state.get("current_view", "main")


def get_results_df():
    """
    Get the current results DataFrame.

    Returns:
        Results DataFrame or None
    """
    return st.session_state.get("results_df")


def is_popup_visible() -> bool:
    """
    Check if a popup is currently visible.

    Returns:
        True if popup is visible
    """
    return st.session_state.get("show_popup", False)


def is_confirm_dialog_visible() -> bool:
    """
    Check if confirmation dialog is visible.

    Returns:
        True if dialog is visible
    """
    return st.session_state.get("show_confirm_dialog", False)


def is_primary_confirm_dialog_visible() -> bool:
    """
    Check if primary affiliation confirmation dialog is visible.

    Returns:
        True if dialog is visible
    """
    return st.session_state.get("show_primary_confirm_dialog", False)


def is_new_record(entity_type: str = "HCP") -> bool:
    """
    Check if the current operation is for a new record (bypass flow).

    Args:
        entity_type: "HCP" or "HCO"

    Returns:
        True if this is a new record
    """
    selected_id = get_selected_id(entity_type)
    return selected_id == 'empty_record' or selected_id == 'N/A'


# ============================================================================
# SESSION STATE SETTERS
# ============================================================================

def set_session_value(key: str, value: Any):
    """
    Set a session state value.

    Args:
        key: Session state key
        value: Value to set
    """
    st.session_state[key] = value


def set_selected_id(entity_id: Any, entity_type: str = "HCP"):
    """
    Set the currently selected entity ID.

    Args:
        entity_id: ID to set
        entity_type: "HCP" or "HCO"
    """
    key = f"selected_{entity_type.lower()}_id"
    st.session_state[key] = entity_id


def set_current_view(view: str):
    """
    Set the current view.

    Args:
        view: View name to set
    """
    st.session_state.current_view = view


def set_results_df(df):
    """
    Set the results DataFrame.

    Args:
        df: DataFrame to set
    """
    st.session_state.results_df = df


def show_popup(message_type: str, record_info: Dict[str, Any]):
    """
    Show a popup with the given message.

    Args:
        message_type: Type of message
        record_info: Dictionary with message details
    """
    st.session_state.show_popup = True
    st.session_state.popup_message_info = {
        'type': message_type,
        **record_info
    }


def hide_popup():
    """Hide the current popup."""
    st.session_state.show_popup = False
    st.session_state.popup_message_info = None


def show_confirm_dialog():
    """Show the confirmation dialog."""
    st.session_state.show_confirm_dialog = True


def hide_confirm_dialog():
    """Hide the confirmation dialog."""
    st.session_state.show_confirm_dialog = False


def show_primary_confirm_dialog(hco_id: str, hco_data: Dict[str, Any] = None):
    """
    Show the primary affiliation confirmation dialog.

    Args:
        hco_id: HCO ID to set as primary
        hco_data: Optional HCO data for insertion
    """
    st.session_state.show_primary_confirm_dialog = True
    st.session_state.primary_hco_id = hco_id
    if hco_data:
        st.session_state.primary_hco_data = hco_data


def hide_primary_confirm_dialog():
    """Hide the primary affiliation confirmation dialog."""
    st.session_state.show_primary_confirm_dialog = False
    st.session_state.primary_hco_id = None
    st.session_state.primary_hco_data = None


def show_reason_popup(hco_name: str, priority: int, reason: str):
    """
    Show the reason popup dialog.

    Args:
        hco_name: Organization name
        priority: Priority number
        reason: Reason text
    """
    st.session_state.show_reason_popup = True
    st.session_state.reason_popup_data = {
        'hco_name': hco_name,
        'priority': priority,
        'reason': reason
    }


def hide_reason_popup():
    """Hide the reason popup dialog."""
    st.session_state.show_reason_popup = False
    st.session_state.reason_popup_data = None


# ============================================================================
# NAVIGATION HELPERS
# ============================================================================

def navigate_to(view: str, clear_selection: bool = False, entity_type: str = "HCP"):
    """
    Navigate to a different view.

    Args:
        view: Target view name
        clear_selection: Whether to clear the selected entity ID
        entity_type: "HCP" or "HCO"
    """
    set_current_view(view)
    if clear_selection:
        set_selected_id(None, entity_type)
    st.rerun()


def navigate_to_main(entity_type: str = "HCP"):
    """
    Navigate to the main view.

    Args:
        entity_type: "HCP" or "HCO"
    """
    navigate_to("main", clear_selection=True, entity_type=entity_type)


def navigate_to_enrichment(entity_id: Any = None, entity_type: str = "HCP"):
    """
    Navigate to the enrichment page.

    Args:
        entity_id: Optional entity ID to select
        entity_type: "HCP" or "HCO"
    """
    if entity_id:
        set_selected_id(entity_id, entity_type)
    set_current_view("enrichment_page")
    st.rerun()


# ============================================================================
# APPROVAL/PROPOSED RECORD HELPERS
# ============================================================================

def set_approved_columns(columns: List[str]):
    """
    Set the list of approved columns for update/insert.

    Args:
        columns: List of column names
    """
    st.session_state.approved_cols = columns


def get_approved_columns() -> List[str]:
    """
    Get the list of approved columns.

    Returns:
        List of approved column names
    """
    return st.session_state.get('approved_cols', [])


def set_proposed_record(record: Dict[str, Any]):
    """
    Set the proposed record for update/insert.

    Args:
        record: Proposed record dictionary
    """
    st.session_state.proposed_record = record


def get_proposed_record() -> Optional[Dict[str, Any]]:
    """
    Get the proposed record.

    Returns:
        Proposed record dictionary or None
    """
    return st.session_state.get('proposed_record')


def set_empty_record_for_enrichment(record: Dict[str, Any], search_query: str = None):
    """
    Set an empty record for the bypass/web search flow.

    Args:
        record: Empty record dictionary
        search_query: Optional search query used
    """
    st.session_state.empty_record_for_enrichment = record
    if search_query:
        st.session_state.web_search_query = search_query


def get_empty_record_for_enrichment() -> Optional[Dict[str, Any]]:
    """
    Get the empty record for enrichment.

    Returns:
        Empty record dictionary or None
    """
    return st.session_state.get('empty_record_for_enrichment')


# ============================================================================
# PRIORITY CACHE HELPERS
# ============================================================================

def get_priority_rankings(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Get cached priority rankings.

    Args:
        cache_key: Cache key for the rankings

    Returns:
        Priority rankings dictionary or None
    """
    cache = st.session_state.get('priority_rankings_cache', {})
    return cache.get(cache_key)


def set_priority_rankings(cache_key: str, rankings: Dict[str, Any]):
    """
    Cache priority rankings.

    Args:
        cache_key: Cache key for the rankings
        rankings: Rankings dictionary to cache
    """
    if 'priority_rankings_cache' not in st.session_state:
        st.session_state.priority_rankings_cache = {}
    st.session_state.priority_rankings_cache[cache_key] = rankings


def clear_priority_cache():
    """Clear all cached priority rankings."""
    st.session_state.priority_rankings_cache = {}

# =================== #
# RESET SESSION STATE #
# =================== #

def reset_search_session_state(entity_type: str = "HCP"):
    """
    Reset the search session state for a specific entity type.

    Args:
        entity_type: "HCP" or "HCO"
    """
    st.session_state.update({
        "messages": [],
        "results_df": None,
        f"selected_{entity_type.lower()}_id": None,
        "selected_record_df": None  # Clear the selected record after insert
    })