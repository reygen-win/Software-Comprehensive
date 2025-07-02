import streamlit as st
from database import DatabaseManager
from ui_components import render_sidebar_and_auth, reset_pagination, render_pagination
from configs import UserRole, UserStatus, ITEMS_PER_PAGE
import datetime

# --- Initialize Connection and UI Rendering ---
page = render_sidebar_and_auth(UserRole.ADMIN)
db_manager = DatabaseManager()

# --- Display any messages related to admin operation ---
if "admin_notification" in st.session_state:
    notification = st.session_state.admin_notification
    st.toast(notification["message"], icon=notification["icon"])
    del st.session_state.admin_notification

# --- Initialize Session State for the "Add User" and "Edit User" Form ---
if 'show_add_user_form' not in st.session_state:
    st.session_state.show_add_user_form = False
if 'user_to_edit' not in st.session_state:
    st.session_state.user_to_edit = None

def clear_user_form_notifications():
    if "user_form_error" in st.session_state:
        del st.session_state.user_form_error

# --- Function to handle the "Add User" form submission ---
def show_add_user_form():
    """
    Handles the form submission for adding a new user.
    This function is called when the user clicks the "＋ Add Users" button.
    """
    st.divider()

    # --- Display any errors related to this specific form ---
    if "user_form_error" in st.session_state:
        st.error(st.session_state.user_form_error)
    
    # --- Form for adding a new user ---
    with st.form("add_user_form"):
        st.subheader("➕ Create New User Account")

        # Form fields for user details
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name*", placeholder="Enter First Name")
            username = st.text_input("Username*", placeholder="Enter Username")
            role = st.selectbox("Role*", options=[r.value for r in UserRole], index=0)
        with col2:
            last_name = st.text_input("Last Name*", placeholder="Enter Last Name")
            id_number = st.text_input("ID Number*", placeholder="Enter ID Number")
            status = st.selectbox("Status*", options=[s.value for s in UserStatus if s != UserStatus.REQUESTED])

        dob = st.date_input("Date of Birth*", min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today(), value=None, help="Format: YYYY-MM-DD")

        col3, col4 = st.columns(2)
        with col3:
            password = st.text_input("Password*", type="password", placeholder="Enter Password")
        with col4:
            confirm_password = st.text_input("Confirm Password*", type="password", placeholder="Confirm Password")

        # Form submission buttons
        col1, col2, _ = st.columns([1.5, 1, 4])
        with col1:
            create_clicked = st.form_submit_button("Create User", use_container_width=True, type="primary")
        with col2:
            cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)

        if create_clicked:
            clear_user_form_notifications()

            full_name = f"{first_name} {last_name}".strip()

            if not all([username, password, full_name, id_number, role, dob, status]):
                st.session_state.user_form_error = "Please fill out all required fields."
            elif password != confirm_password:
                st.session_state.user_form_error = "Passwords do not match. Please try again."
            else:
                result = db_manager.create_user(username, password, full_name, role, id_number, dob, status)
                if result["success"]:
                    st.session_state.admin_notification = {"message": result.get("message"), "icon": "✅"}
                    st.session_state.show_add_user_form = False
                else:
                    st.session_state.user_form_error = result["message"]
            st.rerun()

        if cancel_clicked:
            clear_user_form_notifications()
            st.session_state.show_add_user_form = False
            st.rerun()
        
    st.divider()

def show_edit_user_form(user):
    st.divider()

    # --- Display any errors related to this specific form ---
    if "user_form_error" in st.session_state:
        st.error(st.session_state.user_form_error)
    
    # --- Form for editing an existing user ---
    with st.form("edit_user_form"):
        st.subheader(f"✏️ Edit User: {user.full_name}")
        
        # Pre-fill the form with the user's current data
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name*", value=user.full_name.split()[0] if len(user.full_name.split()) > 0 else "")
            username = st.text_input("Username*", value=user.username)
            role = st.selectbox("Role*", options=[r.value for r in UserRole], index=[r.value for r in UserRole].index(user.role))
        with col2:
            last_name = st.text_input("Last Name*", value=user.full_name.split()[-1] if len(user.full_name.split()) > 1 else "")
            id_number = st.text_input("ID No.*", value=user.id_number)
            status = st.selectbox("Status*", options=[s.value for s in UserStatus if s != UserStatus.REQUESTED],
                                   index=[s.value for s in UserStatus if s != UserStatus.REQUESTED].index(user.status))

        dob = st.date_input("Date of Birth*", min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today(), value=user.dob if user.dob else None, help="Format: YYYY-MM-DD")

        col3, col4 = st.columns(2)
        with col3:
            new_password = st.text_input("New Password", type="password")
        with col4:
            confirm_password = st.text_input("Confirm New Password", type="password")
        st.info("Leave password fields blank to keep the current password.")

        # --- Form submission buttons ---
        col1, col2, _ = st.columns([1.5, 1, 4])
        with col1:
            update_clicked = st.form_submit_button("Update User", use_container_width=True, type="primary")
        with col2:
            cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)

        if update_clicked:
            clear_user_form_notifications()
            password_to_update = None

            # 1. Validate inputs
            if new_password and new_password != confirm_password:
                st.session_state.user_form_error = "New passwords do not match."
                st.rerun()
                st.stop()
            else:
                if new_password:
                    password_to_update = new_password

                # 2. Prepare full name
                full_name = f"{first_name} {last_name}".strip()

                # 3. Update user information
                result = db_manager.update_user_info(user.user_id, username, password_to_update, full_name, role, status, id_number, dob)

                if result["success"]:
                    # Success! Set message for the PARENT page and hide the form.
                    st.session_state.admin_notification = {"message": result.get("message"), "icon": "✏️"}
                    st.session_state.action = 'view'
                    st.session_state.user_to_edit = None
                else:
                    st.session_state.user_form_error = result["message"]
            st.rerun()
                                                    
        if cancel_clicked:
            clear_user_form_notifications()
            st.session_state.action = 'view'
            st.session_state.user_to_edit = None
            st.rerun()

    st.divider()

