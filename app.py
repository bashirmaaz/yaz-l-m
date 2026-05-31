from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import date
from werkzeug.security import generate_password_hash 
from routes.main import main_bp 
import os 
from flask_login import LoginManager 

# models.py'den gerekli objeleri import ediyoruz
from models import db, Teacher, Student, Course, Attendance 

# 1. Flask Uygulamasını Başlatma
app = Flask(__name__) 

# Rotaları uygulamaya kaydet
app.register_blueprint(main_bp)

# 2. Veritabanı Bağlantı Ayarları
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Ah3631&&@localhost:3306/yoklama_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sizin-gizli-anahtariniz-buraya-gelecek' 

# 3. SQLAlchemy'yi Flask Uygulamasına Bağlama
db.init_app(app)


# =================================================================
# 4. FLASK-LOGIN KURULUMU 
# =================================================================

login_manager = LoginManager()
login_manager.init_app(app) 
login_manager.login_view = 'main.login' 
login_manager.login_message = "Lütfen bu sayfaya erişmek için giriş yapın."

@login_manager.user_loader
def load_user(user_id):
    
    from models import db, Teacher 
    return db.session.get(Teacher, int(user_id))




def create_tables():
    """Uygulama bağlamı içinde veritabanı tablolarını oluşturur ve test verisi ekler."""
    with app.app_context():
        #db.drop_all()  Geçici temizlik komutu.
        
        db.create_all() 
        print("Veritabanı tabloları başarıyla oluşturuldu!")

        # ------------------------------------------------------------------
        # Test Verisi Ekleme
        # ------------------------------------------------------------------
        if not db.session.scalars(db.select(Teacher)).first():
            
            teacher = Teacher(
                username='teacher1', 
                password_hash=generate_password_hash('123456'), 
                name='Ali Yılmaz'
            )
            db.session.add(teacher)
            
            student = Student(
                school_number='2025001', 
                name='Ayşe', 
                surname='Demir'
            )
            db.session.add(student)
            
            course = Course(
                name='Yüz Tanıma Projesi', 
                teacher_id=1 
            )
            db.session.add(course)

            db.session.commit()
            print("Test Öğretmen, Öğrenci (2025001) ve Ders eklendi.")


if __name__ == '__main__':
    # Tabloları oluştur
    create_tables()

    # Flask uygulamasını çalıştırma 
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)