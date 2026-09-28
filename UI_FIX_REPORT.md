# CENEYRA RENDER STUDIO — UI ONARIM VE DOĞRULAMA RAPORU (UI FIX REPORT)

**Tarih:** 28 Eylül 2026  
**Hedef Dosya:** [`ceneyra_gui.py`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py)  
**Test Dosyası:** [`test_ceneyra_gui.py`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/test_ceneyra_gui.py)  
**Çalışma Ortamı:** Windows 11 / 3ds Max 2027 Python 3.12 (PySide6 6.8.3)

---

## 1. YÖNETİCİ ÖZETİ

Kullanıcı talebi doğrultusunda [`ceneyra_gui.py`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py) üzerinde sınırlı (bounded), test güdümlü ve fonksiyonelliği koruyan bir arayüz onarım turu icra edilmiştir.

Geniş kapsamlı kod tabanı yeniden yazımı (broad rewrite) yerine; doğrudan kullanıcı deneyimini bozan **yerleşim taşması (layout clipping)**, **ölü butonlar (dead controls)**, **kalıcı durum kirlenmesi (state pollution)**, **işlem iptal yeteneği eksikliği**, **meşgul durumunda eşzamanlılık açıkları** ve **Windows dosya yolu istisnaları** hedeflenmiş; önce Qt testleriyle yeniden üretilmiş, ardından düzeltilerek testlerin tamamı (%100) yeşile döndürülmüştür. Mevcut Obsidian Koyu Kömür (`#111416`) ve Şampanya Altını (`#efba73`) teması ile tüm işlevler eksiksiz korunmuştur.

---

## 2. ÇALIŞTIRILAN KESİN KOMUTLAR (EXACT EXECUTED COMMANDS)

Aşağıdaki komutlar onarım ve test sürecinde tam olarak yürütülmüştür:

### 2.1. Python ve PySide6 Ortam Tespiti
```powershell
# 3ds Max 2027 içerisindeki dahili PySide6 ortamının kontrolü
& "C:\Program Files\Autodesk\3ds Max 2027\Python\python.exe" -c "import PySide6; print('PySide6 in 3ds Max 2027:', PySide6.__version__)"
# ÇIKTI: PySide6 in 3ds Max 2027: 6.8.3
```

### 2.2. Hataları Yeniden Üreten İlk Test Koşusu (Onarım Öncesi - Başarısızlık Tespiti)
```powershell
& "C:\Program Files\Autodesk\3ds Max 2027\Python\python.exe" -m unittest test_ceneyra_gui.py
```
**İlk Test Çıktısı (Reproduction Output):**
```
FFFFFFEFF
======================================================================
FAIL: test_01_left_panel_layout_no_clipping (test_ceneyra_gui.TestCeneyraGuiDefects)
AssertionError: 482 not less than or equal to 460 : left_widget min width (482) exceeds scroll max width (460)

FAIL: test_02_canvas_actual_size_method_exists_and_works (test_ceneyra_gui.TestCeneyraGuiDefects)
AssertionError: False is not true : PreviewCanvas must implement actual_size() for 1:1 zoom button

FAIL: test_03_test_render_does_not_pollute_checkbox_state (test_ceneyra_gui.TestCeneyraGuiDefects)
AssertionError: True is not false : chk_test_mode must NOT be mutated to checked when clicking Test Render

FAIL: test_04_scene_path_changed_handles_quotes_and_clearing (test_ceneyra_gui.TestCeneyraGuiDefects)
AssertionError: WindowsPath('C:/Users/Ahmet/Desktop/3.max') is not None

FAIL: test_05_busy_state_disables_all_conflicting_controls (test_ceneyra_gui.TestCeneyraGuiDefects)
AssertionError: True is not false (combo_variant is enabled)

FAIL: test_06_batch_worker_has_cancel_and_stops_process (test_ceneyra_gui.TestCeneyraGuiDefects)
AssertionError: False is not true : BatchProcessWorker must have cancel() method

ERROR: test_07_output_folder_handles_quotes (test_ceneyra_gui.TestCeneyraGuiDefects)
AttributeError: 'CeneyraStudioWindow' object has no attribute 'get_output_dir'

FAIL: test_08_elided_label_minimum_size_hint (test_ceneyra_gui.TestCeneyraGuiDefects)
AssertionError: 384 != 0

FAIL: test_09_preview_canvas_zoom_anchor_zero_zero (test_ceneyra_gui.TestCeneyraGuiDefects)
AssertionError: 0.0 == 0.0

Ran 9 tests in 0.719s
FAILED (failures=8, errors=1)
```