# --- Page Content ---
if page == "User Management":
    # --- Initialize page number for pagination ---
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0

    # Add user button and search bar
    col1, col2, col3 = st.columns([4, 2, 3])
    with col2:
        if st.button("＋ Add Users", use_container_width=True):
            st.session_state['show_add_user_form'] = True
            st.rerun()
    with col3:
        search_query = st.text_input("Search by Username", placeholder="🔍 Search by Username", label_visibility="collapsed", on_change=reset_pagination)

    # Show the form if the button was clicked
    if st.session_state.show_add_user_form:
        show_add_user_form()
    elif st.session_state.get('action') == 'edit' and st.session_state.get('user_to_edit'):
        show_edit_user_form(st.session_state.user_to_edit)

    st.divider()

    if search_query:
        users = db_manager.search_by_username(search_query)
    else:
        users = db_manager.get_all_users()

    if users:
        # Slice the users list for pagination
        start_index = st.session_state.page_number * ITEMS_PER_PAGE
        end_index = start_index + ITEMS_PER_PAGE

        users_to_display = users[start_index:end_index]

        # Display header
        cols = st.columns([1, 2, 3, 2, 3, 2])
        headers = ["ID", "Username", "Full Name", "Role", "Status", "Actions"]
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")
        st.divider()

        # Display user data
        for user in users_to_display:
            cols = st.columns([1, 2, 3, 2, 3, 2])
            cols[0].write(user.user_id)
            cols[1].write(user.username)
            cols[2].write(user.full_name)
            cols[3].write(user.role)
            cols[4].write(user.status)

            with cols[5]:
                action_cols = st.columns(2)
                # if action_cols[0].button("👁️", key=f"view_{user.user_id}", help="View User Details"):
                #     pass
                if action_cols[0].button("✏️", key=f"edit_{user.user_id}", help="Edit User"):
                    st.session_state.action = 'edit'
                    st.session_state.user_to_edit = user # Store the whole user object
                    st.rerun()
                if action_cols[1].button("🗑️", key=f"delete_{user.user_id}", help="Delete User"):
                    result = db_manager.delete_user(user.user_id)
                    st.session_state.admin_notification = {"message": result.get("message"), "icon": "✅" if result.get("success") else "❌"}
                    st.rerun()
            
        # Render pagination controls
        render_pagination(len(users), ITEMS_PER_PAGE)

    else:
        st.info("No users found.")

elif page == "Doctor Approvals":
    
    # --- Initialize page number for pagination ---
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0
    
    pending_doctors = db_manager.get_pending_doctors()
    if not pending_doctors:
        st.info("No pending doctor approvals.")
    else:
        # Slice the pending_doctors list for pagination
        start_index = st.session_state.page_number * ITEMS_PER_PAGE
        end_index = start_index + ITEMS_PER_PAGE

        doctor_to_display = pending_doctors[start_index:end_index]

        # Display header
        cols = st.columns([1, 2, 3, 3, 2])
        headers = ["ID", "Username", "Full Name", "ID Number", "Actions"]
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")

        # Display doctor data
        for doctor in doctor_to_display:
            cols = st.columns([1, 2, 3, 3, 2])
            cols[0].markdown(f"**{doctor.user_id}**")
            cols[1].markdown(f"**{doctor.username}**")
            cols[2].markdown(f"**{doctor.full_name}**")
            cols[3].markdown(f"**{doctor.id_number}**")

            with cols[4]:
                action_cols = st.columns(2)
                with action_cols[0]:
                    if st.button("✔️", key=f"approve_{doctor.user_id}", use_container_width=True, help="Approve Doctor"):
                        db_manager.approve_doctor(doctor.user_id)
                        st.session_state.admin_notification = {"message": f"Dr. {doctor.full_name} has been approved.", "icon": "✅"}
                        st.rerun()
                with action_cols[1]:
                    if st.button("❌", key=f"reject_{doctor.user_id}", use_container_width=True, help="Reject Doctor"):
                        db_manager.reject_doctor(doctor.user_id)
                        st.session_state.admin_notification = {"message": f"Registration for Dr. {doctor.full_name} has been rejected.", "icon": "ℹ️"}
                        st.rerun()

        st.divider()

        # Render pagination controls
        render_pagination(len(pending_doctors), ITEMS_PER_PAGE)