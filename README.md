# 🦶 Pes Planus (Düz Taban) Analiz Sistemi

Bu proje, ayak röntgen görüntüleri üzerinden otomatik ve manuel olarak **Pes Planus (Düz Taban)** analizi, **Kalkaneal Eğim Açısı** ölçümü ve **Meary's Açısı** hesaplamalarını gerçekleştiren profesyonel bir masaüstü uygulamasıdır. Gelişmiş derin öğrenme modelleri (U-Net) ve geometrik algoritmalar ile entegre bir medikal iş istasyonu sunar.

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue" alt="Python Version"/>
  <img src="https://img.shields.io/badge/GUI-PySide6-green" alt="GUI Framework"/>
  <img src="https://img.shields.io/badge/AI-PyTorch-orange" alt="Deep Learning"/>
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License"/>
</div>

---

## 🚀 Özellikler

- **🤖 Otomatik AI Analizi:** Eğitilmiş U-Net modeli ile kalkaneus kemiğini otomatik segmente eder ve eğim açısını saniyeler içinde hesaplar.
- **📏 Manuel Ölçüm Araçları:**
  - **Kalkaneal Eğim Açısı:** Zemin ve kalkaneus eksenlerini belirleyerek hassas açı ölçümü.
  - **Meary's Açısı:** Talus ve 1. Metatarsal kemik eksenleri arasındaki açıyı ölçme.
  - **Serbest Çizim & Cetvel:** Uzunluk ölçümü, serbest çizim ve açı ölçme araçları.
- **🖼️ Görüntü Desteği:**
  - **DICOM (.dcm):** Medikal görüntü formatlarını doğrudan açma ve hasta bilgilerini görüntüleme.
  - **Standart Formatlar:** PNG, JPG, JPEG desteği.
  - **Zoom & Pan:** Görüntü üzerinde detaylı inceleme yapma imkanı (Mouse tekerleği ve sağ tık).
- **📊 Tanı Sınıflandırması:** Ölçülen açılara göre otomatik tanı önerisi (Pes Planus, Normal, Pes Cavus vb.).
- **🎨 Modern Arayüz:** Karanlık mod (Dark Theme) ile göz yormayan, profesyonel kullanıcı deneyimi.

---

## 📂 Proje Yapısı

```bash
pes_planus_app/
├── main.py                 # Uygulama giriş noktası
├── requirements.txt        # Gerekli kütüphaneler
├── README.md               # Proje dokümantasyonu
├── calcaneus_unet_resnet34_best.pth # Eğitilmiş yapay zeka modeli
└── src/
    ├── ai/                 # Yapay zeka & derin öğrenme modülleri
    │   └── analyzer.py     # Görüntü işleme ve analiz mantığı
    ├── core/               # Çekirdek fonksiyonlar
    │   ├── dicom_loader.py # DICOM dosya okuyucu
    │   └── geometry.py     # Geometrik hesaplamalar
    └── ui/                 # Kullanıcı arayüzü
        ├── main_window.py  # Ana pencere
        ├── canvas.py       # Çizim tuvali (GraphicsView)
        └── modules/        # UI Modülleri (Analiz, Çizim)
```

---

## 🛠️ Kurulum

Projenin çalışması için Python 3.8 veya üzeri bir sürüm gereklidir.

### 1. Repoyu İndirin
```bash
git clone https://github.com/kullaniciadi/pes_planus_app.git
cd pes_planus_app
```

### 2. Sanal Ortam Oluşturun (Opsiyonel ama önerilir)
```bash
python -m venv .venv
# Windows için:
.venv\Scripts\activate
# Mac/Linux için:
source .venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Modeli İndirin/Yerleştirin
`calcaneus_unet_resnet34_best.pth` dosyasının projenin ana dizininde olduğundan emin olun.

---

## ▶️ Kullanım

Uygulamayı başlatmak için terminalden aşağıdaki komutu çalıştırın:

```bash
python main.py
```

### Adım Adım Analiz:
1.  **Dosya Aç:** Sol üstteki "Dosya Aç" butonunu kullanarak bir Röntgen görüntüsü (DICOM veya PNG/JPG) yükleyin.
2.  **Mod Seçimi:** Sağ panelden "Kalkaneal Eğim Açısı" veya "Meary's Açısı" modunu seçin.
3.  **Otomatik Analiz (Önerilen):** "Yapay Zeka" kutusundaki "🤖 Otomatik Analiz" butonuna tıklayın. Sistem kemiği bulup açıyı otomatik hesaplayacaktır.
4.  **Manuel Düzeltme:**
    *   **Zemin (Mavi):** Zemin aracını seçip 2 nokta koyarak zemin doğrusunu çizin.
    *   **Kalkaneus (Pembe):** Kalkaneus aracını seçip kemik alt yüzeyine uygun 2 nokta koyarak ekseni belirleyin.
5.  **Sonuç:** Sağ panelde ölçülen açı ve tanı sınıflandırması anlık olarak gösterilir.

---

## 🔧 Teknik Detaylar

*   **Segmentasyon:** ResNet34 kodlayıcılı U-Net mimarisi kullanılmıştır.
*   **Görüntü İşleme:** OpenCV (cv2) ve NumPy ile morfolojik işlemler, kenar tespiti (Canny) ve doğru tespiti (Hough Transform) yapılmaktadır.
*   **Arayüz:** PySide6 (Qt for Python) kütüphanesi ile geliştirilmiş, ölçeklenebilir vektörel grafik tabanlı (QGraphicsScene) bir çizim motoruna sahiptir.

---

## 🤝 Katkıda Bulunma

Hata bildirimleri ve özellik istekleri için lütfen "Issues" bölümünü kullanın. Pull request'ler memnuniyetle karşılanır.

## 📄 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız.
