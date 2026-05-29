from flask import Flask,flash,request,redirect,render_template,url_for,session,Blueprint,send_file
from app import db
import pandas as pd
import numpy as np
import pymysql
import face_recognition

from app.models import (
    Teacher,
    Student,
    TeacherAssignment,
    Schedule,
    TemporaryScheduleChange,
    Notification,AttendanceSession,Attendance,Notice,Doubt
)
import uuid
from datetime import datetime,timedelta

from app import loginmanager,login_required,current_user,logout_user,login_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import base64




route=Blueprint("route",__name__)
@loginmanager.user_loader
def load_user(user_id):

    if not user_id or user_id == "None":
        return None

    role = session.get('role')

    try:

        if role == 'teacher':
            return Teacher.query.get(int(user_id))

        elif role == 'student':
            return Student.query.get(int(user_id))

    except:
        return None

    return None
@route.route('/')
def home():
    return render_template('index.html')

def normalize_time(t):
    if isinstance(t, str):
        return t[:5]
    return t.strftime("%H:%M")



@route.route('/admin_login', methods=['GET', 'POST'])



def admin_login():

    if request.method == 'POST':

        email = request.form.get('email').strip().lower()

        password = request.form.get('password')

        # HARDCODED ADMIN

        if email == "admin@gmail.com" and password == "890":

            session['admin'] = True
            session['role'] = 'admin'

            flash(
                'Admin login successful!',
                'success'
            )
            old_notifications = Notification.query.filter(
    Notification.created_at < datetime.utcnow() - timedelta(days=7)
).all()

            for note in old_notifications:
                 db.session.delete(note)

                 db.session.commit()


            return redirect(
                url_for('route.admin_dashboard')
            )

        else:

            flash(
                'Invalid email or password!',
                'danger'
            )

    return render_template('admin_login.html')


        
            
def build_timetable(schedules):

    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]

    times = ["08:00","09:00","10:00","11:00","12:00",
             "13:00","14:00","15:00","16:00"]

    timetable = []

    for time in times:

        row = {}
        row["time"] = time

        for day in days:

            lecture = None

            for s in schedules:

                # 🔥 FIX: normalize BOTH sides safely
                if isinstance(s.start_time, str):
                    start = s.start_time[:5]
                else:
                    start = s.start_time.strftime("%H:%M")

                if isinstance(s.day, str):
                    s_day = s.day.strip()
                else:
                    s_day = str(s.day)

                if s_day == day and start == time:

                    teacher = Teacher.query.get(s.teacher_id)

                    teacher_name = teacher.username if teacher else ""

                    lecture = f"""
                    <div class='lecture-box'>
                    <b>{s.subject}</b><br>
                    Teacher: {teacher_name}<br>
                    Room: {s.room}<br>
                    {start} - {s.end_time}<br>
                    {s.year} - {s.branch} - {s.division}
                    </div>
                    """
                    break

            row[day] = lecture if lecture else ""

        timetable.append(row)

    return timetable
    
# ADMIN DASHBOARD
# ===============================





@route.route("/admin_dashboard")
def admin_dashboard():

    if session.get('role') != 'admin':
        return redirect(url_for('route.admin_login'))

    year = request.args.get('year')
    branch = request.args.get('branch')
    division = request.args.get('division')
    teacher_id = request.args.get('teacher_id')

    query = Schedule.query

    if year:
        query = query.filter_by(year=year)

    if branch:
        query = query.filter_by(branch=branch)

    if division:
        query = query.filter_by(division=division)

    if teacher_id:
        query = query.filter_by(teacher_id=teacher_id)

    schedules = query.order_by(
        Schedule.day,
        Schedule.start_time
    ).all()

    # Admin has no current_user.id
    notifications=[]

    return render_template(
        "admin_dashboard.html",
        schedules=schedules,
        notifications=notifications
    )
@route.route('/admin_view_teacher_schedule')
def admin_view_teacher_schedule():

    teacher_id = request.args.get('teacher_id')

    teachers = Teacher.query.all()

    schedules = []

    if teacher_id:
        schedules = Schedule.query.filter_by(teacher_id=teacher_id).all()

    return render_template(
        'admin_view_teacher_schedule.html',
        schedules=schedules,
        teachers=teachers
    )

@route.route('/admin_class_schedule', methods=['GET'])

def admin_class_schedule():

    year = request.args.get('year')
    branch = request.args.get('branch')
    division = request.args.get('division')

    schedules = []

    if year and branch and division:
        schedules = Schedule.query.filter_by(
            year=year,
            branch=branch,
            division=division
        ).order_by(Schedule.day, Schedule.start_time).all()

    return render_template(
        "admin_class_schedule.html",
        schedules=schedules
    )
