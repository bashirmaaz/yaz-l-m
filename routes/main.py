from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash 
from flask_login import login_user, logout_user, login_required, current_user 
from werkzeug.security import check_password_hash, generate_password_hash 
from face_utils import detect_face, get_embedding, compare_embeddings, liveness_check
from models import db, Student, FaceEmbedding, Attendance, Course, Teacher 

# --- YENİ EKLENEN REPOSITORY İMPORTLARI ---
from repositories import TeacherRepository, StudentRepository, CourseRepository, FaceEmbeddingRepository, AttendanceRepository

import numpy as np
from datetime import date
import json
import gc 

main_bp = Blueprint('main', __name__)

# =================================================================
# TEMEL EKRANLAR VE GİRİŞ (AUTHENTICATION)
# =================================================================

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard')) 
    else:
        return redirect(url_for('main.login'))

@main_bp.route('/register_teacher', methods=['GET', 'POST'])
def register_teacher():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        
        existing_teacher = TeacherRepository.get_by_username(username)

        if existing_teacher:
            return render_template('register_teacher.html', error='Bu kullanıcı adı zaten alınmış.')

        if not all([username, password, name]):
             return render_template('register_teacher.html', error='Tüm alanlar doldurulmalıdır.')

        new_teacher = Teacher(
            username=username,
            password_hash=generate_password_hash(password),
            name=name
        )
        
        try:
            TeacherRepository.add(new_teacher)
            flash('Kayıt başarıyla tamamlandı. Giriş yapabilirsiniz.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            return render_template('register_teacher.html', error=f'Veritabanı hatası: {e}')
    
    return render_template('register_teacher.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard')) 

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        teacher = TeacherRepository.get_by_username(username)

        if teacher and check_password_hash(teacher.password_hash, password):
            login_user(teacher, remember=True)
            return redirect(url_for('main.dashboard'))
        else:
            return render_template('login.html', error='Kullanıcı adı veya parola hatalı.')
    
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        course_name = request.form.get('course_name')
        if course_name:
            new_course = Course(
                name=course_name,
                teacher_id=current_user.id 
            )
            try:
                CourseRepository.add(new_course)
                flash(f"'{course_name}' adlı ders başarıyla eklendi.", 'success')
            except Exception as e:
                db.session.rollback()
                flash(f"Ders eklenirken bir hata oluştu: {e}", 'error')
        else:
            flash("Ders adı boş bırakılamaz.", 'error')
        
        return redirect(url_for('main.dashboard'))

    teacher_courses = CourseRepository.get_by_teacher_id(current_user.id)
    return render_template('dashboard.html', teacher_name=current_user.name, courses=teacher_courses)

@main_bp.route('/take_attendance/<int:course_id>')
@login_required
def take_attendance(course_id):
    course = CourseRepository.get_by_id(course_id)
    
    if not course or course.teacher_id != current_user.id:
        flash("Bu dersi alma yetkiniz bulunmamaktadır.", 'error')
        return redirect(url_for('main.dashboard'))
        
    return render_template('index.html', course_id=course.id, course_name=course.name)

@main_bp.route('/student_registration', methods=['GET'])
@login_required
def student_registration():
    return render_template('register_face.html')

# =================================================================
# API ROTLARI (KAYIT VE TANIMA)
# =================================================================

