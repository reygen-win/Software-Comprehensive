import streamlit as st
from database import DatabaseManager
from auth import Authenticator
from configs import UserRole
import datetime

# --- Initialize Connection and Tables ---
db_manager = DatabaseManager()
authenticator = Authenticator(db_manager)

db_manager.create_tables()

# --- UI Functions ---
st.set_page_config(page_title="Cancer Risk Prediction", page_icon="🩺", layout="centered")

def clear_login_error():
    if 'login_error' in st.session_state:
        del st.session_state.login_error

def show_login_page():
    # --- 1. Check for success message from signup page ---
    if "signup_success" in st.session_state:
        # Display the toast message
        st.toast(st.session_state.signup_success, icon="✅")
        del st.session_state.signup_success

    # --- 2. Check for login error messages ---
    if 'login_error' in st.session_state:
        st.error(st.session_state.login_error)

    # --- 3. Login Form ---
    with st.form("login_form"):
        # Centering
        cols = st.columns([2, 2, 1])
        with cols[1]:
            st.image("images/logo.png", width=100)
        cols = st.columns([2.1, 2, 1])
        with cols[1]:
            st.subheader("Sign In")
        cols = st.columns([1.3, 2, 1])
        with cols[1]:
            st.write("Please enter your credentials to log in.")
        cols = st.columns([1.2, 2, 1.2])
        with cols[1]:
            username = st.text_input("Username")
        cols = st.columns([1.2, 2, 1.2])
        with cols[1]:
            password = st.text_input("Password", type="password")

        st.markdown("") # Add a little vertical space

        # Handle form submission
        cols = st.columns([1.2, 2, 1.2])
        with cols[1]:
            if st.form_submit_button("SIGN IN", use_container_width=True):
                # Clear any previous error before attempting to log in
                clear_login_error()

                login_result = authenticator.login_user(username, password)
                if login_result.get("success"):
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = login_result['user_id']
                    st.session_state['username'] = username
                    st.session_state['full_name'] = login_result['full_name']
                    st.session_state['role'] = login_result['role']

                    # Set a personalized success message for the dashboard page.
                    full_name = st.session_state.get('full_name', 'User') # Use .get for safety
                    st.session_state.login_success = f"Welcome back, {full_name}!"

                    # Navigate to the correct dashboard
                    if st.session_state['role'] == UserRole.ADMIN.value:
                        st.switch_page("pages/1_Admin_Dashboard.py")
                    elif st.session_state['role'] == UserRole.DOCTOR.value:
                        st.switch_page("pages/2_Doctor_Dashboard.py")
                    else:  # Patient
                        st.switch_page("pages/3_Patient_Dashboard.py")
                else:
                    st.session_state.login_error = login_result.get("message", "An unknown error occurred.")
                    st.rerun() # Rerun to display the error message immediately

        st.markdown("") # Add a little vertical space

    # Redirect to sign up page
    st.markdown("""<div style="text-align: center; margin-top: 2rem;">New to our platform?</div>""", unsafe_allow_html=True)
    
    signup_cols = st.columns([2, 1, 2])
    with signup_cols[1]:
        if st.button("Sign Up", use_container_width=True):
            clear_signup_notifications()
            st.session_state.page = 'signup'
            st.rerun()

def clear_signup_notifications():
    if "signup_error" in st.session_state:
        del st.session_state.signup_error
    if "signup_success" in st.session_state:
        del st.session_state.signup_success

def show_signup_page():
    # --- 1. Notification Area ---
    # Display any error messages that are stored in the session state
    if "signup_error" in st.session_state:
        st.error(st.session_state.signup_error)

    # --- 2. Sign Up Form ---
    with st.form("signup_form"):
        # Header and Logo
        cols = st.columns([2, 2, 1])
        with cols[1]:
            st.image("images/logo.png", width=100)
        cols = st.columns([2.1, 2, 1])
        with cols[1]:
            st.subheader("Sign Up")
        cols = st.columns([1.1, 2, 1])
        with cols[1]:
            st.write("Please provide your information to sign up.")

        st.divider()

        # Form Input Fields
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name*")
            username = st.text_input("Username*")
            password = st.text_input("Password*", type="password")
            role = st.selectbox("Sign Up As*", [role.value for role in UserRole if not role == UserRole.ADMIN], index=0)
        with col2:
            last_name = st.text_input("Last Name*")
            id_number = st.text_input("ID Number*")
            confirm_password = st.text_input("Confirm Password*", type="password")
            dob = st.date_input("Date of Birth*", min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today(), value=None, help="Format: YYYY-MM-DD")

        st.markdown("") # Add a little vertical space

        # Centered Submit Buttion
        cols = st.columns([1.2, 2, 1.2])
        with cols[1]:
            if st.form_submit_button("SIGN UP", use_container_width=True, type="primary"):
                clear_signup_notifications()

                full_name = f"{first_name} {last_name}".strip()

                # Validate inputs
                if password != confirm_password:
                    st.session_state.signup_error = "Passwords do not match. Please try again."
                elif not all([full_name, username, password, id_number, role]):
                    st.session_state.signup_error = "Please fill in all required fields."
                else:
                    registration_result = authenticator.register_user(username, password, full_name, role, id_number, dob)
                    if registration_result.get("success"):
                        st.session_state.signup_success = registration_result.get("message", "Registration successful! Please sign in.")
                        clear_login_error()
                        st.session_state.page = 'signin'
                        st.rerun()
                    else:
                        st.session_state.signup_error = registration_result.get("message", "An unknown registration error occurred.")
                st.rerun()

    # Redirect to sign in page
    st.markdown("""<div style="text-align: center; margin-top: 2rem;">Already have an account?</div>""", unsafe_allow_html=True)

    signin_cols = st.columns([2, 1, 2])
    with signin_cols[1]:
        if st.button("Sign In", use_container_width=True):
            clear_login_error()
            st.session_state.page = 'signin'
            st.rerun()


# --- Main Logic ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    if st.session_state.get('page') == 'signup':
        show_signup_page()
    else:
        show_login_page()
else:
    # If a user is logged in, redirect to the appropriate dashboard
    if st.session_state['role'] == UserRole.ADMIN.value:
        st.switch_page("pages/1_Admin_Dashboard.py")
    elif st.session_state['role'] == UserRole.DOCTOR.value:
        st.switch_page("pages/2_Doctor_Dashboard.py")
    else:  # Patient
        st.switch_page("pages/3_Patient_Dashboard.py")