@route.route('/smart_add_schedule', methods=['GET', 'POST'])
def smart_add_schedule():

    if session.get('role') != 'admin':
        return redirect(url_for('route.admin_login'))

    teachers = Teacher.query.all()

    if request.method == 'POST':

        year = request.form.get('year')
        branch = request.form.get('branch')
        division = request.form.get('division')

        teacher_id = request.form.get('teacher_id')
        subject = request.form.get('subject')

        day = request.form.get('day')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        room = request.form.get('room')

        # =========================
        # CHECK ROOM CONFLICT
        # =========================
        conflict = Schedule.query.filter_by(
            day=day,
            start_time=start_time,
            room=room
        ).first()

        if conflict:
            flash("Room already occupied at this time!", "danger")
            return redirect(url_for('route.smart_add_schedule'))

        # =========================
        # GET TEACHER (SAFE FIX ADDED)
        # =========================
        teacher = Teacher.query.get(int(teacher_id))

        if not teacher:
            flash("Invalid teacher selected!", "danger")
            return redirect(url_for('route.smart_add_schedule'))

        # =========================
        # CREATE SCHEDULE
        # =========================
        new_schedule = Schedule(
            teacher_id=teacher.id,
            teacher_name=teacher.username,
            subject=subject,
            year=year,
            branch=branch,
            division=division,
            day=day,
            start_time=start_time,
            end_time=end_time,
            room=room
        )

        db.session.add(new_schedule)
        db.session.commit()

        # =========================
        # MESSAGE
        # =========================
        message = f"""
New Lecture Scheduled

Class: {year} {branch} {division}
Subject: {subject}
Day: {day}
Time: {start_time} - {end_time}
Room: {room}
"""

        # =========================
        # TEACHER NOTIFICATION (SAFE FIX)
        # =========================
        if teacher.id:
            db.session.add(Notification(
                receiver_id=int(teacher.id),
                message=message
            ))

        # =========================
        # STUDENT NOTIFICATIONS (MAIN FIX HERE)
        # =========================
        students = Student.query.filter_by(
            year=year,
            branch=branch,
            division=division
        ).all()

        for s in students:

            # 🔥 SAFETY CHECK (THIS PREVENTS YOUR ERROR)
            if not s or not getattr(s, "id", None):
                continue

            try:
                db.session.add(Notification(
                    receiver_id=int(s.id),
                    message=message
                ))
            except Exception as e:
                print(f"Skipping notification for student {s}: {e}")
                continue

        # =========================
        # FINAL COMMIT (SAFE)
        # =========================
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Error while saving notifications: {str(e)}", "danger")
            return redirect(url_for('route.smart_add_schedule'))

        flash("Schedule added successfully!", "success")

        return redirect(url_for('route.admin_dashboard'))

    return render_template(
        "smart_add_schedule.html",
        teachers=teachers
    )

@route.route('/check_rooms', methods=['GET', 'POST'])
@login_required
def check_rooms():

    available_rooms = []

    if request.method == 'POST':

        day = request.form.get('day')
        start_time = request.form.get('start_time')

        # ALL ROOMS IN COLLEGE
        all_rooms = [
            'E100',
            'E101',
            'E102',
            'E103',
            'E104',
            'Lab1',
            'Lab2',
            'Lab3'
        ]

        # GET LECTURES OCCUPYING SAME SLOT
        occupied_lectures = Schedule.query.filter(
            Schedule.day == day,
            Schedule.start_time == start_time
        ).all()

        # EXTRACT OCCUPIED ROOM NAMES
        occupied_rooms = []

        for lecture in occupied_lectures:

            occupied_rooms.append(
                lecture.room.strip()
            )

        # FIND EMPTY ROOMS ONLY
        for room in all_rooms:

            if room not in occupied_rooms:

                available_rooms.append(room)

    return render_template(
        'check_rooms.html',
        available_rooms=available_rooms
    )
@route.route('/teacher_register', methods=['GET', 'POST'])
def teacher_register():

    if request.method == 'POST':

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = Teacher.query.filter_by(email=email).first()

        if existing_user:
            flash('Email already exists!', 'danger')
            return redirect(url_for('route.teacher_register'))

        hashed_password = generate_password_hash(password)

        new_teacher = Teacher(
            username=username,
            email=email,
            password=hashed_password,
            role='teacher'
        )

        db.session.add(new_teacher)
        db.session.commit()

        flash('Teacher registration successful!', 'success')

        return redirect(url_for('route.teacher_login'))

    return render_template('teacher_register.html')

@route.route('/teacher_login', methods=['GET', 'POST'])

def teacher_login():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        # CHECK TEACHER EXISTS

        user = Teacher.query.filter_by(email=email).first()

        # VERIFY PASSWORD

        if user and check_password_hash(user.password, password):

            login_user(user)
            session['role'] = 'teacher'
            session['user_id'] = user.id
            print(current_user.is_authenticated)  # DEBUG ONLY


            flash('Teacher login successful!', 'success')
            old_notifications = Notification.query.filter(
        Notification.created_at <
        datetime.utcnow() - timedelta(days=7)
        ).all()
            for note in old_notifications:
                db.session.delete(note)

                db.session.commit()


            return redirect(url_for('route.teacher_dashboard'))

        else:

            flash('Invalid email or password!', 'danger')
        


    return render_template('teacher_login.html')


@route.route('/student_register', methods=['GET', 'POST'])
def student_register():

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        student_id = request.form.get('student_id')
        roll_no = request.form.get('roll_no')

        year = request.form.get(
    'year'
).strip().upper()

        branch = request.form.get(
    'branch'
).strip().upper()

        division = request.form.get(
    'division'
).strip().upper()

        captured_image = request.form.get('captured_image')



        UPLOAD_FOLDER = os.path.join('static', 'uploads')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        existing_user = Student.query.filter_by(email=email).first()

        if existing_user:
            flash('Email already exists!', 'danger')
            return redirect(url_for('route.student_register'))

        hashed_password = generate_password_hash(password)

        # ------------------------
        # SAVE IMAGE
        # ------------------------
        image_data = captured_image.split(',')[1]
        image_binary = base64.b64decode(image_data)

        filename = secure_filename(f"{username}.png")
        save_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(save_path, 'wb') as f:
            f.write(image_binary)

        # ------------------------
        # CREATE STUDENT
        # ------------------------
        new_student = Student(
            username=username,
            email=email,
            password=hashed_password,
            student_id=student_id,
            roll_no=roll_no,
            year=year,
            branch=branch,
            division=division,
            role='student',
            image_file=filename
        )

        db.session.add(new_student)
        db.session.commit()

        # ------------------------
        # FACE ENCODING (FIXED)
        # ------------------------
        try:
            import face_recognition
            import numpy as np

            image = face_recognition.load_image_file(save_path)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) == 0:
                flash("No face detected!", "danger")
                return redirect(url_for('route.student_register'))

            encoding = encodings[0]

            encoding_folder = "encodings"
            os.makedirs(encoding_folder, exist_ok=True)

            np.save(
                os.path.join(encoding_folder, f"{new_student.id}.npy"),
                encoding
            )

        except Exception as e:
            print("Face encoding error:", e)

        flash('Student registration successful!', 'success')
        return redirect(url_for('route.student_login'))

    return render_template('student_register.html')