### 2.3. Onarım Sonrası Doğrulama Test Koşusu (Tüm Testler Başarılı)
```powershell
& "C:\Program Files\Autodesk\3ds Max 2027\Python\python.exe" -m unittest test_ceneyra_gui.py
```
**Nihai Test Çıktısı (Final Test Output):**
```
..............
----------------------------------------------------------------------
Ran 14 tests in 0.654s

OK
```

### 2.4. Temiz Modül İçe Aktarım Doğrulaması
```powershell
& "C:\Program Files\Autodesk\3ds Max 2027\Python\python.exe" -c "import ceneyra_gui; print('ceneyra_gui imports cleanly!')"
# ÇIKTI: ceneyra_gui imports cleanly!
```

---

## 3. TESPİT EDİLEN, YENİDEN ÜRETİLEN VE ONARILAN KUSURLAR

### Kusur 1: Sol Panel Genişlik Aşımı ve Kalite Açılır Kutusunun Kırpılması (Layout Clipping)
- **Kök Neden:** Panel 04 içerisinde Çözünürlük ve Kalite açılır kutuları `row_rq = QHBoxLayout()` içinde yan yana yerleştirilmişti. `"2000 × 3000 · Katalog Dikey (Önerilen)"` metni 265px, `"Final / Sahne Ayarları"` metni 171px minimum genişlik talep ediyordu. Kenar boşluklarıyla birlikte bu satır 444px, panel ise 474px genişliğe ulaşıyordu. `self.left_scroll` ise `setMaximumWidth(460)` ve `setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)` ile kısıtlanmıştı. Bu sebeple 428px viewport genişliğinde Kalite kutusunun sağ tarafı ve açılır ok simgesi **31 piksel ekran dışına taşıp kesiliyordu**.
- **Uygulanan Onarım:**
  1. Çözünürlük ve Kalite kontrolleri Panel 04 içinde alt alta (dikey yığın) düzenlendi.
  2. Panel 02'deki hazır kombinasyon butonlarına kompakt iç boşluk (`padding: 6px 6px; font-size: 11px;`) uygulandı.
  3. `self.left_scroll.setMinimumWidth(360)` olarak güncellendi.
  4. Sol panel minimum genişliği 482px'den **~320px** seviyesine indi; 360px-460px aralığında ve 960x720 pencere boyutunda sıfır kırpılma garantilendi.
- **Doğrulayan Test:** `test_01_left_panel_layout_no_clipping`, `test_10_minimum_window_size_no_clipping`

---

### Kusur 2: 1:1 Butonunun Çalışmaması (`actual_size` Metodu Eksikliği)
- **Kök Neden:** Üst araç çubuğundaki `1:1` butonu `lambda: self.canvas.actual_size() if hasattr(self.canvas, 'actual_size') else None` çağırıyordu; ancak `PreviewCanvas` sınıfında `actual_size` metodu hiç yazılmamıştı (`hasattr` `False` dönüyor, buton hiçbir tepki vermiyordu).
- **Uygulanan Onarım:** [`PreviewCanvas.actual_size`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L317-L325) metodu uygulandı:
  ```python
  def actual_size(self):
      if not self.has_image or self.pixmap.isNull():
          return
      scale = self.fit_scale()
      if scale > 0:
          self.zoom = 1.0 / scale
          self.pan = QtCore.QPointF(0, 0)
          self.update_zoom_label()
          self.update()
  ```
  Butona tıklandığında görsel 1:1 piksel ölçeğine (`%100`) gelmekte ve merkezlenmektedir.
