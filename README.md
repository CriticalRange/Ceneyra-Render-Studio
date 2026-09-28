# Ceneyra Render Studio

Ceneyra Render Studio, mobilya ve TV ünitesi ürünleri için otomatik malzeme varyantları hazırlama, UVW Box eşleme, önizleme ve V-Ray katalog renderları alma stüdyosudur.

Artık **3ds Max kapalıyken bile** doğrudan `.bat` dosyasıyla bağımsız (standalone) modern masaüstü arayüzü olarak çalışabilir.

---

## 🚀 Hızlı Başlangıç

1. **`CENEYRA_STUDIO.bat`** dosyasına çift tıklayarak stüdyoyu başlatın.
   *(3ds Max'in açık olmasına gerek yoktur; arka planda 3ds Max 2027 / 2026 / 2025 motorunu kullanır).*
2. İsterseniz bir `.max`, `.skp` veya `.vrscene` dosyasını doğrudan `CENEYRA_STUDIO.bat` üzerine sürükleyip bırakabilirsiniz.

---

## 🎨 Arayüz ve İşleyiş

1. **Ürün & Sahne Seçimi (En Üst Solda):**
   - `.max`, `.skp`, `.vrscene` vb. sahne dosyasını seçin veya sürükleyip bırakın.
   - Ürün kodu ve dosya boyutu otomatik algılanır.
2. **Ürün Fotoğrafı / Önizleme Alanı:**
   - Ürün eklendiğinde sistem sahneye ait mevcut katalog renderını (`.png`, `.jpg`) otomatik arar ve gösterir.
   - Eğer önceden alınmış bir render yoksa, şık **"Render / Fotoğraf Bulunamadı"** uyarısı gösterilir.
   - Yakınlaştırma (zoom), kaydırma (pan) ve ekrana sığdırma (fit) desteklenir.
3. **Renk & Varyant Menüsü (Önizlemenin Altında):**
   - Ürünün dönüştürüleceği renk varyantını seçin:
     - **Antrasit Gri** (Gövde, Dikmeler ve Kapaklar)
     - **Beyaz** (Orijinal Sahne Rengi)
     - **Safir Meşe** (Doğal Ahşap + Otomatik Box UVW)
     - **Traverten** (Doğal Mermer Doku)
   - **Pleksi ve Metal Detay Rengi:**
     - **Altın Pleksi** (Gold Detay)
     - **Gümüş Pleksi** (Silver Detay)
   - Hazır hızlı kombinasyon butonları (*Antrasit/Gold*, *Antrasit/Silver*, *Beyaz/Gold* vb.).
4. **Kamera Konumu:**
   - Sahnedeki kamera açısını belirleyin: *Varsayılan Kamera*, *Kamera 01 - Cephe*, *Kamera 02 - Çapraz (45°)*, *Kamera 03 - Detay*.
5. **Render Seçenekleri & Düğmeler:**
   - **Çıktı Klasörü:** Çıktıların kaydedileceği yol ve **Klasörü Aç** (Explorer) butonu.
   - **Çözünürlük:** `2000 × 3000` (Katalog Dikey), `3840 × 2160` (4K UHD), `1920 × 1080` (FHD), `1000 × 1500`, `400 × 600`.
   - **Kalite:** *Final / Sahne Ayarları*, *Kontrol / Orta*, *Taslak / Hızlı Test*.
   - **V-Ray Test Renderı:** Hızlı test renderı seçeneği ve test butonu.
   - **Viewport Yenile:** Şık animasyonlu, sahneyi seçili renkle yenileyip önizleme çeken buton.
   - **Render'ı Başlat:** Yüksek öncelikli render butonu.

---

## 🧩 Parça İsimlendirme & Otomatik Materyal Değişimi

TV üniteleri ve mobilyalar için akıllı parça eşleme sistemi mevcuttur:

| Parça Grubu | İsimlendirme Formatı | Değişim Kuralı |
| :--- | :--- | :--- |
| **Kapaklar** | `kapak001`, `kapak002`, `Group#5*` | Antrasit/Beyaz/Meşe materyaline geçer. Multi/Sub varsa ID 1 güncellenir, ID 2 lazer korunur. |
| **Dikmeler** | `dikme001L`, `dikme001R`, `dikme*` | Gövde ve kapaklarla aynı renk varyantına geçer. |
| **Gövde** | `govde*`, `gövde*`, `Group#1*`..`#4`, `#9` | Seçilen ana materyale geçer. |
| **Pleksi / Detay** | `pleksi*`, `Group#6*`, `altin*`, `gumus*` | Altın (Gold) veya Gümüş (Silver) seçildiğinde otomatik tüm parçalar değişir. |
| **Ayaklar** | `ayak*`, `190 ELEGANZ AYAK*` | Ayak boya ve metal detaylarına uygun materyaller atanır. |

> **İpucu:** Gelişmiş ayarlardaki **"Tüm Parçaları Standart İsimlendir"** butonuyla sahnedeki henüz adlandırılmamış parçaları tek tıkla standart formata dönüştürebilirsiniz.