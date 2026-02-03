import streamlit as st
import pandas as pd
from typing import List, Tuple, Any, Optional
from components.n_column_table_layout import n_column_table_layout


def get_safe_value(record, key: str, fallback_prefix: str = None) -> str:
    """
    Safely get a value from a record (dict or pandas Series).
    
    Args:
        record: Dictionary or pandas Series
        key: Key to look up
        fallback_prefix: Optional prefix to try if key not found (e.g., "HCO_")
    
    Returns:
        String value or 'N/A'
    """
    value = None
    
    if hasattr(record, 'get'):
        value = record.get(key)
    elif hasattr(record, '__getitem__'):
        try:
            value = record[key]
        except (KeyError, IndexError):
            pass
    
    # Try fallback with prefix if value is None/NaN
    if (value is None or (isinstance(value, float) and pd.isna(value))) and fallback_prefix:
        fallback_key = f"{fallback_prefix}{key}"
        if hasattr(record, 'get'):
            value = record.get(fallback_key)
        elif hasattr(record, '__getitem__'):
            try:
                value = record[fallback_key]
            except (KeyError, IndexError):
                pass
    
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 'N/A'
    
    str_value = str(value).strip()
    return str_value if str_value else 'N/A'

def render_address_details(
    record: Any,
    entity_type: str = "HCP",
    title: str = None
):
    """
    Render address details in a two-column layout.
    
    Args:
        record: Dictionary or pandas Series containing the data
        entity_type: "HCP" or "HCO" - determines field configuration
        title: Optional custom title
    """
    fallback_prefix = "HCO_" if entity_type == "HCO" else None
    
    if entity_type == "HCO":
        default_title = "Current HCO Address Details"
        left_fields = [
            ("Address Line 1", "ADDRESS1"),
            ("Address Line 2", "ADDRESS2"),
            ("City", "CITY"),
        ]
        right_fields = [
            ("State", "STATE"),
            ("ZIP", "ZIP"),
            ("Country", "COUNTRY"),
        ]
        # Build header text
        hco_id = get_safe_value(record, 'ID', fallback_prefix)
        hco_name = get_safe_value(record, 'NAME', fallback_prefix)
        header_text = f"ID: {hco_id} - {hco_name}"
    else:
        default_title = "Current Demographic Details"
        left_fields = [
            ("Prefix", "PREFIX"),
            ("First Name", "FIRST_NM"),
            ("Middle Name", "MIDDLE_NM"),
            ("Last Name", "LAST_NM"),
            ("Suffix", "SUFFIX"),
            ("Degree", "DEGREE"),
        ]
        right_fields = [
            ("Address Line 1", "ADDRESS1"),
            ("Address Line 2", "ADDRESS2"),
            ("City", "CITY"),
            ("State", "STATE"),
            ("ZIP", "ZIP"),
            ("Country", "COUNTRY"),
        ]
        # Build header text
        hcp_id = get_safe_value(record, 'ID')
        hcp_name = get_safe_value(record, 'NAME')
        header_text = f"ID: {hcp_id} - {hcp_name}"
    
    n_column_table_layout(
        record=record,
        columns_config=[left_fields, right_fields],
        title=title or default_title,
        header_text=header_text,
        fallback_prefix=fallback_prefix,
        show_border=True
    )


def render_affiliation_details(
    record: Any,
    session,
    entity_type: str = "HCP",
    title: str = None
):
    """
    Render primary affiliation details in a two-column layout.
    
    Args:
        record: Dictionary or pandas Series containing the data
        session: Snowflake session for querying affiliation data
        entity_type: "HCP" or "HCO" - determines field configuration
        title: Optional custom title
    """
    default_title = "Primary HCO Affiliation Details"
    
    st.subheader(title or default_title)
    
    with st.container(border=True):
        hco_col1, hco_col2 = st.columns(2)
        
        if entity_type == "HCP":
            hco_id_val = "N/A"
            hco_name_val = "N/A"
            hco_npi_val = "N/A"
            
            # primary_hco_id = record.get("PRIMARY_AFFL_HCO_ACCOUNT_ID") if hasattr(record, 'get') else None
            # hcp_npi = record.get("NPI") if hasattr(record, 'get') else None
            
            try:
                # if pd.notna(primary_hco_id) and primary_hco_id is not None:
                #     hco_id_val = str(primary_hco_id)
                #     hco_query = session.sql(f"SELECT NAME, NPI FROM HCO WHERE ID = '{primary_hco_id}'").collect()
                #     if hco_query:
                #         hco_name_val = hco_query[0].NAME if hco_query[0].NAME else "N/A"
                #         hco_npi_val = str(hco_query[0].NPI) if hco_query[0].NPI else "N/A"
                # else:
                # aff_query = session.sql(f"SELECT HCO_ID, HCO_NAME FROM HCP_HCO_AFFILIATION WHERE HCP_NPI = '{hcp_npi}' LIMIT 1").collect()
                # if aff_query:
                #     hco_id_val = str(aff_query[0].HCO_ID) if aff_query[0].HCO_ID else "N/A"
                #     hco_name_val = aff_query[0].HCO_NAME if aff_query[0].HCO_NAME else "N/A"

                hco_id_val = record.get("PRIMARY_AFFL_HCO_ACCOUNT_ID") if record.get("PRIMARY_AFFL_HCO_ACCOUNT_ID") is not None else "N/A"
                hco_name_val = record.get("HCO_NAME") if record.get("HCO_NAME") is not None else "N/A"
            except:
                pass
            
            hco_col1.markdown(f'<div class="detail-key">HCO ID:</div><div class="detail-value">{hco_id_val}</div>', unsafe_allow_html=True)
            hco_col2.markdown(f'<div class="detail-key">HCO NPI:</div><div class="detail-value">{hco_npi_val}</div>', unsafe_allow_html=True)
            hco_col1.markdown(f'<div class="detail-key">HCO Name:</div><div class="detail-value">{hco_name_val}</div>', unsafe_allow_html=True)
        
        else:  # HCO
            primary_hco_id_raw = record.get("PRIMARY_AFFL_ACCOUNT_ID")
            primary_hco_id = str(primary_hco_id_raw) if primary_hco_id_raw is not None and pd.notna(primary_hco_id_raw) else "N/A"
            
            primary_hco_name_raw = record.get("OUTLET_NAME")
            primary_hco_name = str(primary_hco_name_raw) if primary_hco_name_raw is not None and pd.notna(primary_hco_name_raw) else "N/A"
            
            hco_col1.markdown(
                f'<div class="detail-key">Parent ID:</div><div class="detail-value">{primary_hco_id}</div>',
                unsafe_allow_html=True
            )
            
            hco_col2.markdown(
                f'<div class="detail-key">Parent HCO NPI:</div><div class="detail-value">N/A</div>',
                unsafe_allow_html=True
            )
            
            hco_col1.markdown(
                f'<div class="detail-key">Parent Name:</div><div class="detail-value">{primary_hco_name}</div>',
                unsafe_allow_html=True
            )
