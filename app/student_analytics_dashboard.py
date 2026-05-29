import streamlit as st
import pymysql
import pandas as pd

# =========================================
# PAGE CONFIG
# =========================================

st.set_page_config(
    page_title="Student Analytics Dashboard",
    layout="wide"
)

# =========================================
# CUSTOM CSS
# =========================================

st.markdown("""
<style>

.main {
    background-color: #f5f7fb;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.08);
}

.subject-box {
    background: white;
    padding: 15px;
    border-radius: 12px;
    margin-bottom: 10px;
    border-left: 6px solid #4CAF50;
    box-shadow: 0px 2px 5px rgba(0,0,0,0.08);
}

.present {
    color: green;
    font-weight: bold;
}

.absent {
    color: red;
    font-weight: bold;
}

.suspicious {
    color: orange;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# =========================================
# GET STUDENT ID
# =========================================

student_id = st.query_params.get("student_id")

if isinstance(student_id, list):
    student_id = student_id[0]

if not student_id:

    st.error("Student ID not provided")
    st.stop()

# =========================================
# DATABASE CONNECTION
# =========================================

conn = pymysql.connect(

    host="localhost",
    user="root",
    password="Dipti@02",
    database="smart_attendance"

)

# =========================================
# QUERY
# =========================================

query = f'''

SELECT

attendance.id,
attendance.status,

attendance_session.subject,
attendance_session.session_code,

attendance_session.start_time,
attendance_session.end_time

FROM attendance

JOIN attendance_session

ON attendance.session_id =
attendance_session.id

WHERE attendance.student_id =
{student_id}

ORDER BY attendance_session.start_time DESC

'''

df = pd.read_sql(query, conn)

# =========================================
# TITLE
# =========================================

st.title("🎓 Student Attendance Analytics Dashboard")

st.markdown("---")

# =========================================
# METRICS
# =========================================

present = len(df[df.status == "present"])

absent = len(df[df.status == "absent"])

suspicious = len(df[df.status == "suspicious"])

total = len(df)

# =========================================
# OVERALL ATTENDANCE PERCENTAGE
# =========================================

valid_attendance = present + absent

attendance_percent = round(
    (present / valid_attendance) * 100,
    2
) if valid_attendance > 0 else 0

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "✅ Present",
    present
)

c2.metric(
    "❌ Absent",
    absent
)

c3.metric(
    "⚠ Suspicious",
    suspicious
)

c4.metric(
    "📊 Attendance %",
    f"{attendance_percent}%"
)

st.markdown("---")

# =========================================
# BAR CHART
# =========================================

st.subheader("📈 Attendance Overview")

st.bar_chart(
    df["status"].value_counts()
)

st.markdown("---")

# =========================================
# SUBJECT-WISE ANALYTICS
# =========================================

st.subheader("📚 Subject Wise Attendance")

subjects = df["subject"].unique()

for subject in subjects:

    subject_df = df[df["subject"] == subject]

    total_subject = len(subject_df)

    present_subject = len(
        subject_df[subject_df.status == "present"]
    )

    subject_percent = round(
        (present_subject / total_subject) * 100,
        2
    )

    with st.expander(
        f"📘 {subject}  |  Attendance: {subject_percent}%"
    ):

        st.markdown(f"""
        <div class='subject-box'>

        <b>Total Lectures:</b> {total_subject}<br>

        <b>Present:</b> {present_subject}<br>

        <b>Absent:</b> {
            len(subject_df[subject_df.status == "absent"])
        }<br>

        <b>Suspicious:</b> {
            len(subject_df[subject_df.status == "suspicious"])
        }

        </div>
        """, unsafe_allow_html=True)

        # =========================================
        # SESSION HISTORY
        # =========================================

        for index, row in subject_df.iterrows():

            status = row["status"]

            if status == "present":
                status_html = "<span class='present'>✅ PRESENT</span>"

            elif status == "absent":
                status_html = "<span class='absent'>❌ ABSENT</span>"

            else:
                status_html = "<span class='suspicious'>⚠ SUSPICIOUS</span>"

            st.markdown(f"""
            <div class='subject-box'>

            <b>Session Code:</b> {row['session_code']}<br>

            <b>Lecture Start:</b> {row['start_time']}<br>

            <b>Lecture End:</b> {row['end_time']}<br>

            <b>Status:</b> {status_html}

            </div>
            """, unsafe_allow_html=True)

# =========================================
# COMPLETE TABLE
# =========================================

st.markdown("---")

st.subheader("🗂 Complete Attendance Record")

display_df = df.rename(columns={

    "subject": "Subject",
    "status": "Status",
    "session_code": "Session Code",
    "start_time": "Lecture Start",
    "end_time": "Lecture End"

})

st.dataframe(
    display_df,
    use_container_width=True
)