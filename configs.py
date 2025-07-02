from enum import Enum

# --- Database ---
# The path to the SQLite database file
DB_PATH = 'database/app_database.db'


# --- User Roles ---
# This is used to manage access control and permissions for different types of users
class UserRole(Enum):
    """Enumeration for user roles in the application."""
    ADMIN = 'admin'
    DOCTOR = 'doctor'
    PATIENT = 'patient'


# --- User Status ---
# This is used to track the state of user accounts, especially for doctors and patients
class UserStatus(Enum):
    """Enumeration for user account statuses."""
    ACTIVE = 'active'
    PENDING_APPROVAL = 'pending_approval'
    REQUESTED = 'requested'

# --- Prediction Classes ---
# Defines the probability threshold for classifying predictions
LOW_RISK_THRESHOLD = 0.4
HIGH_RISK_THRESHOLD = 0.6

# --- Pagination ---
ITEMS_PER_PAGE = 10