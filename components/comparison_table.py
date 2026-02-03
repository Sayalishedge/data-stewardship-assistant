import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Any

from utils.record_operations import insert_record, update_record, get_field_to_db_mapping


def _update_selected_record_after_insert(
    entity_type: str,
    new_id: Any,
    proposed_record: Dict[str, Any],
    approved_cols: List[str]
):
    """
    Update the selected_record_df session state after a successful insert.
    This allows subsequent operations (like affiliation insert) to use the new record ID.
    
    Args:
        entity_type: "HCP" or "HCO"
        new_id: The newly generated ID from the insert operation
        proposed_record: The proposed record data that was inserted
        approved_cols: List of approved column names
    """
    # Get the field to DB column mapping
    field_to_db = get_field_to_db_mapping(entity_type)
    
    # Build the new record data with DB column names
    new_record_data = {"ID": new_id}
    
    for col_name in approved_cols:
        db_col = field_to_db.get(col_name)
        if db_col:
            new_record_data[db_col] = proposed_record.get(col_name)
    
    # Also add common fields that might be needed
    if entity_type == "HCP":
        # Map display names to DB columns for HCP
        new_record_data["NAME"] = proposed_record.get("Name", proposed_record.get("Last Name", ""))
        new_record_data["FIRST_NM"] = proposed_record.get("First Name", "")
        new_record_data["LAST_NM"] = proposed_record.get("Last Name", "")
        new_record_data["NPI"] = proposed_record.get("NPI", "")
    else:
        new_record_data["NAME"] = proposed_record.get("Name", "")
    
    # Create a new DataFrame with the inserted record
    new_record_df = pd.DataFrame([new_record_data])
    
    # Update session state
    st.session_state.selected_record_df = new_record_df
    
    # Update the selected entity ID
    id_key = f"selected_{entity_type.lower()}_id"
    st.session_state[id_key] = new_id


def render_comparison_table(
    current_record: Dict[str, Any],
    proposed_record: Dict[str, Any],
    field_mapping: Dict[str, str],
    record_id: str,
    is_new_record: bool = False,
    expander_title: str = "Comparison",
    expanded: bool = True
):
    """
    Render a Current vs Proposed comparison table with approve checkboxes.
    
    Args:
        current_record: Dictionary with current field values
        proposed_record: Dictionary with proposed field values from web search
        field_mapping: Dict mapping display labels to data keys, e.g., {"Name": "Name", "Address Line 1": "Address Line1"}
        record_id: Unique ID for the record (used for checkbox keys)
        is_new_record: If True, shows "Insert Record" button; else "Update Record"
        expander_title: Title for the expander
        expanded: Whether expander is initially expanded
    """
    with st.expander(expander_title, expanded=expanded):
        # Header row - only 4 columns: Field, Current, Proposed, Approve
        header_cols = st.columns([2.5, 3, 3, 1.5])
        headers = ["Field", "Current", "Proposed", "Approve"]
        for column_obj, header_name in zip(header_cols, headers):
            column_obj.markdown(f'<div class="report-header">{header_name}</div>', unsafe_allow_html=True)
        
        # Data rows
        for field_label, col_name in field_mapping.items():
            current_val = current_record.get(col_name, "N/A") if current_record else "N/A"
            if current_val is None or current_val == "":
                current_val = "N/A"
            
            proposed_val = proposed_record.get(col_name, "N/A") if proposed_record else "N/A"
            if proposed_val is None or proposed_val == "":
                proposed_val = "N/A"
            
            row_cols = st.columns([2.5, 3, 3, 1.5])
            
            # Field name
            row_cols[0].markdown(
                f'<div class="cell-content" style="font-weight: bold;">{field_label}</div>', 
                unsafe_allow_html=True
            )
            
            # Current value
            row_cols[1].markdown(
                f'<div class="cell-content">{current_val}</div>', 
                unsafe_allow_html=True
            )
            
            # Proposed value - highlight if approved
            checkbox_key = f"approve_{record_id}_{col_name}"
            if st.session_state.get(checkbox_key, False):
                row_cols[2].markdown(
                    f'<div class="cell-content report-proposed-column" style="font-weight: bold; color: #4CAF50;">{proposed_val}</div>', 
                    unsafe_allow_html=True
                )
            else:
                row_cols[2].markdown(
                    f'<div class="cell-content report-proposed-column">{proposed_val}</div>', 
                    unsafe_allow_html=True
                )
            
            # Approve checkbox
            with row_cols[3]:
                st.markdown('<div class="cell-content checkbox-container">', unsafe_allow_html=True)
                st.checkbox("", key=checkbox_key, label_visibility="collapsed")
                st.markdown("</div>", unsafe_allow_html=True)
        
        st.write("")
        
        # Action button
        _, btn_col = st.columns([5, 1])
        btn_label = "Insert Record 💾" if is_new_record else "Update Record 💾"
        
        with btn_col:
            if st.button(btn_label, type="primary", key=f"update_btn_{record_id}"):
                approved_cols = []
                for field_label, col_name in field_mapping.items():
                    checkbox_key = f"approve_{record_id}_{col_name}"
                    if st.session_state.get(checkbox_key, False):
                        approved_cols.append(col_name)
                
                if approved_cols:
                    st.session_state.show_confirm_dialog = True
                    st.session_state.approved_cols = approved_cols
                    st.session_state.proposed_record = proposed_record
                    st.rerun()
                else:
                    st.info(f"No fields were selected for {'insert' if is_new_record else 'update'}.")