@route.route('/student_login', methods=['GET', 'POST'])
def student_login():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        user = Student.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            login_user(user)
            session['role'] = 'student'
            session['user_id'] = user.id

            flash('Student login successful!', 'success')
            old_notifications = Notification.query.filter(
    Notification.created_at <
    datetime.utcnow() - timedelta(days=7)
).all()

            for note in old_notifications:
               db.session.delete(note)

               db.session.commit()

            return redirect(url_for('route.student_dashboard'))

        else:

            flash('Invalid email or password!', 'danger')

    return render_template('student_login.html')



@route.route('/teacher_dashboard')
@login_required
def teacher_dashboard():

    if current_user.role!='teacher':
        return redirect(
            url_for(
                'route.teacher_login'
            )
        )

    schedules=Schedule.query.filter_by(
        teacher_id=current_user.id
    ).all()

    notifications=Notification.query.filter_by(
        receiver_id=current_user.id
    ).all()

    now=datetime.utcnow()

    active_sessions=AttendanceSession.query.filter(

    AttendanceSession.teacher_id==
    current_user.id,

    AttendanceSession.end_time>
    now

).all()

    old_sessions=AttendanceSession.query.filter(

    AttendanceSession.teacher_id==
    current_user.id,

    AttendanceSession.end_time<=
    now

).all()
    
    teacher_notices=Notice.query.filter_by(

    teacher_id=current_user.id

).order_by(

    Notice.created_at.desc()

).all()
    
    teacher_doubts=Doubt.query.filter_by(
    teacher_id=current_user.id
).order_by(
    Doubt.created_at.desc()
).all()


    new_doubt_count=Doubt.query.filter_by(
    teacher_id=current_user.id,
    is_seen=False
).count()

    return render_template(

        "teacher_dashboard.html",

        schedules=schedules,

        notifications=notifications,
        sessions=active_sessions,

        old_sessions=old_sessions,
        teacher_notices=teacher_notices,
        teacher_doubts=teacher_doubts,
        new_doubt_count=new_doubt_count

    )


@route.route("/teacher_analytics")
@login_required
def teacher_analytics():

    if current_user.role != "teacher":

        flash(
            "Access denied",
            "danger"
        )

        return redirect(
            url_for("route.teacher_login")
        )

    return redirect(
        "http://localhost:8501/teacher_dashboard"
    )


@route.route('/student_analytics')
@login_required
def student_analytics():

    if current_user.role != "student":

        flash(
            "Access denied",
            "danger"
        )

        return redirect(
            url_for("route.student_login")
        )

    return redirect(
    f"http://localhost:8501/?student_id={current_user.id}"
)
@route.route('/student_dashboard')
@login_required
def student_dashboard():

    if current_user.role != 'student':
        return redirect(url_for('route.student_login'))

    # student schedule
    schedules = Schedule.query.filter_by(
        year=current_user.year,
        branch=current_user.branch,
        division=current_user.division
    ).all()

    # active sessions only (IMPORTANT FIX)
    sessions = AttendanceSession.query.filter_by(
        year=current_user.year,
        branch=current_user.branch,
        division=current_user.division,
        is_active=True
    ).all()
    now = datetime.utcnow()

    
    # attendance stats (student-only)
    present_count = Attendance.query.filter_by(
        student_id=current_user.id,
        status='present'
    ).count()

    absent_count = Attendance.query.filter_by(
        student_id=current_user.id,
        status='absent'
    ).count()

    total = present_count + absent_count

    attendance_percent = round((present_count / total) * 100, 2) if total else 0
    time_slots = [
        "08:00",
        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00"
    ]
    notifications = Notification.query.filter_by(
    receiver_id=current_user.id
).order_by(
    Notification.created_at.desc()
).all()


    notices = Notice.query.filter(

    Notice.year==
    current_user.year.strip().upper(),

    Notice.branch==
    current_user.branch.strip().upper(),

    Notice.division==
    current_user.division.strip().upper()

).order_by(

    Notice.created_at.desc()

).all()
    
    student_doubts=Doubt.query.filter_by(

    year=current_user.year,
    branch=current_user.branch,
    division=current_user.division

).order_by(

    Doubt.created_at.desc()

).all()

    teachers=Teacher.query.all()
    new_doubt_count=Doubt.query.filter_by(

    year=current_user.year,
    branch=current_user.branch,
    division=current_user.division,
    answer=None

).count()

    # IMPORTANT: only 2 things needed for dashboard
    return render_template(
        "student_dashboard.html",
        schedules=schedules,
        sessions=sessions,
        notifications=notifications,
        present_count=present_count,
        absent_count=absent_count,
        attendance_percent=attendance_percent,
        now=now,
        time_slots=time_slots,
        notices=notices,
        student_doubts=student_doubts,
        new_doubt_count=new_doubt_count,
        teachers=teachers,


    )

@login_required
def session_dashboard(code):

    session_obj=AttendanceSession.query.filter_by(
        session_code=code
    ).first_or_404()

    records=Attendance.query.filter_by(
        session_id=session_obj.id
    ).all()

    return render_template(

        "session_dashboard.html",

        session_obj=session_obj,

        records=records
    )