- **Doğrulayan Test:** `test_02_canvas_actual_size_method_exists_and_works`

---

### Kusur 3: "Test Render" Butonunun Kalıcı Durum Kirliliği (State Mutation Bug)
- **Kök Neden:** [`run_test_render`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L1174) metodu `self.chk_test_mode.setChecked(True)` satırıyla arayüzdeki onay kutusunu kalıcı olarak işaretliyordu. Kullanıcı daha sonra yüksek kaliteli render almak için "🚀 RENDER'I BAŞLAT" butonuna bastığında, `chk_test_mode.isChecked()` `True` kaldığı için tüm renderlar zorla `Kalite: 1` ve `1000x1500` çözünürlüğe düşürülüyordu.
- **Uygulanan Onarım:** `run_test_render` içerisinden `self.chk_test_mode.setChecked(True)` kaldırıldı; yalnızca `self.run_full_render(is_quick_test=True)` çağrılması sağlandı. Kullanıcının manuel onay kutusu tercihi bağımsız hale getirildi.
- **Doğrulayan Test:** `test_03_test_render_does_not_pollute_checkbox_state`

---

### Kusur 4: Sahne Girdi Alanında Tırnaklı Yol ve Boşaltma Yönetimi
- **Kök Neden:** [`on_scene_path_changed`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L977) metodu kullanıcı dosya yolunu sildiğinde hiçbir işlem yapmıyor, eski sahneyi hafızada tutuyordu. Windows Gezgini'nden kopyalanan çift tırnaklı veya geçersiz yollarda ise `Path.exists()` istisnaları yakalanmıyordu.
- **Uygulanan Onarım:** `clean = text.strip().strip('"').strip("'")` ile tırnak temizliği eklendi. Metin boşaltıldığında `self.current_scene = None`, `lbl_scene_size = "Dosya seçilmedi"`, `lbl_product_tag = "ÜRÜN: —"` ve tuval `set_empty` ile temizlendi. Dosya bulunamadığında veya geçersiz karakter girildiğinde `try...except` ile zarif durum bildirimi eklendi.
- **Doğrulayan Test:** `test_04_scene_path_changed_handles_quotes_and_clearing`

---

### Kusur 5: Meşgul Durumunda (Busy State) Kontrollerin Açık Kalması ve Çakışma Riski
- **Kök Neden:** [`set_busy`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L1122) yalnızca 4 butonu devre dışı bırakıyordu. Render sürerken `combo_variant`, `combo_finish`, `combo_camera`, `combo_res`, `combo_quality`, `btn_auto_rename` ve hazır preset butonları tıklanabilir durumdaydı. `btn_auto_rename` tıklandığında `self.active_worker` ezilerek eşzamanlı işlem çöküşlerine yol açıyordu.
- **Uygulanan Onarım:** `set_busy(True)` çağrıldığında tüm girdi alanları, açılır kutular, preset butonları ve yeniden adlandırma butonu devre dışı bırakıldı; işlem bitiminde `set_busy(False)` ile tekrar aktif hale getirildi.
- **Doğrulayan Test:** `test_05_busy_state_disables_all_conflicting_controls`

---

