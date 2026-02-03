import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any
from snowflake.snowpark.functions import col


def check_affiliation_exists(session, hcp_npi: str, hco_id: str) -> bool:
    """
    Check if an affiliation record already exists in HCP_HCO_AFFILIATION table.
    """
    if not hcp_npi or not hco_id:
        return False
    
    try:
        query = f"""
            SELECT COUNT(*) as CNT 
            FROM HCP_HCO_AFFILIATION 
            WHERE HCP_NPI = '{hcp_npi}' AND HCO_ID = '{hco_id}'
        """
        result = session.sql(query).collect()
        return result[0].CNT > 0 if result else False
    except Exception as e:
        st.warning(f"Error checking affiliation: {e}")
        return False


def insert_hcp_affiliation_record(
    session,
    hcp_id: str,
    hcp_npi: str,
    hco_data: Dict[str, Any],
    generate_new_id: bool = False
) -> Optional[int]:
    """
    Insert a new affiliation record into HCP_HCO_AFFILIATION table.
    
    Returns:
        If generate_new_id is True: Returns the new HCO_ID on success, None on failure
        If generate_new_id is False: Returns True on success, False on failure
    """
    try:
        hco_id = hco_data.get('HCO ID', hco_data.get('HCO_ID', ''))
        
        # For AI-generated records, generate a new HCO_ID
        # Only consider numeric IDs when calculating MAX to avoid VARCHAR conversion errors
        if generate_new_id or str(hco_id).startswith('ai_generated_') or not hco_id:
            max_id_result = session.sql("""
                SELECT COALESCE(MAX(TRY_TO_NUMBER(HCO_ID)), 0) AS MAX_ID 
                FROM HCP_HCO_AFFILIATION 
                WHERE TRY_TO_NUMBER(HCO_ID) IS NOT NULL
            """).collect()
            max_id = max_id_result[0].MAX_ID if max_id_result[0].MAX_ID else 0
            hco_id = str(int(max_id) + 1)
        
        hco_name = hco_data.get('HCO NAME', hco_data.get('HCO_Name', ''))
        hco_address1 = hco_data.get('HCO ADDRESS', hco_data.get('HCO_Address1', ''))
        hco_city = hco_data.get('HCO CITY', hco_data.get('HCO_City', ''))
        hco_state = hco_data.get('HCO STATE', hco_data.get('HCO_State', ''))
        hco_zip = hco_data.get('HCO ZIP', hco_data.get('HCO_ZIP', ''))
        
        def clean_val(val):
            if val is None:
                return ''
            return str(val).replace("'", "''")
        
        # HCP_HCO_AFFILIATION table columns include: HCP_ACCT_ID, HCP_NPI, HCO_ID, HCO_NAME, HCO_ADDRESS1, HCO_CITY, HCO_STATE, HCO_ZIP
        # HCO_ID is VARCHAR
        insert_sql = f"""
            INSERT INTO HCP_HCO_AFFILIATION (HCP_ACCT_ID, HCP_NPI, HCO_ID, HCO_NAME, HCO_ADDRESS1, HCO_CITY, HCO_STATE, HCO_ZIP)
            VALUES (
                {clean_val(hcp_id) if hcp_id else 'NULL'},
                '{clean_val(hcp_npi)}',
                '{clean_val(hco_id)}',
                '{clean_val(hco_name)}',
                '{clean_val(hco_address1)}',
                '{clean_val(hco_city)}',
                '{clean_val(hco_state)}',
                '{clean_val(hco_zip)}'
            )
        """
        session.sql(insert_sql).collect()
        
        if generate_new_id or str(hco_data.get('HCO ID', hco_data.get('HCO_ID', ''))).startswith('ai_generated_'):
            return hco_id
        return True
    except Exception as e:
        st.error(f"Error inserting affiliation record: {e}")
        return None if generate_new_id else False


def insert_hco_affiliation_record(
    session,
    hco_id: str,
    outlet_data: Dict[str, Any],
    generate_new_id: bool = False
) -> Optional[int]:
    """
    Insert a new affiliation record into OUTLET_HCO_AFFILIATION table.
    
    Args:
        session: Snowflake session
        hco_id: ID of the parent HCO
        outlet_data: The outlet/affiliated HCO data
        generate_new_id: Whether to generate a new OUTLET_ID
        
    Returns:
        If generate_new_id is True: Returns the new OUTLET_ID on success, None on failure
        If generate_new_id is False: Returns True on success, False on failure
    """
    try:
        outlet_id = outlet_data.get('HCO ID', outlet_data.get('HCO_ID', outlet_data.get('OUTLET_ID', '')))
        
        # For AI-generated records, generate a new OUTLET_ID
        if generate_new_id or str(outlet_id).startswith('ai_generated_') or not outlet_id:
            max_id_result = session.sql("SELECT COALESCE(MAX(OUTLET_ID), 0) AS MAX_ID FROM OUTLET_HCO_AFFILIATION").collect()
            max_id = max_id_result[0].MAX_ID if max_id_result[0].MAX_ID else 0
            outlet_id = int(max_id) + 1
        
        outlet_name = outlet_data.get('HCO NAME', outlet_data.get('HCO_Name', outlet_data.get('OUTLET_NAME', '')))
        outlet_address1 = outlet_data.get('HCO ADDRESS', outlet_data.get('HCO_Address1', outlet_data.get('OUTLET_ADDRESS1', '')))
        outlet_city = outlet_data.get('HCO CITY', outlet_data.get('HCO_City', outlet_data.get('OUTLET_CITY', '')))
        outlet_state = outlet_data.get('HCO STATE', outlet_data.get('HCO_State', outlet_data.get('OUTLET_STATE', '')))
        outlet_zip = outlet_data.get('HCO ZIP', outlet_data.get('HCO_ZIP', outlet_data.get('OUTLET_ZIP', '')))
        
        def clean_val(val):
            if val is None:
                return ''
            return str(val).replace("'", "''")
        
        insert_sql = f"""
            INSERT INTO OUTLET_HCO_AFFILIATION (HCO_ID, OUTLET_ID, OUTLET_NAME, OUTLET_ADDRESS1, OUTLET_CITY, OUTLET_STATE, OUTLET_ZIP)
            VALUES (
                '{clean_val(hco_id)}',
                {outlet_id},
                '{clean_val(outlet_name)}',
                '{clean_val(outlet_address1)}',
                '{clean_val(outlet_city)}',
                '{clean_val(outlet_state)}',
                '{clean_val(outlet_zip)}'
            )
        """
        session.sql(insert_sql).collect()
        
        if generate_new_id or str(outlet_data.get('HCO ID', outlet_data.get('HCO_ID', ''))).startswith('ai_generated_'):
            return outlet_id
        return True
    except Exception as e:
        st.error(f"Error inserting outlet affiliation record: {e}")
        return None if generate_new_id else False


