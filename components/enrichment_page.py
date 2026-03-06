import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

# Updated imports to use OpenAI
from utils.openai_research import (
    get_openai_client, 
    get_consolidated_data_for_hcp,
    get_consolidated_data_for_hco # Ensure this is also exported in your utils
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
    """
    entity_type = st.session_state.get("assistant_type", "HCP")
    
    # [CSS styling remains same as your original code]
    st.markdown("""<style>...</style>""", unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Search Results"):
        st.session_state.current_view = "main"
        st.session_state.selected_record_df = None
        st.rerun()
    
    st.divider()
    
    if selected_record_df is None or selected_record_df.empty:
        st.warning(f"No {entity_type} record selected. Please go back and select a record.")
        return
    
    selected_record = selected_record_df.iloc[0]
    selected_id_key = f"selected_{entity_type.lower()}_id"
    selected_id = st.session_state.get(selected_id_key)
    is_new_record = selected_id == 'empty_record' or str(selected_record.get("ID", "N/A")) in ['', 'N/A', 'None']
    
    record_id = selected_record.get("ID", "N/A") if not is_new_record else "NEW"
    record_name = selected_record.get("NAME", "N/A")
    record_npi = selected_record.get("NPI", "N/A")
    
    st.markdown("<h3>📑 Current vs. Proposed Comparison Report</h3>", unsafe_allow_html=True)
    
    # Cache management - Switched prefix to 'openai'
    if is_new_record:
        web_query = st.session_state.get("web_search_query", "NEW")
        cache_key = f"openai_response_{entity_type}_NEW_{web_query}"
    else:
        cache_key = f"openai_response_{entity_type}_{record_id}"

    if cache_key not in st.session_state:
        with st.spinner("🔍 Researching via OpenAI GPT-4o with Web Search..."):
            try:
                client = get_openai_client()
                search_query = st.session_state.get("web_search_query") if is_new_record else None
                hcp_hco_data = selected_record.to_dict() if hasattr(selected_record, 'to_dict') else selected_record
                
                if entity_type == "HCP":
                    ai_response = get_consolidated_data_for_hcp(client=client, hcp_data=hcp_hco_data, search_query=search_query)
                else:
                    ai_response = get_consolidated_data_for_hco(client=client, hco_data=hcp_hco_data, search_query=search_query)
                
                st.session_state[cache_key] = ai_response
            except Exception as e:
                st.error(f"Error fetching data from OpenAI: {str(e)}")
                return

    ai_response = st.session_state.get(cache_key)
    if not ai_response: return

    # --- DATA TRANSFORMATION ---
    # We keep 'transform_perplexity_response_to_record' name if you haven't renamed it in components/comparison_table.py
    proposed_record = transform_perplexity_response_to_record(ai_response, entity_type)
    
    if is_new_record:
        current_record = {key: "N/A" for key in proposed_record.keys()}
    else:
        current_record = transform_current_record_for_comparison(selected_record, entity_type)
    
    field_mapping = get_field_mapping_for_entity(entity_type)
    
    # Expander Logic
    if entity_type == "HCP":
        disp_name = proposed_record.get('Name', record_name) if is_new_record else current_record.get('Name', 'N/A')
        disp_npi = proposed_record.get('NPI', 'N/A') if is_new_record else record_npi
        expander_title = f"Demographic information of : {disp_name} (NPI: {disp_npi})"
    else:
        expander_title = f"Address information of : {current_record.get('Name', record_name)}"
    
    init_popup_session_state()
    popup_placeholder = st.empty()
    dialog_placeholder = st.empty()
    
    if st.session_state.get('show_popup'):
        show_popup(popup_placeholder, st.session_state.popup_message_info['type'], st.session_state.popup_message_info)
        return
    
    # Dialogs
    selected_record_dict = selected_record.to_dict() if hasattr(selected_record, 'to_dict') else dict(selected_record)
    if render_confirm_dialog(session, dialog_placeholder, selected_record_dict, entity_type, is_new_record): return
    if render_primary_confirm_dialog(session, dialog_placeholder, selected_record_dict, entity_type, is_new_record): return

    # Comparison Table
    render_comparison_table(current_record, proposed_record, field_mapping, str(record_id), is_new_record, expander_title)
    
    st.markdown("<hr style='margin-top: 0; margin-bottom: 0; border-top: 1px solid #ccc;'>", unsafe_allow_html=True)
    
    # --- AFFILIATION PROCESSING ---
    ai_affiliations = transform_perplexity_affiliations(ai_response, entity_type)
    
    db_affiliations_df = pd.DataFrame()
    if not is_new_record:
        db_affiliations_df = get_affiliations_from_db(session, entity_type, selected_record_dict)
    
    # 2. Pass the 'proposed_record' into the builder to enable self-reference filtering
    all_affiliations = build_affiliations_dict(
        db_affiliations_df=db_affiliations_df,
        ai_affiliations=ai_affiliations,
        entity_name=current_record.get('Name', record_name),
        entity_type=entity_type,
        proposed_record=proposed_record
    )
    
    current_record_dict = selected_record.to_dict() if hasattr(selected_record, 'to_dict') else dict(selected_record)
    current_record_dict.update(current_record) 
    
    primary_id_field = "PRIMARY_AFFL_HCO_ACCOUNT_ID" if entity_type == "HCP" else "PRIMARY_AFFL_ACCOUNT_ID"
    render_affiliation_expander(session, all_affiliations, current_record_dict, entity_type, primary_id_field, is_new_record)