@route.route(
'/override_attendance/<int:id>',
methods=['POST']
)
@login_required
def override_attendance(id):

    record=Attendance.query.get_or_404(id)

    decision=request.form[
        'decision'
    ]

    record.teacher_decision=decision

    record.status=decision

    db.session.commit()

    flash(
        "Attendance updated",
        "success"
    )

    return redirect(
        request.referrer
    )




    
@route.route('/view_students')
@login_required

def view_students():

    if current_user.role != 'teacher':
        flash('Access denied!', 'danger')
        return redirect(url_for('route.teacher_login'))

    # GET PARAMETERS FROM TEACHER
    year = request.args.get('year')
    branch = request.args.get('branch')
    division = request.args.get('division')

    # SAFETY CHECK
    if not year or not branch or not division:
        flash("Please select all fields", "danger")
        return redirect(url_for('route.teacher_dashboard'))

    students = Student.query.filter_by(
        year=year,
        branch=branch,
        division=division
    ).all()

    return render_template(
        'view_students.html',
        students=students,
        strength=len(students),
        year=year,
        branch=branch,
        division=division
    )
@route.route('/view_class_schedule')
@login_required
def view_class_schedule():

    if current_user.role != 'teacher':
        return redirect(url_for('route.teacher_login'))

    year = request.args.get('year')
    branch = request.args.get('branch')
    division = request.args.get('division')

    schedules = []

    if year and branch and division:
        schedules = Schedule.query.filter_by(
            year=year,
            branch=branch,
            division=division
        ).order_by(Schedule.day, Schedule.start_time).all()

    return render_template(
        "teacher_class_schedule.html",
        schedules=schedules,
        year=year,
        branch=branch,
        division=division
    )





@route.route('/admin_add_schedule', methods=['GET', 'POST'])
def admin_add_schedule():

    if session.get('role') != 'admin':
        return redirect(url_for('route.admin_login'))

    if request.method == 'POST':

        teacher_id = request.form.get('teacher_id')

        schedule = Schedule(

            teacher_id=teacher_id,
            subject=request.form.get('subject').strip(),
            year=request.form.get('year').strip(),
            branch=request.form.get('branch').strip(),
            division=request.form.get('division').strip(),
            day=request.form.get('day').strip(),
            start_time=request.form.get('start_time').strip(),
            end_time=request.form.get('end_time').strip(),
            room=request.form.get('room').strip()
        )

        db.session.add(schedule)
        db.session.commit()

        flash("Schedule Added Successfully!", "success")

        return redirect(url_for('route.admin_dashboard'))

    teachers = Teacher.query.all()

    return render_template(
        'admin_add_schedule.html',
        teachers=teachers
    )
       
# @route.route(
#     "/upload_schedule",
#     methods=["POST"]
# )
# def upload_schedule():

#     import pandas as pd

#     file = request.files["file"]

#     if file.filename == "":

#         flash(
#             "No file selected",
#             "danger"
#         )

#         return redirect(
#             url_for("route.admin_dashboard")
#         )

#     df = pd.read_csv(file)

#     conn = pymysql.connect(

#     host="localhost",
#     user="root",
#     password="Dipti@02",
#     database="smart_attendance"

# )

#     cursor = conn.cursor()

#     for _, row in df.iterrows():

#         cursor.execute("""

#         INSERT INTO schedule(

#             subject,
#             teacher_name,
#             day,
#             start_time,
#             end_time,
#             room,
#             year,
#             branch,
#             division

#         )

#         VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)

#         """,(

#             row["subject"],
#             row["teacher"],
#             row["day"],
#             row["start_time"],
#             row["end_time"],
#             row["room"],
#             row["year"],
#             row["branch"],
#             row["division"]

#         ))

#     conn.commit()

#     cursor.close()
#     conn.close()

#     flash(
#         "Schedule uploaded successfully",
#         "success"
#     )