def get_field_mapping_for_entity(entity_type: str) -> Dict[str, str]:
    """
    Get the field mapping for a given entity type.
    
    Args:
        entity_type: "HCP" or "HCO"
        
    Returns:
        Dictionary mapping display labels to data keys
    """
    if entity_type == "HCP":
        return {
            "Name": "Name",
            "First Name": "First Name",
            "Last Name": "Last Name",
            "NPI": "NPI",
            "Degree": "Degree",
            "Address Line 1": "Address Line1",
            "Address Line 2": "Address Line2",
            "City": "City",
            "State": "State",
            "ZIP Code": "ZIP"
        }
    else:  # HCO
        return {
            "Name": "Name",
            "Address Line 1": "Address Line1",
            "Address Line 2": "Address Line2",
            "City": "City",
            "State": "State",
            "ZIP Code": "ZIP",
            "Country": "Country"
        }


def transform_perplexity_response_to_record(
    perplexity_data: Dict[str, Any],
    entity_type: str
) -> Dict[str, Any]:
    """
    Transform Perplexity API response to a flat record for comparison.
    
    Args:
        perplexity_data: Response from Perplexity API (hcp_data or hco_data)
        entity_type: "HCP" or "HCO"
        
    Returns:
        Flat dictionary with field values
    """
    data_key = "hcp_data" if entity_type == "HCP" else "hco_data"
    entity_data = perplexity_data.get(data_key, {})
    
    # Extract first value from each list field
    record = {}
    
    # Name
    names = entity_data.get("Name", [])
    record["Name"] = names[0] if names else "N/A"

    # First Name
    first_name = entity_data.get("First Name", [])
    record["First Name"] = first_name[0] if first_name else "N/A"

    # Last Name
    last_name = entity_data.get("Last Name", [])
    record["Last Name"] = last_name[0] if last_name else "N/A"

    # NPI
    npi = entity_data.get("NPI", [])
    record["NPI"] = npi[0] if npi else "N/A"

    # Degree
    degree = entity_data.get("Degree", [])
    record["Degree"] = degree[0] if degree else "N/A"
    
    # Address Line 1
    addr1 = entity_data.get("Address Line1", entity_data.get("address_line_1", []))
    record["Address Line1"] = addr1[0] if addr1 else "N/A"
    
    # Address Line 2
    addr2 = entity_data.get("Address Line2", entity_data.get("address_line_2", []))
    record["Address Line2"] = addr2[0] if addr2 else ""
    
    # City
    cities = entity_data.get("City", [])
    record["City"] = cities[0] if cities else "N/A"
    
    # State
    states = entity_data.get("State", [])
    record["State"] = states[0] if states else "N/A"
    
    # ZIP
    zips = entity_data.get("ZIP", [])
    record["ZIP"] = zips[0] if zips else "N/A"
    
    # Country (HCO only)
    if entity_type == "HCO":
        countries = entity_data.get("Country", [])
        record["Country"] = countries[0] if countries else "USA"
    
    return record


def transform_current_record_for_comparison(
    record: Any,
    entity_type: str
) -> Dict[str, Any]:
    """
    Transform current record (pandas Series or dict) to comparison format.
    
    Args:
        record: Current record from database
        entity_type: "HCP" or "HCO"
        
    Returns:
        Dictionary with field values matching the field_mapping keys
    """
    if hasattr(record, 'to_dict'):
        record = record.to_dict()
    elif hasattr(record, 'get'):
        pass
    else:
        record = {}
    
    def get_val(key):
        val = record.get(key, "N/A")
        if val is None or (isinstance(val, float) and str(val) == 'nan'):
            return "N/A"
        return str(val).strip() if val else "N/A"
    
    result = {
        "Name": get_val("NAME"),
        "First Name": get_val("FIRST_NAME"),
        "Last Name": get_val("LAST_NAME"),
        "NPI": get_val("NPI"),
        "Degree": get_val("DEGREE"),
        "Address Line1": get_val("ADDRESS1"),
        "Address Line2": get_val("ADDRESS2") or "",
        "City": get_val("CITY"),
        "State": get_val("STATE"),
        "ZIP": get_val("ZIP"),
    }
    
    if entity_type == "HCO":
        result["Country"] = get_val("COUNTRY") or "USA"
    
    return result


