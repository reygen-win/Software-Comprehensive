import sqlite3
import hashlib
from configs import DB_PATH, UserStatus, UserRole
from models import Prediction, User, Assignment

class DatabaseManager:
    """Class to manage database operations for the cancer prediction app."""


    def __init__(self, db_path=DB_PATH):
        """Initializes the database connection."""
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row             # Set row factory to return rows as dictionaries
        self.conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign key constraints
        print("Database connection established.")

    def create_tables(self):
        """Create all necessary tables in the database."""
        cursor = self.conn.cursor()

        # --- Users Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id             INTEGER PRIMARY KEY AUTOINCREMENT,
                username            VARCHAR(20) NOT NULL UNIQUE,
                password_hash       VARCHAR(128) NOT NULL,
                full_name           VARCHAR(30) NOT NULL,
                role                VARCHAR(10) NOT NULL CHECK(role IN ('admin', 'doctor', 'patient')),
                status              VARCHAR(20) NOT NULL CHECK(status IN ('active', 'pending_approval')),
                id_number           CHAR(18) NOT NULL UNIQUE,
                dob                 DATE
            );
        """)

        # --- Doctor-Patient Assignments Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctor_patient_assignments (
                assignment_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id           INTEGER NOT NULL,
                patient_id          INTEGER NOT NULL,
                status              VARCHAR(20) NOT NULL CHECK(status IN ('requested', 'active')),
                FOREIGN KEY(doctor_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(patient_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
        """)

        # --- Predictions Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id           INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id               INTEGER NOT NULL,
                patient_id              INTEGER NOT NULL,
                prediction_timestamp    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                age                     INT NOT NULL,
                cancer_stage            VARCHAR(5) NOT NULL CHECK(cancer_stage IN ('I', 'II', 'III', 'IV')),
                tumor_size              REAL NOT NULL,
                tumor_type              VARCHAR(20) NOT NULL CHECK(tumor_type IN ('Lung', 'Stomach', 'Cervical', 'Liver', 'Colorectal', 'Breast')),
                metastasis              VARCHAR(5) NOT NULL CHECK(metastasis IN ('Yes', 'No')),
                treatment_type          VARCHAR(20) NOT NULL CHECK(treatment_type IN ('Radiation', 'Chemotherapy', 'Surgery', 'Targeted Therapy', 'Immunotherapy')),
                comorbidities           VARCHAR(15) NOT NULL CHECK(comorbidities IN ('No Comorbidities', 'Diabetes, Hepatitis B', 'Hepatitis B', 'Hypertension', 'Diabetes, Hypertension', 'Diabetes, Hepatitis B', 'Hypertension, Hepatitis B')),
                predicted_class         VARCHAR(15) NOT NULL,
                prediction_probability  REAL NOT NULL,
                FOREIGN KEY(doctor_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(patient_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
        """)

        self.conn.commit()
        print("Tables created successfully.")

    def close(self):
        """Closes the database connection if it is open."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")
        else:
            print("No active database connection to close.")

    def get_user_fullname(self, user_id):
        """Fetches the full name of a user by their user ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT full_name FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result['full_name'] if result else None
    
    def get_user_for_authentication(self, username):
        """Fetches a user by username for authentication purposes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()
    
    # --- Admin Methods ---
    def get_all_users(self) -> list[User]:
        """Fetches all users from the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id, username, full_name, id_number, role, status, dob FROM users ORDER BY user_id")
        rows = cursor.fetchall()
        return [User(**row) for row in rows]
    
    def search_by_username(self, username) -> list[User]:
        """Searches for users by username."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT user_id, username, full_name, id_number, role, status, dob 
            FROM users WHERE username LIKE ?
            ORDER BY user_id
        """, ('%' + username + '%',))
        rows = cursor.fetchall()
        return [User(**row) for row in rows]
    
    def create_user(self, username, password, full_name, role, id_number, dob, status=UserStatus.ACTIVE.value):
        """Adds a new user to the database."""
        cursor = self.conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role, status, id_number, dob)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (username, password_hash, full_name, role, status, id_number, dob))
            self.conn.commit()
            if role == UserRole.DOCTOR.value and status == UserStatus.PENDING_APPROVAL.value:
                return {"success": True, "message": "Sign up request sent successfully and is waiting for Administrator's approval!"}
            elif role == UserRole.PATIENT.value and status == UserStatus.ACTIVE.value:
                return {"success": True, "message": "Sign up successful!"}
            else:
                return {"success": True, "message": "User created successfully!"}
        except sqlite3.IntegrityError:
            return {"success": False, "message": "Username or ID number already exists."}
        
    def delete_user(self, user_id):
        """Deletes a user from the database."""
        cursor = self.conn.cursor()
        # 1. Fetch the user to be deleted
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        user_full_name = user['full_name'] if user else None
        if not user:
            return {"success": False, "message": "User not found."}
        
        # 2. Delete the user
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return {"success": cursor.rowcount > 0, "message": f"User {user_full_name} deleted successfully." if cursor.rowcount > 0 else "User not found."}
    
    def update_user_info(self, user_id, username=None, password=None, full_name=None, role=None, status=None, id_number=None, dob=None):
        """Updates user's information in the database."""
        # 1. Fetch current user's data
        curr_cursor = self.conn.cursor()
        curr_cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        current_user = curr_cursor.fetchone()
        if not current_user:
            return {"success": False, "message": "User not found."}
        
        # 2. Prepare new values, keeping current values if not provided
        new_username = username if username else current_user['username']
        new_full_name = full_name if full_name else current_user['full_name']
        new_role = role if role else current_user['role']
        new_status = status if status else current_user['status']
        new_id_number = id_number if id_number else current_user['id_number']
        new_dob = dob if dob else current_user['dob']
        password_hash = current_user['password_hash'] if not password else hashlib.sha256(password.encode()).hexdigest()

        # 3. Update user information
        try:
            update_cursor = self.conn.cursor()
            update_cursor.execute("""
                UPDATE users
                SET username = ?, password_hash = ?, full_name = ?, role = ?, status = ?, id_number = ?, dob = ?
                WHERE user_id = ?
            """, (new_username, password_hash, new_full_name, new_role, new_status, new_id_number, new_dob, user_id))
            self.conn.commit()
            return {"success": True, "message": "User information updated successfully."}
        except sqlite3.IntegrityError:
            return {"success": False, "message": "Update failed. Username or ID number may already be in use."}
    
    def get_pending_doctors(self) -> list[User]:
        """Fetches all doctors with pending approval status."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT user_id, username, full_name, id_number, role, status, dob 
            FROM users WHERE role = ? AND status = ?
        """, (UserRole.DOCTOR.value, UserStatus.PENDING_APPROVAL.value))
        rows = cursor.fetchall()
        return [User(**row) for row in rows]
    
    def approve_doctor(self, doctor_id):
        """Approves a doctor by changing their status to active."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET status = ? WHERE user_id = ? AND role = ? AND status = ?", 
                       (UserStatus.ACTIVE.value, doctor_id, UserRole.DOCTOR.value, UserStatus.PENDING_APPROVAL.value))
        self.conn.commit()
        return {"success": cursor.rowcount > 0, "message": "Doctor approved successfully." if cursor.rowcount > 0 else "Doctor not found."}
    
    def reject_doctor(self, doctor_id):
        """Rejects a doctor by deleting their record."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ? AND status = ?", (doctor_id, UserStatus.PENDING_APPROVAL.value))
        self.conn.commit()
        return {"success": cursor.rowcount > 0, "message": "Doctor rejected successfully." if cursor.rowcount > 0 else "Doctor not found."}
    
    # --- Patient Methods ---
    def get_history_summary(self, patient_id) -> list[Prediction]:
        """Fetches all predictions made for a specific patient."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.*, u.full_name as doctor_name
            FROM predictions p 
            JOIN users u ON p.doctor_id = u.user_id
            WHERE p.patient_id = ? ORDER BY p.prediction_timestamp DESC
        """, (patient_id,))
        rows = cursor.fetchall()
        return [Prediction(**row) for row in rows]
    
    def get_patient_details(self, prediction_id) -> list[Prediction]:
        """Fetches detailed information about a specific prediction."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM predictions WHERE prediction_id = ?", (prediction_id,))
        result = cursor.fetchone()
        
        if result:
            return Prediction(**result)
        return None
    
    def get_history_by_doctor(self, patient_id: int, doctor_name: str) -> list[Prediction]:
        """Fetches all predictions made by a specific doctor name for a patient."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.*, u.full_name as doctor_name
            FROM predictions p JOIN users u ON p.doctor_id = u.user_id
            WHERE p.patient_id = ? AND u.full_name LIKE ?
            ORDER BY p.prediction_timestamp DESC
        """, (patient_id, ('%' + doctor_name + '%'),))
        rows = cursor.fetchall()
        return [Prediction(**row) for row in rows]
    
    def find_available_doctors(self, patient_id) -> list[User]:
        """Finds doctors who are available for assignment to a patient."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT user_id, username, full_name, id_number, role, status, dob
            FROM users
            WHERE role = ? AND status = ? AND user_id NOT IN (
                SELECT doctor_id FROM doctor_patient_assignments WHERE patient_id = ?
            )
        """, (UserRole.DOCTOR.value, UserStatus.ACTIVE.value, patient_id,))
        rows = cursor.fetchall()
        return [User(**row) for row in rows]
    
    def create_assignment_request(self, doctor_id, patient_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT assignment_id FROM doctor_patient_assignments WHERE doctor_id = ? AND patient_id = ?", (doctor_id, patient_id))
        if cursor.fetchone():
            return {"success": False, "message": f"You have already sent a request to Dr. {self.get_user_fullname(doctor_id)}!"}
        
        cursor.execute("INSERT INTO doctor_patient_assignments (doctor_id, patient_id, status) VALUES (?, ?, ?)", (doctor_id, patient_id, UserStatus.REQUESTED.value))
        self.conn.commit()
        return {"success": True, "message": f"Connection request to Dr. {self.get_user_fullname(doctor_id)} sent successfully!"}
    
    def search_available_by_doctor_name(self, doctor_name) -> list[User]:
        """Searches for available doctor by their full name."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT user_id, username, full_name, id_number, role, status, dob
            FROM users 
            WHERE role = ? AND full_name LIKE ?
        """, (UserRole.DOCTOR.value, '%' + doctor_name + '%',))
        rows = cursor.fetchall()
        return [User(**row) for row in rows]
    
    # --- Doctor Methods ---
    def get_assigned_patients(self, doctor_id: int) -> list[User]:
        """Fetches all patients assigned to a specific doctor."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT u.user_id, u.username, u.full_name, u.id_number, u.role, u.status, u.dob
            FROM users u JOIN doctor_patient_assignments a ON u.user_id = a.patient_id
            WHERE a.doctor_id = ? AND a.status = ?
        """, (doctor_id, UserStatus.ACTIVE.value))
        rows = cursor.fetchall()
        return [User(**row) for row in rows]
    
    def get_patient_by_id(self, patient_id: int) -> list[User]:
        """Fetches a patient by their user ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT user_id, username, full_name, id_number, role, status, dob 
            FROM users WHERE user_id = ?
        """, (patient_id,))
        result = cursor.fetchone()
        return User(**result) if result else None
    
    def get_patient_records(self, doctor_id) -> list[Prediction]:
        """Fetches all records of patients who have requested to be assigned to the doctor."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT p.*, u.full_name as patient_name
            FROM predictions p
            JOIN users u ON p.patient_id = u.user_id
            WHERE p.doctor_id = ?
            ORDER BY p.prediction_timestamp DESC
        """, (doctor_id,))
        
        rows = cursor.fetchall()

        preds = [Prediction(**row) for row in rows]
        return preds
    
    def get_history_by_patient_id(self, patient_id: int) -> list[Prediction]:
        """
        Fetches the complete prediction history for a single patient, ordered by time (from oldest to newest).
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT h.*, p.full_name AS patient_name, d.full_name AS doctor_name
            FROM predictions h
            JOIN users p ON h.patient_id = p.user_id
            JOIN users d ON h.doctor_id = d.user_id
            WHERE h.patient_id = ?
            ORDER BY h.prediction_timestamp DESC
        """, (patient_id,))
        rows = cursor.fetchall()
        return [Prediction(**row) for row in rows]
    
    def search_patients_by_name(self, doctor_id, patient_name) -> list[Prediction]:
        """Searches for patients by their full name who are assigned to the doctor."""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT p.*, u.full_name as patient_name
            FROM predictions p
            JOIN users u ON p.patient_id = u.user_id
            WHERE p.doctor_id = ? AND u.full_name LIKE ?
        """, (doctor_id, '%' + patient_name + '%',))
        rows = cursor.fetchall()

        preds = [Prediction(**row) for row in rows]
        return preds
    
    def get_patient_requests(self, doctor_id) -> list[Assignment]:
        """Fetches all requests from patients to be assigned to the doctor."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT a.*, u.username as patient_username, u.full_name as patient_name
            FROM doctor_patient_assignments a JOIN users u ON a.patient_id = u.user_id
            WHERE a.doctor_id = ? AND a.status = ?
        """, (doctor_id, UserStatus.REQUESTED.value))
        rows = cursor.fetchall()

        assignments = [Assignment(**row) for row in rows]
        return assignments
    
    def search_requests_by_patient_name(self, doctor_id, patient_name) -> list[Assignment]:
        """Searches for patient requests by their full name."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT a.*, u.username as patient_username, u.full_name as patient_name
            FROM doctor_patient_assignments a 
            JOIN users u ON a.patient_id = u.user_id
            WHERE a.doctor_id = ? AND a.status = ? AND u.full_name LIKE ?
        """, (doctor_id, UserStatus.REQUESTED.value, '%' + patient_name + '%',))
        rows = cursor.fetchall()

        assignments = [Assignment(**row) for row in rows]
        return assignments
    
    def approve_patient_request(self, assignment_id):
        """Approves a patient assignment request by changing its status to active."""
        # 1. Fetch the patient_id associated with the assignment to get the name.
        cursor = self.conn.cursor()
        cursor.execute("SELECT patient_id FROM doctor_patient_assignments WHERE assignment_id = ?", (assignment_id,))
        record = cursor.fetchone()
        if not record:
            return {"success": False, "message": "Request not found."}
        
        patient_id = record['patient_id']
        patient_name = self.get_user_fullname(patient_id)

        # 2. Perform Update
        cursor.execute("UPDATE doctor_patient_assignments SET status = ? WHERE assignment_id = ?", (UserStatus.ACTIVE.value, assignment_id,))
        self.conn.commit()
        return {"success": cursor.rowcount > 0, "message": f"Patient {patient_name}'s request approved." if cursor.rowcount > 0 else "Request not found."}
    
    def reject_patient_request(self, assignment_id):
        """Rejects a patient assignment request by deleting it."""
        cursor = self.conn.cursor()

        # 1. Fetch the patient_id associated with the assignment to get the name.
        cursor.execute("SELECT patient_id FROM doctor_patient_assignments WHERE assignment_id = ?", (assignment_id,))
        record = cursor.fetchone()
        if not record:
            return {"success": False, "message": "Request not found."}
        
        patient_id = record['patient_id']
        patient_name = self.get_user_fullname(patient_id)

        # 2. Perform Delete
        cursor.execute("DELETE FROM doctor_patient_assignments WHERE assignment_id = ?", (assignment_id,))
        self.conn.commit()
        return {"success": cursor.rowcount > 0, "message": f"Patient {patient_name}'s request rejected." if cursor.rowcount > 0 else "Request not found."}
    
    def log_prediction(self, prediction: Prediction):
        """Logs a prediction in the database."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO predictions (doctor_id, patient_id, age, cancer_stage, tumor_size, tumor_type, metastasis, treatment_type, comorbidities, predicted_class, prediction_probability)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prediction.doctor_id,
                prediction.patient_id,
                prediction.age,
                prediction.cancer_stage,
                prediction.tumor_size,
                prediction.tumor_type,
                prediction.metastasis,
                prediction.treatment_type,
                prediction.comorbidities,
                prediction.predicted_class,
                prediction.prediction_probability
            ))
            self.conn.commit()
            return {"success": True, "message": "Prediction logged successfully."}
        except sqlite3.Error as e:
            self.conn.rollback()
            return {"success": False, "message": f"Error logging prediction: {str(e)}"}
        
    def __del__(self):
        """Ensures the database connection is closed when the object is deleted."""
        self.close()
