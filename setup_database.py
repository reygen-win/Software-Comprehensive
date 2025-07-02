import hashlib
from configs import UserRole, UserStatus
from database import DatabaseManager

# --- Initialize Database ---
def setup_database():
    db_manager = DatabaseManager()
    db_manager.create_tables()

    # Create default admin user
    admin_username = "admin"
    admin_password = "admin123"
    admin_full_name = "Admin User"
    admin_role = UserRole.ADMIN.value
    admin_id_number = "ADMIN0000"
    admin_status = UserStatus.ACTIVE.value
    admin_dob = "2000-01-01"  # Default date of birth for admin
    
    result = db_manager.create_user(
        username=admin_username,
        password=admin_password,
        full_name=admin_full_name,
        role=admin_role,
        id_number=admin_id_number,
        status=admin_status,
        dob=admin_dob
    )
    
    print(f"Admin user creation: {result['message']}")
    
    print("Database setup complete.")
    db_manager.close()

if __name__ == "__main__":
    setup_database()