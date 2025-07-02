import streamlit as st
import hashlib
from database import DatabaseManager
from configs import UserRole, UserStatus

class Authenticator:
    """Handles user authentication and registration."""
    def __init__(self, db_manager: DatabaseManager):
        """Initializes the Authenticator with a SHARED database manager instance."""
        self.db_manager = db_manager

    def register_user(self, username, password, full_name, role, id_number, dob):
        """Registers a new user in the database."""
        status = UserStatus.PENDING_APPROVAL.value if role == UserRole.DOCTOR.value else UserStatus.ACTIVE.value
        return self.db_manager.create_user(username, password, full_name, role, id_number, dob, status=status)
        
    def login_user(self, username, password):
        """Logs in a user by checking credentials."""
        # Check if the username exists in the database
        user = self.db_manager.get_user_for_authentication(username)
        if not user:
            return {"success": False, "message": "Invalid username or password."}
        
        # If exists, check the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash != user['password_hash']:
            return {"success": False, "message": "Invalid username or password."}
        
        # If the password matches, check the user status
        if user['status'] != UserStatus.ACTIVE.value:
            return {"success": False, "message": "Your account is being verified by the Administrator."}
        
        # If everything is valid, return success
        return {"success": True, "user_id": user['user_id'], "role": user['role'], "full_name": user['full_name']}

    def forgot_password(self, username, id_number):
        """Handles forgot password functionality."""
        pass


def logout():
        """Logs out the user by clearing all session state variables."""
        keys_to_clear = ['logged_in', 'user_id', 'username', 'full_name', 'role']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state['logged_in'] = False