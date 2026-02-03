import streamlit as st
import pandas as pd
from typing import List, Tuple, Any


def get_safe_value(record, key: str, fallback_prefix: str = None) -> str:
    """
    Safely get a value from a record (dict or pandas Series).
    """
    value = None
    
    if hasattr(record, 'get'):
        value = record.get(key)
    elif hasattr(record, '__getitem__'):
        try:
            value = record[key]
        except (KeyError, IndexError):
            pass
    
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


def n_column_table_layout(
    record: Any,
    columns_config: List[List[Tuple[str, str]]],
    title: str = None,
    header_text: str = None,
    fallback_prefix: str = None,
    show_border: bool = True
):
    """
    Render a multi-column key-value layout for displaying record details.
    
    Args:
        record: Dictionary or pandas Series containing the data
        columns_config: List of column configurations, where each column is a list of (label, key) tuples
                       Example: [
                           [("Address Line 1", "ADDRESS1"), ("City", "CITY")],  # Left column
                           [("State", "STATE"), ("ZIP", "ZIP")]                  # Right column
                       ]
        title: Optional title/subheader for the section
        header_text: Optional header text to display at the top (e.g., "ID: 123 - Name")
        fallback_prefix: Optional prefix to try if key not found (e.g., "HCO_")
        show_border: Whether to wrap in a bordered container
    """
    if title:
        st.subheader(title)
    
    container = st.container(border=show_border) if show_border else st.container()
    
    with container:
        if header_text:
            st.markdown(f'**{header_text}**', unsafe_allow_html=True)
            st.markdown("<hr style='margin-top: 0; margin-bottom: 0; border-top: 1px solid #ccc;'>", unsafe_allow_html=True)
        
        # Create columns based on the number of column configs
        num_columns = len(columns_config)
        cols = st.columns(num_columns)
        
        # Render each column
        for col_idx, (col, field_list) in enumerate(zip(cols, columns_config)):
            for label, key in field_list:
                value = get_safe_value(record, key, fallback_prefix)
                col.markdown(
                    f'<div class="detail-key">{label}:</div>'
                    f'<div class="detail-value">{value}</div>',
                    unsafe_allow_html=True
                )
