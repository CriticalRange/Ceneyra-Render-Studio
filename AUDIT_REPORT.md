# CENEYRA RENDER STUDIO — KAPSAMLI MÜHENDİSLİK DENETİM RAPORU (ENGINEERING AUDIT REPORT)

**Tarih:** 28 Eylül 2026  
**Denetim Türü:** Salt Okunur (Read-Only) Kapsamlı Kaynak Kod, Süreç, Güvenlik ve Mimari Denetimi  
**Kapsanan Dosyalar:**
- Çalıştırıcılar (Launchers): `CENEYRA_STUDIO.bat`, `Launch-Ceneyra-Render-Studio.bat`
- Bağımsız Masaüstü Arayüzü: `ceneyra_gui.py` (PySide6)
- Batch & Otomasyon Köprüsü: `CRS_BatchWorker.ms`, `CRS_VariantAutomation.ms`
- Çekirdek MAXScript Motoru: `Ceneyra_Render_Studio.ms`, `CRS_Core.ms`, `CRS_Engine.ms`, `CRS_UI.ms`, `CRS_Worker.ms`
- Test Paketi: `CRS_Tests.ms`, `CRS_GuiTests.ms`, `CRS_LaunchTests.ms`, `CRS_RenderTests.ms`
- Dokümantasyon: `README.md`

---

## 1. YÖNETİCİ ÖZETİ (EXECUTIVE SUMMARY)

Ceneyra Render Studio, mobilya ve TV ünitesi modelleri için malzeme varyantları hazırlama, UVW eşleme ve V-Ray katalog renderları alma amacıyla geliştirilmiş hibrit bir sistemdir.

Yapılan detaylı statik analiz ve kaynak kod denetimi sonucunda, sistemin **birbirinden kopuk iki paralel mimariye** bölündüğü tespit edilmiştir:
1. **Orijinal Çekirdek Mimari (`CRS_Core.ms` + `CRS_Engine.ms` + `CRS_UI.ms`):** 3ds Max içinde çalışan; SHA-256 tabanlı sahne/doku parmak izi alma, baseline sahne yakalama/geri yükleme (`CRS_capture` / `CRS_restore`), MultiMatte maskeleri, çoklu iş kuyruğu ve işlem kilitleme (`worker.lock`) gibi gelişmiş kurumsal güvencelere sahip, olgun ve disiplinli bir yapı.
2. **Yeni Eklenen Headless Masaüstü Mimarisi (`ceneyra_gui.py` + `CRS_BatchWorker.ms` + `CRS_VariantAutomation.ms`):** Standalone PySide6 arayüzünden `3dsmaxbatch.exe` çağıran; ancak orijinal çekirdek motoru ve onun sağladığı güvenlik/veri bütünlüğü mekanizmalarını **tamamen baypas eden**, yıkıcı sahne üzerine yazma (destructive overwrite), zombi işlem sızıntıları, güvenli sahne denetiminin kapatılması (`-safescene off`) ve UI ile worker arasındaki bağlantısızlıklar (dead controls) barındıran kontrolsüz bir yapı.

Aşağıdaki raporda, tespit edilen somut hatalar öncelik seviyelerine (P0-P3) ve tam dosya/satır numaralarına göre kanıtlarıyla sunulmuş; README vaatleri ile fiili durum karşılaştırılmış; eksik yetenekler ve akılcı özellik önerileri ayrı bölümlerde detaylandırılmıştır.

---

## 2. README VAATLERİ VE FİİLİ GERÇEKLİK KARŞILAŞTIRMASI