def update_hcp_primary_affiliation(session, hcp_id: str, hco_id: int) -> bool:
    """
    Update the PRIMARY_AFFL_HCO_ACCOUNT_ID in the NPI table for an HCP.
    
    Args:
        session: Snowflake session
        hcp_id: ID of the HCP record
        hco_id: ID of the HCO to set as primary
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        npi_table = session.table("NPI")
        update_assignments = {"PRIMARY_AFFL_HCO_ACCOUNT_ID": hco_id}
        update_result = npi_table.update(update_assignments, col("ID") == hcp_id)
        return update_result.rows_updated > 0
    except Exception as e:
        st.error(f"Error updating primary affiliation: {e}")
        return False


def update_hco_primary_affiliation(session, hco_id: str, outlet_id: int) -> bool:
    """
    Update the PRIMARY_AFFL_ACCOUNT_ID in the HCO table.
    
    Args:
        session: Snowflake session
        hco_id: ID of the HCO record
        outlet_id: ID of the outlet/parent HCO to set as primary
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        hco_table = session.table("HCO")
        update_assignments = {"PRIMARY_AFFL_ACCOUNT_ID": outlet_id}
        update_result = hco_table.update(update_assignments, col("ID") == hco_id)
        return update_result.rows_updated > 0
    except Exception as e:
        st.error(f"Error updating primary affiliation: {e}")
        return False


def set_primary_affiliation(
    session,
    entity_type: str,
    selected_record: Dict[str, Any],
    hco_data: Dict[str, Any],
    hco_id: str,
    is_new_record: bool = False
) -> tuple:
    """
    Set the primary affiliation for an entity (HCP or HCO).
    
    Args:
        session: Snowflake session
        entity_type: "HCP" or "HCO"
        selected_record: The entity record
        hco_data: The HCO affiliation data
        hco_id: The HCO ID to set as primary
        is_new_record: Whether this is a new record
        
    Returns:
        Tuple of (success: bool, final_hco_id: int/str, message: str)
    """
    selected_id = selected_record.get('ID', '')
    
    # Check if AI-generated
    is_ai_generated = (
        str(hco_id).startswith('ai_generated_') or 
        hco_data.get('SOURCE') == 'Generated by AI' or
        hco_data.get('SOURCE', '').lower() == 'generated by ai'
    )
    
    final_hco_id = hco_id
    
    if entity_type == "HCP":
        hcp_npi = selected_record.get('NPI', '')
        
        # For AI-generated HCO, first insert the affiliation record
        if is_ai_generated and hco_data:
            result = insert_hcp_affiliation_record(session, selected_id, hcp_npi, hco_data, generate_new_id=True)
            if result is not None:
                final_hco_id = result
                st.toast(f"Affiliation record created with HCO ID: {final_hco_id}", icon="✅")
            else:
                return (False, None, "Failed to create affiliation record.")
        elif is_new_record and hco_data:
            if not check_affiliation_exists(session, hcp_npi, hco_id):
                success = insert_hcp_affiliation_record(session, selected_id, hcp_npi, hco_data)
                if success:
                    st.toast("Affiliation record created successfully!", icon="✅")
        
        # Update primary affiliation in NPI table
        if update_hcp_primary_affiliation(session, selected_id, final_hco_id):
            return (True, final_hco_id, f"Primary affiliation updated to HCO ID: {final_hco_id}")
        else:
            return (False, None, "Could not update the primary affiliation.")
    
    else:  # HCO
        # For AI-generated HCO affiliations, first insert into OUTLET_HCO_AFFILIATION
        if is_ai_generated and hco_data:
            result = insert_hco_affiliation_record(session, selected_id, hco_data, generate_new_id=True)
            if result is not None:
                final_hco_id = result
                st.toast(f"Outlet affiliation record created with OUTLET ID: {final_hco_id}", icon="✅")
            else:
                return (False, None, "Failed to create outlet affiliation record.")
        
        # Update PRIMARY_AFFL_ACCOUNT_ID in HCO table
        if update_hco_primary_affiliation(session, selected_id, final_hco_id):
            return (True, final_hco_id, f"Primary affiliation updated to ID: {final_hco_id}")
        else:
            return (False, None, "Could not update the primary affiliation.")
