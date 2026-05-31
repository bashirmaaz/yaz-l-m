
const video = document.getElementById('camera-feed');
const resultDiv = document.getElementById('result');

// Global Değişkenler ve Buton Referansları
let stream = null;
let recognitionInterval = null;
let currentCourseId = null;

const REGISTER_BUTTON = document.getElementById('register-button');
const START_RECOGNITION_BTN = document.getElementById('start-recognition-btn');
const STOP_RECOGNITION_BTN = document.getElementById('stop-recognition-btn');

// Sayfa Yüklendiğinde
document.addEventListener('DOMContentLoaded', () => {
    // 1. Ders ID'sini HTML'den al
    const courseIdElement = document.getElementById('current-course-id');
    if (courseIdElement) {
        currentCourseId = courseIdElement.value;
    }

    // 2. Buton durumlarını ayarla
    if (START_RECOGNITION_BTN) {
        START_RECOGNITION_BTN.disabled = !currentCourseId;
    }
    resultDiv.innerHTML = 'Sonuçlar burada görünecek...';
});


// Durum güncelleme fonksiyonu
function updateStatus(type, message) {
    let className = '';
    if (type === 'success') className = 'status-success';
    else if (type === 'fail' || type === 'error') className = 'status-error';
    else if (type === 'info') className = 'status-info';

    resultDiv.innerHTML = `<span class="${className}">${message}</span>`;
}

// ----------------------------------------------------
// Kamera Yönetimi
// ----------------------------------------------------

async function startVideo(mode) {
    if (recognitionInterval) stopRecognition(); // Tanıma döngüsü varsa durdur
    if (stream) stopCamera(); // Zaten açıksa önce durdur

    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        updateStatus('info', 'Kamera başarıyla başlatıldı. Yüzünüzü ortalayın.');

        // Buton durumlarını ayarla
        if (mode === 'register') {
            REGISTER_BUTTON.disabled = false;
        }
        START_RECOGNITION_BTN.disabled = true;
        STOP_RECOGNITION_BTN.disabled = false;

    } catch (err) {
        updateStatus('error', 'Kamera açılamadı. Lütfen tarayıcı iznini kontrol edin.');
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
        video.srcObject = null;
    }
}

function captureFrame() {
    const canvas = document.createElement('canvas');


    canvas.width = 320;
    canvas.height = 240;

    const context = canvas.getContext('2d');

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.7));
}

// 1. Yüz Kayıt İşlemi (fullRegister)


async function fullRegister() {
    const schoolNumber = document.getElementById('onboard-school-number').value.trim();
    const name = document.getElementById('onboard-name').value.trim();
    const surname = document.getElementById('onboard-surname').value.trim();

    if (!schoolNumber || !name || !surname) {
        updateStatus('error', "Lütfen tüm kayıt bilgilerini doldurun.");
        return;
    }
    if (!stream) {
        updateStatus('error', 'Kamera akışı aktif değil. Lütfen önce kamerayı açın.');
        return;
    }

    // Adım 1: Metin Kaydı
    updateStatus('info', '1/2: Öğrenci ön kaydı yapılıyor...');
    const textFormData = new FormData();
    textFormData.append('school_number', schoolNumber);
    textFormData.append('name', name);
    textFormData.append('surname', surname);

    try {
        let response = await fetch('/api/student_onboard', { method: 'POST', body: textFormData });
        let data = await response.json();

        if (data.status === 'error') {
            updateStatus('error', 'Ön Kayıt Hatası: ' + data.message);
            return;
        }
        updateStatus('info', `2/2: Ön kayıt başarılı. Yüz kaydı yapılıyor...`);

    } catch (err) {
        updateStatus('error', 'Ön Kayıt Sırasında Bağlantı Hatası.');
        return;
    }

    // Adım 2: Yüz Kaydı
    const frameBlob = await captureFrame();
    const faceFormData = new FormData();
    faceFormData.append('school_number', schoolNumber);
    faceFormData.append('frame', frameBlob, 'face.jpg');

    try {
        let response = await fetch('/api/register', { method: 'POST', body: faceFormData });
        let data = await response.json();

        if (data.status === 'success') {
            updateStatus('success', '✅ Yüz Kaydı Başarılı: ' + data.message);
        } else {
            updateStatus('error', '❌ Yüz Kaydı Başarısız: ' + data.message);
        }
    } catch (err) {
        updateStatus('error', 'Yüz Kaydı Sırasında Bağlantı Hatası.');
    } finally {
        stopCamera();
        REGISTER_BUTTON.disabled = true;
    }
}



// 2. Yoklama İşlemleri (startRecognition / stopRecognition)


function startRecognition() {
    if (!currentCourseId) {
        updateStatus('error', 'Lütfen Dashboard\'dan bir ders seçin.');
        return;
    }

    // Kamerayı başlat ve tanıma döngüsünü kur
    startVideo('recognize').then(() => {
        // Her 1000ms (1 saniye) aralıkta kare gönder
        recognitionInterval = setInterval(sendFrameForRecognition, 1000);

        START_RECOGNITION_BTN.disabled = true;
        STOP_RECOGNITION_BTN.disabled = false;

        updateStatus('info', `Yoklama başladı. Yüzünüzü tanımaya çalışıyorum...`);
    });
}

function stopRecognition() {
    if (recognitionInterval) {
        clearInterval(recognitionInterval);
        recognitionInterval = null;
    }
    stopCamera();

    // Yoklama butonu tekrar aktif olur
    START_RECOGNITION_BTN.disabled = currentCourseId ? false : true;
    STOP_RECOGNITION_BTN.disabled = true;

    updateStatus('info', 'Yoklama durduruldu.');
}

async function sendFrameForRecognition() {
    if (!stream || !currentCourseId) return;

    const frameBlob = await captureFrame();
    const formData = new FormData();
    formData.append('frame', frameBlob, 'frame.jpg');

    // Dinamik Ders ID'sini API'ye gönderiyoruz.
    formData.append('course_id', currentCourseId);

    try {
        const response = await fetch('/api/recognize', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        // OTOMATİK DURDURMA KONTROLÜ
        if (data.status === 'success' && data.matched === true) {
            if (data.message && data.message.includes("zaten bugün yoklama aldı")) {
                updateStatus('info', `Tanındı: ${data.student.name}. ${data.message}`);
            } else {
                // Başarılı kayıtta döngüyü kes
                stopRecognition();
                updateStatus('success', `✅ Tanındı ve Kaydedildi: ${data.student.name} (${data.distance})`);
            }

        } else if (data.status === 'fail') {
            updateStatus('error', `❌ Başarısız: ${data.message}`);
        } else {
            updateStatus('info', `Tanınamadı. En yakın mesafe: ${data.distance}.`);
        }

    } catch (error) {
        updateStatus('error', 'Sunucu bağlantı hatası.');
    }
}