@main_bp.route('/api/student_onboard', methods=['POST'])
def student_onboard():
    school_number = request.form.get('school_number')
    name = request.form.get('name')
    surname = request.form.get('surname')
    
    if not all([school_number, name, surname]):
        return jsonify({"status": "error", "message": "Okul numarası, isim ve soyisim gerekli."}), 400

    existing_student = StudentRepository.get_by_school_number(school_number)
    if existing_student:
        return jsonify({"status": "error", "message": f"Okul numarası {school_number} zaten sistemde kayıtlı."}), 409

    new_student = Student(school_number=school_number, name=name, surname=surname)
    
    try:
        StudentRepository.add(new_student)
        return jsonify({
            "status": "success", 
            "message": f"{name} {surname} ön kaydı başarıyla yapıldı. Lütfen şimdi Yüz Kaydını tamamlayın.",
            "student_id": new_student.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Veritabanı hatası: {e}"}), 500

@main_bp.route('/api/register', methods=['POST'])
def register_face():
    school_number = request.form.get('school_number')
    
    if 'frame' not in request.files or not school_number:
        return jsonify({"status": "error", "message": "Okul numarası veya görüntü eksik."}), 400

    frame_file = request.files['frame']
    frame_bytes = frame_file.read()

    student = StudentRepository.get_by_school_number(school_number)
    if not student:
        return jsonify({"status": "error", "message": f"Önce {school_number} numaralı öğrenciyi Sisteme Ekleyin."}), 404 

    existing_embedding = FaceEmbeddingRepository.get_by_student_id(student.id)
    if existing_embedding:
        return jsonify({"status": "error", "message": "Bu öğrencinin yüzü zaten kayıtlı."}), 409 

    face_crop, error_msg = detect_face(frame_bytes)
    if face_crop is None:
        return jsonify({"status": "fail", "message": f"Yüz algılanamadı: {error_msg}"}), 200

    new_embedding_vector = get_embedding(face_crop)
    if new_embedding_vector is None:
        return jsonify({"status": "fail", "message": "Yüz gömmesi oluşturulamadı."}), 200

    all_embeddings_query = FaceEmbeddingRepository.get_all_embeddings()

    db_embeddings = []
    for emb_id, student_id_db, emb_json in all_embeddings_query:
        emb_vector = np.array(json.loads(emb_json))
        db_embeddings.append((emb_id, student_id_db, emb_vector))

    matched, matched_embedding_info, distance = compare_embeddings(new_embedding_vector, db_embeddings, threshold=0.30)

    if matched:
        emb_id, student_id_db, _ = matched_embedding_info
        existing_student = StudentRepository.get_by_id(student_id_db)
        
        try:
            StudentRepository.delete(student) 
        except Exception as rollback_e:
            db.session.rollback()
            print(f"HATA: Öğrenci silinirken hata oluştu: {rollback_e}")
        
        return jsonify({
            "status": "error", 
            "message": f"Bu yüz zaten sistemde kayıtlı ve {existing_student.name} ({existing_student.school_number}) öğrencisine ait. Tekrar kayıt yapılamaz. (Mesafe: {distance:.4f})"
        }), 409

    embedding_json = json.dumps(new_embedding_vector.tolist())
    new_face_embedding = FaceEmbedding(student_id=student.id, embedding=embedding_json, created_at=date.today())
    
    try:
        FaceEmbeddingRepository.add(new_face_embedding)
        gc.collect()
        return jsonify({"status": "success", "message": f"{student.name} öğrencisinin yüz kaydı tamamlandı.", "student_id": student.id}), 201
    except Exception as e:
        db.session.rollback()
        gc.collect()
        return jsonify({"status": "error", "message": f"Veritabanı kaydı hatası: {e}"}), 500

@main_bp.route('/api/recognize', methods=['POST'])
def recognize():
    if 'frame' not in request.files:
        return jsonify({"status": "error", "message": "Görüntü dosyası eksik"}), 400

    frame_bytes = request.files['frame'].read()
    course_id = request.form.get('course_id', type=int) or 1 
    
    face_crop, error_msg = detect_face(frame_bytes)
    
    if face_crop is None:
        return jsonify({"status": "fail", "matched": False, "message": error_msg}), 200

    if not liveness_check(face_crop):
        return jsonify({"status": "fail", "matched": False, "message": "Canlılık testi başarısız."}), 200

    new_embedding = get_embedding(face_crop)
    if new_embedding is None:
        return jsonify({"status": "fail", "matched": False, "message": "Embedding oluşturulamadı."}), 200

    all_embeddings_query = FaceEmbeddingRepository.get_all_embeddings()
    
    db_embeddings = []
    for emb_id, student_id, emb_json in all_embeddings_query:
        emb_vector = np.array(json.loads(emb_json))
        db_embeddings.append((emb_id, student_id, emb_vector))

    matched, matched_embedding_info, distance = compare_embeddings(new_embedding, db_embeddings, threshold=0.30) 
    result = {"status": "success", "matched": matched, "distance": round(distance, 4)}

    if matched:
        emb_id, student_id, _ = matched_embedding_info
        student = StudentRepository.get_by_id(student_id)
        today_attendance = AttendanceRepository.get_student_attendance_by_date(student_id, date.today())
        
        if today_attendance and today_attendance.present:
             result['message'] = f"{student.name} zaten bugün yoklama aldı."
        else:
            try:
                if today_attendance:
                     today_attendance.present = True
                     AttendanceRepository.update()
                else:
                     new_attendance = Attendance(
                        course_id=course_id, 
                        student_id=student_id,
                        date=date.today(),
                        present=True,
                        verified_by_face_id=emb_id
                     )
                     AttendanceRepository.add(new_attendance)
                     
                result['message'] = f"{student.name} tanındı ve yoklama kaydedildi."
            except Exception as e:
                db.session.rollback()
                return jsonify({"status": "error", "message": f"Yoklama kaydı sırasında veritabanı hatası: {e}"}), 500
                
        result['student'] = {"id": student.id, "name": student.name, "school_number": student.school_number}
    else:
        result['message'] = f"Yüz tanınamadı. En yakın mesafe: {result['distance']}"

    gc.collect() 
    return jsonify(result)

@main_bp.route('/reports', methods=['GET'])
@login_required
def attendance_reports():
    selected_course_id = request.args.get('course_id', type=int)
    teacher_courses = CourseRepository.get_by_teacher_id(current_user.id)
    
    report_data = []
    course_name = "Tüm Dersler"
    
    if teacher_courses and selected_course_id:
        selected_course = next((c for c in teacher_courses if c.id == selected_course_id), None)
        
        if selected_course:
            course_name = selected_course.name
            attendance_records = AttendanceRepository.get_course_reports(selected_course_id)

            for att, student in attendance_records:
                report_data.append({
                    "date": att.date.strftime("%d-%m-%Y"),
                    "student_name": f"{student.name} {student.surname}",
                    "school_number": student.school_number,
                    "present": "VAR" if att.present else "YOK"
                })
        else:
            flash("Seçilen ders bulunamadı veya yetkiniz yok.", 'error')

    return render_template('reports.html', 
                           courses=teacher_courses, 
                           selected_course_id=selected_course_id,
                           course_name=course_name,
                           report_data=report_data)