#     return redirect(
#         url_for("route.admin_dashboard")
#     )
@route.route('/teacher_schedule', methods=["GET","POST"])
@login_required
def teacher_schedule():

    # ==========================
    # ALL ROOMS
    # ==========================

    all_rooms = [
        "E100",
        "E101",
        "E102",
        "E103",
        "E104",
        "E105",
        "E106",
        "E107",
        "E108",
        "E109",
        "E110",
        "Lab1",
        "Lab2",
        "Lab3"
    ]

    selected_day = request.args.get("day")
    selected_time = request.args.get("start_time")

    free_rooms = all_rooms.copy()

    # ==========================
    # FIND EMPTY ROOMS
    # ==========================

    if selected_day and selected_time:

        selected_time_obj = datetime.strptime(
            selected_time,
            "%H:%M"
        ).time()

        occupied = Schedule.query.filter(

            Schedule.day == selected_day,
            Schedule.start_time == selected_time_obj

        ).all()

        occupied_rooms = [

            x.room.strip()

            for x in occupied

        ]

        free_rooms = [

            room for room in all_rooms
            if room not in occupied_rooms

        ]


    # ==========================
    # SAVE LECTURE
    # ==========================

    if request.method == "POST":

        subject = request.form.get("subject")
        day = request.form.get("day")

        start_time = request.form.get(
            "start_time"
        )

        end_time = request.form.get(
            "end_time"
        )

        year = request.form.get("year")
        branch = request.form.get("branch")
        division = request.form.get("division")
        room = request.form.get("room")

        valid_from = request.form.get(
            "valid_from"
        )

        valid_until = request.form.get(
            "valid_until"
        )

        start_time_obj = datetime.strptime(
            start_time,
            "%H:%M"
        ).time()

        end_time_obj = datetime.strptime(
            end_time,
            "%H:%M"
        ).time()


        # ==========================
        # CLASS CONFLICT
        # ==========================

        class_conflict = Schedule.query.filter(

            Schedule.day == day,

            Schedule.start_time == start_time_obj,

            Schedule.year == year,

            Schedule.branch == branch,

            Schedule.division == division

        ).first()


        if class_conflict:

            teacher = Teacher.query.get(
                class_conflict.teacher_id
            )

            teacher_name = (
                teacher.username
                if teacher
                else "Unknown"
            )

            flash(

                f"Lecture already assigned by {teacher_name}",

                "danger"

            )

            return redirect(
                url_for(
                    "route.teacher_schedule"
                )
            )


        # ==========================
        # TEACHER CONFLICT
        # ==========================

        teacher_conflict = Schedule.query.filter(

            Schedule.teacher_id ==
            current_user.id,

            Schedule.day == day,

            Schedule.start_time ==
            start_time_obj

        ).first()


        if teacher_conflict:

            flash(

                "You already have a lecture at this time",

                "danger"

            )

            return redirect(
                url_for(
                    "route.teacher_schedule"
                )
            )


        # ==========================
        # ROOM CONFLICT
        # ==========================

        room_conflict = Schedule.query.filter(

            Schedule.day == day,

            Schedule.start_time ==
            start_time_obj,

            Schedule.room == room

        ).first()


        if room_conflict:

            flash(

                f"Room {room} already occupied",

                "danger"

            )

            return redirect(
                url_for(
                    "route.teacher_schedule"
                )
            )


        # ==========================
        # SAVE
        # ==========================

        new_schedule = Schedule(

            teacher_id=current_user.id,

            subject=subject,

            day=day,

            start_time=start_time_obj,

            end_time=end_time_obj,

            year=year,

            branch=branch,

            division=division,

            room=room,

            valid_from=valid_from,

            valid_until=valid_until
        )

        db.session.add(
            new_schedule
        )


        # ==========================
        # NOTIFICATIONS
        # ==========================

        message = f"""
Schedule Updated

Subject : {subject}

Class :
{year} {branch} {division}

Day :
{day}

Time :
{start_time}-{end_time}

Room :
{room}
"""


        students = Student.query.filter_by(

            year=year,
            branch=branch,
            division=division

        ).all()


        for s in students:

            db.session.add(

                Notification(

                    receiver_id=s.id,

                    message=message
                )
            )


        teachers = Teacher.query.all()

        for t in teachers:

            db.session.add(

                Notification(

                    receiver_id=t.id,

                    message=message
                )
            )


        db.session.commit()


        flash(
            "Lecture saved successfully",
            "success"
        )

        return redirect(
            url_for(
                "route.teacher_schedule"
            )
        )


    # ==========================
    # DISPLAY SCHEDULE
    # ==========================

    schedules = Schedule.query.filter_by(

        teacher_id=current_user.id

    ).all()


    days = [

        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday"

    ]


    time_slots = [

        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00"

    ]


    timetable = {}


    for slot in time_slots:

        timetable[slot] = {}

        for d in days:

            timetable[slot][d] = None


    for s in schedules:

        d = s.day.strip()

        t = s.start_time.strftime(
            "%H:%M"
        )

        if t in timetable:

            timetable[t][d] = s


    return render_template(

        "teacher_schedule.html",

        timetable=timetable,

        days=days,

        time_slots=time_slots,

        free_rooms=free_rooms
    )
@route.route('/view_schedule', methods=['GET'])
@login_required
def view_schedule():

    year = request.args.get("year")
    branch = request.args.get("branch")
    division = request.args.get("division")

    schedules = Schedule.query.filter_by(
        year=year,
        branch=branch,
        division=division
    ).all()

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday"
    ]

    time_slots = [
        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00"
    ]

    timetable = {}

    for slot in time_slots:

        timetable[slot] = {}

        for day in days:
            timetable[slot][day] = None


    for s in schedules:

        day = s.day.strip().capitalize()

        time = s.start_time.strftime("%H:%M")

        if day in days and time in timetable:

            timetable[time][day] = s


    return render_template(
        "class_schedule.html",
        timetable=timetable,
        days=days,
        time_slots=time_slots,
        year=year,
        branch=branch,
        division=division
    )

@route.route('/edit_schedule/<int:id>', methods=['GET','POST'])
@login_required
def edit_schedule(id):

    schedule = Schedule.query.get_or_404(id)

    if current_user.role != "teacher":
        return "Unauthorized",403


    days=[
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday"
    ]

    all_rooms=[
        "E100",
        "E101",
        "E102",
        "E103",
        "Lab1",
        "Lab2",
        "Lab3"
    ]


    if request.method=="POST":

        day=request.form.get("day")
        start_time=request.form.get("start_time")
        end_time=request.form.get("end_time")
        room=request.form.get("room")

        valid_until=request.form.get(
            "valid_until"
        )


        # ROOM CONFLICT CHECK

        conflict=Schedule.query.filter(

            Schedule.id!=schedule.id,
            Schedule.day==day,
            Schedule.start_time==start_time,
            Schedule.room==room

        ).first()


        if conflict:

            flash(
                f"Room {room} already assigned at {start_time}",
                "danger"
            )

            return redirect(
                url_for(
                    "route.edit_schedule",
                    id=id
                )
            )


        # UPDATE

        schedule.subject=request.form.get(
            "subject"
        )

        schedule.day=day
        schedule.start_time=start_time
        schedule.end_time=end_time

        schedule.year=request.form.get(
            "year"
        )

        schedule.branch=request.form.get(
            "branch"
        )

        schedule.division=request.form.get(
            "division"
        )

        schedule.room=room

        db.session.commit()


        # CREATE TEMP CHANGE ENTRY

        temp=TemporaryScheduleChange(

            schedule_id=schedule.id,

            valid_until=datetime.strptime(
                valid_until,
                "%Y-%m-%d"
            )
        )

        db.session.add(temp)


        # NOTIFY STUDENTS

        students=Student.query.filter_by(

            year=schedule.year,
            branch=schedule.branch,
            division=schedule.division

        ).all()


        message=f"""

Schedule updated

Subject:
{schedule.subject}

Day:
{day}

Time:
{start_time}-{end_time}

Room:
{room}

Valid till:
{valid_until}

"""


        for s in students:

            db.session.add(

                Notification(

                    receiver_id=s.id,
                    message=message
                )

            )


        # NOTIFY TEACHERS

        teachers=Teacher.query.all()

        for t in teachers:

            db.session.add(

                Notification(

                    receiver_id=t.id,
                    message=message
                )

            )


        db.session.commit()


        flash(
            "Schedule updated successfully",
            "success"
        )

        return redirect(
            url_for(
                "route.teacher_schedule"
            )
        )


    # FREE ROOMS

    occupied=Schedule.query.filter_by(

        day=schedule.day,
        start_time=schedule.start_time

    ).all()


    occupied_rooms=[x.room for x in occupied]

    free_rooms=[

        room for room in all_rooms
        if room not in occupied_rooms

    ]


    return render_template(

        "edit_schedule.html",

        schedule=schedule,

        days=days,

        free_rooms=free_rooms
    )
    
