import streamlit as st
import pymysql
import pandas as pd

st.set_page_config(
    page_title="Teacher Dashboard",
    layout="wide"
)

st.title(
    "Teacher Analytics Dashboard"
)

conn=pymysql.connect(
    host="localhost",
    user="root",
    password="Dipti@02",
    database="smart_attendance"
)

query='''
SELECT

student.username,
student.roll_no,
attendance_session.subject,
attendance.status

FROM attendance

JOIN student
ON attendance.student_id=student.id

JOIN attendance_session
ON attendance.session_id=
attendance_session.id
'''

df=pd.read_sql(
    query,
    conn
)

student_stats=[]

for student in df.username.unique():

    temp=df[
        df.username==student
    ]

    total=len(temp)

    present=len(
        temp[
            temp.status=="present"
        ]
    )

    absent=len(
        temp[
            temp.status=="absent"
        ]
    )

    suspicious=len(
        temp[
            temp.status=="suspicious"
        ]
    )

    percentage=0

    if total>0:

        percentage=round(
            present/total*100,
            2
        )

    student_stats.append({

        "Student":student,

        "Present":present,

        "Absent":absent,

        "Suspicious":suspicious,

        "Attendance %":percentage

    })

student_df=pd.DataFrame(
    student_stats
)

c1,c2,c3,c4=st.columns(4)

c1.metric(
    "Students",
    len(student_df)
)

c2.metric(
    "Present",
    len(df[df.status=="present"])
)

c3.metric(
    "Absent",
    len(df[df.status=="absent"])
)

c4.metric(
    "Suspicious",
    len(df[df.status=="suspicious"])
)

st.markdown("---")

st.subheader(
"Subject-wise Attendance"
)

subject=df.groupby(
"subject"
)["status"].count()

st.bar_chart(
subject
)

st.markdown("---")

st.subheader(
"Student Attendance Report"
)

if student_df.empty:

    st.warning(
    "No attendance records found"
    )

else:

    def highlight(row):

        if row["Attendance %"]<50:

            return [
            'background-color:#ff9999'
            ]*len(row)

        return [
            'background-color:#90EE90'
            ]*len(row)

    styled=student_df.style.apply(
        highlight,
        axis=1
    )

    st.dataframe(
        styled,
        use_container_width=True
    )

    st.markdown("---")

    st.subheader(
    "Individual Student"
    )

    selected=st.selectbox(

    "Choose Student",

    student_df["Student"].tolist()

    )

    student_record=df[
        df.username==selected
    ]

    st.dataframe(

        student_record[
        [
        "subject",
        "status"
        ]
        ],

        use_container_width=True
    )

    percent=student_df[

        student_df["Student"]==
        selected

    ]["Attendance %"].iloc[0]

    st.metric(

    "Attendance Percentage",

    f"{percent}%"

    )

    if percent<50:

        st.error(
        "Low Attendance"
        )

    else:

        st.success(
        "Attendance Good"
        )