import time
import streamlit as st


def show_popup(popup_placeholder, message_type: str, record_info: dict):
    """
    Renders a success popup using Streamlit's native success message.
    Auto-dismisses after a delay.

    Args:
        popup_placeholder: Streamlit empty placeholder for the popup
        message_type: Type of message ('update_success', 'insert_success', 'primary_success')
        record_info: Dictionary with message details
    """
    if message_type == "update_success" and 'message' in record_info:
        title = "Update Successful!"
        message = record_info['message']
    elif message_type == "insert_success" and 'message' in record_info:
        title = "Insert Successful!"
        message = record_info['message']
    elif message_type == "primary_success":
        title = "Primary Affiliation Updated!"
        message = f"Primary affiliation set with HCO ID: {record_info.get('hco_id')}."
    else:
        title = "Success!"
        message = "Operation completed successfully."

    with popup_placeholder.container():
        st.success(f"**{title}** {message}", icon="✅")

    time.sleep(2)
    st.session_state.show_popup = False
    st.session_state.popup_message_info = None
    # st.rerun()


def show_reason_popup(hco_name: str, priority: str, reason: str):
    """
    Show a modal dialog with the priority reason for an affiliation.
    Uses Streamlit's native dialog for proper centering and dismissal.

    Args:
        hco_name: Name of the HCO
        priority: Priority ranking
        reason: Reason for the priority
    """
    @st.dialog("🎯 Priority Ranking Details", width="small")
    def reason_dialog():
        st.markdown(f"**Priority:** {priority}")
        st.markdown(f"**HCO:** {hco_name}")
        st.markdown(f"**Reason:** {reason}")

        if st.button("Close", key="close_reason_dialog"):
            st.session_state.show_reason_popup = False
            st.session_state.reason_popup_data = None
            st.rerun()

    reason_dialog()


def init_popup_session_state():
    """Initialize session state variables for popups."""
    if "show_popup" not in st.session_state:
        st.session_state.show_popup = False
    if "popup_message_info" not in st.session_state:
        st.session_state.popup_message_info = None
    if "show_confirm_dialog" not in st.session_state:
        st.session_state.show_confirm_dialog = False
    if "show_primary_confirm_dialog" not in st.session_state:
        st.session_state.show_primary_confirm_dialog = False
    if "show_reason_popup" not in st.session_state:
        st.session_state.show_reason_popup = False
    if "reason_popup_data" not in st.session_state:
        st.session_state.reason_popup_data = None
    if "primary_hco_id" not in st.session_state:
        st.session_state.primary_hco_id = None
    if "primary_hco_data" not in st.session_state:
        st.session_state.primary_hco_data = None