@route.route('/delete_notification/<int:id>')
@login_required
def delete_notification(id):

    notification = Notification.query.get_or_404(id)

    if notification.receiver_id != current_user.id:
        flash("Access denied", "danger")
        return redirect(url_for('route.home'))

    db.session.delete(notification)
    db.session.commit()

    return redirect(request.referrer)

@route.route('/mark_seen/<int:id>')
@login_required
def mark_seen(id):

    notification=Notification.query.get_or_404(
        id
    )

    if notification.receiver_id != current_user.id:

        flash(
            "Access denied",
            "danger"
        )

        return redirect(
            url_for(
                'route.home'
            )
        )

    notification.is_seen=True

    db.session.commit()

    return redirect(
        request.referrer
    )




@route.route('/create_session', methods=['POST'])
@login_required
def create_session():

    if current_user.role!='teacher':
        return "Unauthorized",403

    year=request.form['year']
    branch=request.form['branch']
    division=request.form['division']
    subject=request.form['subject']

    duration=int(
        request.form['duration']
    )

    code=str(
        uuid.uuid4()
    )[:6]

    new_session=AttendanceSession(

        teacher_id=current_user.id,

        subject=subject,

        year=year,
        branch=branch,
        division=division,

        session_code=code,

        start_time=datetime.utcnow(),

        end_time=
        datetime.utcnow()
        +timedelta(
            minutes=duration
        )

    )

    db.session.add(
        new_session
    )

    students=Student.query.filter_by(

        year=year,
        branch=branch,
        division=division

    ).all()

    for s in students:

        note=Notification(

            receiver_id=s.id,

            message=f"""
Teacher created attendance

Subject:
{subject}

Time:
{new_session.start_time.strftime('%H:%M')}
-
{new_session.end_time.strftime('%H:%M')}

Session Code:
{code}
"""

        )

        db.session.add(note)

    db.session.commit()

    flash(
        "Attendance session created",
        "success"
    )

    return redirect(
        url_for(
            'route.teacher_dashboard'
        )
    )

@route.route('/delete_session/<int:id>')
@login_required
def delete_session(id):

    session_obj = AttendanceSession.query.get_or_404(id)

    # allow only teacher who created it
    if current_user.role != "teacher" or session_obj.teacher_id != current_user.id:
        flash("Unauthorized access", "danger")
        return redirect(
            url_for('route.teacher_dashboard')
        )

    # delete attendance records first
    Attendance.query.filter_by(
        session_id=session_obj.id
    ).delete()

    db.session.delete(session_obj)

    db.session.commit()

    flash(
        "Session deleted successfully",
        "success"
    )

    return redirect(
        url_for('route.teacher_dashboard')
    )
@route.route('/join_session/<code>', methods=['GET', 'POST'])
@login_required
def join_session(code):

    if current_user.role != "student":
        return "Unauthorized"

    session_obj = AttendanceSession.query.filter_by(
        session_code=code
    ).first()

    if not session_obj:

        flash(
            "Invalid Session",
            "danger"
        )

        return redirect(
            url_for('route.student_dashboard')
        )

    # SESSION EXPIRED
    if datetime.utcnow() > session_obj.end_time:

        flash(
            "Session expired",
            "danger"
        )

        return redirect(
            url_for('route.student_dashboard')
        )

    # ALREADY SUBMITTED
    existing = Attendance.query.filter_by(

        student_id=current_user.id,
        session_id=session_obj.id

    ).first()

    if existing:

        flash(
            "Attendance already submitted",
            "warning"
        )

        return redirect(
            url_for('route.student_dashboard')
        )

    # OPEN CAMERA PAGE
    if request.method == "GET":

        return render_template(
            'join_session.html'
        )

    # =========================
    # POST REQUEST
    # =========================

    image = request.form.get("image")

    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")

    if not image:

        flash(
            "Capture photo first",
            "danger"
        )

        return redirect(request.url)

    try:

        header, encoded = image.split(",")

        image_binary = base64.b64decode(encoded)

    except Exception:

        flash(
            "Invalid image format",
            "danger"
        )

        return redirect(request.url)

    # SAVE SELFIE
    filename = f"{current_user.id}_{code}.jpg"

    os.makedirs(
        "static/selfies",
        exist_ok=True
    )

    path = os.path.join(
        "static/selfies",
        filename
    )

    with open(path, "wb") as f:
        f.write(image_binary)

    # SAVE ATTENDANCE
    attendance = Attendance(

        student_id=current_user.id,

        session_id=session_obj.id,

        image_file=filename,

        latitude=float(latitude) if latitude else 0,

        longitude=float(longitude) if longitude else 0,

        status="present"
    )

    db.session.add(attendance)

    db.session.commit()

    flash(
        "Attendance marked successfully!",
        "success"
    )

    return redirect(
        url_for('route.student_dashboard')
    )

