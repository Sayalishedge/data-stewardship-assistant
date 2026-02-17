import streamlit as st
from components.table import render_table
from components.detail_layout import render_address_details, render_affiliation_details
from utils.snowflake import execute_sql

def display_interpretation(content: dict):
    if not content:
        return
    user_query = content.get("user_query")
    st.markdown(f'You searched : "{user_query}"')

    if "text" in content and content.get("text"):
        interpretation_full_text = content.get("text")
        prefix_to_remove = "This is our interpretation of your question:"
        interpretation_clean = interpretation_full_text.replace(
            prefix_to_remove, ""
        ).strip()
        st.markdown(
            f'This is our interpretation of your question : "{interpretation_clean}"'
        )

def display_search_results():
    # Custom CSS for the detail section (from reference code)
    st.markdown("""
        <style>
            .detail-key { font-weight: bold; color: #4F8BE7; margin-top: 0.5rem;}
            .detail-value { padding-bottom: 0.5rem; }
            div[data-testid="stHorizontalBlock"]:has(div.cell-content),
            div[data-testid="stHorizontalBlock"]:has(div.hco-cell) { border-bottom: 1px solid #e6e6e6; }
            div[data-testid="stHorizontalBlock"]:has(div.cell-content):hover,
            div[data-testid="stHorizontalBlock"]:has(div.hco-cell):hover { background-color: #f8f9fa; }
            .cell-content, .hco-cell { padding: 0.3rem 0.5rem; font-size: 14px; display: flex; align-items: center; height: 48px; }
            .report-header, .hco-header { font-weight: bold; color: #4f4f4f; padding: 0.5rem; }
            .hco-header { border-bottom: 2px solid #ccc; }
        </style>
    """, unsafe_allow_html=True)
    
    if len(st.session_state.messages) > 0:
        assistant_messages = [msg for msg in st.session_state.messages if msg["role"] == "assistant"]
        latest_assistant_response = assistant_messages[-1]
        if assistant_messages:
            st.markdown("---")
            display_interpretation(content=latest_assistant_response["content"])

            # 1. Search Results Table (Full Width)
            search_response_container = st.container(border=True)
            with search_response_container:
                st.subheader("Search Results")
                if "sql" in latest_assistant_response.get("content") and latest_assistant_response.get("content").get("sql") is not None:
                    # Only execute SQL if results_df is not already cached
                    # This prevents duplicate records when returning from enrichment page
                    if st.session_state.get("results_df") is None:
                        row_data_df = execute_sql(session=st.session_state.get("session"), query=latest_assistant_response.get("content").get("sql"), return_pandas=True)
                        if not row_data_df.empty:
                            st.session_state.results_df = row_data_df
                    
                    row_data_df = st.session_state.get("results_df")
                    if row_data_df is not None and not row_data_df.empty:
                        render_table(
                            col_sizes_tuple=(0.8, 0.8, 1.2, 1, 2, 1, 0.5),
                            col_header_names_list=["Select", "ID", "Name", "NPI", "Address", "City", "State"],
                            row_data=row_data_df,
                            title = "Please select a record from the table to proceed:"
                        )
                    else:
                        st.info("We couldn't find any records matching your search.", icon="ℹ️")
                        st.markdown("")
                        if st.button("🔍 Still want to proceed with Web Search?", type="primary"):
                            entity_type = st.session_state.get("assistant_type", "HCP")
                            st.session_state.web_search_query = st.session_state.get("last_prompt")
                            # Create a default empty record for enrichment
                            st.session_state.empty_record_for_enrichment = {
                                'ID': 'N/A',
                                'NAME': '',
                                'NPI': '',
                                'ADDRESS1': '',
                                'ADDRESS2': '',
                                'CITY': '',
                                'STATE': '',
                                'ZIP': '',
                                'COUNTRY': '',
                                'PRIMARY_AFFL_HCO_ACCOUNT_ID': None,
                                'PRIMARY_AFFL_ACCOUNT_ID': None
                            }
                            st.session_state[f"selected_{entity_type.lower()}_id"] = 'empty_record'
                            st.session_state.current_view = "enrichment_page"
                            st.rerun()

            # 2. Selected Record Details (Only appears when a record is selected)
            entity_type = st.session_state.get("assistant_type", "HCP")
            selected_id_key = f"selected_{entity_type.lower()}_id"
            selected_id = st.session_state.get(selected_id_key)
            results_df = st.session_state.get("results_df")
            
            if selected_id and results_df is not None and not results_df.empty:
                selected_record_df = results_df[results_df["ID"] == selected_id]
                
                if not selected_record_df.empty:
                    selected_record = selected_record_df.iloc[0]
                    
                    # Two-column layout for details sections
                    details_col_left, details_col_right = st.columns(2)
                    
                    with details_col_left:
                        render_address_details(selected_record, entity_type=entity_type)
                    
                    with details_col_right:
                        render_affiliation_details(
                            selected_record, 
                            session=st.session_state.get("session"),
                            entity_type=entity_type
                        )
                    
                    st.divider()
                    
                    # Enrich Button
                    button_col, _ = st.columns([0.2, 0.8])
                    with button_col:
                        if st.button("Enrich with AI Assistant 🚀", type="primary"):
                            st.session_state.current_view = "enrichment_page"
                            st.rerun()