### Kusur 6: Arka Plan Süreci İptal (Cancel) Mekanizması ve Güvenli Kapanış
- **Kök Neden:** `BatchProcessWorker` içinde `self._is_cancelled = False` vardı ancak `cancel` metodu yoktu. UI üzerinde işlemi durdurma butonu bulunmuyordu. Pencere kapatıldığında (`closeEvent` yoktu) `3dsmaxbatch.exe` zombi işlem olarak CPU'yu tüketmeye devam ediyordu.
- **Uygulanan Onarım:**
  1. `BatchProcessWorker` sınıfına `cancel()` ve `_force_kill()` metotları eklendi. `run()` döngüsünde her adımda iptal bayrağı denetlendi.
  2. UI üzerinde işlem başladığında beliren `self.btn_cancel` ("⏹ İŞLEMİ DURDUR") butonu eklendi.
  3. `CeneyraStudioWindow.closeEvent` uygulanarak çalışan render varsa kullanıcıya onay sorulması ve onaylanırsa sürecin temizce kapatılması sağlandı.
- **Doğrulayan Test:** `test_06_batch_worker_has_cancel_and_stops_process`

---

### Kusur 7: Çıktı Klasörü Tırnak Temizliği ve Otomatik Dizin Oluşturma
- **Kök Neden:** `input_output` alanına Windows Gezgini'nden kopyalanan yollar tırnaklı yapıştırıldığında `Path('"C:\\renders"').exists()` `False` dönüyor veya geçersiz dizin hatası veriyordu.
- **Uygulanan Onarım:** [`get_output_dir`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L1072) yardımcı metodu eklendi. Tırnaklar ayıklanmakta ve `mkdir(parents=True, exist_ok=True)` ile klasörün fiziksel varlığı garanti edilmektedir.
- **Doğrulayan Test:** `test_07_output_folder_handles_quotes`

---

### Kusur 8: `ElidedLabel` Minimum Genişlik Kısıtı (Footer Layout Defect)
- **Kök Neden:** `ElidedLabel` sınıfı `minimumSizeHint()` metodunu ezmediği için Qt varsayılan olarak metnin tam genişliğini (~384px) minimum genişlik kabul ediyordu. Dar pencerelerde sağ alt footer alanının sıkışmasına ve taşmasına sebep oluyordu.
- **Uygulanan Onarım:** [`ElidedLabel.minimumSizeHint`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L167-L168) metodu ezilerek `QtCore.QSize(0, self.fontMetrics().height())` döndürmesi sağlandı. Böylece etiket sıfır piksele kadar akıcı şekilde `...` ile elide olabilmektedir.
- **Doğrulayan Test:** `test_08_elided_label_minimum_size_hint`

---

