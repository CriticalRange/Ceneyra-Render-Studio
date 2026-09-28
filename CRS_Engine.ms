fn CRS_status dir state message job:"" done:0 total:0 image:"" = (
    local doc = CRS_xml()
    local root = CRS_child doc doc "status"
    for pair in #(#("state",state),#("message",message),#("job",job),#("done",done),#("total",total),#("image",image),#("time",localTime)) do CRS_attr root pair[1] pair[2]
    local processClass = dotNetClass "System.Diagnostics.Process"
    local currentProcess = processClass.GetCurrentProcess()
    CRS_attr root "pid" currentProcess.Id
    CRS_writeXml doc (CRS_join dir "status.xml")
)
fn CRS_control dir value = (
    (dotNetClass "System.IO.File").WriteAllText (CRS_join dir "control.txt") value
)
fn CRS_readControl dir = (
    local path = CRS_join dir "control.txt"
    if not doesFileExist path do return "run"
    local value = (dotNetClass "System.IO.File").ReadAllText path
    substituteString (substituteString value "\r" "") "\n" ""
)
fn CRS_outputName d job = (
    local v = d.variants[job.variantIndex]
    local c = d.cameras[job.cameraIndex]
    d.product + v.code + c.number as string
)
fn CRS_makeRun d outputRoot = (
    if d.jobs.count == 0 do throw "Kuyruk bos."
    CRS_restore d
    local dir = CRS_mkdir (CRS_join outputRoot ((CRS_token d.product) + "_" + CRS_guid()))
    local scene = CRS_join dir "snapshot.max"
    if not (saveMaxFile scene useNewFile:false clearNeedSaveFlag:false quiet:true) do throw "Islem kopyasi kaydedilemedi."
    CRS_saveProfile d (CRS_join dir "profile.xml") (CRS_join dir "palette.mat")
    local doc = CRS_xml()
    local root = CRS_child doc doc "queue"
    CRS_attr root "version" 1
    local assets = #()
    local visited = #()
    local variantIndices = #()
    for job in d.jobs do appendIfUnique variantIndices job.variantIndex
    for vi in variantIndices do for i in d.activeRoles where d.variants[vi].mats[i] != "KEEP" do CRS_walkMaps (CRS_material d d.variants[vi].mats[i]) visited assets
    -- A hidden reflection card can still contribute to a V-Ray beauty render.
    for n in geometry where n.renderable do CRS_walkMaps n.material visited assets
    if environmentMap != undefined do CRS_walkMaps environmentMap visited assets
    local fingerprints = CRS_child doc root "fingerprints"
    for path in #(scene, CRS_join dir "profile.xml", CRS_join dir "palette.mat", CRS_join CRS_Root "CRS_Core.ms", CRS_join CRS_Root "CRS_Engine.ms", CRS_join CRS_Root "CRS_Worker.ms") do (
        local e = CRS_child doc fingerprints "file"
        CRS_attr e "path" path; CRS_attr e "hash" (CRS_hash path)
    )
    for path in assets where doesFileExist path do (
        local e = CRS_child doc fingerprints "file"
        CRS_attr e "path" path; CRS_attr e "hash" (CRS_hash path)
    )
    local warnings = CRS_child doc root "warnings"
    for path in assets where not doesFileExist path do (
        local e = CRS_child doc warnings "missingTexture"
        CRS_attr e "path" path
    )
    for job in d.jobs do (
        local e = CRS_child doc root "job"
        CRS_attr e "id" job.id; CRS_attr e "variant" job.variantIndex; CRS_attr e "camera" job.cameraIndex
    )
    CRS_writeXml doc (CRS_join dir "queue.xml")
    CRS_control dir "run"
    CRS_status dir "ready" "Kuyruk hazır." total:d.jobs.count
    dir
)
fn CRS_launch dir = (
    local exe = CRS_join (getDir #maxRoot) "3dsmaxbatch.exe"
    if not doesFileExist exe do throw "3dsmaxbatch.exe bulunamadi."
    local info = dotNetObject "System.Diagnostics.ProcessStartInfo"
    info.FileName = exe
    local mxsDir = substituteString dir "\\" "\\\\"
    info.Arguments = "\"" + CRS_join CRS_Root "CRS_Worker.ms" + "\" -mxsString \"jobDir:" + mxsDir + "\" -safescene on -v 2 -listenerlog \"" + CRS_join dir "listener.log" + "\" -log \"" + CRS_join dir "max.log" + "\""
    info.UseShellExecute = false
    -- A windowless batch process also hides the V-Ray VFB. Minimize the batch
    -- console, but leave its child render window available for live preview.
    info.CreateNoWindow = false
    info.WindowStyle = (dotNetClass "System.Diagnostics.ProcessWindowStyle").Minimized
    (dotNetClass "System.Diagnostics.Process").Start info
)
fn CRS_uniquePath path = (
    if not doesFileExist path do return path
    local root = getFilenamePath path
    local stem = getFilenameFile path
    local ext = getFilenameType path
    local i = 2
    local result = CRS_join root (stem + "_retry" + i as string + ext)
    while doesFileExist result do (i += 1; result = CRS_join root (stem + "_retry" + i as string + ext))
    result
)
fn CRS_writeBitmap b path data:false = (
    local tmp = (getFilenamePath path) + "." + CRS_guid() + (getFilenameType path)
    b.filename = tmp
    local saved = if data then save b gamma:1.0 else save b
    if not saved do throw ("Gorsel kaydedilemedi: " + path)
    if not doesFileExist tmp or (getFileSize tmp) < 32 do throw "Bos render dosyasi."
    -- Beauty PNGs retain the V-Ray alpha channel. Do not flatten the
    -- transparent environment onto white; data masks are also untouched.
    (dotNetClass "System.IO.File").Move tmp path
    path
)
fn CRS_donePath dir job = CRS_join dir (job.id + ".done.xml")
fn CRS_verifyDone dir job = (
    local marker = CRS_donePath dir job
    if not doesFileExist marker do return undefined
    local root = (CRS_loadXml marker).DocumentElement
    if CRS_get root "job" != job.id do throw "Is bitis kaydi uyusmuyor."
    for e in CRS_elements root "file" do (
        local path = CRS_get e "path"
        if not doesFileExist path do throw ("Tamamlanan cikti eksik: " + path)
        if CRS_hash path != CRS_get e "hash" do throw ("Tamamlanan cikti degismis: " + path + ". Yeni kuyruk olusturun.")
    )
    CRS_get root "image"
)
fn CRS_markDone dir job paths seconds = (
    local doc = CRS_xml()
    local root = CRS_child doc doc "done"
    CRS_attr root "job" job.id; CRS_attr root "image" paths[1]; CRS_attr root "seconds" seconds
    for path in paths do (
        local e = CRS_child doc root "file"
        CRS_attr e "path" path; CRS_attr e "hash" (CRS_hash path)
    )
    CRS_writeXml doc (CRS_donePath dir job)
)
fn CRS_renderSettings d = (
    local vr = renderers.current
    if not isProperty vr #imageSampler_renderMask_type do throw "Bu surum V-Ray CPU renderer gerektirir."
    vr.imageSampler_renderMask_type = if d.mode == 2 then 2 else 0
    vr.output_on = true
    if isProperty vr #output_fileOnly do vr.output_fileOnly = false
    vr.output_saveFile = false
    vr.output_saveRawFile = false
    vr.output_splitgbuffer = false
    vr.output_getsetsfrommax = true
    rendSaveFile = false
    rendType = #view
    renderWidth = d.width
    renderHeight = d.height
    renderPixelAspect = 1.0
    if d.quality < 3 do (
        vr.imageSampler_type_new = 1
        vr.progressive_minSamples = 1
        vr.progressive_maxSamples = if d.quality == 1 then 12 else 48
        vr.progressive_noise_threshold = if d.quality == 1 then 0.08 else 0.025
        vr.progressive_max_render_time = if d.quality == 1 then 0.5 else 2.0
    )
    vr
)
fn CRS_makeMattes d = (
    local manager = maxOps.GetCurRenderElementMgr()
    manager.RemoveAllRenderElements()
    manager.SetElementsActive d.masks
    if not d.masks do return #()
    local seen = #()
    local occupied = for n in geometry collect n.gbufferChannel
    local ids = #()
    local candidate = 501
    for i = 1 to 5 do (
        while findItem occupied candidate > 0 do candidate += 1
        if candidate > 65535 do throw "Bos Object ID bulunamadi."
        append ids candidate
        candidate += 1
    )
    for group in #(#(1,ids[1]),#(2,ids[2]),#(3,ids[3]),#(4,ids[4]),#(5,ids[5])) do (
        for n in CRS_nodes d.bindings[group[1]].nodes do (
            if findItem seen n > 0 do throw "Nesne maskeleri icin govde/kapak/pleksi/ayak bolumleri cakismamali."
            append seen n
            n.gbufferChannel = group[2]
        )
    )
    local a = MultiMatteElement elementName:"CRS_Body_Door_Plexi" MatID:false R_gbufIDOn:true G_gbufIDOn:true B_gbufIDOn:true R_gbufID:ids[1] G_gbufID:ids[2] B_gbufID:ids[3]
    local b = MultiMatteElement elementName:"CRS_Leg_Trim" MatID:false R_gbufIDOn:true G_gbufIDOn:true B_gbufIDOn:false R_gbufID:ids[4] G_gbufID:ids[5]
    manager.AddRenderElement a
    manager.AddRenderElement b
    #(a,b)
)
fn CRS_renderJob d job dir = (
    local v = d.variants[job.variantIndex]
    local c = CRS_resolve d.cameras[job.cameraIndex].node
    local changed = CRS_apply d v
    CRS_boxForTextureVariant d v
    if d.mode == 2 do (
        for n in CRS_nodes d.receivers do appendIfUnique changed n
        if changed.count == 0 do throw "Render Mask secimi bos."
        select changed
    )
    CRS_renderSettings d
    local elements = CRS_makeMattes d
    local b = undefined
    local elementBitmaps = #()
    local cancelled = false
    local paths = #()
    local start = timestamp()
    try (
        -- Keep the V-Ray VFB visible for progressive, in-frame feedback. The
        -- studio panel displays each verified frame as soon as it is saved.
        b = render camera:c frame:(d.frameTicks as time) outputSize:[d.width,d.height] renderType:#normal vfb:true progressbar:true renderElements:d.masks renderElementBitmaps:&elementBitmaps cancelled:&cancelled
        if cancelled or b == undefined do throw "Render iptal edildi; is tamamlandi olarak isaretlenmedi."
        if d.masks and (elementBitmaps == undefined or elementBitmaps.count < 2) do throw "V-Ray MultiMatte bitmapleri donmedi; is tamamlanmadi."
        local folder = CRS_mkdir (CRS_join dir (if d.mode == 2 then "PATCH" else "BEAUTY"))
        folder = CRS_mkdir (CRS_join folder v.finish)
        local base = CRS_outputName d job
        if d.mode == 2 do base += "_PATCH"
        local out = CRS_uniquePath (CRS_join folder (base + ".png"))
        append paths (CRS_writeBitmap b out)
        if d.masks do (
            local names = #("_MASK_BodyR_DoorG_PlexiB", "_MASK_LegR_TrimG")
            for i = 1 to 2 do (
                if elementBitmaps[i] == undefined do throw "MultiMatte bos."
                append paths (CRS_writeBitmap elementBitmaps[i] (CRS_uniquePath (CRS_join folder (base + names[i] + ".png"))) data:true)
            )
        )
        close b
        b = undefined
        if elementBitmaps != undefined do for bitmap in elementBitmaps where bitmap != undefined do close bitmap
        elementBitmaps = #()
        CRS_markDone dir job paths ((timestamp()-start)/1000.0)
    ) catch (
        local err = getCurrentException()
        if b != undefined do close b
        if elementBitmaps != undefined do for bitmap in elementBitmaps where bitmap != undefined do close bitmap
        CRS_restore d
        throw()
    )
    CRS_restore d
    paths[1]
)
fn CRS_runQueue dir = (
    local lockPath = CRS_join dir "worker.lock"
    local lease = undefined
    local lastImage = ""
    local completed = 0
    local total = 0
    try (
        lease = (dotNetClass "System.IO.File").Open lockPath (dotNetClass "System.IO.FileMode").OpenOrCreate (dotNetClass "System.IO.FileAccess").ReadWrite (dotNetClass "System.IO.FileShare").None
    ) catch (lease = undefined)
    if lease == undefined do (
        CRS_status dir "failed" "Kuyruk kilidi açılamadı. Başka işlem çalışıyor veya klasöre erişilemiyor."
        throw "Bu kuyruk için başka işlem çalışıyor veya klasöre erişilemiyor."
    )
    try (
        local plan = (CRS_loadXml (CRS_join dir "queue.xml")).DocumentElement
        total = (CRS_elements plan "job").count
        CRS_status dir "loading" "Sahne ve dokular doğrulanıyor." total:total
        if CRS_get plan "version" != "1" do throw "Kuyruk surumu desteklenmiyor."
        for e in CRS_elements plan "fingerprints/file" do (
            local path = CRS_get e "path"
            if not doesFileExist path do throw ("Kaynak eksik: " + path)
            if CRS_hash path != CRS_get e "hash" do throw ("Kaynak degismis: " + path + ". Yeni kuyruk olusturun.")
        )
        if not (loadMaxFile (CRS_join dir "snapshot.max") quiet:true) do throw "Sahne kopyasi acilamadi."
        local d = CRS_readProfile (CRS_join dir "profile.xml") (CRS_join dir "palette.mat")
        CRS_capture d
        for e in CRS_elements plan "job" do append d.jobs (CRS_Job id:(CRS_get e "id") variantIndex:((CRS_get e "variant") as integer) cameraIndex:((CRS_get e "camera") as integer))
        total = d.jobs.count
        local vi = #()
        local ci = #()
        for job in d.jobs do (CRS_token job.id; appendIfUnique vi job.variantIndex; appendIfUnique ci job.cameraIndex)
        CRS_check d vi ci
        for job in d.jobs do (
            local old = CRS_verifyDone dir job
            if old != undefined then (completed += 1; lastImage = old) else (
                local control = CRS_readControl dir
                while control == "pause" do (
                    CRS_status dir "paused" "Kuyruk duraklatıldı." done:completed total:total image:lastImage
                    sleep 1
                    control = CRS_readControl dir
                )
                if control == "stop" do exit
                CRS_status dir "rendering" (CRS_outputName d job) job:job.id done:completed total:total image:lastImage
                lastImage = CRS_renderJob d job dir
                completed += 1
                CRS_status dir "rendering" "Kare kaydedildi." job:job.id done:completed total:total image:lastImage
                gc light:true
            )
        )
        CRS_restore d
        CRS_status dir (if completed == total then "completed" else "stopped") (if completed == total then "Kuyruk tamamlandı." else "Kuyruk durdu. Bitmiş kareler korunuyor.") done:completed total:total image:lastImage
        lease.Close()
        true
    ) catch (
        local err = getCurrentException()
        CRS_status dir "failed" err done:completed total:total image:lastImage
        lease.Close()
        format "CRS WORKER ERROR: %\n" err
        false
    )
)
