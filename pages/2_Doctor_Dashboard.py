import streamlit as st
from database import DatabaseManager
from ui_components import render_sidebar_and_auth, reset_pagination, render_pagination
from configs import UserRole, HIGH_RISK_THRESHOLD, LOW_RISK_THRESHOLD, ITEMS_PER_PAGE
from models import Prediction
import pandas as pd
from utils import load_model_artifacts, preprocess_for_prediction, to_float, highlight_risk, calculate_age


# --- Initialize Connection and UI Rendering ---
page = render_sidebar_and_auth(UserRole.DOCTOR)
db_manager = DatabaseManager()

# --- Page Content ---
if page == "My Dashboard":
    # --- Initialize page number for pagination ---
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0

    # --- Initialize session state for viewing patient details ---
    if 'viewing_patient_id' not in st.session_state:
        st.session_state.viewing_patient_id = None
    if 'viewing_patient_name' not in st.session_state:
        st.session_state.viewing_patient_name = None
    
    # Details for viewing a specific patient's history function
    def show_patient_details(patient_id, patient_name):
        """ Fetch the complete history for this specific patient """
        st.title(f"History for: {patient_name}")

        if st.button("← Back to Main Dashboard"):
            st.session_state.viewing_patient_id = None
            st.session_state.viewing_patient_name = None
            st.rerun()

        st.divider()

        patient_history = db_manager.get_history_by_patient_id(patient_id)
        if not patient_history:
            st.info("No prediction history found for this patient.")
            return

        # --- Create and Display the Visualization ---
        st.subheader("Risk Trend Over Time")
        chart_data = pd.DataFrame(patient_history)
        chart_data['prediction_timestamp'] = pd.to_datetime(chart_data['prediction_timestamp'])
        chart_data = chart_data.sort_values(by='prediction_timestamp') # Ensure data is sorted for the chart
        chart_data.set_index('prediction_timestamp', inplace=True)
        chart_data = chart_data[['prediction_probability']].rename(columns={'prediction_probability': 'Risk Probability'})
        
        st.line_chart(chart_data)
        
        # --- Display the Detailed Table ---
        st.subheader("Detailed History")
        for record in patient_history:
            cols = st.columns([2, 2.8, 1.5, 1.5])
            cols[0].write(record.prediction_timestamp.strftime('%Y-%m-%d %H:%M:%S'))
            cols[1].write(f"Assessed by: Dr. {record.doctor_name}")
            cols[2].markdown(f'<span style="{highlight_risk(record.predicted_class)}">{record.predicted_class}</span>', unsafe_allow_html=True)
            cols[3].write(f"{to_float(record.prediction_probability):.1%}")
        st.divider()

    # --- Main Page Controller ---
    if st.session_state.viewing_patient_id is not None and st.session_state.viewing_patient_name is not None:
        # If we are viewing a specific patient, show their details
        show_patient_details(st.session_state.viewing_patient_id, st.session_state.viewing_patient_name)

    else:
        cols = st.columns([4, 2, 3])
        with cols[2]:
            search_query = st.text_input("Search by Patient Name", placeholder="🔍 Search by Patient Name", label_visibility="collapsed", on_change=reset_pagination)

        st.divider()

        if search_query:
            predictions = db_manager.search_patients_by_name(st.session_state['user_id'], search_query)
        else:
            predictions = db_manager.get_patient_records(st.session_state['user_id'])

        if not predictions:
            st.info("No patient records found.")
            st.stop()
        else:
            # Slice the predictions for pagination
            start_index = st.session_state.page_number * ITEMS_PER_PAGE
            end_index = start_index + ITEMS_PER_PAGE

            predictions_to_display = predictions[start_index:end_index]

            # Headers for the predictions table
            cols = st.columns([3, 2.5, 2.5, 2, 1])
            headers = ["Visit Time", "Patient Name", "Predicted Class", "Probability", "Actions"]
            for col, header in zip(cols, headers):
                col.markdown(f"**{header}**")

            st.divider()

            # Display prediction records of patients
            for pred in predictions_to_display:
                cols = st.columns([3, 2.5, 2.5, 2, 1])
                cols[0].write(pred.prediction_timestamp)
                cols[1].write(pred.patient_name)
                cols[2].markdown(f'<span style="{highlight_risk(pred.predicted_class)}">{pred.predicted_class}</span>', unsafe_allow_html=True)
                cols[3].write(f"{to_float(pred.prediction_probability):.2%}")

                with cols[4]:
                    if st.button("👁️", key=f"details_{pred.prediction_id}", help="View Patient's Full History and Trend"):
                        st.session_state.viewing_patient_id = pred.patient_id
                        st.session_state.viewing_patient_name = pred.patient_name
                        st.rerun()

            # Render pagination controls
            render_pagination(total_items=len(predictions), items_per_page=ITEMS_PER_PAGE)