@route.route(
    '/send_notice',
    methods=['POST']
)
@login_required
def send_notice():

    if current_user.role != "teacher":
        return "Unauthorized", 403

    message = request.form.get("message")

    year = request.form.get("year")
    branch = request.form.get("branch")
    division = request.form.get("division")

    if not message:

        flash(
            "Notice message cannot be empty",
            "danger"
        )

        return redirect(
            url_for('route.teacher_dashboard')
        )

    # SAVE NOTICE
    notice = Notice(

        teacher_id=current_user.id,

        teacher_name=current_user.username,

        message=message,

        year=year,

        branch=branch,

        division=division
    )

    db.session.add(notice)

    # SEND NOTIFICATIONS TO STUDENTS
    students = Student.query.filter_by(

        year=year,
        branch=branch,
        division=division

    ).all()

    for student in students:

        notification = Notification(

            receiver_id=student.id,

            message=f"""
New Notice From {current_user.username}

{message}
"""
        )

        db.session.add(notification)

    db.session.commit()

    flash(
        "Notice sent successfully!",
        "success"
    )

    return redirect(
        url_for('route.teacher_dashboard')
    )

@route.route(
    '/upload_class_photo/<code>',
    methods=['POST']
)
@login_required
def upload_class_photo(code):

    if current_user.role != "teacher":
        return "Unauthorized",403

    session_obj=AttendanceSession.query.filter_by(
        session_code=code
    ).first_or_404()

    file=request.files.get(
        "class_image"
    )

    if not file:
        flash(
            "Please upload image",
            "danger"
        )

        return redirect(
            request.referrer
        )

    folder="static/class_photos"

    os.makedirs(
        folder,
        exist_ok=True
    )

    filename=secure_filename(
        file.filename
    )

    path=os.path.join(
        folder,
        filename
    )

    file.save(path)

    image=face_recognition.load_image_file(
        path
    )

    face_locations=face_recognition.face_locations(
        image
    )

    face_encodings=face_recognition.face_encodings(
        image,
        face_locations
    )

    students=Student.query.filter_by(

        year=session_obj.year,
        branch=session_obj.branch,
        division=session_obj.division

    ).all()

    matched=[]

    for face_encoding in face_encodings:

        for student in students:

            encoding_path=f"encodings/{student.id}.npy"

            if not os.path.exists(
                encoding_path
            ):
                continue

            student_encoding=np.load(
                encoding_path
            )

            result=face_recognition.compare_faces(

                [student_encoding],
                face_encoding,
                tolerance=0.45
            )

            if result[0]:

                matched.append(
                    student.id
                )

                break


   # AUTO MARK ONLY FACE MATCHED STUDENTS

    for student_id in matched:

        existing = Attendance.query.filter_by(

        student_id=student_id,
        session_id=session_obj.id

    ).first()

        if existing:
           continue

        record = Attendance(

        student_id=student_id,
        session_id=session_obj.id,
        status="present"

    )

        db.session.add(record)


    db.session.commit()

    flash(
        "Photo analyzed successfully",
        "success"
    )

    return redirect(

        url_for(
            "route.session_dashboard",
            code=code
        )
    )


@route.route('/session_dashboard/<code>')
@login_required
def session_dashboard(code):

    session_obj = AttendanceSession.query.filter_by(
        session_code=code
    ).first_or_404()

    attendance = Attendance.query.filter_by(
        session_id=session_obj.id
    ).all()

    # TOTAL CLASS STUDENTS
    total_students = Student.query.filter_by(
        year=session_obj.year,
        branch=session_obj.branch,
        division=session_obj.division
    ).count()

    # COUNTS
    present_count = Attendance.query.filter_by(
        session_id=session_obj.id,
        status="present"
    ).count()

    absent_count = Attendance.query.filter_by(
        session_id=session_obj.id,
        status="absent"
    ).count()

    suspicious_count = Attendance.query.filter_by(
        session_id=session_obj.id,
        status="suspicious"
    ).count()

    return render_template(

        "session_dashboard.html",

        session_obj=session_obj,

        attendance=attendance,

        total_students=total_students,

        present_count=present_count,

        absent_count=absent_count,

        suspicious_count=suspicious_count
    )


@route.route('/export_notices')
@login_required
def export_notices():

    import os
    import pandas as pd
    from flask import send_file

    notices = Notice.query.all()

    data=[]

    for n in notices:

        data.append({

            "Teacher":n.teacher_name,
            "Message":n.message,
            "Year":n.year,
            "Branch":n.branch,
            "Division":n.division,
            "Date":n.created_at

        })

    df=pd.DataFrame(data)

    # Create folder automatically
    export_folder=os.path.join(
        os.getcwd(),
        "exports"
    )

    os.makedirs(
        export_folder,
        exist_ok=True
    )

    csv_path=os.path.join(
        export_folder,
        "notices.csv"
    )

    df.to_csv(
        csv_path,
        index=False
    )

    return send_file(
        csv_path,
        as_attachment=True
    )
@route.route(
'/add_doubt',
methods=['POST']
)
@login_required
def add_doubt():

    subject=request.form.get(
        'subject'
    )

    teacher_id=request.form.get(
        'teacher_id'
    )

    message=request.form.get(
        'message'
    )

    doubt=Doubt(

        student_id=current_user.id,

        subject=subject,

        teacher_id=teacher_id,

        message=message,

        year=current_user.year,

        branch=current_user.branch,

        division=current_user.division

    )

    db.session.add(
        doubt
    )

    notification=Notification(

        receiver_id=teacher_id,

        message=f"New doubt in {subject} from {current_user.year} {current_user.branch} {current_user.division}"

    )

    db.session.add(
        notification
    )

    db.session.commit()

    flash(
        "Doubt posted",
        "success"
    )

    return redirect(
        url_for(
            'route.student_dashboard'
        )
    )

