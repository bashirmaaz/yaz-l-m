from models import db, Teacher, Student, Course, FaceEmbedding, Attendance

class TeacherRepository:
    @staticmethod
    def get_by_username(username):
        return db.session.scalar(db.select(Teacher).filter_by(username=username))

    @staticmethod
    def add(teacher):
        db.session.add(teacher)
        db.session.commit()

class StudentRepository:
    @staticmethod
    def get_by_school_number(school_number):
        return db.session.scalar(db.select(Student).filter_by(school_number=school_number))
    
    @staticmethod
    def get_by_id(student_id):
        return db.session.get(Student, student_id)

    @staticmethod
    def add(student):
        db.session.add(student)
        db.session.commit()
        
    @staticmethod
    def delete(student):
        db.session.delete(student)
        db.session.commit()

class CourseRepository:
    @staticmethod
    def get_by_teacher_id(teacher_id):
        return db.session.scalars(db.select(Course).filter_by(teacher_id=teacher_id)).all()

    @staticmethod
    def get_by_id(course_id):
        return db.session.get(Course, course_id)

    @staticmethod
    def add(course):
        db.session.add(course)
        db.session.commit()

class FaceEmbeddingRepository:
    @staticmethod
    def get_by_student_id(student_id):
        return db.session.scalar(db.select(FaceEmbedding).filter_by(student_id=student_id))

    @staticmethod
    def get_all_embeddings():
        return db.session.execute(
            db.select(FaceEmbedding.id, FaceEmbedding.student_id, FaceEmbedding.embedding)
        ).all()

    @staticmethod
    def add(embedding):
        db.session.add(embedding)
        db.session.commit()

class AttendanceRepository:
    @staticmethod
    def get_student_attendance_by_date(student_id, target_date):
        return db.session.scalar(
            db.select(Attendance).filter_by(student_id=student_id, date=target_date)
        )

    @staticmethod
    def get_course_reports(course_id):
        return db.session.execute(
            db.select(Attendance, Student)
            .join(Student, Attendance.student_id == Student.id)
            .filter(Attendance.course_id == course_id)
            .order_by(Attendance.date.asc(), Student.name.asc())
        ).all()

    @staticmethod
    def add(attendance):
        db.session.add(attendance)
        db.session.commit()
        
    @staticmethod
    def update():
        db.session.commit()