
from flask_sqlalchemy import SQLAlchemy  
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Text
from sqlalchemy.orm import relationship, DeclarativeBase
from flask_login import UserMixin
import json

# SQLAlchemy için Temel Sınıf
class Base(DeclarativeBase):
    pass

# db nesnesini Flask-SQLAlchemy ile oluştuR
db = SQLAlchemy(model_class=Base)

class Teacher(db.Model, UserMixin):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False) # Bcrypt hash'i
    name = Column(String(100), nullable=False)

    # Bir öğretmen birden fazla ders verebilir
    courses = relationship("Course", backref="teacher", lazy='dynamic')

    
    def get_id(self):
        return str(self.id)

class Student(db.Model):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    school_number = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)

    
    embeddings = relationship("FaceEmbedding", backref="student", uselist=False)
    attendance_records = relationship("Attendance", backref="student", lazy='dynamic')


class Course(db.Model):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    
    
    attendance_records = relationship("Attendance", backref="course", lazy='dynamic')


class FaceEmbedding(db.Model):
    __tablename__ = 'face_embeddings'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), unique=True, nullable=False)
    
    embedding = Column(Text, nullable=False) 
    created_at = Column(Date, nullable=False)

    def get_embedding_list(self):
        
        return json.loads(self.embedding)


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    date = Column(Date, nullable=False)
    present = Column(Boolean, default=False)
    
    
    verified_by_face_id = Column(Integer, ForeignKey('face_embeddings.id'), nullable=True)