def render_confirm_dialog(
    session,
    dialog_placeholder,
    selected_record: Dict[str, Any],
    entity_type: str = "HCP",
    is_new_record: bool = False
) -> bool:
    """
    Render the confirmation dialog for Insert/Update operations.
    
    Args:
        session: Snowflake session
        dialog_placeholder: Streamlit placeholder for the dialog
        selected_record: Current entity record
        entity_type: "HCP" or "HCO"
        is_new_record: Whether this is a new record
        
    Returns:
        True if dialog is shown, False otherwise
    """
    if not st.session_state.get('show_confirm_dialog'):
        return False
    
    approved_cols = st.session_state.get('approved_cols', [])
    proposed_record = st.session_state.get('proposed_record', {})
    
    with dialog_placeholder.container():
        action_text = "insert a new record" if is_new_record else "update the selected fields"
        st.warning(f"Are you sure you want to {action_text}? This action cannot be undone.", icon="⚠️")
        
        # Field mapping for display
        field_to_db = get_field_to_db_mapping(entity_type)
        
        # Table 1: Changes to be applied
        changes_to_display = []
        for field_label, db_col in field_to_db.items():
            if field_label in approved_cols:
                current_val = selected_record.get(db_col, "N/A")
                proposed_val = proposed_record.get(field_label, "N/A")
                changes_to_display.append([field_label, current_val, proposed_val])
        
        if changes_to_display:
            st.markdown("---")
            record_id = selected_record.get('ID', 'NEW')
            st.markdown(f"**Changes to be applied for Account ID: `{record_id}`**")
            
            cols_header = st.columns([2, 2, 2])
            cols_header[0].markdown('**Field**')
            cols_header[1].markdown('**Current Value**')
            cols_header[2].markdown('**Proposed Value**')
            
            for field, current_val, proposed_val in changes_to_display:
                cols_row = st.columns([2, 2, 2])
                cols_row[0].markdown(field)
                cols_row[1].markdown(f'`{current_val}`')
                cols_row[2].markdown(f'<span style="color:#4CAF50; font-weight:bold;">`{proposed_val}`</span>', unsafe_allow_html=True)
            
            st.markdown("---")
        else:
            st.info("No fields were selected for update.")
        
        # Table 2: Other record details (not changing) - only for updates
        if not is_new_record and hasattr(selected_record, 'keys'):
            remaining_details = []
            change_db_cols = [field_to_db.get(col, col) for col in approved_cols] + ["ID"]
            
            for field in selected_record.keys():
                if field not in change_db_cols:
                    remaining_details.append([field, selected_record.get(field)])
            
            if remaining_details:
                st.markdown("**Other profile details of the account (not changing):**")
                remaining_df = pd.DataFrame(remaining_details, columns=["Field", "Value"])
                st.dataframe(remaining_df, hide_index=True, use_container_width=True)
                st.markdown("---")
        
        # Buttons
        col1, col2 = st.columns([1, 1])
        confirm_btn_label = "Yes, Insert" if is_new_record else "Yes, Update"
        
        with col1:
            if st.button(confirm_btn_label, key="confirm_yes"):
                if not approved_cols:
                    st.info("No fields were selected. Please go back and select fields.")
                    st.session_state.show_confirm_dialog = False
                    st.rerun()
                else:
                    spinner_text = "Inserting record..." if is_new_record else "Updating record..."
                    with st.spinner(spinner_text):
                        try:
                            if is_new_record:
                                success, new_id, message = insert_record(
                                    session=session,
                                    entity_type=entity_type,
                                    approved_cols=approved_cols,
                                    proposed_record=proposed_record
                                )
                                if success:
                                    # Update selected_record_df with the new ID so affiliation insert can work
                                    _update_selected_record_after_insert(entity_type, new_id, proposed_record, approved_cols)
                                    
                                    st.session_state.show_popup = True
                                    st.session_state.popup_message_info = {
                                        'type': 'insert_success',
                                        'id': new_id,
                                        'message': message
                                    }
                            else:
                                record_id = selected_record.get('ID')
                                success, message = update_record(
                                    session=session,
                                    entity_type=entity_type,
                                    record_id=record_id,
                                    approved_cols=approved_cols,
                                    proposed_record=proposed_record
                                )
                                if success:
                                    st.session_state.show_popup = True
                                    st.session_state.popup_message_info = {
                                        'type': 'update_success',
                                        'id': record_id,
                                        'message': message
                                    }
                            
                            if not success:
                                st.error(message)
                                st.stop()  # Stop to see the error
                        except Exception as e:
                            import traceback
                            st.error(f"An error occurred: {e}")
                            st.code(traceback.format_exc())
                            st.stop()  # Stop to see the error
                        
                        st.session_state.show_confirm_dialog = False
                        st.rerun()
        
        with col2:
            if st.button("Cancel", key="confirm_cancel"):
                st.session_state.show_confirm_dialog = False
                st.rerun()
    
    return True
