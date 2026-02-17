import streamlit as st
import pandas as pd
from streamlit.components.v1 import html
from utils.snowflake import get_connection_config_from_secrets, get_snowflake_session_from_dict
from utils.session import init_data_steward_session_state, reset_search_session_state
from utils.cortex import call_cortex_analyst, parse_analyst_response
from utils.ui import display_search_results
from components.enrichment_page import render_enrichment_page

# Overall App Config
st.set_page_config(
    page_title="Data Stewardship Assistant",
    layout="wide",
)

# Initialize session state BEFORE any other logic
if "assistant_type" not in st.session_state:
    st.session_state["assistant_type"] = "HCP"
    init_data_steward_session_state("HCP")

# Ensure current_view is always initialized
if "current_view" not in st.session_state:
    st.session_state["current_view"] = "main"

session = get_snowflake_session_from_dict(_config=get_connection_config_from_secrets())
st.session_state["session"] = session

# =========================================== #
# Overall App Layout - Sidebar + Main Content #
# =========================================== #

# Sidebar Layout
with st.sidebar:
    st.header("🤖 Data Stewardship Assistant")
    st.info("This app is the single source of truth for Data Stewards, leveraging Snowflake Cortex AI & Perplexity to seamlessly consolidate the latest demographic and affiliation updates from multiple web sources and the Enterprise Data Warehouse, ensuring master data accuracy.")

    options = {
        "HCP Assistant": "HCP",
        "HCO Assistant": "HCO",
    }

    label = st.selectbox(
        "Select a type of assistant",
        options.keys(),
        index=0,
        placeholder="Select an option",
    )
    value = options[label] if label else None

    if value is not None and value != st.session_state.get("assistant_type"):
        st.session_state["assistant_type"] = value
        init_data_steward_session_state(value, force_reset=True)
        st.rerun()

    # Custom CSS to hide the scrollbar in the sidebar
    st.markdown("""
        <style>
            [data-testid = "stSidebarContent"] { overflow: hidden; }
        </style>
    """, unsafe_allow_html=True)

# Main Content Layout
def render_main_page(session):
    search_input_container = st.container(border=True)
    with search_input_container:
        user_input_text = st.chat_input(f"Please search for an {st.session_state.get('assistant_type')} account")
        current_prompt = user_input_text

        if current_prompt and current_prompt != st.session_state.get("last_prompt"):
            st.session_state.last_prompt = current_prompt
            st.session_state.web_search_query = None

            # Reset enrichment-related state
            st.session_state.enrichment_query = None
            st.session_state.empty_record_for_enrichment = None
            st.session_state.selected_record_df = None
            st.session_state.proposed_record = None
            st.session_state.approved_cols = []

            # These can be defined as regular variables and not as session state as these are not expected to change
            DATABASE = "CORTEX_ANALYST_HCK"
            SCHEMA = "PUBLIC"
            STAGE = "HACKATHON"

            # Reset earlier messages (user & assistant), results_df, and selection (hcp or hco)
            reset_search_session_state(st.session_state.get("assistant_type"))

            # Add formatted user input to messages to track history
            st.session_state.messages.append(
                {"role": "user", "content": [{"type": "text", "text": current_prompt}]}
            )

            # Show loading UI
            with st.spinner("Generating response..."):
                try:
                    assistant_type = st.session_state.get('assistant_type')
                    if assistant_type == "HCP":
                        search_prompt = (
                            f"You are querying a Snowflake semantic model for Healthcare Providers (HCP).\n\n"
                            f"SEARCH RULES:\n"
                            f"- If the input is a 10-digit number, treat it as an NPI and search the NPI column.\n"
                            f"- Otherwise, treat the input as a provider name. Always use case-insensitive comparison (ILIKE).\n"
                            f"AFFILIATION RULES:\n"
                            f"- Always return HCP details from the NPI table.\n"
                            f"- Only populate hospital (HCO) fields when PRIMARY_AFFL_HCO_ACCOUNT_ID is NOT NULL.\n"
                            f"- Never return non-primary hospital affiliations.\n"
                            f"- If no primary affiliation exists, hospital fields must be NULL.\n\n"
                            f"SQL RULES:\n"
                            f"- Always use CTEs.\n"
                            f"- Default LIMIT is 50.\n\n"
                            f"EXAMPLES:\n"
                            f"Search for: {current_prompt}"
                        )
                    else:
                        search_prompt = (
                            f"You are querying a Snowflake semantic model for Healthcare Organizations (HCO).\n\n"
                            f"SEARCH RULES:\n"
                            f"- Treat the input as an organization name and search using:\n"
                            f"    NAME ILIKE '%{current_prompt}%'\n\n"
                            f"AFFILIATION RULES:\n"
                            f"- Always return HCO details from the main HCO table.\n"
                            f"- Only populate affiliation fields when PRIMARY_AFFL_ACCOUNT_ID is NOT NULL.\n"
                            f"- Never return non-primary affiliations.\n"
                            f"- If no primary affiliation exists, affiliation fields must be NULL.\n\n"
                            f"SQL RULES:\n"
                            f"- Always use CTEs.\n"
                            f"- Default LIMIT is 50.\n\n"
                            f"Search for: {current_prompt}"
                        )
                    response = parse_analyst_response(
                        call_cortex_analyst(
                            session,
                            search_prompt,
                            st.session_state.get("semantic_model_file"),
                            DATABASE,
                            SCHEMA,
                            STAGE
                        )
                    )

                    response["user_query"] = current_prompt.strip()

                    # Add formatted assistant response to messages to track history
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )

                except Exception as e:
                    st.write(e)
                    st.error(f"error occured: {str(e)}")

    # Show results (outside the container so they persist on rerun)
    display_search_results()

# Page Router - render based on current_view
if st.session_state.get("current_view", "main") == "main":
    render_main_page(session)
elif st.session_state.get("current_view") == "enrichment_page":
    entity_type = st.session_state.get("assistant_type", "HCP")
    selected_id_key = f"selected_{entity_type.lower()}_id"
    selected_id = st.session_state.get(selected_id_key)
    
    # Check if we have an updated selected_record_df (e.g., after insert of new record)
    # This takes priority to ensure affiliation operations use the newly inserted record ID
    if st.session_state.get("selected_record_df") is not None and not st.session_state.selected_record_df.empty:
        render_enrichment_page(session, st.session_state.selected_record_df)
    # Handle empty record flow (from "Still want to proceed with Web Search?" button)
    elif selected_id == 'empty_record' and st.session_state.get('empty_record_for_enrichment'):
        empty_record = st.session_state.empty_record_for_enrichment
        selected_record_df = pd.DataFrame([empty_record])
        render_enrichment_page(session, selected_record_df)
    elif selected_id and st.session_state.get("results_df") is not None:
        selected_record_df = st.session_state.results_df[
            st.session_state.results_df["ID"] == selected_id
        ]
        render_enrichment_page(session, selected_record_df)
    else:
        st.warning(f"Please select an {entity_type} record from the main page first.")
        if st.button("Back to Main Page"):
            st.session_state.current_view = "main"
            st.rerun()