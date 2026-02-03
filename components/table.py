import streamlit as st

def render_table(col_sizes_tuple, col_header_names_list, row_data, title = None):
    if title:
        st.write(title)

    cols = st.columns(col_sizes_tuple)

    for col, header_name in zip(cols, col_header_names_list):
        col.markdown(f"**{header_name}**")

    for _, row in row_data.iterrows():
        row_id = row.get("ID")
        if row_id is None:
            continue
        is_selected = row_id == st.session_state.get(f"selected_{st.session_state.get("assistant_type").lower()}_id")
        row_cols = st.columns(col_sizes_tuple)

        if is_selected:
            row_cols[0].write("🔘")
        else:
            if row_cols[0].button("", key=f"select_{row_id}"):
                st.session_state[f"selected_{st.session_state.get("assistant_type").lower()}_id"] = row_id
                st.rerun()

        row_cols[1].write(row_id)
        row_cols[2].write(row.get("NAME", ""))
        row_cols[3].write(row.get("NPI", "N/A"))
        row_cols[4].write(row.get("ADDRESS1", "N/A"))
        row_cols[5].write(row.get("CITY", "N/A"))
        row_cols[6].write(row.get("STATE", "N/A"))