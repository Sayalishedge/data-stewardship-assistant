import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from snowflake.snowpark.functions import col


# Field mapping from display labels to database column names
# Keys match the col_name values from comparison_table field_mapping
HCP_FIELD_MAPPING = {
    "Name": "NAME",
    "First Name": "FIRST_NM",
    "Last Name": "LAST_NM",
    "NPI": "NPI",
    "Degree": "DEGREE",
    "Address Line1": "ADDRESS1",
    "Address Line 1": "ADDRESS1",
    "Address Line2": "ADDRESS2",
    "Address Line 2": "ADDRESS2",
    "City": "CITY",
    "State": "STATE",
    "ZIP": "ZIP",
    "ZIP Code": "ZIP"
}

HCO_FIELD_MAPPING = {
    "Name": "NAME",
    "Address Line1": "ADDRESS1",
    "Address Line 1": "ADDRESS1",
    "Address Line2": "ADDRESS2",
    "Address Line 2": "ADDRESS2",
    "City": "CITY",
    "State": "STATE",
    "ZIP": "ZIP",
    "ZIP Code": "ZIP",
    "Country": "COUNTRY"
}


def get_field_to_db_mapping(entity_type: str) -> Dict[str, str]:
    """Get the field to database column mapping for an entity type."""
    return HCP_FIELD_MAPPING if entity_type == "HCP" else HCO_FIELD_MAPPING


def get_table_info(entity_type: str) -> Tuple[str, str, str]:
    """Get database, schema, and table name for an entity type."""
    DATABASE = "CORTEX_ANALYST_HCK"
    SCHEMA = "PUBLIC"
    TABLE_NAME = "NPI" if entity_type == "HCP" else "HCO"
    return DATABASE, SCHEMA, TABLE_NAME


def insert_record(
    session,
    entity_type: str,
    approved_cols: List[str],
    proposed_record: Dict[str, Any]
) -> Tuple[bool, Optional[int], str]:
    """
    Insert a new record into the database.
    
    Args:
        session: Snowflake session
        entity_type: "HCP" or "HCO"
        approved_cols: List of approved field names (these are the col_name values from field_mapping)
        proposed_record: Dictionary with proposed values
        
    Returns:
        Tuple of (success, new_id, message)
    """
    if not approved_cols:
        return (False, None, "No fields were selected for insert.")
    
    try:
        db_column_map = get_field_to_db_mapping(entity_type)
        DATABASE, SCHEMA, TABLE_NAME = get_table_info(entity_type)
        
        # Build assignments from approved columns
        assignments = {}
        columns_list = []
        
        for col_name in approved_cols:
            db_col_name = db_column_map.get(col_name)
            if db_col_name:
                new_value = proposed_record.get(col_name)
                if hasattr(new_value, 'item'):
                    new_value = new_value.item()
                # Avoid duplicate columns
                if db_col_name not in columns_list:
                    assignments[db_col_name] = new_value
                    columns_list.append(db_col_name)
        
        if not columns_list:
            return (False, None, f"No valid columns found for insert. Approved: {approved_cols}")
        
        # Generate new ID based on entity type
        # HCP (NPI table) uses numeric IDs, HCO uses string IDs like 'SHA_000006494'
        if entity_type == "HCP":
            max_id_result = session.sql(
                f'SELECT COALESCE(MAX(ID), 0) AS MAX_ID FROM "{DATABASE}"."{SCHEMA}"."{TABLE_NAME}"'
            ).collect()
            max_id = max_id_result[0].MAX_ID if max_id_result[0].MAX_ID else 0
            new_id = int(max_id) + 1
        else:
            # HCO uses string IDs with format like 'SHA_XXXXXXXXX'
            max_id_result = session.sql(
                f"""SELECT MAX(CAST(REPLACE(ID, 'SHA_', '') AS INTEGER)) AS MAX_NUM 
                    FROM "{DATABASE}"."{SCHEMA}"."{TABLE_NAME}" 
                    WHERE ID LIKE 'SHA_%'"""
            ).collect()
            max_num = max_id_result[0].MAX_NUM if max_id_result[0].MAX_NUM else 0
            new_id = f"AISEARCH_{str(int(max_num) + 1).zfill(9)}"
        
        # Add ID to columns and assignments
        columns_list.insert(0, "ID")
        assignments["ID"] = new_id
        
        # Build INSERT SQL
        col_names = ", ".join(columns_list)
        col_values_list = []
        for c in columns_list:
            val = assignments.get(c)
            if c == "ID" and entity_type == "HCP":
                col_values_list.append(str(val))  # Numeric, no quotes for HCP
            elif val is not None and str(val).strip() != "" and str(val) != "N/A":
                # Escape single quotes in string values
                escaped_val = str(val).replace("'", "''")
                # Handle COUNTRY column - convert full name to 2-letter code
                if c == "COUNTRY":
                    country_map = {"USA": "US", "UNITED STATES": "US", "UNITED STATES OF AMERICA": "US"}
                    escaped_val = country_map.get(escaped_val.upper(), escaped_val[:2])
                col_values_list.append(f"'{escaped_val}'")
            else:
                col_values_list.append("NULL")
        
        col_values = ", ".join(col_values_list)
        insert_sql = f'INSERT INTO "{DATABASE}"."{SCHEMA}"."{TABLE_NAME}" ({col_names}) VALUES ({col_values})'
        
        # Execute the insert
        session.sql(insert_sql).collect()
        
        cols_str = ", ".join(columns_list)
        message = f"New record inserted successfully with ID: {new_id}. Columns: {cols_str}."
        return (True, new_id, message)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return (False, None, f"Error inserting record: {str(e)}\n{error_details}")


def update_record(
    session,
    entity_type: str,
    record_id: Any,
    approved_cols: List[str],
    proposed_record: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Update an existing record in the database.
    
    Args:
        session: Snowflake session
        entity_type: "HCP" or "HCO"
        record_id: ID of the record to update
        approved_cols: List of approved field names
        proposed_record: Dictionary with proposed values
        
    Returns:
        Tuple of (success, message)
    """
    if not approved_cols:
        return (False, "No fields were selected for update.")
    
    try:
        db_column_map = get_field_to_db_mapping(entity_type)
        DATABASE, SCHEMA, TABLE_NAME = get_table_info(entity_type)
        
        # Build assignments from approved columns
        assignments = {}
        columns_list = []
        
        for col_name in approved_cols:
            db_col_name = db_column_map.get(col_name)
            if db_col_name:
                new_value = proposed_record.get(col_name)
                if hasattr(new_value, 'item'):
                    new_value = new_value.item()
                # Avoid duplicate columns
                if db_col_name not in columns_list:
                    assignments[db_col_name] = new_value
                    columns_list.append(db_col_name)
        
        if not columns_list:
            return (False, f"No valid columns found for update. Approved: {approved_cols}")
        
        # Perform update
        target_table = session.table(f'"{DATABASE}"."{SCHEMA}"."{TABLE_NAME}"')
        update_result = target_table.update(assignments, col("ID") == record_id)
        
        if update_result.rows_updated > 0:
            cols_str = ", ".join(columns_list)
            message = f"Record for ID: {record_id} updated successfully. Changed columns: {cols_str}."
            return (True, message)
        else:
            return (False, f"Record for ID {record_id} was not found for update.")
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return (False, f"Error updating record: {str(e)}\n{error_details}")