| README Vaadi | Fiili Durum / Gerçekleşme | Doğruluk Durumu | Dosya / Satır Kanıtı |
| :--- | :--- | :---: | :--- |
| **"3ds Max kapalıyken bile doğrudan .bat ile bağımsız masaüstü arayüzü"** | `.bat`, 3ds Max kurulumundaki dahili Python'ı arar. Max kurulu değilse sistemdeki `python`'a düşer. Ancak sistem Python'ında `PySide6` yüklü olmadığından pencere anında kapanır. | ⚠️ Kısmen Doğru / Kırılgan | [CENEYRA_STUDIO.bat#L11-L29](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CENEYRA_STUDIO.bat#L11-L29) |
| **".max, .skp veya .vrscene dosyasını sürükleyip bırakabilirsiniz"** | UI `.skp` ve `.vrscene` uzantılarını kabul eder; ancak arka planda `CRS_BatchWorker.ms` yalnızca `loadMaxFile` çağırır. `loadMaxFile` SketchUp veya V-Ray sahne dosyalarını açamaz, işlem sessizce çöker. | ❌ Yanıltıcı / Çalışmıyor | [CRS_BatchWorker.ms#L46](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_BatchWorker.ms#L46), [ceneyra_gui.py#L891](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L891) |
| **"RGB MultiMatte Maske Çıktısı Al"** | UI üzerinde onay kutusu (`chk_masks`) bulunur; ancak bu ayar `BatchProcessWorker`'a hiçbir zaman iletilmez. `CRS_BatchWorker.ms` içinde render element oluşturma veya kaydetme kodu bulunmamaktadır. | ❌ Vaat Var, Kod Yok (Kopuk) | [ceneyra_gui.py#L800](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L800), [ceneyra_gui.py#L1116-L1127](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L1116-L1127) |
| **"Tüm Parçaları Standart İsimlendir (kapak001...) tek tıkla adlandırılmamış parçaları dönüştürür"** | Fonksiyon (`getPartsByRole`), nesneleri bulmak için zaten isimlerinde `*kapak*`, `*dikme*`, `*govde*` aramaktadır. İsimlendirilmemiş parçaları bulamaz. Ayrıca orijinal sahneyi yedeksiz ezer. | ❌ Mantık Hatası & Veri Kaybı Riski | [CRS_VariantAutomation.ms#L36-L58](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_VariantAutomation.ms#L36-L58), [CRS_BatchWorker.ms#L64](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_BatchWorker.ms#L64) |
| **"Seçilen Çözünürlük ve Kalitede Render Alma"** | Kullanıcı Kaliteyi "Taslak" seçtiğinde, seçtiği çözünürlük (ör. 4K veya 2000x3000) kullanıcıya haber verilmeden arka planda sessizce `(1000, 1500)` değerine ezilir. | ⚠️ Gizli Yan Etki | [ceneyra_gui.py#L1101-L1102](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L1101-L1102) |
| **"Orijinal Sahnenin Korunması (Güvenli Çalışma Kopyası)"** | Orijinal `Launch-Ceneyra-Render-Studio.bat` kopyalama önerirken, yeni `CRS_BatchWorker.ms` rename modunda doğrudan kullanıcı sahnesinin üzerine `saveMaxFile` kaydetmektedir. | ❌ Güvenlik Kuralı İhlali | [CRS_BatchWorker.ms#L64](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_BatchWorker.ms#L64) |

---

## 3. MİMARİ ANALİZ: PYTHON UI -> BATCH WORKER -> MAXSCRIPT ENTEGRASYONU

Sistem mimarisi incelendiğinde ciddi bir entegrasyon kopukluğu (architectural gap) görülmektedir:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [YENİ HİBRİT YOLAK - STANDALONE PYTHON UI]                                              │
│                                                                                        │
│   ceneyra_gui.py (PySide6)                                                             │
│       │                                                                                │
│       ▼ subprocess.Popen                                                               │
│   3dsmaxbatch.exe (Flags: -safescene off, -mxsString ...)                              │
│       │                                                                                │
│       ▼                                                                                │
│   CRS_BatchWorker.ms ───► CRS_VariantAutomation.ms                                     │
│       │                      │                                                         │
│       ├─ render (Basit)      ├─ Direct node.material assignment (Geri almasız)         │
│       └─ status.json         └─ UVW Map modifier stack mutasyonu                       │
│                                                                                        │
│   [TAMAMEN DEVRE DIŞI BIRAKILAN / BYPASS EDİLEN ÇEKİRDEK GÜVENLİK MODÜLLERİ]          │
│   ❌ CRS_Core.ms (CRS_capture, CRS_restore, CRS_Model, SHA-256 parmak izi)            │
│   ❌ CRS_Engine.ms (MultiMatteElement maskeleri, pause/resume/stop, worker.lock)       │
│   ❌ CRS_Worker.ms (Doğrulanmış iş kuyrukları, snapshot.max güvenli kopyası)          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Temel Entegrasyon Zafiyetleri:
1. **İki Ayrı Gerçeklik (Split Source of Truth):**
   `CRS_Core.ms` içinde varyantlar matris olarak (ör. 6 malzeme yuvası, 10 katalog varyantı: `BG`, `BS`, `AG`, `AS`, `BTG`, `BTS`, `ATG`, `ATS`, `DBG`, `DBS`) tanımlanmışken; `ceneyra_gui.py` ve `CRS_VariantAutomation.ms` bağımsız bir `applyVariant` yapısı kurmuş ve bu iki yapı birbirinin veri modellerini tanımaz hale gelmiştir.
2. **Telemetri ve Durum İletişimi Zayıflığı:**
   `CRS_BatchWorker.ms`, durumu `statusPath` JSON dosyasına yazmaktadır. Ancak 3ds Max bir MAXScript hatası aldığında veya `render` çağrısı anında çöktüğünde `writeStatus` bloğuna erişememekte; Python tarafındaki `BatchProcessWorker` ise yalnızca return code'a bakarak takılabilmekte veya generic bir hata üretmektedir.

---

## 4. ÖNCELİKLENDİRİLMİŞ SOMUT HATALAR VE KANITLAR

### 4.1. KRİTİK SEVİYE HATALAR (CRITICAL / P0 - P1)

#### BUG-01: Rename Modunda Orijinal Sahnenin Yedeksiz Üzerine Yazılması (Destructive Overwrite)
- **Konum:** [`CRS_BatchWorker.ms` Satır 63-66](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_BatchWorker.ms#L63-L66)
- **Kod:**
  ```maxscript
  if mode == "rename" do (
      CRS_Automator.standardizePartNames()
      if sceneFile != undefined and doesFileExist sceneFile do (
          saveMaxFile sceneFile quiet:true
      )
  ```
- **Hata Tanımı:** Kullanıcı arayüzde "Tüm Parçaları Standart İsimlendir" butonuna bastığında, batch worker orijinal sahneyi doğrudan `saveMaxFile sceneFile quiet:true` ile kaydeder. Orijinal nesne hiyerarşisi, adlandırması veya sahne durumu geri dönüşsüz biçimde bozulabilir. `CRS_Core.ms`'in en temel prensibi olan "orijinal sahneye asla yazmama" kuralı çiğnenmektedir.
- **Yeniden Üretim:** Arayüzde bir `.max` sahnesi seçip "Tüm Parçaları Standart İsimlendir" butonuna tıklayın. Orijinal dosyanın son değiştirilme tarihinin güncellendiğini ve sahne içeriğinin üzerine yazıldığını gözlemleyin.

---

#### BUG-02: `-safescene off` ile Güvenlik Açığı Oluşturulması (Untrusted Script Execution)
- **Konum:** [`ceneyra_gui.py` Satır 469](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L469)
- **Kod:**
  ```python
  cmd = [
      batch_exe,
      str(worker_script),
      ...
      "-safescene", "off",
      "-v", "2"
  ]
  ```
- **Hata Tanımı:** `CRS_Engine.ms` (satır 71) ve `README.md` güvenli render için `-safescene on` zorunlu tutarken, Python arayüzü headless çağrıda güvenliği bilerek kapatmaktadır (`-safescene off`). Üçüncü taraflardan gelen bir `.max` dosyasının içinde gömülü kötü amaçlı MAXScript (sahne scriptleri, Pre-Render script virüsleri) otomatik olarak kullanıcının sisteminde tam yetkiyle çalıştırılır.
- **Yeniden Üretim:** `ceneyra_gui.py` içerisindeki `cmd` listesine bakın. Güvenli sahne korumasının kapatıldığı sabittir.

---

#### BUG-03: Zombi `3dsmaxbatch.exe` Süreçleri ve İptal/Yaşam Döngüsü Yönetimi Eksikliği
- **Konum:** [`ceneyra_gui.py` Satır 477-505](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L477-L505) ve [`ceneyra_gui.py` Sınıf Tanımı Satır 526-536](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L526-L536)
- **Hata Tanımı:**
  1. `BatchProcessWorker` içinde `self._is_cancelled = False` değişkeni tanımlanmış ancak hiçbir yerde kullanılmamıştır.
  2. UI'da bir iptal (Cancel/Stop) butonu yoktur.
  3. `CeneyraStudioWindow` sınıfında `closeEvent` metodu bulunmamaktadır. Kullanıcı arayüz penceresini kapattığında, arka plandaki `3dsmaxbatch.exe` süreci sonlandırılmaz; işletim sisteminde CPU'yu %100 kullanan bir "zombi" işlem olarak arka planda çalışmaya devam eder.
- **Yeniden Üretim:** Bir render başlatın, hemen ardından pencereyi sağ üstteki çarpıdan kapatın. Görev Yöneticisi'ni açın; `3dsmaxbatch.exe` işleminin arka planda render almaya devam ettiğini görün.

---

#### BUG-04: Multi-Material Yapısının Bozulması ve Lazer Yüzeyinin Kalıcı Kaybı
- **Konum:** [`CRS_VariantAutomation.ms` Satır 89-103](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_VariantAutomation.ms#L89-L103)
- **Kod:**
  ```maxscript
  fn setDoorMaterial doorNode targetMtl faceID:1 = (
      if doorNode == undefined or targetMtl == undefined do return false
      if isKindOf doorNode.material MultiMaterial then (
          local mm = copy doorNode.material
          local slot = findItem mm.materialIDList faceID
          if slot > 0 then (
              mm.materialList[slot] = targetMtl
          ) else if mm.materialList.count >= faceID then (
              mm.materialList[faceID] = targetMtl
          )
          doorNode.material = mm
      ) else (
          doorNode.material = targetMtl
      )
      true
  )
  ```
- **Hata Tanımı:** Kapak nesnelerinde lazer kanalları (ID 2) bulunmaktadır. Eğer sahne içe aktarılırken veya bir dönüşümde kapak nesnesi geçici olarak standart bir materyalle gelmişse, kod `doorNode.material = targetMtl` yaparak nesneyi tekil malzemeye çevirmekte; sonrasında ID tabanlı lazer detaylandırma yeteneği imkansız hale gelmektedir. Ayrıca `CRS_Core.ms`'deki gibi bir orijinal durum yedeklemesi yapılmadığından, sahnedeki malzeme değişimleri kalıcı hale gelmektedir.

---

#### BUG-05: Türkçe Karakter ASCII `toLower` Eşleşme Çöküşü
- **Konum:** [`CRS_VariantAutomation.ms` Satır 8-10 ve Satır 42](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_VariantAutomation.ms#L8-L10)
- **Kod:**
  ```maxscript
  fn toLowerStr str = (
      toLower (str as string)
  )
  ...
  "govde": patList = #("*govde*", "*gövde*", "*body*", "*karkas*", "group#1 *", ...)
  ```
- **Hata Tanımı:** 3ds Max MAXScript motorundaki `toLower` fonksiyonu yalnızca standart ASCII (A-Z) karakterleri küçültür. Türkçe `Ö`, `İ`, `Ş`, `Ç`, `Ğ`, `Ü` karakterleri büyük harf olarak kalır. Örneğin sahnedeki bir nesnenin adı `"GÖVDE_01"` ise:
  `toLower "GÖVDE_01"` ifadesi `"gÖvde_01"` üretir.
  Ardından `matchPattern "gÖvde_01" pattern:"*gövde*"` sorgulandığında, `Ö` harfi `ö` ile eşleşmediği için desen eşleşmesi **başarısız olur**! Türkiye mobilya sektöründeki Türkçe adlandırılmış parçalar algılanamaz.

---

### 4.2. YÜKSEK SEVİYE HATALAR (HIGH / P2)

#### BUG-06: Desteklendiği İddia Edilen `.skp` ve `.vrscene` Dosyalarının Açılamaması
- **Konum:** [`CRS_BatchWorker.ms` Satır 46](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_BatchWorker.ms#L46), [`ceneyra_gui.py` Satır 601, 891](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L601)
- **Hata Tanımı:** UI ve README `.skp` ve `.vrscene` dosyalarının desteklendiğini iddia etmektedir. Ancak `CRS_BatchWorker.ms` yalnızca `loadMaxFile sceneFile quiet:true` kullanır. 3ds Max'te SketchUp veya vrscene dosyaları `loadMaxFile` ile açılamaz (`importFile` veya V-Ray standalone importer gerekir). `loadMaxFile` `false` döner ve boş/eski sahne üzerinde render alınmaya çalışılır.

---

#### BUG-07: Gelişmiş Ayarlardaki Maske ve UVW Seçeneklerinin Worker'a İletilmemesi (Dead Controls)
- **Konum:** [`ceneyra_gui.py` Satır 795, 800 ve Satır 1116-1127](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L795)
- **Hata Tanımı:**
  - `self.chk_uvw_box = QtWidgets.QCheckBox("UVW Box Mapping Uygula...")`
  - `self.chk_masks = QtWidgets.QCheckBox("RGB MultiMatte Maske Çıktısı Al")`
  Bu iki kontrol arayüzde yer alır ve kullanıcı bunları işaretleyebilir/kaldırabilir. Ancak `run_full_render` metodunda `BatchProcessWorker` başlatılırken bu değerler parametre olarak aktarılmaz. `CRS_BatchWorker.ms` komut satırı argümanlarında da bu parametrelerin karşılığı yoktur.

---

#### BUG-08: Geliştirici Kişisel Yollarının Hardcoded Bırakılması
- **Konum:** [`ceneyra_gui.py` Satır 900 ve Satır 951](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L900)
- **Kod:**
  ```python
  candidates = [
      Path(r"C:\Users\Ahmet\Desktop\3.max"),
      STUDIO_DIR / "sample.max",
      STUDIO_DIR / "KA1546.max"
  ]
  ...
  Path(r"C:\Users\Ahmet\Desktop\Colab_Render\output")
  ```
- **Hata Tanımı:** Başka bir bilgisayarda veya kullanıcı oturumunda bu yollar mevcut değildir; ancak bu makinede program açılır açılmaz kullanıcının Masaüstündeki `3.max` dosyasını otomatik varsayılan sahne olarak seçmektedir. Taşınabilirlik (portability) ilkelerine aykırıdır.

---

#### BUG-09: Headless Viewport Önizlemesinde Boş Görüntü (`gw.getViewportDib`) ve Kilitlenme
- **Konum:** [`CRS_BatchWorker.ms` Satır 98-106](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_BatchWorker.ms#L98-L106)
- **Kod:**
  ```maxscript
  local b = gw.getViewportDib()
  if b != undefined do (
      ...
      writeStatus "completed" ...
  )
  quitMax #noPrompt
  ```
- **Hata Tanımı:** `3dsmaxbatch.exe` penceresiz ve grafik bağlamsız (headless) çalıştığında, OpenGL/DirectX viewport başlatılmamış olabilir. Bu durumda `gw.getViewportDib()` `undefined` döner. Kod `if b != undefined` bloğuna giremediği için `writeStatus "completed"` yazılmaz ve hemen ardından `quitMax #noPrompt` çalışır. Python tarafındaki UI işlemi başarısız sayar ve viewport önizlemesi boş kalır.

---

#### BUG-10: V-Ray Dışı Motorlarda Sessiz Hata ve Çöküş
- **Konum:** [`CRS_BatchWorker.ms` Satır 112-127](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_BatchWorker.ms#L112-L127)
- **Hata Tanımı:** Sahne açıldığında varsayılan renderer Arnold veya Scanline ise, `isProperty vr #imageSampler_type_new` koşulu sağlanmaz. Kod mevcut motoru V-Ray olarak değiştirmez veya kullanıcıyı uyarmaz; doğrudan `render` çağrısı yapar. V-Ray materyalleri Scanline/Arnold altında siyah çıkar veya sahne render hatasıyla çöker.

---

### 4.3. ORTA VE DÜŞÜK SEVİYE HATALAR (MEDIUM / P3)

#### BUG-11: 1:1 Butonunun Çalışmaması (`actual_size` Metodu Yok)
- **Konum:** [`ceneyra_gui.py` Satır 840](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L840)
- **Kod:**
  ```python
  btn_full.clicked.connect(lambda: self.canvas.actual_size() if hasattr(self.canvas, 'actual_size') else None)
  ```
- **Hata Tanımı:** `PreviewCanvas` sınıfında `actual_size` metodu tanımlanmamıştır. Butona basıldığında `hasattr` kontrolü `False` döndürür ve buton hiçbir işlem yapmaz. Tamamen ölü bir UI butonudur.

---

#### BUG-12: `search_product_photo` Yanıltıcı Görsel Eşleşmesi (False Positive)
- **Konum:** [`ceneyra_gui.py` Satır 958](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L958)
- **Kod:** `f"{stem}*.png"`
- **Hata Tanımı:** Sahne adı kısa olduğunda (örneğin Masaüstündeki `3.max` -> `stem = "3"`), arama deseni `"3*.png"` olur. Masaüstündeki veya çıktı klasöründeki `3dsmax_setup.png`, `30_render.png`, `3D_model.png` gibi `3` ile başlayan tamamen alakasız herhangi bir görsel en son değiştirilme tarihine göre ürünün render fotoğrafı zannedilerek arayüze basılır.

---

#### BUG-13: Kullanıcı Çözünürlüğünün "Taslak" Kalitede Sessizce Ezilmesi
- **Konum:** [`ceneyra_gui.py` Satır 1101-1102](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L1101-L1102)
- **Kod:**
  ```python
  if quality == 1 and not is_quick_test:
      res = (1000, 1500)
  ```
- **Hata Tanımı:** Kullanıcı arayüzde özel bir çözünürlük (örneğin 4K UHD) seçip kaliteyi "Taslak" yaptığında, sistem kullanıcıya haber vermeksizin çözünürlüğü `1000x1500` boyutuna indirir. Kullanıcının açık tercihi ezilmektedir.

---

#### BUG-14: Meşgul Durumunda (Busy State) Seçim Kontrollerinin Açık Kalması
- **Konum:** [`ceneyra_gui.py` Satır 1037-1049](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L1037-L1049)
- **Hata Tanımı:** `set_busy(True)` fonksiyonu render butonlarını devre dışı bırakırken; `combo_variant`, `combo_finish`, `combo_camera`, `combo_res`, `combo_quality` ve hazır kombinasyon butonlarını (`btn_ag`, `btn_as`, `btn_bg`) devre dışı bırakmaz. Render devam ederken kullanıcı varyant veya kamera değiştirebilir; bu durum çalışan işlem ile ekrandaki seçimin uyuşmazlığına yol açar.

---

#### BUG-15: .NET `File.Move` Mevcut Dosya Üzerine Yazma İstisnası
- **Konum:** [`CRS_Engine.ms` Satır 97](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_Engine.ms#L97)
- **Kod:** `(dotNetClass "System.IO.File").Move tmp path`
- **Hata Tanımı:** .NET Framework 4.8'de `File.Move(source, dest)` aşırı yüklemesi hedef dosya zaten mevcutsa `System.IO.IOException` fırlatır. Hedef dosya önceden varsa geçici dosya taşınamaz ve render kaydı çöker.

---

#### BUG-16: `CENEYRA_STUDIO.bat` Başlatıcısında Sessiz Çöküş ve Eksik Bağımlılık Geri Bildirimi
- **Konum:** [`CENEYRA_STUDIO.bat` Satır 12-29](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CENEYRA_STUDIO.bat#L12-L29)
- **Kod:**
  ```bat
  set "PY_EXE=python"
  start "CENEYRA Studio" "%PY_EXE%" "%UI_SCRIPT%"
  exit /b 0
  ```
- **Hata Tanımı:** 3ds Max standart `C:\Program Files\Autodesk` klasöründe bulunmadığında (ör. farklı bir sürücüye kurulmuşsa veya kullanıcı yalnızca arayüzü çalıştırmak istiyorsa), script varsayılan sistem `python` komutuna düşer. Ancak standart Python kurulumunda `PySide6` modülü bulunmadığında Python `ModuleNotFoundError: No module named 'PySide6'` hatası verir. `start` komutu asenkron çalışıp `.bat` hemen `exit /b 0` ile kapandığı için konsol 50 milisaniyede yok olur ve kullanıcıya hiçbir hata mesajı gösterilmez; program hiçbir tepki vermeden sessizce çöker.

---

#### BUG-17: Alt Süreçlerde `QT_PLUGIN_PATH` Ortam Sızıntısı ve AdskLicensingAgent Çöküşü (Exit Code 4294967166 / Sahnenin Açılamaması) [ONARILDI]
- **Konum:** [`ceneyra_gui.py` Satır 519-528](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L519-L528), [`ceneyra_gui.py` Satır 1140](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L1140), [`CRS_BatchWorker.ms` Satır 13-25](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/CRS_BatchWorker.ms#L13-L25)
- **Hata Tanımı:** 3ds Max 2027 içerisindeki dahili Python ortamı (`python.exe`), `QT_PLUGIN_PATH` değişkenini `C:\Program Files\Autodesk\3ds Max 2027\qt\plugins` (Qt 6.8.3) olarak tanımlar. `ceneyra_gui.py` içerisinden `subprocess.Popen` ile `3dsmaxbatch.exe` veya `3dsmax.exe` başlatıldığında, alt süreçler bu ortamı doğrudan devralır. 3ds Max lisans doğrulamasını yapan `AdskLicensingAgent.exe` (Qt 6.8.5) çalıştırıldığında bu ortam değişkenini okur ve Qt 6.8.3 eklentilerini (`qwindows.dll`) yüklemeye kalkışır. Sürüm ve ABI uyumsuzluğu nedeniyle modal Qt hata kutusu (`This application failed to start because no Qt platform plugin could be initialized...`) açarak çöker veya donar. Bu durum batch render işlemlerinin `4294967166` (-130 / Lisanslama Hatası) ile sonlanmasına ve arayüzdeki "Sahneyi 3ds Max Arayüzünde Aç" butonunun sahneli 3ds Max'i açamamasına (arkada askıda kalmasına) yol açar.
- **Çözüm / Durum:** `get_clean_env()` fonksiyonu ile `QT_` ön ekli tüm ortam değişkenleri alt süreç çağrılarından temizlenmiş; `CRS_BatchWorker.ms` içindeki tamsayı parametre dönüşümleri güvenli hale getirilmiştir. Arayüzdeki "Sahneyi Aç" butonu sahne yolunu panoya da kopyalayarak açık Max penceresine anında `Ctrl+V` ile yapıştırma kolaylığı sağlamıştır.

---

## 5. ARAYÜZ (PYSIDE6 UI) TASARIM, DUYARLILIK VE UX DENETİMİ


### 5.1. 1280x720 ve 1600x900 Çözünürlük Duyarlılığı Analizi
- **1280x720 Çözünürlük:**
  - `ceneyra_gui.py` başlangıç boyutu `1180x840` olarak ayarlanmıştır ([Satır 529](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L529)). Bu durum, 720p ekranda pencerenin dikeyde ekranın dışına taşmasına ve alt kısımdaki durum çubuğu ile log butonunun görünmemesine neden olur.
  - Sol panelde dikey kaydırma çubuğu (`QScrollArea`) bulunması olumludur; ancak "Gelişmiş Ayarlar" açıldığında içerik ~980px yüksekliğe ulaşmakta ve çok fazla kaydırma gerektirmektedir.
  - Çözünürlük ve Kalite açılır kutuları yan yana konulduğunda ([Satır 713-733](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L713-L733)), 380px panel genişliğinde "2000 × 3000 · Katalog Dikey (Önerilen)" metni kutuya sığmayarak elide edilmekte/kesilmektedir.
- **1600x900 Çözünürlük:**
  - Sol panel genişliği `setMaximumWidth(460)` ile sınırlandırıldığı için düzen dengeli kalmakta, sağ taraftaki önizleme tuvali (`PreviewCanvas`) genişleyerek ferah bir çalışma alanı sunmaktadır.

### 5.2. Renk Paleti ve Erişilebilirlik (WCAG / Contrast)
- **Marka Kimliği:** Obsidian Koyu Gri (`#111416`, `#181d20`) zemin üzerinde Şampanya Altını (`#efba73`) vurgu rengi estetik olarak başarılıdır ve stüdyo kimliğini yansıtmaktadır.
- **Kontrast Değerlendirmesi:**
  - Birincil Buton (`#efba73` üzerine `#1c1813` koyu metin): Kontrast oranı **~11.2:1** (WCAG AAA seviyesinde mükemmel).
  - İkincil Butonlar (`#262e33` üzerine `#efba73` metin): Kontrast oranı **~7.4:1** (WCAG AAA seviyesinde).
  - Alt Başlıklar (`#8f9b9f` metin rengi): Kontrast oranı **~4.5:1** (WCAG AA sınırında; loş ekranlarda okunurluğu artırmak için `#a5b3b7` önerilir).
  - Devre Dışı Kontroller (`#586469` üzerine `#293135` sınır): Kontrast düşüktür ancak devre dışı durumlar için standarttır.

### 5.3. Önizleme Tuvali (Canvas) ve Etkileşimler
- Tuval üzerinde fare tekerleğiyle yakınlaştırma (zoom), sürükleyerek kaydırma (pan) ve çift tıklamayla sığdırma (fit) akıcı biçimde çalışmaktadır.
- Fotoğraf bulunamadığında devreye giren özel vektörel ikon ve açıklayıcı metin tasarımı görsel olarak tatmin edicidir.
- Ancak yukarıda belirtildiği üzere, üst bardaki "1:1" butonu kod eksikliği nedeniyle çalışmamaktadır.

---

## 6. EKSİK YETENEKLER (MISSING CAPABILITIES)

1. **SketchUp (`.skp`) ve V-Ray Scene (`.vrscene`) Doğrudan İçe Aktarma:**
   UI dosya filtresinde bu formatlar yer almasına rağmen, arka planda bunları 3ds Max içine aktaracak import köprüsü ve malzeme dönüştürücü motor bulunmamaktadır.
2. **Kuyruk Yönetimi (Queue / Batch List):**
   Orijinal `CRS_UI.ms` ve `CRS_Engine.ms` çoklu varyant ve kameraları birleştirip 20 işlik bir render kuyruğu oluşturabilirken; `ceneyra_gui.py` yalnızca tek seferde tek bir varyant/kamera renderı alabilmektedir. Toplu katalog kuyruğu yeteneği GUI'ye taşınmamıştır.
3. **RGB MultiMatte Maske Çıktısı (Headless):**
   Headless batch worker'da nesne bazlı (Gövde, Kapak, Pleksi, Ayak) render elemanları ve maske PNG çıktıları üretilememektedir.
4. **Durdurma / Duraklatma (Pause / Resume / Cancel):**
   Başlatılan bir headless render işlemini duraklatma veya güvenli şekilde iptal etme yeteneği bulunmamaktadır.
5. **Doku / Asset Bütünlük Denetimi (Pre-Flight Asset Check):**
   `CRS_Engine.ms`'de bulunan render öncesi eksik doku kontrolü (`CRS_missing`) headless worker'a entegre edilmemiştir. Eksik kaplamalar durumunda V-Ray eksik dokuyla hatalı render almaktadır.

---

## 7. MANTIKLI VE UYGULANABİLİR ÖZELLİK ÖNERİLERİ (FEATURE PROPOSALS)

1. **Tek Birleşik Motor (Unified Architecture Bridge):**
   `ceneyra_gui.py`'nin doğrudan `CRS_Engine.ms` ve `CRS_Worker.ms` tarafından üretilen `queue.xml` yapısını beslemesi; böylece parmak izi, kilit mekanizması, çoklu kuyruk ve MultiMatte yeteneklerinin otomatik olarak kazanılması.
2. **Güvenli Geçici Kopya Çalışma Alanı (Isolated Scratch Scene):**
   Açılan her sahnenin otomatik olarak `cache/temp_<uuid>.max` kopyasının oluşturulması ve tüm varyant/isimlendirme/render işlemlerinin bu geçici kopya üzerinde yapılması; kullanıcının orijinal sahnesinin dokunulmazlığının garanti edilmesi.
3. **Subprocess Yönetimi ve Temiz Kapanış (Process Lifetime Manager):**
   `CeneyraStudioWindow.closeEvent` içinde aktif `QThread` ve arka plandaki `3dsmaxbatch.exe` sürecinin `process.terminate()` / `taskkill /F /T` ile temizlenmesi.
4. **Türkçe Karakter Normalizasyonu:**
   `CRS_VariantAutomation.ms` içine Unicode-safe karakter haritalama tablosu (`Ö->ö`, `İ->i`, `Ş->ş`, `Ç->ç`, `Ğ->ğ`, `Ü->ü`) eklenerek Türk mobilya üreticilerinin sahne adlandırmalarıyla %100 uyum sağlanması.
5. **Toplu Varyant Katalog Sihirbazı:**
   Arayüze eklenecek "Tüm Renk Kombinasyonlarını Sırala" butonuyla, 4 renk x 2 pleksi x 3 kamera kombinasyonunun tek tıkla kuyruğa eklenmesi ve tahmini süre göstergesi.

---

## 8. TEST KALİTESİ VE EKSİK BAĞIMLILIKLAR

### 8.1. Mevcut Test Paketi Durumu:
- Mevcut `CRS_Tests.ms`, `CRS_GuiTests.ms`, `CRS_LaunchTests.ms`, `CRS_RenderTests.ms` dosyaları yalnızca orijinal MAXScript kodunu test etmektedir.
- Bu testler çalıştırılabilmek için ortam değişkeni olarak `CRS_TEST_SCENE` ile `KA1546` disposable sahnesini beklemekte; sahne yoksa derhal başarısız olmaktadır.
- `CRS_Tests.ms` Satır 18'de `maxOps.getNodeByHandle 36662` gibi sabit nesne tanıtıcısına (handle) bağımlıdır; bu durum testleri aşırı kırılgan yapmaktadır.

### 8.2. Yeni Eklenen Kodların Test Durumu:
- `ceneyra_gui.py` için **hiçbir birim testi (unit test), mock testi veya arayüz testi bulunmamaktadır**.
- `CRS_BatchWorker.ms` ve `CRS_VariantAutomation.ms` için otomatikleştirilmiş hiçbir test yazılmamıştır.
- PySide6 bileşenlerinin penceresiz (offscreen) ortamda doğrulanmasını sağlayacak bir `pytest-qt` altyapısı kurulmamıştır.

### 8.3. Eksik Bağımlılıklar:
- Sistem Python'ında (Python 3.12) `PySide6` kütüphanesi eksiktir. Sadece 3ds Max 2027 kurulumundaki gömülü Python ortamında PySide6 mevcuttur.
- `.bat` başlatıcısı ortam doğrulamasını zorunlu kılmamaktadır.

---

## 9. YENİDEN ÜRETİLEBİLİRLİK (REPRODUCIBILITY) VE DOĞRULANAMAYAN HUSUSLAR

### 9.1. Hataların Yeniden Üretim Adımları:
1. **Zombi İşlem:** `CENEYRA_STUDIO.bat` ile uygulamayı açın, bir sahne seçip Render başlatın ve GUI penceresini kapatın. PowerShell üzerinden `Get-Process 3dsmaxbatch` komutunu çalıştırarak sürecin arka planda kaldığını doğrulayın.
2. **Ölü Buton:** Arayüzdeki "1:1" butonuna tıklayın; hiçbir yakınlaştırma veya pencere değişikliği olmadığını gözlemleyin.
3. **Kalıcı Sahne Üzerine Yazma:** Bir test sahnesi seçin, Gelişmiş Ayarlar'dan "Tüm Parçaları Standart İsimlendir" butonuna basın. Sahne dosyasının son değiştirilme tarihine bakın; dosyanın üzerine yazıldığını teyit edin.
4. **Çözünürlük Ezilmesi:** Çözünürlüğü `3840x2160`, Kaliteyi `Taslak / Hızlı Test` seçin ve Render başlatın. Log konsolundaki `Komut:` çıktısında `width:1000 height:1500` gönderildiğini görün.

### 9.2. Doğrulanamayan Hususlar (Limitations of Static & Non-Destructive Validation):
- Gerçek pahalı V-Ray renderları (kullanıcı yönergesi gereği) çalıştırılmamıştır; bu nedenle V-Ray 7 lisans sunucusu yanıt süreleri ve çok yüksek çözünürlüklü V-Ray Frame Buffer bellek tüketimi fiili render bazında ölçülmemiştir.
- Kullanıcıya ait `3.max` ve türevi sahneler tahrif edilmemesi için değiştirilmemiş veya kaydedilmemiştir.

---

## 10. SONUÇ VE ÖNERİLEN EYLEM PLANI

Ceneyra Render Studio, arayüz estetiği ve kullanıcı deneyimi açısından modern ve şık bir tasarıma kavuşturulmuştur. Ancak bu modern kabuk, arka planda çekirdek motorun sağladığı güvenlik, kuyruk yönetimi ve veri koruma disiplininden kopmuştur. 

Sistemin üretim ortamında güvenle kullanılabilmesi için:
1. `CRS_BatchWorker.ms` içindeki yıkıcı `saveMaxFile` derhal kaldırılmalı ve çalışma kopyası prensibi zorunlu tutulmalıdır.
2. `-safescene on` aktif edilmeli, süreç sonlanma (`closeEvent` / `taskkill`) yönetimi eklenmelidir.
3. UI'daki ölü kontroller (`1:1` butonu, maske ve UVW onay kutuları) arka plan motoruna tam olarak bağlanmalıdır.
4. Çekirdek mimarideki çoklu iş kuyruğu ve MultiMatte yetenekleri bağımsız Python arayüzüne entegre edilmelidir.

### 10.1. Tamamlanan UI Onarım Turu (UI Repair Pass):
Arayüz tarafındaki kritik yerleşim ve kullanılabilirlik kusurları (sol panel genişlik aşımı ve kalite kutusu kırpılması, 1:1 butonu, Test Render kalıcı durum kirliliği, meşgul durumunda kontrollerin açık kalması, süreç iptal ve güvenli kapanış yönetimi, tırnaklı dosya yolları ve tuval yakınlaştırma çapa hataları) [`ceneyra_gui.py`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py) üzerinde onarılmış ve [`test_ceneyra_gui.py`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/test_ceneyra_gui.py) içindeki 14 adet Qt testiyle %100 doğrulanmıştır. Detaylar ve çalıştırılan komutlar için [`UI_FIX_REPORT.md`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/UI_FIX_REPORT.md) dokümanına bakınız.

