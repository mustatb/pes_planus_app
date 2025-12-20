# Pes Planus Analiz & Medical Workstation

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![PyQt](https://img.shields.io/badge/GUI-PySide6-green?style=for-the-badge&logo=qt)
![PyTorch](https://img.shields.io/badge/AI-PyTorch-orange?style=for-the-badge&logo=pytorch)
![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)

**Pes Planus Analiz**, ortopedik radyoloji için geliştirilmiş, yapay zeka destekli bir teşhis destek sistemidir. Ayak röntgen görüntüleri (Lateral grafi) üzerinde otomatik **Kalkaneal Eğim Açısı** ölçümü yaparak, *Pes Planus (Düz Taban)* ve *Pes Cavus (Çukur Taban)* deformitelerinin hızlı ve hassas analizini sağlar.

---

## 📋 İçindekiler
- [Özellikler](#-özellikler)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
    - [Tekli Analiz](#1-tekli-analiz-ana-ekran)
    - [Toplu Analiz](#2-toplu-analiz-sekmesi)
- [Proje Mimarisi](#-proje-yapısı)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Lisans](#-lisans)

---

## 🌟 Özellikler

### 🧠 Gelişmiş Yapay Zeka
*   **Segmentasyon Motoru:** U-Net (ResNet34 encoder) mimarisi ile %98+ hassasiyetle kemik segmentasyonu.
*   **Otonom Ölçüm:** İnsan müdahalesine gerek kalmadan landmark tespiti ve açı hesaplama.
*   **Akıllı Taraf Tespiti (OCR):** Görüntü üzerindeki 'L' / 'R' işaretlerini okuyarak taraf bilgisini otomatik çıkarır.

### ⚡ Yüksek Verimlilik (Batch Processing)
*   **Toplu İşlem:** Klasör bazlı çalışarak binlerce hastayı dakikalar içinde analiz eder.
*   **Excel Export:** Hasta ID, İsim, Taraf, Açı ve Tanı bilgilerini detaylı Excel raporu olarak sunar.
*   **Görsel Arşiv:** Analiz edilen her görüntüyü işlenmiş haliyle arşivler.
*   **Dinamik Filtreleme:** Sonuçlar üzerinde isim, ID bazlı arama ve A-Z sıralama imkanı.

### 🎨 Profesyonel Arayüz
*   **Modern UI:** Koyu mod (Dark Theme) destekli, göz yormayan medikal arayüz tasarımı.
*   **DICOM Görüntüleyici:** Tıbbi standartlara (.dcm) tam uyumlu, metadata okuyabilen görüntüleyici.
*   **İnteraktif Araçlar:** Zoom, Pan, Contrast ayarı ve manuel ölçüm düzeltme araçları.

---

## 🚀 Kurulum

### Sistem Gereksinimleri
*   **OS:** Windows 10/11 (Önerilen), Linux, macOS
*   **Python:** 3.10 veya daha yeni
*   **RAM:** Minimum 4GB (8GB önerilir)
*   **GPU:** NVIDIA GPU (Opsiyonel, analiz hızını artırır)

### Adım 1: Depoyu Klonlayın
```bash
git clone https://github.com/kullaniciadi/pes_planus_app.git
cd pes_planus_app
```

### Adım 2: Sanal Ortam Kurulumu
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
```

### Adım 3: Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

---

## 💻 Kullanım

Uygulamayı başlatmak için:
```bash
python main.py
```

### 1. Tekli Analiz (Ana Ekran)
Radyoloğun günlük kullanımı için tasarlanmıştır.
1.  **Görüntü Yükleme:** Dosya gezgini veya sürükle-bırak ile görüntüyü yükleyin.
2.  **AI Analiz:** "Otomatik Analiz" butonuna tıklayın. Model saniyeler içinde çalışır.
3.  **Doğrulama:** Çizilen çizgileri kontrol edin, gerekirse uç noktaları (Point A/B) mouse ile kaydırarak ince ayar yapın.

### 2. Toplu Analiz Sekmesi
Araştırma ve retrospektif çalışmalar için idealdir.
1.  **Klasör Seçimi:** Hasta klasörünü sisteme tanıtın (Alt klasörleri de tarar).
2.  **Veri Yönetimi:** Tablo üzerinden sonuçları izleyin, "İsim" kolonuyla sıralayın veya arama kutusuyla hasta bulun.
3.  **Dışa Aktarım:** "Excel'e Aktar" veya "Rapor Oluştur (Zip)" seçenekleri ile verilerinizi alın.

---

## 📂 Proje Yapısı

```bash
pes_planus_app/
├── src/
│   ├── ai/                 # Deep Learning Modelleri (U-Net)
│   ├── core/               # Image Processing & İş Mantığı
│   │   ├── geometry.py     # Açı Hesaplama Algoritmaları
│   │   └── marker_detector.py # OCR & Taraf Tespiti
│   └── ui/                 # PySide6 Arayüz Modülleri
├── resources/              # İkonlar ve Statik Dosyalar
├── calcaneus_unet_resnet34_best.pth  # Model Ağırlıkları
└── main.py                 # Application Entry Point
```

---

## 🛠 Teknoloji Yığını

*   **Dil:** Python 3.10
*   **GUI:** PySide6 (Qt)
*   **AI/ML:** PyTorch, Segmentation Models Pytorch (SMP)
*   **Görüntü İşleme:** OpenCV, NumPy
*   **OCR:** EasyOCR
*   **Data:** Pandas, OpenPyXL, Pydicom

---

## ⚖️ Lisans

Bu proje **"Özel Lisans"** altında lisanslanmıştır. Kaynak kodları yalnızca izin verilen kullanım alanlarında, akademik veya dahili geliştirme amacıyla kullanılabilir. Ticari dağıtımı izne tabidir.

---

**Sürüm:** 1.2.0 (Stable)  
**Tarih:** Aralık 2025
