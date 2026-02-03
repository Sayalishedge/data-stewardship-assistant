import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

from utils.perplexity import (
    get_perplexity_client,
    get_consolidated_data_for_hcp,
    get_consolidated_data_for_hco
)
from components.comparison_table import (
    render_comparison_table,
    get_field_mapping_for_entity,
    transform_perplexity_response_to_record,
    transform_current_record_for_comparison,
    render_confirm_dialog
)
from components.affiliation_table import (
    build_affiliations_dict,
    render_affiliation_expander,
    render_primary_confirm_dialog,
    transform_perplexity_affiliations
)
from components.popup import (
    show_popup,
    show_reason_popup,
    init_popup_session_state
)
from utils.affiliation_queries import get_affiliations_from_db


def render_enrichment_page(session, selected_record_df: pd.DataFrame):
    """
    Render the enrichment page for a selected record.
    
    Args:
        session: Snowflake session
        selected_record_df: DataFrame containing the selected record
    """
    entity_type = st.session_state.get("assistant_type", "HCP")
    
    # CSS for comparison table styling
    st.markdown("""
        <style>
            .cell-content { padding: 0.3rem 0.5rem; font-size: 14px; display: flex; align-items: center; min-height: 40px; }
            .report-header { font-weight: bold; color: #4f4f4f; padding: 0.5rem; border-bottom: 2px solid #ccc; }
            .report-proposed-column { border-left: 2px solid #D3D3D3; padding-left: 1rem; }
            .checkbox-container { width: 100%; text-align: center; }
            .checkbox-container div[data-testid="stCheckbox"] { padding-top: 8px; }
            div[data-testid="stExpander"] button { margin-top: -0.5rem; }
        </style>
    """, unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Search Results"):
        st.session_state.current_view = "main"
        st.session_state.selected_record_df = None  # Clear the inserted record state
        st.rerun()
    
    st.divider()
    
    # Check if we have a valid record
    if selected_record_df is None or selected_record_df.empty:
        st.warning(f"No {entity_type} record selected. Please go back and select a record.")
        return
    
    selected_record = selected_record_df.iloc[0]
    
    # Determine if this is a new record (Web Search flow) or existing record
    selected_id_key = f"selected_{entity_type.lower()}_id"
    selected_id = st.session_state.get(selected_id_key)
    is_new_record = selected_id == 'empty_record' or str(selected_record.get("ID", "N/A")) in ['', 'N/A', 'None']
    
    record_id = selected_record.get("ID", "N/A") if not is_new_record else "NEW"
    record_name = selected_record.get("NAME", "N/A")
    record_npi = selected_record.get("NPI", "N/A")
    
    # Title
    st.markdown("<h3>📑 Current vs. Proposed Comparison Report</h3>", unsafe_allow_html=True)
    
    if is_new_record:
        web_search_query = st.session_state.get("web_search_query", "")
        st.markdown(
            f"<h5>New Record from Web Search: {web_search_query}</h5>", 
            unsafe_allow_html=True
        )
    else:
        if entity_type == "HCP":
            st.markdown(
                f"<h5>Comparing for ID: {record_id} | {record_name} | NPI: {record_npi}</h5>", 
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<h5>Comparing for ID: {record_id} | {record_name}</h5>", 
                unsafe_allow_html=True
            )
    
    # Fetch data from Perplexity if not already cached
    cache_key = f"perplexity_response_{entity_type}_{record_id}"
    
    if cache_key not in st.session_state:
        with st.spinner("🔍 Fetching latest data from web sources..."):
            try:
                client = get_perplexity_client()
                search_query = st.session_state.get("web_search_query") if is_new_record else None
                
                if entity_type == "HCP":
                    perplexity_response = get_consolidated_data_for_hcp(
                        client=client,
                        hcp_data=selected_record.to_dict() if hasattr(selected_record, 'to_dict') else selected_record,
                        search_query=search_query
                    )
                else:
                    perplexity_response = get_consolidated_data_for_hco(
                        client=client,
                        hco_data=selected_record.to_dict() if hasattr(selected_record, 'to_dict') else selected_record,
                        search_query=search_query
                    )
                
                st.session_state[cache_key] = perplexity_response
            except Exception as e:
                st.error(f"Error fetching data from Perplexity: {str(e)}")
                st.session_state[cache_key] = None
    
    perplexity_response = st.session_state.get(cache_key)
    
    if perplexity_response is None:
        st.warning("Could not fetch data from web sources. Please try again.")
        return

    # Transform data for comparison
    proposed_record = transform_perplexity_response_to_record(perplexity_response, entity_type)
    
    # For new records, current values should be N/A
    if is_new_record:
        current_record = {key: "N/A" for key in proposed_record.keys()}
    else:
        current_record = transform_current_record_for_comparison(selected_record, entity_type)
    
    # Get field mapping
    field_mapping = get_field_mapping_for_entity(entity_type)
    
    # Expander title
    if entity_type == "HCP":
        expander_title = f"Demographic information of : {current_record.get('Name', 'N/A')} (NPI: {record_npi})"
    else:
        expander_title = f"Address information of : {current_record.get('Name', 'N/A')}"
    
    # Initialize popup session state
    init_popup_session_state()
    
    # Create placeholders for dialogs and popups
    popup_placeholder = st.empty()
    dialog_placeholder = st.empty()
    
    # Handle popups first
    if st.session_state.get('show_popup'):
        show_popup(popup_placeholder, st.session_state.popup_message_info['type'], st.session_state.popup_message_info)
        return
    
    # Handle reason popup (uses Streamlit's native dialog)
    if st.session_state.get('show_reason_popup') and st.session_state.get('reason_popup_data'):
        reason_data = st.session_state.reason_popup_data
        show_reason_popup(
            reason_data.get('hco_name', 'Unknown'),
            str(reason_data.get('priority', '-')),
            reason_data.get('reason', 'No reason available')
        )
    
    # Handle Insert/Update confirmation dialog
    selected_record_dict = selected_record.to_dict() if hasattr(selected_record, 'to_dict') else dict(selected_record)
    if render_confirm_dialog(
        session=session,
        dialog_placeholder=dialog_placeholder,
        selected_record=selected_record_dict,
        entity_type=entity_type,
        is_new_record=is_new_record
    ):
        return
    
    # Handle primary confirmation dialog
    if render_primary_confirm_dialog(
        session=session,
        dialog_placeholder=dialog_placeholder,
        selected_record=selected_record_dict,
        entity_type=entity_type,
        is_new_record=is_new_record
    ):
        return
    
    # Render comparison table
    render_comparison_table(
        current_record=current_record,
        proposed_record=proposed_record,
        field_mapping=field_mapping,
        record_id=str(record_id),
        is_new_record=is_new_record,
        expander_title=expander_title,
        expanded=True
    )
    
    st.markdown("<hr style='margin-top: 0; margin-bottom: 0; border-top: 1px solid #ccc;'>", unsafe_allow_html=True)
    
    # Build affiliations from Perplexity response
    ai_affiliations = transform_perplexity_affiliations(perplexity_response, entity_type)
    
    # Query DB affiliations (only for existing records)
    db_affiliations_df = pd.DataFrame()
    if not is_new_record:
        selected_record_dict = selected_record.to_dict() if hasattr(selected_record, 'to_dict') else dict(selected_record)
        db_affiliations_df = get_affiliations_from_db(session, entity_type, selected_record_dict)
    
    # Build combined affiliations dict
    entity_name = current_record.get('Name', '') or record_name
    all_affiliations = build_affiliations_dict(
        db_affiliations_df=db_affiliations_df,
        ai_affiliations=ai_affiliations,
        entity_name=entity_name,
        entity_type=entity_type
    )
    
    # Prepare current record dict for affiliation expander
    current_record_dict = selected_record.to_dict() if hasattr(selected_record, 'to_dict') else dict(selected_record)
    current_record_dict.update(current_record)  # Add transformed fields
    
    # Render affiliation expander
    primary_id_field = "PRIMARY_AFFL_HCO_ACCOUNT_ID" if entity_type == "HCP" else "PRIMARY_AFFL_ACCOUNT_ID"
    render_affiliation_expander(
        session=session,
        all_affiliations=all_affiliations,
        current_record=current_record_dict,
        entity_type=entity_type,
        primary_id_field=primary_id_field,
        is_new_record=is_new_record
    )
