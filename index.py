import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime

# --- Database connection ---
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='12345678',
            database='police'
        )
        return connection
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

def fetch_data(query):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            result = cursor.fetchall()
            return pd.DataFrame(result)
        except Exception as e:
            st.error(f"Query Error: {e}")
        finally:
            cursor.close()
            connection.close()
    return pd.DataFrame()

# --- Page setup ---
st.set_page_config("SecureCheck Police Dashboard", layout="wide")
st.title("🚨 SecureCheck: Police Check Post Digital Ledger")
st.markdown("**Real-time monitoring and insights for law enforcement**")

# --- Display data ---
st.header("Police Logs Overview")
data = fetch_data("SELECT * FROM police_logs")
if data.empty:
    st.warning("No data found in the `police_logs` table. Please check your database.")
else:
    st.dataframe(data, use_container_width=True)

    # --- Metrics ---
    st.header("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Stops", data.shape[0])
    col2.metric("Total Arrests", data[data["stop_outcome"].str.contains("arrest", case=False, na=False)].shape[0])
    col3.metric("Total Warnings", data[data["stop_outcome"].str.contains("warning", case=False, na=False)].shape[0])
    col4.metric("Drug-Related Stops", data[data["drugs_related_stop"] == 1].shape[0])

    # --- Charts ---
    st.header("Visual Insights")
    tab1, tab2 = st.tabs(["Stops by Violation", "Driver Gender Distribution"])

    with tab1:
        if 'violation' in data.columns:
            chart_data = data['violation'].value_counts().reset_index()
            chart_data.columns = ['Violation', 'Count']
            fig = px.bar(chart_data, x='Violation', y='Count', color='Violation', title="Violation Types")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if 'driver_gender' in data.columns:
            gender_data = data['driver_gender'].value_counts().reset_index()
            gender_data.columns = ['Gender', 'Count']
            fig = px.pie(gender_data, names='Gender', values='Count', title="Gender Distribution")
            st.plotly_chart(fig, use_container_width=True)

    # --- Advanced Queries ---
    st.header("Advanced Insights")
    query_options = {
        "Total Number of Police Stops": 
            "SELECT COUNT(*) AS total_stops FROM police_logs",

        "Count of Stops by Violation Type": 
            "SELECT violation, COUNT(*) AS count FROM police_logs GROUP BY violation ORDER BY count DESC",

        "Number of Arrests vs. Warnings": 
            "SELECT stop_outcome, COUNT(*) AS count FROM police_logs GROUP BY stop_outcome",

        "Average Age of Drivers Stopped": 
            "SELECT AVG(driver_age) AS average_age FROM police_logs",

        "Top 5 Most Frequent Search Types": 
            "SELECT search_type, COUNT(*) AS count FROM police_logs WHERE search_type IS NOT NULL AND search_type != '' GROUP BY search_type ORDER BY count DESC LIMIT 5",

        "Count of Stops by Gender": 
            "SELECT driver_gender, COUNT(*) AS count FROM police_logs GROUP BY driver_gender",

        "Most Common Violation for Arrests": 
            "SELECT violation, COUNT(*) AS count FROM police_logs WHERE stop_outcome LIKE '%Arrest%' GROUP BY violation ORDER BY count DESC LIMIT 1",

        "Top 10 Drug-Related Stops (Vehicles)": 
            "SELECT violation, COUNT(*) AS count FROM police_logs WHERE drugs_related_stop = TRUE GROUP BY violation ORDER BY count DESC LIMIT 10",

        "Highest Arrest Rate by Age Group": 
            "SELECT CASE WHEN driver_age < 25 THEN '<25' WHEN driver_age BETWEEN 25 AND 40 THEN '25-40' ELSE '40+' END AS age_group, COUNT(*) FILTER (WHERE is_arrested = TRUE) * 100.0 / COUNT(*) AS arrest_rate FROM police_logs GROUP BY age_group ORDER BY arrest_rate DESC",

        "Violations Rarely Leading to Arrest": 
            "SELECT violation, COUNT(*) FILTER (WHERE is_arrested = TRUE) * 100.0 / COUNT(*) AS arrest_rate FROM police_logs GROUP BY violation HAVING COUNT(*) > 10 ORDER BY arrest_rate ASC LIMIT 5"

    }

    selected_query = st.selectbox("Choose a query to run:", list(query_options.keys()))
    if st.button("Run Query"):
        query_result = fetch_data(query_options[selected_query])
        if not query_result.empty:
            st.subheader(f"Result: {selected_query}")
            st.dataframe(query_result)
        else:
            st.info("No results returned for this query.")

    # --- New Log Prediction Form ---
    st.header("Predict Stop Outcome & Violation")
    with st.form("log_form"):
        stop_date = st.date_input("Stop Date")
        stop_time = st.time_input("Stop Time")
        country_name = st.text_input("Country Name")
        driver_gender = st.selectbox("Driver Gender", ["M", "F"])
        driver_age = st.number_input("Driver Age", min_value=16, max_value=100, value=30)
        driver_race = st.text_input("Driver Race")
        search_conducted = st.selectbox("Search Conducted?", ["0", "1"])
        search_type = st.text_input("Search Type")
        drugs_related_stop = st.selectbox("Drug Related?", ["0", "1"])
        stop_duration = st.selectbox("Stop Duration", data['stop_duration'].dropna().unique())
        vehicle_number = st.text_input("Vehicle Number")

        submitted = st.form_submit_button("Predict")

if submitted:
    st.subheader("Prediction Results")

    stop_time_str = stop_time.strftime("%I:%M %p")
    data['driver_age'] = pd.to_numeric(data['driver_age'], errors='coerce')

    mapped_gender = "M" if driver_gender.lower() == "male" else "F"

    similar = data[
        (data['driver_gender'] == mapped_gender) &
        (abs(data['driver_age'] - driver_age) <= 10)
    ]

    if not similar.empty:
        predicted_violation = similar['violation'].mode()[0] if 'violation' in similar.columns and not similar['violation'].isna().all() else "Unknown"
        predicted_outcome = similar['stop_outcome'].mode()[0] if 'stop_outcome' in similar.columns and not similar['stop_outcome'].isna().all() else "Unknown"
    else:
        predicted_violation = data['violation'].mode()[0] if 'violation' in data.columns else "Unknown"
        predicted_outcome = data['stop_outcome'].mode()[0] if 'stop_outcome' in data.columns else "Unknown"




    search_text = "a search was conducted" if search_conducted == "1" else "no search was conducted"
    drug_text = "was drug-related" if drugs_related_stop == "1" else "was not drug-related"
    search_type_text = f"The search type was **{search_type}**." if search_conducted == "1" and search_type else "No specific search type was recorded."
    race_text = f"The driver belonged to the **{driver_race}** race." if driver_race else "Driver race was not specified."
    vehicle_text = f"The vehicle number was **{vehicle_number}**." if vehicle_number else "Vehicle number was not provided."
    country_text = f"The stop occurred in **{country_name}** country." if country_name else "Country information was not specified."

    
    st.success(f"**Predicted Violation:** {predicted_violation}")
    st.success(f"**Predicted Stop Outcome:** {predicted_outcome}")


    # summary
    summary = (
        f"🚗 A {driver_age}-year-old {driver_gender} driver was stopped for **{predicted_violation}** at **{stop_time_str}**. "
        f"{country_text} {race_text} {vehicle_text} "
        f"{search_text.capitalize()}, and they received a **{predicted_outcome}**. "
        f"The stop lasted **{stop_duration}** and {drug_text}. "
        f"{search_type_text}"
    )

    st.subheader("Predicted Summary:")
    st.markdown(summary)