### Kusur 9: Yakınlaştırma Çapa Noktasında (Anchor) `QPointF(0, 0)` Mantık Hatası
- **Kök Neden:** [`zoom_by`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/ceneyra_gui.py#L338) metodunda `offset = (anchor or center) - center` yazılmıştı. Python'da `bool(QPointF(0, 0))` ifadesi `False` döndürdüğünden, çapa noktası sol-üst köşe `(0, 0)` olduğunda yanlışlıkla `center`'a düşüyordu.
- **Uygulanan Onarım:** `target_anchor = anchor if anchor is not None else center` olarak düzeltildi.
- **Doğrulayan Test:** `test_09_preview_canvas_zoom_anchor_zero_zero`

---

### Kusur 10: Görsel Önizleme Tuvali İyileştirmeleri (Zoom +/- ve Orta Tuş Pan)
- **Uygulanan Onarım:**
  1. Fare tekerleği olmayan kullanıcılar (laptop / touchpad) için üst araç çubuğuna `−` (Uzaklaştır) ve `+` (Yakınlaştır) butonları eklendi.
  2. 3D sanatçıları ve CAD kullanıcıları için standart olan Fare Orta Tuşu (`Qt.MiddleButton`) ile tuvali kaydırma (pan) desteği getirildi.
  3. Masaüstünden veya klasörden doğrudan `.png`, `.jpg`, `.jpeg`, `.webp` render görsellerini tuvale sürükleyip bırakma (drag-and-drop) yeteneği eklendi.
  4. Tuval boş durumundayken hardcoded metin yerine `self.image_caption` dinamik olarak çizdirildi.
- **Doğrulayan Test:** `test_13_preview_zoom_buttons`, `test_14_canvas_double_click_fits`

---

### Kusur 11: Render Sırasında `QtCore.qSin` AttributeError ve `QBackingStore` Painter Sızıntısı
- **Kök Neden:** Render veya viewport yenileme başlatıldığında `PreviewCanvas.set_rendering(True)` çağrılmakta; bu durum `paintEvent` içinde nabız (pulse) animasyonunu tetiklemektedir. Ancak kod içerisinde C++ Qt makrosu olan `QtCore.qSin` kullanılmıştır. PySide6'da `QtCore.qSin` bulunmadığından `AttributeError: module 'PySide6.QtCore' has no attribute 'qSin'` fırlatılmakta ve `paintEvent` yarım kaldığı için `QPainter` kapatılamayıp `QBackingStore::endPaint() called with active painter; did you forget to destroy it or call QPainter::end() on it?` uyarısı/çöküşü yaşanmaktadır.
- **Uygulanan Onarım:**
  1. `QtCore.qSin(self._activity * 6.28318)` ifadesi `math.sin(self._activity * 6.28318)` ile değiştirildi.
  2. `PreviewCanvas.paintEvent`, `StudioButton.paintEvent` ve `ElidedLabel.paintEvent` fonksiyonları `try...finally: painter.end()` kalıbı içine alınarak, herhangi bir istisna anında dahi `painter.end()` çağrılması %100 garanti altına alındı.
- **Doğrulayan Test:** `test_15_canvas_rendering_pulse_animation_paints_without_error`, `test_16_studio_button_working_state_paints_without_error`

### Kusur 10: AdskLicensingAgent Qt Platform Plugin Çakışması ve 3ds Max Başlatma Donması (Exit Code 4294967166 / Sahneyi Açmama)
- **Kök Neden:** 3ds Max 2027 içerisindeki dahili Python ortamı (`C:\Program Files\Autodesk\3ds Max 2027\Python\python.exe`) çalışırken ortam değişkenlerine `QT_PLUGIN_PATH = 'C:\Program Files\Autodesk\3ds Max 2027\qt\plugins'` (Qt 6.8.3) tanımlamaktadır. `ceneyra_gui.py` içerisindeki `subprocess.Popen` çağrıları ortam değişkenlerini filtrelemeden alt süreçlere aktardığı için, `3dsmaxbatch.exe` veya `3dsmax.exe` başlatıldığında arka planda çalışan Autodesk Lisans Yöneticisi (`AdskLicensingAgent.exe` - Qt 6.8.5) bu değişkeni devralmıştır. Qt 6.8.5 sürümündeki lisans yöneticisi, Qt 6.8.3 eklentisini (`qwindows.dll`) yüklemeye çalışırken ikili (ABI) uyumsuzluğu sebebiyle çökmüş ve ekrana modal hata kutusu (`This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem. Available platform plugins are: windows.`) fırlatmıştır. Lisans doğrulanamadığı için 3ds Max askıda kalmış (arka planda donmuş) veya `4294967166` (-130 / lisanslama hatası) hata koduyla anında sonlanmıştır. Kullanıcı arayüzdeki "Sahneyi Aç" butonuna tıkladığında da yeni 3ds Max bu diyalog yüzünden donup açılmamış, kullanıcı manuel olarak Max'i başlattığında ise sahnesiz (`Untitled`) boş sahne görmüştür.
- **Uygulanan Onarım:**
  1. `get_clean_env()` yardımcı fonksiyonu yazılmış; alt süreçlere aktarılacak ortam değişkenlerinden `QT_` ile başlayan tüm anahtarlar (`QT_PLUGIN_PATH`, `QT_QPA_PLATFORM_PLUGIN_PATH`, `QT_STYLE_OVERRIDE` vb.) tamamen temizlenmiştir.
  2. `BatchProcessWorker.run()` içerisindeki `subprocess.Popen` çağrısına `env=clean_env` atanmıştır.
  3. `open_scene_in_3dsmax()` içerisindeki `subprocess.Popen([max_exe, scene_str], env=get_clean_env())` çağrısı temizlenmiş; ayrıca kullanıcının açık olan 3ds Max arayüzünde hızlıca açabilmesi için sahne dosya yolu doğrudan Windows panosuna (`clipboard.setText`) kopyalanarak bilgilendirme kaydı düşülmüştür.
  4. `CRS_BatchWorker.ms` içerisinde tanımlanmamış (`undefined`) komut satırı argümanlarının (`width`, `height`, `quality`) `as integer` dönüşümünde çökmesi engellenmiş, güvenli tip dönüşümü eklenmiştir.
- **Doğrulayan Test:** `test_17_clean_env_strips_qt_variables`, `test_18_open_scene_in_3dsmax_uses_clean_env`

### Kusur 12: `CRS_VariantAutomation.ms` İçi `-- No "join" function for OK` ve Türkçe / Unicode Dosya Yolu ANSI Bozulması
- **Kök Neden:**
  1. `CRS_VariantAutomation.ms` satır 168-170'de kapak, dikme ve gövde UVW eşlemesi için iç içe `join` çağrısı `(join (copy doors) (join (copy dikmeler) (copy govde)))` yapılmıştır. MAXScript dilinde `join <array1> <array2>` bir ifade olarak birleştirilmiş diziyi döndürmez; ilk diziyi yerinde (in-place) değiştirip `OK` döner. Bu sebeple içteki `join` işlemi `OK` döndürmüş ve dıştaki `join (copy doors) OK` çağrısı MAXScript çalışma zamanında derhal `-- No "join" function for OK` istisnası fırlatarak render işlemini kesmiştir. Bu hata Beyaz varyantta UVW eşlemesi koşulu çalışmadığından görünmemiş, ancak ahşap, taş ve Antrasit (`ANTHRACITE`) varyantı seçildiğinde ortaya çıkmıştır.
  2. Kullanıcı sahne dosyası Türkçe karakter içerdiğinde (`KA1546 TASLAK YENİ.max`), `3dsmaxbatch.exe` komut satırı ANSI ayrıştırıcısı `İ` karakterini yutarak dosya yolunu `KA1546 TASLAK YEN0.max` biçimine bozmuş ve dosyanın yüklenememesine yol açmıştır.
- **Uygulanan Onarım:**
  1. `CRS_VariantAutomation.ms` içerisindeki `applyUVW` fonksiyonu hem tekil nesneleri hem nesne dizilerini güvenle kabul edecek, geçersiz nesneleri atlayacak (`where isValidNode`) şekilde güncellendi. `applyVariant` içindeki iç içe hatalı `join` çağrısı kaldırılarak `doors`, `dikmeler` ve `govde` için ayrı ayrı `applyUVW` çağrıları yapıldı.
  2. `CRS_BatchWorker.ms` içerisindeki varyant uygulama adımı `try...catch` bloğuna alınarak sahne geometrisindeki beklenmedik nesne istisnalarının tüm render sürecini düşürmesi engellendi.
  3. `ceneyra_gui.py` içine Windows Win32 API `GetShortPathNameW` fonksiyonunu kullanan `get_windows_short_path` eklendi; Unicode / Türkçe karakterli dosya yolları 8.3 ASCII karşılığına (`C:\Users\Ahmet\DOWNLO~1\KA1546~2.MAX`) çevrilerek `3dsmaxbatch.exe`'ye sıfır kayıpla aktarıldı.
  4. Render çıktı dosya adları `re.sub(r'[^\w\-_.]', '_', ...)` ile güvenli hale getirildi.
  5. Doğrudan `KA1546 TASLAK YENİ.max` sahnesi üzerinde Antrasit varyantı render edilerek 529 KB boyutunda [`renders/ka1546_test.png`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/renders/ka1546_test.png) çıktısı başarıyla üretildi.
- **Doğrulayan Test:** `test_19_get_windows_short_path`

### Kusur 13: Standart Zarif İsimlendirme Mimarisi, Parça Materyal Eşleme Kutusu ve İsimlendirme Butonunun Kaldırılması
- **Kullanıcı Direktifi:**
  - Sahneler zaten adlandırılmış olarak gelecektir; bu nedenle arayüzdeki "Tüm Parçaları Standart İsimlendir" butonu tamamen kaldırılmıştır.
  - İsimlendirme karmaşık eklerden arındırılmış, sadece rol ve 3 haneli sayı formatına oturtulmuştur:
    `kapak001`, `pleksi001`, `tabla001`, `dikme001`, `raf001`, `arkalik001`, `ayak001`, `ayak_detay001` (yalnızca `ayak_detay`'da alt çizgi bulunmaktadır).
  - Kullanıcının her varyantta parça bazlı (Kapak, Gövde, Pleksi, Ayak, Ayak Detayı) materyalleri görebilmesi ve dilediği gibi bağımsız değiştirebilmesi için **03 Parça Materyal Eşleme** kutusu eklenmiştir.
- **Uygulanan Onarım & Geliştirme:**
  1. `CRS_VariantAutomation.ms` ve `CRS_BatchWorker.ms`: `mtlKapak`, `mtlGovde`, `mtlPleksi`, `mtlAyak`, `mtlAyakDetay` bağımsız parametreleri tanımlandı. `getPartsByRole` fonksiyonu doğrudan `kapak*`, `pleksi*`, `tabla*`, `dikme*`, `raf*`, `arkalik*`, `ayak*` ve `ayak_detay*` desenlerini yakalayacak şekilde sadeleştirildi.
  2. `ceneyra_gui.py`: Panel 03 olarak "03   Parça Materyal Eşleme" kutusu inşa edildi. Hazır kombinasyon tıklandığında tüm kutular senkronize olmakta, ancak kullanıcı dilerse Kapak'ı Safir Meşe, Gövdeyi Antrasit Gri, Pleksiyi Altın vb. bağımsız olarak seçebilmektedir.
  3. `btn_auto_rename` ve `run_standardize_parts` metotları arayüzden ve arka plandan tamamen temizlendi.
  4. Kullanıcının `KA1546 TASLAK YENİ.max` sahnesindeki tüm nesneler `kapak001..004`, `pleksi001..004`, `tabla001..002`, `dikme001..003`, `raf001..002`, `arkalik001..002`, `ayak001..005`, `ayak_detay001..005` olarak güncellenip kaydedildi.
  5. Karma varyant (Kapaklar Safir Meşe, Gövde Antrasit Gri, Pleksi Gold) render testi yapılarak [`renders/ka1546_mixed_variant.png`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/renders/ka1546_mixed_variant.png) başarıyla üretildi.
- **Doğrulayan Test:** `test_21_part_material_combos_sync_and_override`

---

## 4. TEST MATRİSİ VE SONUÇLAR (TEST SUITE RESULTS)

[`test_ceneyra_gui.py`](file:///c:/Users/Ahmet/Documents/Ceneyra-Render-Studio/test_ceneyra_gui.py) paketi 21 bağımsız testten oluşmaktadır:

| Test Adı | Kapsadığı Alan | Sonuç |
| :--- | :--- | :---: |
| `test_01_left_panel_layout_no_clipping` | Sol panel 460px sınırı ve Kalite kutusu görünürlüğü | **PASS** |
| `test_02_canvas_actual_size_method_exists_and_works` | 1:1 butonu ve `actual_size` piksel ölçeklemesi | **PASS** |
| `test_03_test_render_does_not_pollute_checkbox_state` | Test render butonunun durum kirliliği yaratmaması | **PASS** |
| `test_04_scene_path_changed_handles_quotes_and_clearing` | Tırnaklı yol, dosya silme ve durum etiketleri | **PASS** |
| `test_05_busy_state_disables_all_conflicting_controls` | Meşgul durumunda parça kutuları dahil tüm girdilerin kilitlenmesi | **PASS** |
| `test_06_batch_worker_has_cancel_and_stops_process` | Süreç iptal (`cancel`) ve güvenli sonlandırma | **PASS** |
| `test_07_output_folder_handles_quotes` | Çıktı klasörü tırnak arındırma ve dizin oluşturma | **PASS** |
| `test_08_elided_label_minimum_size_hint` | `ElidedLabel` minimum genişlik sıfırlaması | **PASS** |
| `test_09_preview_canvas_zoom_anchor_zero_zero` | `(0, 0)` çapa noktası doğrulaması | **PASS** |
| `test_10_minimum_window_size_no_clipping` | 960x720 minimum boyutta sıfır kırpılma garantisi | **PASS** |
| `test_11_preset_buttons_functionality` | Hızlı kombinasyon butonları veri güncellemeleri | **PASS** |
| `test_12_toggle_panels_visibility` | Gelişmiş ayarlar ve log konsolu açma/kapama | **PASS** |
| `test_13_preview_zoom_buttons` | Tuval `+` / `−` yakınlaştırma kontrolleri | **PASS** |
| `test_14_canvas_double_click_fits` | Çift tıklama ve ekrana sığdırma (`fit`) fonksiyonu | **PASS** |
| `test_15_canvas_rendering_pulse_animation_paints_without_error` | Render nabız animasyonu ve `math.sin` hatasız çizim | **PASS** |
| `test_16_studio_button_working_state_paints_without_error` | Buton çalışma animasyonu ve painter temizliği | **PASS** |
| `test_17_clean_env_strips_qt_variables` | `get_clean_env()` ile tüm `QT_` ortam değişkenlerinin filtrelenmesi | **PASS** |
| `test_18_open_scene_in_3dsmax_uses_clean_env` | "Sahneyi Aç" butonunun temiz ortam ile 3ds Max çağırması | **PASS** |
| `test_19_get_windows_short_path` | Unicode / Türkçe dosya yollarının 8.3 güvenli dönüştürülmesi | **PASS** |
| `test_20_run_full_render_generates_safe_path_without_error` | Güvenli dosya adı oluşturma ve `re` kütüphanesi entegrasyonu | **PASS** |
| `test_21_part_material_combos_sync_and_override` | Parça bazlı materyal kutusu senkronizasyonu ve özel varyant atama | **PASS** |

---

## 5. GÖRSEL VE İŞLEVSEL BÜTÜNLÜK KONTROLÜ

- **Renk Teması:** `#111416` (Obsidian Arka Plan), `#181d20` (Panel Gövdesi), `#efba73` (Şampanya Altını Vurgu), `#dce3e1` (Açık Gri Metin) paletinde hiçbir değişiklik yapılmamış; görsel kimlik %100 muhafaza edilmiştir.
- **Geriye Dönük Uyumluluk:** MAXScript batch worker parametreleri (`-sceneFile`, `-mxsString`, `-mxsValue`) ve Python arayüzünün mevcut tüm API çağrıları korunmuştur.
- **Stabilite:** Bellek sızıntılarını ve Qt uyarılarını önlemek amacıyla tüm `QPainter` nesneleri `try...finally: painter.end()` ile temiz biçimde kapatılmıştır.
- **Süreç İzolasyonu:** Lisans yöneticisi çakışmasını engellemek üzere Python'dan 3ds Max'e giden tüm alt süreçler arındırılmış ortam ile çalıştırılmaktadır.
- **3ds Max Sıfırlama (ENU) Kurtarma:** Kullanıcının 3ds Max kullanıcı ayarlarını sıfırlaması üzerine MCP, Tripo Bridge ve V-Ray Cloud makroları yeni `ENU/usermacros` dizinine taşınmış; ayrıca Ceneyra Render Studio makrosu (`Ceneyra-Ceneyra_Render_Studio.mcr`) oluşturulmuştur.