@route.route(
'/answer_doubt/<int:id>',
methods=['POST']
)
@login_required
def answer_doubt(id):

    doubt=Doubt.query.get_or_404(id)

    doubt.answer=request.form.get(
        'answer'
    )

    doubt.is_seen=True

    db.session.commit()

    return redirect(
        url_for(
            'route.teacher_dashboard'
        )
    )

@route.route(
'/post_doubt',
methods=['POST']
)
@login_required
def post_doubt():

    doubt=Doubt(

        teacher_id=request.form.get(
            'teacher_id'
        ),

        subject=request.form.get(
            'subject'
        ),

        message=request.form.get(
            'message'
        ),

        year=current_user.year,

        branch=current_user.branch,

        division=current_user.division,

        is_seen=False
    )

    db.session.add(
        doubt
    )

    db.session.commit()

    return redirect(
        url_for(
            'route.student_dashboard'
        )
    )

@route.route('/admin_schedule_view', methods=['GET'])
def admin_schedule_view():

    year = request.args.get("year")
    branch = request.args.get("branch")
    division = request.args.get("division")

    schedules = []

    if year and branch and division:

        schedules = Schedule.query.filter_by(
            year=year,
            branch=branch,
            division=division
        ).all()

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday"
    ]

    time_slots = [

        "08:00",
        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00"

    ]

    timetable = {}

    for slot in time_slots:

        timetable[slot] = {}

        for day in days:

            timetable[slot][day] = None

    for s in schedules:

        slot = s.start_time.strftime("%H:00")

        if slot in timetable:

            timetable[slot][s.day] = s

    return render_template(

        "admin_schedule_view.html",

        timetable=timetable,
        days=days,
        time_slots=time_slots

    )

@route.route('/delete_schedule/<int:id>')
def delete_schedule(id):

    s = Schedule.query.get(id)

    if s:

        db.session.delete(s)

        db.session.commit()

        flash(
            "Schedule deleted successfully",
            "success"
        )

    return redirect(request.referrer)


@route.route('/export_attendance')
@login_required
def export_attendance():

    import pandas as pd
    import os
    from flask import send_file

    subject = request.args.get("subject")
    year = request.args.get("year")
    branch = request.args.get("branch")
    division = request.args.get("division")

    # FILTER ATTENDANCE
    records = db.session.query(

        Attendance,
        Student,
        AttendanceSession

    ).join(

        Student,
        Attendance.student_id == Student.id

    ).join(

        AttendanceSession,
        Attendance.session_id == AttendanceSession.id

    ).filter(

        AttendanceSession.subject == subject,
        AttendanceSession.year == year,
        AttendanceSession.branch == branch,
        AttendanceSession.division == division

    ).all()

    data = []

    for attendance, student, session in records:

        data.append({

            "Student Name": student.username,
            "Roll No": student.roll_no,
            "Subject": session.subject,
            "Status": attendance.status,
            "Session Code": session.session_code,
            "Date": session.start_time.strftime("%d-%m-%Y"),
            "Start Time": session.start_time.strftime("%H:%M"),
            "End Time": session.end_time.strftime("%H:%M")

        })

    df = pd.DataFrame(data)

    # CREATE EXPORT FOLDER
    export_folder = os.path.join(
        os.getcwd(),
        "exports"
    )

    os.makedirs(
        export_folder,
        exist_ok=True
    )

    # CSV FILE PATH
    filename = f"{subject}_attendance.csv"

    filepath = os.path.join(
        export_folder,
        filename
    )

    # SAVE CSV
    df.to_csv(
        filepath,
        index=False
    )

    # DOWNLOAD
    return send_file(
        filepath,
        as_attachment=True
    )

@route.route('/export_notifications')
def export_notifications():

    import pandas as pd
    import os

    if session.get('role') != 'admin':
        return "Unauthorized", 403

    year = request.args.get('year')
    branch = request.args.get('branch')
    division = request.args.get('division')
    subject = request.args.get('subject')

    sessions_query = AttendanceSession.query

    # FILTERS
    if year:
        sessions_query = sessions_query.filter(
            AttendanceSession.year == year
        )

    if branch:
        sessions_query = sessions_query.filter(
            AttendanceSession.branch == branch
        )

    if division:
        sessions_query = sessions_query.filter(
            AttendanceSession.division == division
        )

    if subject:
        sessions_query = sessions_query.filter(
            AttendanceSession.subject == subject
        )

    sessions = sessions_query.all()

    data = []

    for s in sessions:

        notifications = Notification.query.filter(

            Notification.message.like(
                f"%{s.session_code}%"
            )

        ).all()

        for n in notifications:

            data.append({

                "Subject": s.subject,

                "Year": s.year,

                "Branch": s.branch,

                "Division": s.division,

                "Session Code": s.session_code,

                "Notification Message": n.message,

                "Created At": n.created_at.strftime(
                    "%d-%m-%Y %H:%M"
                )

            })

    df = pd.DataFrame(data)

    export_folder = os.path.join(
        os.getcwd(),
        "exports"
    )

    os.makedirs(
        export_folder,
        exist_ok=True
    )

    file_path = os.path.join(
        export_folder,
        "notifications_export.csv"
    )

    df.to_csv(
        file_path,
        index=False
    )

    return send_file(
        file_path,
        as_attachment=True
    )


@route.route('/logout')
@login_required
def logout():

    logout_user()

    flash('Logged out successfully!', 'success')

    return redirect(url_for('route.home'))


