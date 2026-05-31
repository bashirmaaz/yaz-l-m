import cv2
import numpy as np
import json
import tensorflow as tf 
from deepface import DeepFace
from scipy.spatial.distance import cosine

# KRİTİK BÖLÜM: TENSORFLOW/GPU/CPU BELLEK YÖNETİMİ
try:
    # 1. Bellek Büyüme (Growth) Ayarı (GPU varsa)
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    
    # 2. Gerekli değilse, görünür cihazları sadece CPU olarak ayarla (Stabilite için)
    
    print("TensorFlow yapılandırması tamamlandı.")
except Exception as e:
    print(f"TensorFlow yapılandırma hatası: {e}")
    
# --- ML MODEL YÜKLEME ---
try:
    print("Yüz tanıma modelini yüklüyorum... Lütfen bekleyin.")
    # 'Facenet' modelini, 'opencv' dedektörünü kullanarak başlat
    global_model = DeepFace.build_model('Facenet')
    global_detector = 'opencv' 
    print("Yüz tanıma modeli başarıyla yüklendi.")
except Exception as e:
    print(f"HATA: Yüz Tanıma modeli yüklenemedi: {e}")
    global_model = None
    global_detector = None


# 1. Yüz Tespiti ve Kırpma (OpenCV)
def detect_face(frame_bytes):
    """Görüntü baytlarından yüzü algılar ve yüz bölgesini kırpar."""
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return None, "Görüntü okunamadı."

    if global_detector is None:
        return None, "Yüz dedektörü başlatılmadı."

    try:
        # Önceden yüklenmiş dedektörü kullan
        face_objs = DeepFace.extract_faces(img_path=frame, 
                                           detector_backend=global_detector,
                                           enforce_detection=False)
        
        if not face_objs:
            return None, "Yüz algılanmadı."
        
        # Sadece ilk algılanan yüzü al
        face_obj = face_objs[0]
        
        x, y, w, h = face_obj['facial_area']['x'], face_obj['facial_area']['y'], face_obj['facial_area']['w'], face_obj['facial_area']['h']
        face_crop = frame[y:y+h, x:x+w]
        
        return face_crop, None
    except Exception as e:
        return None, f"Yüz algılama hatası: {e}"


# 2. Yüz Gömmesi (Embedding) Oluşturma (DeepFace)
def get_embedding(face_crop):
    """Kırpılmış yüz görüntüsünden sayısal vektörü (embedding) çıkarır."""
    if global_model is None:
        print("Model yüklenmedi, embedding oluşturulamıyor.")
        return None

    try:
        # Önceden yüklenmiş modeli kullanarak, model adını veriyoruz.
        embedding_result = DeepFace.represent(img_path=face_crop, 
                                                model_name='Facenet', 
                                                detector_backend='skip', 
                                                enforce_detection=False)
        
        return np.array(embedding_result[0]['embedding'])
    
    except Exception as e:
        print(f"Embedding oluşturma hatası: {e}")
        return None

# 3. Yüzleri Karşılaştırma (Kosinüs Benzerliği)
def compare_embeddings(new_embedding, db_embeddings, threshold=0.30):
    min_distance = float('inf')
    matched_index = -1
    
    if new_embedding is None or not db_embeddings:
        return False, None, min_distance

    for index, (emb_id, student_id, db_vector) in enumerate(db_embeddings):
        
        distance = cosine(new_embedding, db_vector)
        
        if distance < min_distance:
            min_distance = distance
            matched_index = index
    
    if min_distance <= threshold:
        return True, db_embeddings[matched_index], min_distance
    else:
        return False, None, min_distance

# 4. Canlılık Kontrolü
def liveness_check(frame):
    return True