elif page == "Predict":
    st.write("Use the form below to make a new prediction for a patient.")
    assigned_patients = db_manager.get_assigned_patients(st.session_state['user_id'])
    if not assigned_patients:
        st.info("You have no assigned patients.")
    else:
        patient_map = {user.full_name: user.user_id for user in assigned_patients}
        patient_name = st.selectbox("Select Patient", options=list(patient_map.keys()), label_visibility="collapsed")
        with st.form("prediction_form"):
            st.write(f"Creating new prediction record for **{patient_name}**")
            st.write("Please fill out the following details for the prediction:")
            cancer_stage = st.selectbox("Cancer Stage", ["I", "II", "III", "IV"])
            tumor_size = st.number_input("Tumor Size (cm)", 0.1, 20.0, 5.0)
            tumor_type = st.selectbox("Tumor Type", ["Stomach", "Lung", "Breast", "Cervical", "Liver", "Colorectal"])
            metastasis = st.selectbox("Metastasis", ["No", "Yes"])
            treatment_type = st.selectbox("Treatment Type", ["Radiation", "Chemotherapy", "Surgery", "Targeted Therapy", "Immunotherapy"])
            comorbidities = st.selectbox("Comorbidities", [
                "No Comorbidities",
                "Diabetes, Hepatitis B",
                "Hepatitis B",
                "Hypertension",
                "Diabetes, Hypertension",
                "Diabetes, Hepatitis B",
                "Hypertension, Hepatitis B"
            ])

            if st.form_submit_button("Submit Prediction"):
                # 1. Calculate age from patient id
                patient_id_to_predict = patient_map.get(patient_name)
                patient_details = db_manager.get_patient_by_id(patient_id_to_predict)
                if patient_details and patient_details.dob:
                    calculated_age = calculate_age(patient_details.dob)
                    st.info(f"Automatically calculated age for {patient_name}: **{calculated_age}**")
                else:
                    st.error("System Error: Unable to calculate age from patient details. Please check the patient's date of birth.")
                    st.stop()

                # 2. Collect inputs
                features = {
                    'Age': calculated_age,
                    'CancerStage': cancer_stage,
                    'TumorSize': tumor_size,
                    'TumorType': tumor_type,
                    'Metastasis': metastasis,
                    'TreatmentType': treatment_type,
                    'Comorbidities': comorbidities
                }
                
                df = pd.DataFrame([features])
                
                # 3. Load model artifacts
                artifacts = load_model_artifacts()
                if not artifacts:
                    st.error("System Error: Model artifacts not found.")
                    st.stop()

                # 4. Preprocess inputs
                df = preprocess_for_prediction(df, artifacts)
                if df is None:
                    st.error("System Error: Error in preprocessing data. Please check your inputs.")
                    st.stop()

                # 5. Load model and make prediction
                model = artifacts['model']
                probability = model.predict_proba(df)[0][1]
                predicted_class = "High Risk" if probability >= HIGH_RISK_THRESHOLD else ("Low Risk" if probability < LOW_RISK_THRESHOLD else "Medium Risk")

                # 6. Log prediction to database
                preds = Prediction(
                    prediction_id=None,  # Auto-incremented by the database
                    prediction_timestamp=None,  # Auto-generated by the database
                    doctor_id=st.session_state['user_id'],
                    patient_id=patient_map[patient_name],
                    age=calculated_age,
                    cancer_stage=cancer_stage,
                    tumor_size=tumor_size,
                    tumor_type=tumor_type,
                    metastasis=metastasis,
                    treatment_type=treatment_type,
                    comorbidities=comorbidities,
                    predicted_class=predicted_class,
                    prediction_probability=probability
                )

                # 7. Convert probability to float
                preds.prediction_probability = to_float(probability)

                # 8. Log the prediction
                result = db_manager.log_prediction(preds)
                if result['success']:
                    st.success(f"Prediction for **{patient_name}**: {predicted_class} (Probability: {probability:.2f})")
                    st.success(result['message'])
                else:
                    st.error(result['message'])

elif page == "Patient Requests":
    # --- Display notification of actions taken on this page ---
    if "patient_request_notification" in st.session_state:
        notification = st.session_state.patient_request_notification
        st.toast(notification["message"], icon=notification["icon"])
        del st.session_state.patient_request_notification

    # --- Initialize page number for pagination ---
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0

    # Search bar for patient requests
    cols = st.columns([4, 1, 3])
    with cols[2]:
        search_query = st.text_input("Search by Patient Name", placeholder="🔍 Search by Patient Name", label_visibility="collapsed", on_change=reset_pagination)

    st.divider()

    if search_query:
        patient_requests = db_manager.search_requests_by_patient_name(st.session_state['user_id'], search_query)
    else:
        patient_requests = db_manager.get_patient_requests(st.session_state['user_id'])

    if not patient_requests:
        st.info("No patient requests found.")
        st.stop()
    else:
        # Slice the patient requests for pagination
        start_index = st.session_state.page_number * ITEMS_PER_PAGE
        end_index = start_index + ITEMS_PER_PAGE

        requests_to_display = patient_requests[start_index:end_index]

        # Headers for the patient requests table
        cols = st.columns([2, 3, 3, 2])
        headers = ["Patient_ID", "Patient Name", "Status", "Actions"]
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")

        st.divider()

        # Display patient request list
        for request in requests_to_display:
            cols = st.columns([2, 3, 3, 2])
            cols[0].write(request.patient_id)
            cols[1].write(request.patient_name)
            cols[2].write(request.status.capitalize())

            with cols[3]:
                action_cols = st.columns(2)
                if action_cols[0].button("✔️", key=f"approve_{request.assignment_id}", help="Approve Request"):
                    result = db_manager.approve_patient_request(request.assignment_id)
                    if result.get("success"):
                            notification = {"message": result.get("message"), "icon": "✅"}
                    else:
                        notification = {"message": result.get("message"), "icon": "❌"}
                    st.session_state.patient_request_notification = notification
                    st.rerun()
                    
                elif action_cols[1].button("❌", key=f"reject_{request.assignment_id}", help="Reject Request"):
                    result = db_manager.reject_patient_request(request.assignment_id)
                    if result.get("success"):
                        notification = {"message": result.get("message"), "icon": "ℹ️"}
                    else:
                        notification = {"message": result.get("message"), "icon": "❌"}
                    st.session_state.patient_request_notification = notification
                    st.rerun()

        st.divider()

        # Render pagination controls
        render_pagination(total_items=len(patient_requests), items_per_page=ITEMS_PER_PAGE)
else:
    st.error("Invalid page selected. Please check your navigation.")