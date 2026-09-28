global CRS_UI
try (destroyDialog CRS_UI) catch()

rollout CRS_UI "CENEYRA | Render Stüdyosu" width:1180 height:880 (
    local safeScene = ""
    local worker = undefined
    local runDir = ""
    local shownImage = ""
    local viewportFile = ""
    local completedImages = #()
    local updating = false
    local autoPending = false
    local autoTick = 0
    local lastState = ""
    local advancedMode = false
    local progressPulse = 0

    dotNetControl title "System.Windows.Forms.Label" pos:[16,12] width:970 height:34
    button btnAdvanced "Gelişmiş ayarlar" pos:[1000,12] width:164 height:34
    button btnCopy "1  Güvenli çalışma kopyası" pos:[16,54] width:230 height:30
    button btnScan "2  KA1546 eşle" pos:[254,54] width:146 height:30
    button btnManual "Başka ürün / Elle eşle" pos:[408,54] width:176 height:30
    button btnLoad "Profil aç" pos:[592,54] width:110 height:30
    button btnSave "Profil kaydet" pos:[710,54] width:110 height:30
    button btnHelp "Kullanım / Güvenlik" pos:[828,54] width:168 height:30
    button btnRestore "Malzemeleri geri al" pos:[1004,54] width:160 height:30

    groupBox gbBindings "Nesne eşleme + UVW" pos:[16,94] width:320 height:385
    listBox lstRoles "Bölümler" pos:[28,114] width:294 height:7
    button btnBind "Seçili nesneleri bağla" pos:[28,246] width:172 height:27
    button btnSelect "Sahnede seç" pos:[208,246] width:114 height:27
    spinner spFace "Malzeme ID (0 = tümü):" pos:[28,280] width:288 fieldwidth:90 range:[0,65535,0] type:#integer
    button btnID "ID eşlemesini güncelle" pos:[28,305] width:294 height:24
    spinner spChannel "Map channel:" pos:[28,339] width:138 fieldwidth:50 range:[1,99,1] type:#integer
    spinner spTurn "Yön:" pos:[190,339] width:126 fieldwidth:62 range:[-360,360,0] type:#integer
    checkbox cbBox "Box mapping (gövde için)" pos:[28,367] checked:false
    button btnUVW "UVW ekle / güncelle" pos:[28,394] width:174 height:28
    button btnReceivers "Maske alıcıları" pos:[210,394] width:112 height:28
    label lblUVW "Kapak: düzlemsel. Lazer/geometri ve mevcut ID'ler korunur." pos:[28,432] width:286 height:35

    groupBox gbPalette "Malzeme paleti" pos:[16,490] width:320 height:205
    listBox lstPalette "" pos:[28,510] width:294 height:5
    spinner spSlot "Editor slot:" pos:[28,601] width:140 fieldwidth:52 range:[1,24,1] type:#integer
    editText edKey "Kod:" pos:[178,598] width:144 text:"CUSTOM"
    button btnAddMat "Editör yuvasını palete ekle / yenile" pos:[28,634] width:294 height:28
    label lblPalette "Gerçek V-Ray malzemeleri kullanılır." pos:[28,668] width:288 height:18

    groupBox gbVariants "Varyantlar" pos:[350,94] width:420 height:385
    editText edProduct "Ürün:" pos:[362,115] width:178 text:"KA1546"
    dropdownList ddFinish "" pos:[550,112] width:206 items:#("Tüm kaplamalar","Yalnız GOLD","Yalnız SILVER") selection:1
    dotNetControl variants "System.Windows.Forms.CheckedListBox" pos:[362,147] width:394 height:155
    button btnAll "Tümünü işaretle" pos:[362,309] width:144 height:26
    button btnNone "Seçimi kaldır" pos:[514,309] width:144 height:26
    button btnDeleteVariant "Satırı sil" pos:[666,309] width:90 height:26
    editText edCode "Kod:" pos:[362,346] width:154
    editText edLabel "Ad:" pos:[522,346] width:234
    dropdownList ddBody "Gövde" pos:[362,373] width:124
    dropdownList ddDoor "Kapak" pos:[497,373] width:124
    dropdownList ddPlex "Pleksi" pos:[632,373] width:124
    button btnEdit "Satırı güncelle" pos:[362,434] width:124 height:27
    button btnNew "Yeni Kombinasyon" pos:[497,434] width:124 height:27
    button btnMore "Ayak / lazer detayı" pos:[632,434] width:124 height:27

    groupBox gbRoles "Yalnız bu bölümleri değiştir" pos:[350,490] width:420 height:105
    dotNetControl roles "System.Windows.Forms.CheckedListBox" pos:[362,510] width:394 height:74

    groupBox gbCameras "Kameralar / katalog kare numarası" pos:[350,605] width:420 height:90
    dotNetControl camList "System.Windows.Forms.CheckedListBox" pos:[362,625] width:260 height:58
    spinner spCamera "No:" pos:[635,627] width:120 fieldwidth:70 range:[1,99,1] type:#integer
    button btnCameraNo "Numarayı ata" pos:[635,653] width:120 height:25

    dotNetControl preview "System.Windows.Forms.PictureBox" pos:[788,103] width:376 height:435
    label lblPreview "Önizleme | Henüz görsel yok" pos:[788,546] width:376 height:20
    checkbox cbLive "Anlık viewport önizlemesi" pos:[788,570] checked:true
    checkbox cbAuto "Otomatik V-Ray taslak" pos:[988,570] checked:false
    button btnViewport "Viewport yenile" pos:[788,598] width:176 height:30
    button btnPreview "V-Ray test renderı" pos:[974,598] width:190 height:30
    dotNetControl gallery "System.Windows.Forms.ListBox" pos:[788,638] width:376 height:57

    groupBox gbRender "Render kuyruğu" pos:[16,704] width:1148 height:126
    dropdownList ddQuality "" pos:[28,724] width:156 items:#("Taslak / hızlı","Kontrol / orta","Final / sahne ayarları") selection:3
    label lblRenderInfo "" pos:[250,598] width:300 height:18
    spinner spWidth "W:" pos:[194,729] width:112 fieldwidth:70 range:[16,16000,2000] type:#integer
    spinner spHeight "H:" pos:[312,729] width:112 fieldwidth:70 range:[16,16000,3000] type:#integer
    dropdownList ddMode "" pos:[434,724] width:180 items:#("Tam render / BEAUTY","Render maskesi / PATCH") selection:1
    checkbox cbMasks "RGB maske çıktısı" pos:[626,730] checked:true
    button btnBuild "Kuyruğu hesapla" pos:[788,724] width:176 height:28
    button btnOutput "Çıktı klasörü" pos:[974,724] width:176 height:28
    editText edOutput "" pos:[28,760] width:742
    button btnSelected "Seçilenleri renderla" pos:[788,760] width:176 height:32
    button btnRenderAll "Tüm renkleri renderla" pos:[974,760] width:176 height:32
    button btnPause "Duraklat" pos:[28,794] width:112 height:24
    button btnResume "Devam et" pos:[148,794] width:112 height:24
    button btnStop "Kare sonunda dur" pos:[268,794] width:144 height:24
    button btnResumeFile "Eski kuyruğu aç" pos:[420,794] width:148 height:24
    button btnOpen "Çıktıları aç" pos:[576,794] width:130 height:24
    dotNetControl progress "System.Windows.Forms.ProgressBar" pos:[718,800] width:330 height:16
    dotNetControl frameProgress "System.Windows.Forms.ProgressBar" pos:[1055,800] width:95 height:16
    dotNetControl lblProgress "System.Windows.Forms.Label" pos:[718,823] width:432 height:20
    label lblStatus "Başlamak için güvenli çalışma kopyası oluşturun." pos:[18,849] width:1146 height:18
    timer poll interval:1000 active:true

    fn fail message = (lblStatus.text = message; messageBox message title:"Ceneyra Render Stüdyosu")
    fn requireWork = (
        if safeScene == "" or safeScene != maxFilePath + maxFileName do throw "Önce güvenli çalışma kopyası oluşturun. Orijinal sahnede düzenleme engellendi."
        true
    )
    fn busy = (worker != undefined and not worker.HasExited)
    fn updateRenderInfo = (
        local modeName = if ddMode.selection == 2 then "PATCH" else "Tam render"
        lblRenderInfo.text = modeName + " | " + spWidth.value as string + "x" + spHeight.value as string + " | RGB maske " + (if cbMasks.checked then "açık" else "kapalı")
        if not advancedMode do btnSelected.text = if ddMode.selection == 2 then "PATCH başlat" else "Render başlat"
    )
    fn setLayout advanced = (
        advancedMode = advanced
        btnAdvanced.text = if advanced then "Basit görünüm" else "Gelişmiş ayarlar"
        lblRenderInfo.visible = not advanced
        for control in #(btnCopy,btnManual,btnLoad,btnSave,btnRestore,
            gbBindings,lstRoles,btnBind,btnSelect,spFace,btnID,spChannel,spTurn,cbBox,btnUVW,btnReceivers,lblUVW,
            gbPalette,lstPalette,spSlot,edKey,btnAddMat,lblPalette,
            btnDeleteVariant,edCode,edLabel,ddBody,ddDoor,ddPlex,btnEdit,btnNew,btnMore,
            gbRoles,roles,spCamera,btnCameraNo,spWidth,spHeight,ddMode,cbMasks,btnBuild,btnRenderAll,btnPause,btnResumeFile,cbAuto) do control.visible = advanced
        if advanced then (
            gbVariants.text = "Varyantlar"; gbCameras.text = "Kameralar / katalog kare numarası"; gbRender.text = "Render kuyruğu"
            btnHelp.text = "Kullanım / Güvenlik"
            btnScan.text = "2  KA1546 eşle"; btnScan.pos = [254,54]; btnScan.width = 146
            btnHelp.pos = [828,54]; btnHelp.width = 168
            gbVariants.pos = [350,94]; gbVariants.height = 385
            edProduct.pos = [362,115]; ddFinish.pos = [550,112]
            variants.pos = [362,147]; variants.height = 155
            btnAll.pos = [362,309]; btnAll.width = 144
            btnNone.pos = [514,309]; btnNone.width = 144
            gbCameras.pos = [350,605]; gbCameras.height = 90
            camList.pos = [362,625]; camList.width = 260; camList.height = 58
            preview.pos = [788,103]; preview.width = 376; preview.height = 435
            lblPreview.pos = [788,546]; cbLive.pos = [788,570]
            btnViewport.pos = [788,598]; btnViewport.width = 176
            btnPreview.pos = [974,598]; btnPreview.width = 190
            gallery.pos = [788,638]; gallery.width = 376; gallery.height = 57
            gbRender.pos = [16,704]; gbRender.height = 126
            ddQuality.pos = [28,724]; edOutput.pos = [28,760]; edOutput.width = 742
            btnOutput.pos = [974,724]; btnOutput.width = 176
            btnSelected.text = "Seçilenleri renderla"; btnSelected.pos = [788,760]; btnSelected.width = 176; btnSelected.height = 32
            btnResume.pos = [148,794]; btnResume.width = 112
            btnStop.pos = [268,794]; btnStop.width = 144
            btnOpen.pos = [576,794]; btnOpen.width = 130
            progress.pos = [718,800]; progress.Width = 330; progress.Height = 16
            frameProgress.pos = [1055,800]; frameProgress.Width = 95; frameProgress.Height = 16
            lblProgress.pos = [718,823]; lblProgress.Width = 432
            lblStatus.pos = [18,849]
        ) else (
            gbVariants.text = "2  Varyant seçimi"; gbCameras.text = "3  Kamera seçimi"; gbRender.text = "4  Render"
            btnHelp.text = "Nasıl kullanılır"
            cbAuto.checked = false; autoPending = false
            btnScan.text = "1  KA1546 sahnesini hazırla"; btnScan.pos = [16,54]; btnScan.width = 270
            btnHelp.pos = [298,54]; btnHelp.width = 170
            gbVariants.pos = [16,94]; gbVariants.height = 300
            edProduct.pos = [50,115]; ddFinish.pos = [220,112]
            variants.pos = [28,147]; variants.height = 190
            btnAll.pos = [28,352]; btnAll.width = 185
            btnNone.pos = [224,352]; btnNone.width = 185
            gbCameras.pos = [16,405]; gbCameras.height = 115
            camList.pos = [28,432]; camList.width = 394; camList.height = 58
            preview.pos = [450,103]; preview.width = 714; preview.height = 330
            lblPreview.pos = [450,440]; cbLive.pos = [450,465]
            btnViewport.pos = [450,490]; btnViewport.width = 220
            btnPreview.pos = [682,490]; btnPreview.width = 220
            gallery.pos = [450,530]; gallery.width = 714; gallery.height = 40
            gbRender.pos = [16,575]; gbRender.height = 137
            ddQuality.pos = [28,595]; edOutput.pos = [28,634]; edOutput.width = 742
            btnOutput.pos = [572,594]; btnOutput.width = 198
            btnSelected.text = "Render başlat"; btnSelected.pos = [930,592]; btnSelected.width = 220; btnSelected.height = 48
            btnResume.pos = [942,672]; btnResume.width = 98
            btnStop.pos = [1050,672]; btnStop.width = 100
            btnOpen.pos = [788,672]; btnOpen.width = 144
            progress.pos = [28,686]; progress.Width = 580; progress.Height = 18
            frameProgress.pos = [616,686]; frameProgress.Width = 154; frameProgress.Height = 18
            lblProgress.pos = [28,661]; lblProgress.Width = 742
            lblStatus.pos = [18,718]
        )
        updateRenderInfo()
    )
    fn styleList control = (
        control.BackColor = (dotNetClass "System.Drawing.Color").FromArgb 35 39 46
        control.ForeColor = (dotNetClass "System.Drawing.Color").FromArgb 228 230 233
        control.Font = dotNetObject "System.Drawing.Font" "Segoe UI" 9.0
        control.BorderStyle = (dotNetClass "System.Windows.Forms.BorderStyle").FixedSingle
    )
    fn checkedIndices control = (
        local result = #()
        for i = 0 to control.Items.Count-1 where control.GetItemChecked i do append result (i+1)
        result
    )
    fn syncRoles = (
        lstRoles.items = for b in CRS_Data.bindings collect (b.label + "  |  " + b.nodes.count as string + " nesne  |  ID " + b.faceID as string)
        roles.Items.Clear()
        for i = 1 to CRS_Data.bindings.count do roles.Items.Add CRS_Data.bindings[i].label (findItem CRS_Data.activeRoles i > 0)
        if lstRoles.selection > 0 and lstRoles.selection <= CRS_Data.bindings.count do spFace.value = CRS_Data.bindings[lstRoles.selection].faceID
    )
    fn syncPalette = (
        lstPalette.items = for p in CRS_Data.palette collect (p.key + " | " + p.label)
        local names = #("KEEP | Mevcut kalsin")
        join names (for p in CRS_Data.palette collect (p.key + " | " + p.label))
        ddBody.items = names; ddDoor.items = names; ddPlex.items = names
    )
    fn fillVariants = (
        updating = true
        local old = amax 0 variants.SelectedIndex
        local checkedNames = #()
        for i = 0 to variants.Items.Count-1 where variants.GetItemChecked i do append checkedNames (variants.Items.Item[i] as string)
        local firstLoad = variants.Items.Count == 0
        variants.Items.Clear()
        for i = 1 to CRS_Data.variants.count do (
            local v = CRS_Data.variants[i]
            local name = v.code + "   " + v.label
            variants.Items.Add name (if firstLoad then i == 1 else findItem checkedNames name > 0)
        )
        if variants.Items.Count > 0 do variants.SelectedIndex = amin old (variants.Items.Count-1)
        updating = false
    )
    fn paletteIndex key = (
        for i = 1 to CRS_Data.palette.count where CRS_Data.palette[i].key == key do return (i+1)
        1
    )
    fn paletteKey index = if index < 2 then "KEEP" else CRS_Data.palette[index-1].key
    fn populateEditor = (
        local i = variants.SelectedIndex+1
        if i > 0 and i <= CRS_Data.variants.count do (
            local v = CRS_Data.variants[i]
            edCode.text = v.code; edLabel.text = v.label
            ddBody.selection = paletteIndex v.mats[1]
            ddDoor.selection = paletteIndex v.mats[2]
            ddPlex.selection = paletteIndex v.mats[3]
        )
    )
    fn syncAll = (
        updating = true
        edProduct.text = CRS_Data.product
        spWidth.value = CRS_Data.width; spHeight.value = CRS_Data.height
        ddQuality.selection = CRS_Data.quality; ddMode.selection = CRS_Data.mode; cbMasks.checked = CRS_Data.masks
        syncRoles()
        syncPalette()
        camList.Items.Clear()
        for i = 1 to CRS_Data.cameras.count do (
            local c = CRS_Data.cameras[i]
            camList.Items.Add (c.number as string + "  |  " + c.node.label) (i == 1)
        )
        if camList.Items.Count > 0 do camList.SelectedIndex = 0
        fillVariants()
        populateEditor()
        updating = false
    )
    fn readSettings = (
        CRS_Data.product = CRS_token edProduct.text
        CRS_Data.width = spWidth.value; CRS_Data.height = spHeight.value
        CRS_Data.quality = ddQuality.selection; CRS_Data.mode = ddMode.selection
        CRS_Data.masks = cbMasks.checked
        CRS_Data.activeRoles = checkedIndices roles
        CRS_Data.frameTicks = currentTime as integer
    )
    fn showImage path caption = (
        if not doesFileExist path do return false
        local source = (dotNetClass "System.Drawing.Image").FromFile path
        local image = dotNetObject "System.Drawing.Bitmap" source
        source.Dispose()
        local old = preview.Image
        preview.Image = image
        if old != undefined do old.Dispose()
        shownImage = path
        lblPreview.text = caption
        true
    )
    fn viewportPreview = (
        requireWork()
        readSettings()
        local i = variants.SelectedIndex+1
        if i < 1 do return false
        CRS_apply CRS_Data CRS_Data.variants[i]
        CRS_boxForTextureVariant CRS_Data CRS_Data.variants[i]
        local ci = camList.SelectedIndex+1
        if ci > 0 do viewport.setCamera (CRS_resolve CRS_Data.cameras[ci].node)
        local previous = #(hideByCategory.lights,hideByCategory.cameras,hideByCategory.helpers,viewport.GetShowEdgeFaces(),selection as array)
        local b = undefined
        local captureError = undefined
        try (
            hideByCategory.lights = true; hideByCategory.cameras = true; hideByCategory.helpers = true
            viewport.SetShowEdgeFaces false
            clearSelection()
            for p in CRS_Data.palette do showTextureMap p.mtl true
            completeRedraw()
            b = gw.getViewportDib()
        ) catch (captureError = getCurrentException())
        hideByCategory.lights = previous[1]; hideByCategory.cameras = previous[2]; hideByCategory.helpers = previous[3]
        viewport.SetShowEdgeFaces previous[4]
        select previous[5]
        redrawViews()
        if captureError != undefined do throw captureError
        local folder = CRS_mkdir (CRS_join CRS_Root "cache")
        if viewportFile == "" do viewportFile = CRS_join folder ("viewport_" + CRS_guid() + ".png")
        local path = viewportFile
        b.filename = path
        save b
        close b
        showImage path ("Viewport | " + CRS_Data.variants[i].code + " | Final render değil")
    )
    fn requestPreview = (
        if not updating and cbLive.checked and safeScene == maxFilePath + maxFileName do (
            try (viewportPreview()) catch (lblStatus.text = getCurrentException())
        )
        if cbAuto.checked and not updating do (autoPending = true; autoTick = timestamp())
    )
    fn selectedVariants all:false = (
        local result = #()
        for i = 1 to CRS_Data.variants.count where (all or variants.GetItemChecked (i-1)) do (
            local finish = CRS_Data.variants[i].finish
            if ddFinish.selection == 1 or (ddFinish.selection == 2 and finish == "GOLD") or (ddFinish.selection == 3 and finish == "SILVER") do append result i
        )
        result
    )
    fn summarize all:false = (
        requireWork()
        readSettings()
        local vi = selectedVariants all:all
        local ci = checkedIndices camList
        CRS_buildJobs CRS_Data vi ci
        local requested = vi.count * ci.count
        lblStatus.text = requested as string + " kombinasyon → " + CRS_Data.jobs.count as string + " benzersiz render. Aynı malzeme seçimi bir kez renderlanır."
        CRS_Data.jobs.count
    )
    fn startQueue all:false previewOnly:false = (
        requireWork()
        if busy() do throw "Render işlemi sürüyor. Bitmesini bekleyin veya kare sonunda durdurun."
        readSettings()
        local oldSettings = #(CRS_Data.width,CRS_Data.height,CRS_Data.quality,CRS_Data.mode,CRS_Data.masks)
        try (
            if previewOnly then (
                local vi = variants.SelectedIndex+1
                local ci = camList.SelectedIndex+1
                if vi < 1 or ci < 1 do throw "Önizleme için bir varyant ve kamera seçin."
                local ratio = CRS_Data.height as float / CRS_Data.width
                CRS_Data.width = 400
                CRS_Data.height = amax 16 (amin 1200 (400*ratio) as integer)
                CRS_Data.quality = 1; CRS_Data.mode = 1; CRS_Data.masks = false
                CRS_buildJobs CRS_Data #(vi) #(ci)
            ) else (
                summarize all:all
                if CRS_Data.mode == 2 and not (queryBox "PATCH modu yalnız seçili bölümleri yeniden hesaplar. Diğer yüzeylerdeki yansıma, GI ve gölge değişimleri otomatik güncellenmez. Bu çıktılar tam katalog karesi değildir. Devam?" title:"Render maskesi uyarısı") do return false
                if not (queryBox (CRS_Data.jobs.count as string + " render başlatılsın mı?\nÇıktılar yeni bir alt klasöre kaydedilecek. Mevcut katalog dosyaları değişmeyecek.") title:"Kuyruk onayı") do return false
            )
            local folder = if previewOnly then CRS_join CRS_Root "previews" else edOutput.text
            if folder == "" do throw "Çıktı klasörü boş."
            runDir = CRS_makeRun CRS_Data folder
            local warnings = CRS_elements (CRS_loadXml (CRS_join runDir "queue.xml")).DocumentElement "warnings/missingTexture"
            if warnings.count > 0 and not previewOnly do (
                if not (queryBox (warnings.count as string + " sahne dokusu bulunamadı.\nİlk eksik: " + CRS_get warnings[1] "path" + "\nListe queue.xml içinde. Eksik dokularla render başlatılsın mı?") title:"Sahne kontrolü") do return false
            )
            worker = CRS_launch runDir
            btnResume.enabled = true; btnStop.enabled = true
            completedImages = #(); gallery.Items.Clear()
            local oldPreview = preview.Image
            preview.Image = undefined
            if oldPreview != undefined do oldPreview.Dispose()
            shownImage = ""
            progress.Value = 0
            frameProgress.Visible = true
            lblProgress.text = "0 / " + CRS_Data.jobs.count as string + " kare tamamlandı"
            lblPreview.text = "Önizleme | İlk render karesi bekleniyor"
            lblStatus.text = "V-Ray başlatılıyor. Canlı kare ayrı VFB penceresinde açılır."
            autoPending = false
        ) catch (
            CRS_Data.width = oldSettings[1]; CRS_Data.height = oldSettings[2]; CRS_Data.quality = oldSettings[3]; CRS_Data.mode = oldSettings[4]; CRS_Data.masks = oldSettings[5]
            throw()
        )
        CRS_Data.width = oldSettings[1]; CRS_Data.height = oldSettings[2]; CRS_Data.quality = oldSettings[3]; CRS_Data.mode = oldSettings[4]; CRS_Data.masks = oldSettings[5]
        true
    )
    fn editVariant newRow:false = (
        requireWork()
        local index = variants.SelectedIndex+1
        if not newRow and index < 1 do throw "Bir satır seçin."
        local mats = if index > 0 then copy CRS_Data.variants[index].mats else #("KEEP","KEEP","KEEP","KEEP","KEEP","KEEP")
        mats[1] = paletteKey ddBody.selection
        mats[2] = paletteKey ddDoor.selection
        mats[3] = paletteKey ddPlex.selection
        local finish = if mats[3] == "SILVER" then "SILVER" else if mats[3] == "GOLD" then "GOLD" else "CUSTOM"
        local v = CRS_Variant code:(CRS_token edCode.text) label:edLabel.text finish:finish mats:mats
        if newRow then (append CRS_Data.variants v; index = CRS_Data.variants.count) else CRS_Data.variants[index] = v
        fillVariants()
        variants.SelectedIndex = index-1
        populateEditor()
        requestPreview()
    )
    fn detailsDialog = (
        local index = variants.SelectedIndex+1
        if index < 1 do return false
        global CRS_Details
        try (destroyDialog CRS_Details) catch()
        rollout CRS_Details "Varyant / ayak ve lazer" width:360 height:270 (
            dropdownList leg "Ayak boya" width:330
            dropdownList trim "Ayak metal detayı" width:330
            dropdownList laser "Lazer ID yüzleri" width:330
            label note "KEEP: mevcut malzemeyi korur. Kapak lazer geometrisi değişmez." width:330 height:34
            button apply "Varyanta kaydet" width:330
            on CRS_Details open do (
                local items = #("KEEP | Mevcut kalsin")
                join items (for p in CRS_Data.palette collect p.key)
                leg.items = items; trim.items = items; laser.items = items
                local v = CRS_Data.variants[CRS_UI.variants.SelectedIndex+1]
                leg.selection = CRS_UI.paletteIndex v.mats[4]
                trim.selection = CRS_UI.paletteIndex v.mats[5]
                laser.selection = CRS_UI.paletteIndex v.mats[6]
            )
            on apply pressed do (
                try (
                    CRS_UI.requireWork()
                    local v = CRS_Data.variants[CRS_UI.variants.SelectedIndex+1]
                    v.mats[4] = CRS_UI.paletteKey leg.selection
                    v.mats[5] = CRS_UI.paletteKey trim.selection
                    v.mats[6] = CRS_UI.paletteKey laser.selection
                    destroyDialog CRS_Details
                    CRS_UI.requestPreview()
                ) catch (messageBox (getCurrentException()))
            )
        )
        createDialog CRS_Details
    )

    on CRS_UI open do (
        title.Text = "CENEYRA   /   Render Stüdyosu"
        title.Font = dotNetObject "System.Drawing.Font" "Segoe UI Semibold" 16.0 (dotNetClass "System.Drawing.FontStyle").Bold
        title.ForeColor = (dotNetClass "System.Drawing.Color").FromArgb 209 176 115
        title.BackColor = (dotNetClass "System.Drawing.Color").FromArgb 28 31 36
        for control in #(variants,roles,camList,gallery) do styleList control
        variants.CheckOnClick = true; roles.CheckOnClick = true; camList.CheckOnClick = true
        variants.IntegralHeight = false; camList.IntegralHeight = false
        roles.MultiColumn = true; roles.ColumnWidth = 190
        preview.BackColor = (dotNetClass "System.Drawing.Color").FromArgb 22 25 30
        preview.SizeMode = (dotNetClass "System.Windows.Forms.PictureBoxSizeMode").Zoom
        lblProgress.Text = "0 / 0 kare tamamlandı"
        lblProgress.Font = dotNetObject "System.Drawing.Font" "Segoe UI Semibold" 10.0 (dotNetClass "System.Drawing.FontStyle").Bold
        lblProgress.ForeColor = (dotNetClass "System.Drawing.Color").FromArgb 209 176 115
        lblProgress.BackColor = (dotNetClass "System.Drawing.Color").FromArgb 70 70 70
        progress.Minimum = 0; progress.Maximum = 100; progress.Value = 0
        progress.Style = (dotNetClass "System.Windows.Forms.ProgressBarStyle").Continuous
        frameProgress.Style = (dotNetClass "System.Windows.Forms.ProgressBarStyle").Marquee
        frameProgress.MarqueeAnimationSpeed = 30
        frameProgress.Visible = false
        edOutput.text = CRS_join CRS_Root "renders"
        local work = toLower (CRS_join CRS_Root "work\\")
        if findString (toLower (maxFilePath+maxFileName)) work == 1 do safeScene = maxFilePath+maxFileName
        if CRS_Data.bindings.count > 0 do syncAll()
        setLayout false
        btnResume.enabled = false; btnStop.enabled = false
    )
    on CRS_UI close do (
        if CRS_Data.scene == maxFilePath+maxFileName do CRS_restore CRS_Data
        if preview.Image != undefined do preview.Image.Dispose()
        try (destroyDialog CRS_Details) catch()
    )
    on btnCopy pressed do try (
        if not (queryBox "Aktif sahnenin yeni bir çalışma kopyası oluşturulacak. Orijinal dosyaya kayıt yapılmaz. Devam?" title:"Güvenli kopya") do return false
        if CRS_Data.scene == maxFilePath+maxFileName do CRS_restore CRS_Data
        local folder = CRS_mkdir (CRS_join CRS_Root "work")
        local path = CRS_join folder ("CENEYRA_WORK_" + CRS_guid() + ".max")
        if not (saveMaxFile path useNewFile:true clearNeedSaveFlag:true quiet:true) do throw "Çalışma kopyası kaydedilemedi."
        safeScene = maxFilePath+maxFileName
        CRS_Data = CRS_Model()
        syncAll()
        lblStatus.text = "Güvenli kopya aktif. Şimdi KA1546 eşle veya elle eşle."
    ) catch (fail (getCurrentException()))
    on btnScan pressed do try (
        if CRS_Data.scene == maxFilePath+maxFileName do CRS_restore CRS_Data
        if safeScene == "" or safeScene != maxFilePath + maxFileName do (
            CRS_seedKA1546()
            local folder = CRS_mkdir (CRS_join CRS_Root "work")
            local path = CRS_join folder ("CENEYRA_WORK_" + CRS_guid() + ".max")
            if not (saveMaxFile path useNewFile:true clearNeedSaveFlag:true quiet:true) do throw "Çalışma kopyası kaydedilemedi."
            safeScene = maxFilePath+maxFileName
        )
        CRS_Data = CRS_seedKA1546()
        syncAll()
        lblStatus.text = if advancedMode then ("KA1546 eşlendi: " + CRS_Data.cameras.count as string + " kamera. Ayak/gövde eşlemesini kontrol edin.") else "Sahne hazır. Varyant ve kameraları seçin; önizlemeden sonra render başlatın."
        requestPreview()
    ) catch (fail (getCurrentException()))
    on btnAdvanced pressed do setLayout (not advancedMode)
    on btnManual pressed do try (requireWork(); CRS_restore CRS_Data; CRS_Data = CRS_emptyScene(); syncAll()) catch (fail (getCurrentException()))
    on lstRoles selected i do if i > 0 do spFace.value = CRS_Data.bindings[i].faceID
    on btnBind pressed do try (
        requireWork()
        local i = lstRoles.selection
        if i < 1 or selection.count == 0 do throw "Bir bölüm ve sahnede geometri seçin."
        local nodes = selection as array
        for n in nodes where superClassOf n != GeometryClass do throw "Yalnız geometri seçin; grup başlığını değil."
        CRS_restore CRS_Data
        CRS_Data.bindings[i].nodes = for n in nodes collect CRS_makeRef n
        CRS_capture CRS_Data
        syncRoles()
    ) catch (fail (getCurrentException()))
    on btnSelect pressed do try (select (CRS_nodes CRS_Data.bindings[lstRoles.selection].nodes)) catch (fail (getCurrentException()))
    on btnID pressed do try (requireWork(); CRS_Data.bindings[lstRoles.selection].faceID = spFace.value; syncRoles()) catch (fail (getCurrentException()))
    on btnUVW pressed do try (
        requireWork()
        local nodes = CRS_nodes CRS_Data.bindings[lstRoles.selection].nodes
        undo "Ceneyra UVW" on CRS_uvw nodes channel:spChannel.value boxMode:cbBox.checked turn:spTurn.value
        lblStatus.text = "UVW güncellendi. Kanal 1: yüzey; kanal 2: isteğe bağlı lazer bitmap. Ctrl+Z ile geri alınabilir."
        requestPreview()
    ) catch (fail (getCurrentException()))
    on btnReceivers pressed do try (
        requireWork()
        CRS_Data.receivers = for n in selection where superClassOf n == GeometryClass collect CRS_makeRef n
        lblStatus.text = CRS_Data.receivers.count as string + " ek render maskesi alıcısı bağlandı (zemin/yansıma yüzeyleri)."
    ) catch (fail (getCurrentException()))
    on btnAddMat pressed do try (
        requireWork()
        local key = CRS_token (toUpper edKey.text)
        if key == "KEEP" do throw "KEEP ayrılmış bir koddur."
        local p = CRS_Swatch key:key label:meditMaterials[spSlot.value].name mtl:(copy meditMaterials[spSlot.value])
        local index = 0
        for i = 1 to CRS_Data.palette.count where CRS_Data.palette[i].key == key do index = i
        if index == 0 then append CRS_Data.palette p else (
            if not (queryBox (key + " palet malzemesi yenilensin mi?") title:"Palet") do return false
            CRS_Data.palette[index] = p
        )
        syncPalette(); populateEditor()
    ) catch (fail (getCurrentException()))
    on variants SelectedIndexChanged sender args do if not updating do (populateEditor(); requestPreview())
    on ddBody selected i do if not updating do lblStatus.text = "Malzeme seçimini uygulamak için Satırı güncelle'ye basın."
    on ddDoor selected i do if not updating do lblStatus.text = "Malzeme seçimini uygulamak için Satırı güncelle'ye basın."
    on ddPlex selected i do if not updating do lblStatus.text = "Malzeme seçimini uygulamak için Satırı güncelle'ye basın."
    on btnAll pressed do for i = 0 to variants.Items.Count-1 do variants.SetItemChecked i true
    on btnNone pressed do for i = 0 to variants.Items.Count-1 do variants.SetItemChecked i false
    on btnEdit pressed do try (editVariant()) catch (fail (getCurrentException()))
    on btnNew pressed do try (editVariant newRow:true) catch (fail (getCurrentException()))
    on btnDeleteVariant pressed do try (
        requireWork()
        local i = variants.SelectedIndex+1
        if i > 0 and queryBox "Bu varyant satırı profilden kaldırılsın mı? Dosyalar silinmez." do (deleteItem CRS_Data.variants i; fillVariants(); populateEditor())
    ) catch (fail (getCurrentException()))
    on btnMore pressed do detailsDialog()
    on camList SelectedIndexChanged sender args do (
        local i = camList.SelectedIndex+1
        if i > 0 do (
            spCamera.value = CRS_Data.cameras[i].number
            if not updating do requestPreview()
        )
    )
    on cbAuto changed state do (autoPending = false; if state do requestPreview())
    on btnCameraNo pressed do try (
        local i = camList.SelectedIndex+1
        if i < 1 do throw "Bir kamera seçin."
        CRS_Data.cameras[i].number = spCamera.value
        camList.Items.Item[i-1] = spCamera.value as string + "  |  " + CRS_Data.cameras[i].node.label
    ) catch (fail (getCurrentException()))
    on ddQuality selected i do (
        local sizes = #([400,600],[1000,1500],[2000,3000])
        spWidth.value = sizes[i].x; spHeight.value = sizes[i].y
        updateRenderInfo()
    )
    on ddMode selected i do updateRenderInfo()
    on cbMasks changed state do updateRenderInfo()
    on spWidth changed value do updateRenderInfo()
    on spHeight changed value do updateRenderInfo()
    on btnViewport pressed do try (viewportPreview()) catch (fail (getCurrentException()))
    on btnPreview pressed do try (startQueue previewOnly:true) catch (fail (getCurrentException()))
    on btnBuild pressed do try (summarize()) catch (fail (getCurrentException()))
    on btnSelected pressed do try (startQueue()) catch (fail (getCurrentException()))
    on btnRenderAll pressed do try (startQueue all:true) catch (fail (getCurrentException()))
    on btnOutput pressed do (
        local path = getSavePath caption:"Yeni render klasörlerinin oluşturulacağı ana klasör"
        if path != undefined do edOutput.text = path
    )
    on btnPause pressed do if runDir != "" do (CRS_control runDir "pause"; lblStatus.text = "Duraklatma istendi; mevcut kare tamamlanınca durur.")
    on btnStop pressed do if runDir != "" do (CRS_control runDir "stop"; lblStatus.text = "Durdurma istendi; mevcut kare tamamlanınca kapanır.")
    on btnResume pressed do try (
        if runDir == "" do throw "Önce bir kuyruk açın."
        CRS_control runDir "run"
        if not busy() do worker = CRS_launch runDir
    ) catch (fail (getCurrentException()))
    on btnResumeFile pressed do try (
        if busy() do throw "Mevcut işlem bitmeden kuyruk değiştirilemez."
        local path = getOpenFileName caption:"Devam edilecek queue.xml" types:"Ceneyra Queue (*.xml)|*.xml|"
        if path != undefined do (
            if (CRS_loadXml path).DocumentElement.Name != "queue" do throw "queue.xml seçmelisiniz."
            runDir = getFilenamePath path
            completedImages = #(); gallery.Items.Clear()
            btnResume.enabled = true; btnStop.enabled = true
            lblStatus.text = "Kuyruk seçildi. Devam et ile aynı sahne kopyasından sürdürebilirsiniz."
        )
    ) catch (fail (getCurrentException()))
    on btnOpen pressed do try (shellLaunch (if runDir != "" then runDir else edOutput.text) "") catch (fail (getCurrentException()))
    on gallery SelectedIndexChanged sender args do (
        local i = gallery.SelectedIndex+1
        if i > 0 and i <= completedImages.count do try (showImage completedImages[i] ("V-Ray | Tamamlanan kare: " + getFilenameFile completedImages[i])) catch()
    )
    on btnRestore pressed do try (CRS_requireScene CRS_Data; CRS_restore CRS_Data; redrawViews(); lblStatus.text = "Başlangıç malzemeleri geri alındı. UVW değiştiricileri korunur.") catch (fail (getCurrentException()))
    on btnSave pressed do try (
        requireWork(); readSettings()
        local path = getSaveFileName caption:"Yeni profil kaydet" types:"Ceneyra Profile (*.xml)|*.xml|"
        if path != undefined do (
            local matPath = (getFilenamePath path)+(getFilenameFile path)+".mat"
            if doesFileExist path or doesFileExist matPath do throw "Uzerine yazmak yerine yeni bir profil adi secin."
            CRS_saveProfile CRS_Data path matPath
            lblStatus.text = "Profil ve materyal kutuphanesi kaydedildi. Sahne kaydedilmedi."
        )
    ) catch (fail (getCurrentException()))
    on btnLoad pressed do try (
        requireWork()
        local path = getOpenFileName caption:"Ceneyra profili" types:"Ceneyra Profile (*.xml)|*.xml|"
        if path != undefined do (
            local d = CRS_readProfile path ((getFilenamePath path)+(getFilenameFile path)+".mat")
            for b in d.bindings do CRS_nodes b.nodes
            CRS_restore CRS_Data
            CRS_Data = CRS_capture d
            syncAll()
        )
    ) catch (fail (getCurrentException()))
    on btnHelp pressed do if not advancedMode then messageBox (
        "1. Güncel KA1546 sahnesini açıp 'Sahnesini hazırla'ya basın. Stüdyo yeni bir çalışma kopyası oluşturur.\n" +
        "2. Varyantları ve kameraları işaretleyin. Başlangıçta birer seçim yapılır.\n" +
        "3. V-Ray test renderı ile görüntüyü kontrol edin. Kalite ve çıktı klasörünü seçip 'Render başlat'a basın.\n" +
        "4. Canlı render V-Ray VFB penceresinde görünür. Stüdyo paneli tamamlanan kareleri gösterir; çubuk tamamlanan/toplam kareyi izler.\n\n" +
        "Nesne eşleme, malzeme, UVW, PATCH ve eski kuyruklar gelişmiş ayarlardadır. Orijinal .max ve katalog dosyaları otomatik değiştirilmez."
    ) title:"Ceneyra Render Stüdyosu | Hızlı kullanım" else messageBox (
        "1. Orijinal sahneyi açın; güvenli çalışma kopyası oluşturun. Panel orijinalde malzeme/UVW değiştirmez.\n" +
        "2. KA1546 eşle; bölümleri sahnede seçerek kontrol edin. Başka ürün için elle eşleme kullanın.\n" +
        "3. Kapak yüzeyi ID 1, lazer ID 2. Tek malzeme atayıp lazeri kaybetmeyin. UVW kanal 1 yüzey, kanal 2 ayrı desen içindir.\n" +
        "4. Varyantları ve kameraları işaretleyin. Kuyruğu hesapla, aynı malzeme kombinasyonlarını birleştirir.\n" +
        "5. Canlı render ayrı V-Ray VFB penceresinde, tamamlanan kareler stüdyo önizlemesinde görünür. Final kalite sahnenin örnekleme ayarlarını kullanır.\n" +
        "6. PATCH tam katalog karesi değildir. Yansıma, GI ve gölge değişimleri için tam render kullanın.\n" +
        "7. Duraklat/Dur mevcut kare sonunda uygulanır. Devam et, bitmiş dosyaları doğrular; kaynak değiştiyse yeni kuyruk gerekir.\n" +
        "8. Her işlem yeni klasör açar. Orijinal .max ve katalog dosyalarının üzerine yazılmaz."
    ) title:"Ceneyra Render Stüdyosu | Kullanım"
    on poll tick do (
        if runDir != "" and doesFileExist (CRS_join runDir "status.xml") do try (
            local status = (CRS_loadXml (CRS_join runDir "status.xml")).DocumentElement
            local state = CRS_get status "state"
            local done = (CRS_get status "done") as integer
            local total = (CRS_get status "total") as integer
            progress.Value = if total > 0 then (amin 100 (amax 0 ((100.0*done/total) as integer))) else 0
            frameProgress.Visible = findItem #("loading","rendering") state > 0
            progressPulse += 1
            local dots = case (mod progressPulse 4) of (0: ""; 1: "."; 2: ".."; default: "...")
            local stateText = case state of (
                "ready": "Kuyruk hazır"
                "loading": "Sahne yükleniyor"
                "rendering": "Render sürüyor"
                "paused": "Duraklatıldı"
                "completed": "Render tamamlandı"
                "stopped": "Kuyruk durdu"
                "failed": "Render hatası"
                default: state
            )
            lblProgress.text = if state == "rendering" and done < total then (
                "Kare " + (done+1) as string + "/" + total as string + " işleniyor" + dots +
                "  |  " + done as string + " kare tamamlandı  |  Canlı görüntü V-Ray VFB'de"
            ) else (done as string + " / " + total as string + " kare tamamlandı  |  " + stateText)
            lblStatus.text = stateText + "  |  " + CRS_get status "message"
            local image = CRS_get status "image"
            if image != "" and findItem completedImages image == 0 do (
                append completedImages image
                gallery.Items.Add (getFilenameFile image)
                showImage image ("V-Ray | Tamamlanan kare: " + getFilenameFile image)
            )
            if worker != undefined and worker.HasExited and findItem #("completed","stopped","failed") state == 0 do lblStatus.text = "Render işlemi kapandı. listener.log / max.log dosyalarını kontrol edin."
            if state == "failed" and lastState != "failed" do messageBox ((CRS_get status "message") + "\n\nKuyruk: " + runDir) title:"Render hatası"
            lastState = state
        ) catch (lblStatus.text = "Durum dosyası okunamadı; tekrar denenecek.")
        if autoPending and timestamp()-autoTick > 1200 and not busy() do try (startQueue previewOnly:true) catch (autoPending = false; lblStatus.text = getCurrentException())
    )
)
