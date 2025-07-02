import streamlit as st
from auth import logout
from configs import UserRole

def render_sidebar_and_auth(required_role: UserRole):
    """
    Handles session authentication and renders the common sidebar UI.
    This function should be called at the start of each page to ensure the user is authenticated

    Args:
        required_role (UserRole): The role required to access the page.

    Returns:
        str: The navigation page selected by the user.
    """
    # --- Check for a login success message and display it once ---
    if "login_success" in st.session_state:
        st.toast(st.session_state.login_success, icon="👋")
        del st.session_state.login_success

    # 1. Authentication Check
    if 'logged_in' not in st.session_state or not st.session_state['logged_in'] or st.session_state.get('role') != required_role.value:
        st.error("Access Denied. Please log in with the appropriate account.")
        st.stop()

    # 2. Render Sidebar
    with st.sidebar:
        st.image("images/logo.png", width=50)
        st.header(st.session_state.get('username', 'Guest'))
        st.write(f"Role: {st.session_state.get('role', '').capitalize()}")
        st.divider()

        # Define navigation options based on user role
        if st.session_state['role'] == UserRole.ADMIN.value:
            nav_options = ["User Management", "Doctor Approvals"]
        elif st.session_state['role'] == UserRole.DOCTOR.value:
            nav_options = ["My Dashboard", "Predict", "Patient Requests"]
        else: # Patient
            nav_options = ["My Dashboard", "Find Doctor"]

        page = st.radio("Navigation", nav_options, key="nav_options", on_change=reset_pagination)
        st.divider()

        # Logout button
        if st.button("Logout"):
            logout()
            st.switch_page("app.py")

    # 3. Return the selected page
    st.title(page)  # Set the page title to the selected page
    return page

def reset_pagination():
    """Resets the page number to the first page, used for search."""
    if 'page_number' in st.session_state:
        st.session_state.page_number = 0

def render_pagination(total_items: int, items_per_page: int):
    """
    Renders the pagination controls and handles page number state.

    Args:
        total_items (int): The total number of items in the list being paginated.
        items_per_page (int): The number of items to display on each page.
    """
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0

    # --- Calculate total pages ---
    total_pages = (total_items + items_per_page - 1) // items_per_page
    # Ensure total_pages is at least 1
    total_pages = max(1, total_pages)

    # --- Adjust page number if it exceeds total pages ---
    if st.session_state.page_number >= total_pages:
        st.session_state.page_number = 0

    # --- Disable buttons if at the start or end ---
    prev_disabled = st.session_state.page_number == 0
    next_disabled = st.session_state.page_number >= total_pages - 1

    st.divider()

    # --- Render the buttons and page number display ---
    nav_cols = st.columns([2, 1, 1.2, 1, 2])

    with nav_cols[1]:
        if st.button("⬅️", disabled=prev_disabled, help="Previous Page"):
            st.session_state.page_number -= 1
            st.rerun()

    with nav_cols[3]:
        if st.button("➡️", disabled=next_disabled, help="Next Page"):
            st.session_state.page_number += 1
            st.rerun()

    with nav_cols[2]:
        st.write(f"Page {st.session_state.page_number + 1} of {total_pages}")