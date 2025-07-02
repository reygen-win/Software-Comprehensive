import streamlit as st
from database import DatabaseManager
from ui_components import render_sidebar_and_auth, reset_pagination, render_pagination
from configs import UserRole, ITEMS_PER_PAGE
from utils import highlight_risk

# --- Initialize Connection and UI Rendering ---
page = render_sidebar_and_auth(UserRole.PATIENT)
db_manager = DatabaseManager()

# --- Page Content ---
if page == "My Dashboard":
    # --- Initialize page number for pagination ---
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0

    # Search bar
    cols = st.columns([4, 2, 3])
    with cols[2]:
        search_query = st.text_input("Search by Doctor Name", placeholder="🔍 Search by Doctor Name", label_visibility="collapsed", on_change=reset_pagination)

    st.divider()

    if search_query:
        history = db_manager.get_history_by_doctor(st.session_state['user_id'], search_query)
    else:
        history = db_manager.get_history_summary(st.session_state['user_id'])

    if not history:
        st.info("No history found.")
        st.stop()

    else:
        # Slice the history for pagination
        start_index = st.session_state.page_number * ITEMS_PER_PAGE
        end_index = start_index + ITEMS_PER_PAGE

        history_to_display = history[start_index:end_index]

        # Headers for the history table
        cols = st.columns([3, 2, 2, 2])
        headers = ["Visit Time", "Assessed By", "Risk Level", "Risk Rate"]
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")
        st.divider()

        # Display the history records
        for record in history_to_display:
            cols = st.columns([3, 2, 2, 2])
            cols[0].write(record.prediction_timestamp)
            cols[1].write(record.doctor_name)
            cols[2].markdown(f'<span style="{highlight_risk(record.predicted_class)}">{record.predicted_class}</span>', unsafe_allow_html=True)
            cols[3].write(f"{record.prediction_probability:.2%}")

        # Render pagination controls
        render_pagination(len(history), ITEMS_PER_PAGE)

elif page == "Find Doctor":
    # --- Display notification of actions taken on this page ---
    if "find_doctor_notification" in st.session_state:
        notification = st.session_state.find_doctor_notification
        st.toast(notification["message"], icon=notification["icon"])
        del st.session_state.find_doctor_notification

    # --- Initialize page number for pagination ---
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0

    # Search bar
    cols = st.columns([4, 2, 3])
    with cols[2]:
        search_query = st.text_input("Search by Doctor Name", placeholder="🔍 Search by Doctor Name", label_visibility="collapsed", on_change=reset_pagination)

    st.divider()

    # --- Fetch available doctors based on search query or default ---
    if search_query:
        available_doctors = db_manager.search_available_by_doctor_name(search_query)
    else:
        available_doctors = db_manager.find_available_doctors(st.session_state['user_id'])
    
    # --- Display available doctors ---
    if not available_doctors:
        st.info("No doctors available at this time. Please check back later.")
        st.stop()
    else:
        # Slice the available doctors for pagination
        start_index = st.session_state.page_number * ITEMS_PER_PAGE
        end_index = start_index + ITEMS_PER_PAGE

        doctors_to_display = available_doctors[start_index:end_index]

        cols = st.columns([2, 3, 2])
        # Headers for the doctor list
        headers = ["Doctor ID", "Doctor Name", "Actions"]
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")

        st.divider()

        # Available doctors list
        for doctor in doctors_to_display:
            cols = st.columns([2, 3, 2])
            cols[0].write(doctor.user_id)
            cols[1].write(doctor.full_name)
            
            with cols[2]:
                if st.button("✉️", key=f"req_{doctor.user_id}", use_container_width=True, help="Send Assignment Request"):
                    result = db_manager.create_assignment_request(doctor.user_id, st.session_state['user_id'])

                    if result.get("success"):
                        notification = {"message": result.get("message", "Request sent successfully!"), "icon": "✅"}
                    else:
                        notification = {"message": result.get("message", "Failed to send request."), "icon": "❌"}
                    
                    st.session_state.find_doctor_notification = notification
                    st.rerun()

        # Render pagination controls
        render_pagination(len(available_doctors), ITEMS_PER_PAGE)