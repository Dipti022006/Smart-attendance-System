from app import db
from app import loginmanager
from flask_login import UserMixin
from datetime import datetime,timedelta

class Student(UserMixin, db.Model):

        id = db.Column(db.Integer, primary_key=True,autoincrement=True)
        student_id = db.Column(db.String(50), unique=True)
        username = db.Column(db.String(100), nullable=False)

        email = db.Column(db.String(150), unique=True, nullable=False)

        password = db.Column(db.String(200), nullable=False)

        role = db.Column(db.String(20), nullable=False)
        year = db.Column(db.String(20),nullable=False)
        branch = db.Column(db.String(50))        
        division = db.Column(db.String(10))      
        roll_no = db.Column(db.String(20))

        image_file = db.Column(db.String(300))
        attendance=db.relationship(
    'Attendance',
    backref='student'
)

class Teacher(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True,autoincrement=True)

    username = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(150), unique=True, nullable=False)

    password = db.Column(db.String(200), nullable=False)

    role = db.Column(db.String(20), nullable=False)

# ===============================
# ADMIN MODEL
# ===============================

# class Admin(db.Model, UserMixin):
#     __tablename__ = 'admin'

#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(100))
#     email = db.Column(db.String(100), unique=True)
#     password = db.Column(db.String(255))
#     role = db.Column(db.String(50))
# # ===============================

# ===============================
# TEACHER ASSIGNMENT TABLE
# ===============================

class TeacherAssignment(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey('teacher.id'),
        nullable=False
    )

    subject = db.Column(db.String(100), nullable=False)

    year = db.Column(db.String(50), nullable=False)

    branch = db.Column(db.String(100), nullable=False)

    division = db.Column(db.String(10), nullable=False)


# ===============================
class Schedule(db.Model):

    id=db.Column(db.Integer,primary_key=True)

    subject=db.Column(db.String(100))

    room=db.Column(db.String(50))

    day=db.Column(db.String(20))

    start_time=db.Column(db.Time)

    end_time=db.Column(db.Time)

    year=db.Column(db.String(50))

    branch=db.Column(db.String(50))

    division=db.Column(db.String(20))

    teacher_id=db.Column(
        db.Integer,
        db.ForeignKey('teacher.id')
    )

    teacher_name=db.Column(
        db.String(100)
    )

    teacher=db.relationship(
        'Teacher',
        backref='schedules'
    )
    valid_from=db.Column(
        db.Date,
        nullable=True
    )

    valid_until=db.Column(
        db.Date,
        nullable=True
    )

    temporary=db.Column(
        db.Boolean,
        default=False
    )

class TemporaryScheduleChange(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    schedule_id = db.Column(
        db.Integer,
        db.ForeignKey('schedule.id'),
        nullable=False
    )

    changed_subject = db.Column(db.String(100))

    changed_room = db.Column(db.String(50))

    changed_teacher = db.Column(db.String(100))

    changed_date = db.Column(db.String(50))

    expiry_date = db.Column(db.String(50))

    reason = db.Column(db.String(300))



class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text)
    receiver_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    is_seen = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

class AttendanceSession(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey('teacher.id')
    )

    subject = db.Column(
        db.String(100)
    )

    year = db.Column(
        db.String(20)
    )

    branch = db.Column(
        db.String(50)
    )

    division = db.Column(
        db.String(10)
    )

    start_time = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    end_time = db.Column(
        db.DateTime
    )

    session_code = db.Column(
        db.String(100),
        unique=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )
class Attendance(db.Model):

    id=db.Column(
        db.Integer,
        primary_key=True
    )

    student_id=db.Column(
        db.Integer,
        db.ForeignKey('student.id')
    )

    session_id=db.Column(
        db.Integer,
        db.ForeignKey('attendance_session.id')
    )

    status=db.Column(
        db.String(50),
        default="absent"
    )
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    confidence=db.Column(
        db.Float,
        default=0
    )

    suspicious=db.Column(
        db.Boolean,
        default=False
    )

    teacher_decision=db.Column(
        db.String(50)
    )

    image_file=db.Column(
        db.String(200)
    )

class Notice(db.Model):

    id=db.Column(
        db.Integer,
        primary_key=True
    )

    teacher_id=db.Column(
        db.Integer,
        db.ForeignKey(
            'teacher.id'
        )
    )

    teacher_name=db.Column(
        db.String(100)
    )

    message=db.Column(
        db.Text,
        nullable=False
    )

    year=db.Column(
        db.String(50)
    )

    branch=db.Column(
        db.String(50)
    )

    division=db.Column(
        db.String(50)
    )

    created_at=db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class Doubt(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey('student.id')
    )

    subject = db.Column(
        db.String(100)
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey('teacher.id')
    )

    message = db.Column(
        db.Text
    )

    year = db.Column(
        db.String(50)
    )

    branch = db.Column(
        db.String(50)
    )

    division = db.Column(
        db.String(50)
    )

    is_answered = db.Column(
        db.Boolean,
        default=False
    )

    answer = db.Column(
        db.Text
    )
    is_seen=db.Column(
    db.Boolean,
    default=False
)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )