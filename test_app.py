import pytest
from app import app
from models import db, Teacher, Student
from repositories import TeacherRepository, StudentRepository

# --- TEST İÇİN SAHTE (MOCK) İSTEMCİ VE VERİTABANI KURULUMU ---
@pytest.fixture
def client():
    # Uygulamayı test moduna al
    app.config['TESTING'] = True
    # Ana veritabanını bozmamak için sadece RAM üzerinde çalışan geçici bir SQLite veritabanı kullan
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' 
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all() # Geçici tabloları oluştur
            yield client
            db.session.remove()
            db.drop_all() # Test bitince her şeyi temizle

# =================================================================
# TEST SENARYOLARI (Rapor UT-01, UT-02 İçin)
# =================================================================

def test_teacher_creation(client):
    """Senaryo (UT-01): Geçerli bilgilerle yeni bir öğretmen oluşturulabilmeli."""
    with app.app_context():
        new_teacher = Teacher(username="test_hoca", password_hash="fake_hash", name="Test Hoca")
        TeacherRepository.add(new_teacher)
        
        saved_teacher = TeacherRepository.get_by_username("test_hoca")
        
        assert saved_teacher is not None
        assert saved_teacher.name == "Test Hoca"
        assert saved_teacher.username == "test_hoca"

def test_student_onboard_api_success(client):
    """Senaryo (UT-02): API üzerinden doğru verilerle öğrenci ön kaydı yapılabilmeli."""
    response = client.post('/api/student_onboard', data={
        'school_number': '2026001',
        'name': 'Ahmet',
        'surname': 'Yılmaz'
    })
    
    assert response.status_code == 201 # 201 Created kodu dönmeli
    assert b"success" in response.data or b"basariyla" in response.data

def test_student_onboard_api_duplicate(client):
    """Senaryo (UT-03): Sistemde var olan bir okul numarasıyla ikinci kez kayıt yapılamamalı."""
    # 1. İlk kaydı yap
    client.post('/api/student_onboard', data={
        'school_number': '999888', 'name': 'Veli', 'surname': 'Kaya'
    })
    
    # 2. Aynı numarayla tekrar kayıt dene
    response_duplicate = client.post('/api/student_onboard', data={
        'school_number': '999888', 'name': 'Ali', 'surname': 'Can'
    })
    
    assert response_duplicate.status_code == 409 # 409 Conflict (Çakışma) kodu dönmeli
    assert b"zaten sistemde kayitli" in response_duplicate.data.lower() or b"error" in response_duplicate.data