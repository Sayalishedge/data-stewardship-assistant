import pandas as pd
import streamlit as st
from typing import Optional


def get_hcp_affiliations_from_db(session, hcp_npi: str) -> pd.DataFrame:
    """
    Query HCP affiliations from the HCP_HCO_AFFILIATION table.
    
    Args:
        session: Snowflake session
        hcp_npi: NPI of the HCP
        
    Returns:
        DataFrame with affiliation records
    """
    if not hcp_npi or pd.isna(hcp_npi):
        return pd.DataFrame()
    
    try:
        query = f"SELECT * FROM HCP_HCO_AFFILIATION WHERE HCP_NPI = '{hcp_npi}'"
        return session.sql(query).to_pandas()
    except Exception as e:
        st.warning(f"Could not fetch HCP affiliations: {e}")
        return pd.DataFrame()


def get_hco_affiliations_from_db(session, hco_id: str) -> pd.DataFrame:
    """
    Query HCO affiliations from the OUTLET_HCO_AFFILIATION table.
    Also joins with HCO table to get outlet details if not in affiliation table.
    
    Args:
        session: Snowflake session
        hco_id: ID of the HCO
        
    Returns:
        DataFrame with affiliation records
    """
    if not hco_id or pd.isna(hco_id):
        return pd.DataFrame()
    
    try:
        # First try to get data from OUTLET_HCO_AFFILIATION
        query = f"SELECT * FROM OUTLET_HCO_AFFILIATION WHERE HCO_ID = '{hco_id}'"
        df = session.sql(query).to_pandas()
        
        # If outlet details are empty, try to join with HCO table to get outlet info
        if not df.empty:
            # Check if OUTLET_NAME is empty for all rows
            if df['OUTLET_NAME'].isna().all() or (df['OUTLET_NAME'] == '').all():
                # Join with HCO table to get outlet details
                query_with_join = f"""
                    SELECT 
                        a.HCO_ID,
                        a.OUTLET_ID,
                        h.NAME as OUTLET_NAME,
                        h.ADDRESS1 as OUTLET_ADDRESS1,
                        h.ADDRESS2 as OUTLET_ADDRESS2,
                        h.CITY as OUTLET_CITY,
                        h.STATE as OUTLET_STATE,
                        h.ZIP as OUTLET_ZIP,
                        h.COUNTRY as OUTLET_COUNTRY
                    FROM OUTLET_HCO_AFFILIATION a
                    LEFT JOIN HCO h ON a.OUTLET_ID = h.ID
                    WHERE a.HCO_ID = '{hco_id}'
                """
                df = session.sql(query_with_join).to_pandas()
        
        return df
    except Exception as e:
        st.warning(f"Could not fetch HCO affiliations: {e}")
        return pd.DataFrame()


def get_affiliations_from_db(session, entity_type: str, record: dict) -> pd.DataFrame:
    """
    Get affiliations from database based on entity type.
    
    Args:
        session: Snowflake session
        entity_type: "HCP" or "HCO"
        record: Entity record containing NPI or ID
        
    Returns:
        DataFrame with affiliation records
    """
    if entity_type == "HCP":
        npi = record.get("NPI", record.get("npi", ""))
        return get_hcp_affiliations_from_db(session, str(npi) if npi else "")
    else:
        hco_id = record.get("ID", record.get("HCO_ID", ""))
        return get_hco_affiliations_from_db(session, str(hco_id) if hco_id else "")
