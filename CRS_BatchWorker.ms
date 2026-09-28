-- Ceneyra Render Studio - Batch Worker Script for 3dsmaxbatch.exe
-- Handles headless rendering, persistent queue processing, RenderMask diffing, and telemetry.

(
    local scriptDir = getFilenamePath (getSourceFileName())
    if scriptDir == undefined or scriptDir == "" do (
        scriptDir = "c:\\Users\\Ahmet\\Documents\\Ceneyra-Render-Studio\\"
    )
    fileIn (scriptDir + "CRS_VariantAutomation.ms")
    local automator = ::CRS_Automator

    local sceneFile = maxOps.mxsCmdLineArgs[#sceneFile]
    local mode = maxOps.mxsCmdLineArgs[#mode] -- "queue", "render", "viewport", "query", "rename"
    local queueFile = maxOps.mxsCmdLineArgs[#queueFile]
    local statusPath = maxOps.mxsCmdLineArgs[#statusPath]
    local cancelPath = maxOps.mxsCmdLineArgs[#cancelPath]
    local targetColor = maxOps.mxsCmdLineArgs[#targetColor]
    local finishColor = maxOps.mxsCmdLineArgs[#finishColor]
    local cameraName = maxOps.mxsCmdLineArgs[#cameraName]
    local rawWidth = maxOps.mxsCmdLineArgs[#width]
    local rawHeight = maxOps.mxsCmdLineArgs[#height]
    local rawQuality = maxOps.mxsCmdLineArgs[#quality]
    local width = if rawWidth != undefined then (try(rawWidth as integer) catch(2000)) else 2000
    local height = if rawHeight != undefined then (try(rawHeight as integer) catch(3000)) else 3000
    local quality = if rawQuality != undefined then (try(rawQuality as integer) catch(3)) else 3
    local outputPath = maxOps.mxsCmdLineArgs[#outputPath]
    local baseImagePath = maxOps.mxsCmdLineArgs[#baseImage]
    local mtlKapak = maxOps.mxsCmdLineArgs[#mtlKapak]
    local mtlGovde = maxOps.mxsCmdLineArgs[#mtlGovde]
    local mtlPleksi = maxOps.mxsCmdLineArgs[#mtlPleksi]
    local mtlAyak = maxOps.mxsCmdLineArgs[#mtlAyak]
    local mtlAyakDetay = maxOps.mxsCmdLineArgs[#mtlAyakDetay]
    local mtlKulp = maxOps.mxsCmdLineArgs[#mtlKulp]

    if width == undefined or width < 16 do width = 2000
    if height == undefined or height < 16 do height = 3000
    if quality == undefined do quality = 3
    if mode == undefined do mode = "render"
    if targetColor == undefined do targetColor = "ANTHRACITE"
    if finishColor == undefined do finishColor = "GOLD"

    fn writeStatus state msg pct:0 img:"" jobIdx:0 totalJobs:0 jobMode:"" = (
        if statusPath != undefined and statusPath != "" do (
            try (
                local f = createFile statusPath encoding:#utf8
                format "{\n" to:f
                format "  \"state\": \"%\",\n" state to:f
                format "  \"message\": \"%\",\n" msg to:f
                format "  \"percent\": %,\n" pct to:f
                format "  \"job_idx\": %,\n" jobIdx to:f
                format "  \"job_total\": %,\n" totalJobs to:f
                format "  \"job_mode\": \"%\",\n" jobMode to:f
                format "  \"image\": \"%\"\n" (substituteString img "\\" "\\\\") to:f
                format "}\n" to:f
                close f
            ) catch()
        )
    )

    writeStatus "loading" "Sahne yukleniyor ve parcalar hazirlaniyor..." pct:5

    -- 1. Load scene ONCE if needed
    if sceneFile != undefined and sceneFile != "" and doesFileExist sceneFile do (
        if maxFilePath + maxFileName != sceneFile do (
            loadMaxFile sceneFile useFileUnits:true quiet:true
        )
    )

    format "Ceneyra Batch Worker baslatildi. Mod: %, Sahne: %\n" mode (maxFilePath + maxFileName)

    -- Configure PNG exporter for 32-bit RGBA alpha support
    try (
        pngio.setType #true24
        pngio.setAlpha true
    ) catch()

    -- Helper to find camera
    fn resolveCamera camName = (
        local renderCam = undefined
        if camName != undefined and camName != "" and camName != "default" and camName != "varsayilan" do (
            for c in cameras where (classOf c != Targetobject and superClassOf c == camera and matchPattern (toLower c.name) pattern:(toLower camName)) do (
                renderCam = c
                exit
            )
        )
        if renderCam == undefined and cameras.count > 0 do (
            for c in cameras where (classOf c != Targetobject and superClassOf c == camera) do (
                renderCam = c
                exit
            )
        )
        renderCam
    )

    -- Helper to configure VRay quality
    fn setupVRayQuality q = (
        local vr = renderers.current
        if isProperty vr #imageSampler_type_new do (
            vr.imageSampler_type_new = if q < 3 then 1 else 0 -- 1: Progressive, 0: Bucket
            if q == 1 then (
                vr.progressive_minSamples = 1
                vr.progressive_maxSamples = 12
                vr.progressive_noise_threshold = 0.08
                vr.progressive_max_render_time = 0.5
            ) else if q == 2 then (
                vr.progressive_minSamples = 1
                vr.progressive_maxSamples = 48
                vr.progressive_noise_threshold = 0.03
                vr.progressive_max_render_time = 2.0
            )
        )
        vr
    )

    -- =========================================================================
    -- MODE: QUEUE (Continuous Single-Session Batch with RenderMask)
    -- =========================================================================
    if mode == "queue" then (
        if queueFile == undefined or not (doesFileExist queueFile) do (
            writeStatus "failed" ("Kuyruk dosyasi bulunamadi: " + (if queueFile != undefined then queueFile else "tanimsiz")) pct:0
            return false
        )

        global CRS_BATCH_QUEUE = #()
        fileIn queueFile
        local totalJobs = CRS_BATCH_QUEUE.count
        format "Kuyruk yuklendi: % is bulundu.\n" totalJobs

        local vr = renderers.current
        local baseCache = #() -- array of DataPairs: (key, path)

        for i = 1 to totalJobs do (
            -- Check for external cancellation
            if cancelPath != undefined and doesFileExist cancelPath do (
                writeStatus "cancelled" "Kullanici tarafindan iptal edildi." pct:(i * 100 / totalJobs)
                format "Kuyruk kullanici tarafindan iptal edildi.\n"
                exit
            )

            local job = CRS_BATCH_QUEUE[i]
            local jId = if (isProperty job #id) then job.id else i
            local jMode = if (isProperty job #renderMode) then job.renderMode else "full"
            local jCamName = if (isProperty job #camera) then job.camera else "default"
            local jW = if (isProperty job #width) then job.width else 2000
            local jH = if (isProperty job #height) then job.height else 3000
            local jQual = if (isProperty job #quality) then job.quality else 3
            local jOut = if (isProperty job #outputPath) then job.outputPath else ""
            local jMaskOut = if (isProperty job #maskPath) then job.maskPath else (getFilenamePath jOut + "mask_" + getFilenameFile jOut + ".png")
            local jBaseImg = if (isProperty job #baseImage) then job.baseImage else ""

            local jTarget = if (isProperty job #targetColor) then job.targetColor else "ANTHRACITE"
            local jFinish = if (isProperty job #finishColor) then job.finishColor else "GOLD"
            local jMtlGovde = if (isProperty job #mtlGovde) then job.mtlGovde else jTarget
            local jMtlKapak = if (isProperty job #mtlKapak) then job.mtlKapak else jTarget
            local jMtlPleksi = if (isProperty job #mtlPleksi) then job.mtlPleksi else jFinish
            local jMtlKulp = if (isProperty job #mtlKulp) then job.mtlKulp else jFinish
            local jMtlAyak = if (isProperty job #mtlAyak) then job.mtlAyak else jTarget
            local jMtlAyakDetay = if (isProperty job #mtlAyakDetay) then job.mtlAyakDetay else jFinish

            local pctJob = int (((i - 1.0) / totalJobs) * 100.0)
            local progressMsg = "İş #" + (i as string) + "/" + (totalJobs as string) + " render ediliyor: " + jTarget + "/" + jMtlKapak + " (" + jMtlPleksi + ")"
            writeStatus "rendering" progressMsg pct:pctJob jobIdx:i totalJobs:totalJobs jobMode:jMode

            -- Setup Camera & Quality
            local renderCam = resolveCamera jCamName
            setupVRayQuality jQual
            renderWidth = jW
            renderHeight = jH
            rendSaveFile = false

            -- 1. Apply Materials to Scene
            try (
                automator.applyVariant targetColor:jTarget finishColor:jFinish \
                                      mtlKapak:jMtlKapak mtlGovde:jMtlGovde mtlPleksi:jMtlPleksi \
                                      mtlAyak:jMtlAyak mtlAyakDetay:jMtlAyakDetay mtlKulp:jMtlKulp
            ) catch (
                format "UYARI: Varyant uygulanirken hata: %\n" (getCurrentException())
            )

            local cancelled = false
            local img = undefined
            makeDir (getFilenamePath jOut) all:true

            -- 2. Execute RENDERMASK or FULL RENDER
            if jMode == "mask" and jBaseImg != "" and (doesFileExist jBaseImg) then (
                -- RENDERMASK ACCELERATION
                format "--> [JOB %] RenderMask Hizlandirmasi baslatiliyor: Pleksi/Kulp/Ayak detaylari...\n" i
                local maskNodes = #()
                join maskNodes (automator.getPartsByRole "pleksi")
                join maskNodes (automator.getPartsByRole "kulp")
                join maskNodes (automator.getPartsByRole "ayak_detay")
                -- If leg color also differs from base, include legs
                if (isProperty job #includeAyakInMask) and job.includeAyakInMask == true do (
                    join maskNodes (automator.getPartsByRole "ayak")
                )

                if maskNodes.count > 0 then (
                    select maskNodes
                    vr.imageSampler_renderMask_type = 2 -- Selected objects only!
                    if isProperty vr #progressive_show_mask do vr.progressive_show_mask = true

                    img = render camera:renderCam outputSize:[jW, jH] vfb:false progressbar:true cancelled:&cancelled
                    if img != undefined and not cancelled do (
                        makeDir (getFilenamePath jMaskOut) all:true
                        img.filename = jMaskOut
                        save img
                        close img

                        -- Composite mask directly over base image
                        try (
                            local bBase = openBitmap jBaseImg
                            local bComp = bitmap jW jH
                            copy bBase bComp
                            close bBase

                            local bMask = openBitmap jMaskOut
                            pasteBitmap bMask bComp (box2 0 0 jW jH) [0,0] type:#composite
                            close bMask

                            bComp.filename = jOut
                            save bComp
                            close bComp
                        ) catch (
                            format "UYARI: MAXScript pasteBitmap compositing hatasi: %\n" (getCurrentException())
                        )
                    )
                ) else (
                    -- Fallback to full render if no mask nodes found
                    vr.imageSampler_renderMask_type = 0
                    img = render camera:renderCam outputSize:[jW, jH] vfb:false progressbar:true cancelled:&cancelled
                    if img != undefined and not cancelled do (
                        img.filename = jOut
                        save img
                        close img
                    )
                )
            ) else (
                -- FULL BASE RENDER
                format "--> [JOB %] Full Base Render aliniyor...\n" i
                vr.imageSampler_renderMask_type = 0 -- Full frame
                img = render camera:renderCam outputSize:[jW, jH] vfb:false progressbar:true cancelled:&cancelled
                if img != undefined and not cancelled do (
                    img.filename = jOut
                    save img
                    close img
                )
            )

            -- Reset RenderMask
            vr.imageSampler_renderMask_type = 0

            local pctDone = int ((i * 1.0 / totalJobs) * 100.0)
            if cancelled then (
                writeStatus "cancelled" ("İş #" + (i as string) + " iptal edildi.") pct:pctDone jobIdx:i totalJobs:totalJobs jobMode:jMode
                exit
            ) else (
                writeStatus "job_completed" ("İş #" + (i as string) + " tamamlandi.") pct:pctDone img:jOut jobIdx:i totalJobs:totalJobs jobMode:jMode
                format "İş % tamamlandi: % (Mod: %)\n" i jOut jMode
            )
        )

        writeStatus "completed" "Tum kuyruk basariyla tamamlandi." pct:100 totalJobs:totalJobs
        format "Toplu Render Kuyrugu Tamamlandi.\n"

    -- =========================================================================
    -- MODE: QUERY (Extract metadata: cameras, parts)
    -- =========================================================================
    ) else if mode == "query" then (
        local metaPath = if outputPath != undefined and outputPath != "" then outputPath else (
            if sceneFile != undefined and sceneFile != "" then ((getFilenamePath sceneFile) + "scene_meta.json") else (scriptDir + "cache\\scene_meta.json")
        )
        automator.exportSceneInfo metaPath
        writeStatus "completed" "Sahne bilgileri alindi." pct:100

    -- =========================================================================
    -- MODE: RENAME (Standardize part names)
    -- =========================================================================
    ) else if mode == "rename" then (
        automator.standardizePartNames()
        if sceneFile != undefined and doesFileExist sceneFile do (
            saveMaxFile sceneFile quiet:true
        )
        writeStatus "completed" "Parca isimleri standartlastirildi." pct:100

    -- =========================================================================
    -- MODE: VIEWPORT SNAPSHOT
    -- =========================================================================
    ) else if mode == "viewport" then (
        writeStatus "rendering" "Viewport onizlemesi olusturuluyor..." pct:60
        local renderCam = resolveCamera cameraName
        if renderCam != undefined do viewport.setCamera renderCam
        hideByCategory.lights = true
        hideByCategory.cameras = true
        hideByCategory.helpers = true
        redrawViews()
        completeRedraw()
        local b = gw.getViewportDib()
        if b != undefined do (
            if outputPath == undefined or outputPath == "" do outputPath = (scriptDir + "cache\\viewport_preview.png")
            makeDir (getFilenamePath outputPath) all:true
            b.filename = outputPath
            save b
            close b
            writeStatus "completed" "Viewport onizlemesi hazir." pct:100 img:outputPath
        )

    -- =========================================================================
    -- MODE: SINGLE RENDER (With RenderMask Support if Base Image provided)
    -- =========================================================================
    ) else (
        writeStatus "rendering" "V-Ray render motoru hazirlaniyor..." pct:40
        local renderCam = resolveCamera cameraName
        local vr = setupVRayQuality quality
        renderWidth = width
        renderHeight = height
        rendSaveFile = false

        -- Apply Material Variant to Parts
        try (
            automator.applyVariant targetColor:targetColor finishColor:finishColor \
                                  mtlKapak:mtlKapak mtlGovde:mtlGovde mtlPleksi:mtlPleksi \
                                  mtlAyak:mtlAyak mtlAyakDetay:mtlAyakDetay mtlKulp:mtlKulp
        ) catch (
            format "UYARI: Varyant uygulanirken hata: %\n" (getCurrentException())
        )

        local img = undefined
        local cancelled = false
        if outputPath == undefined or outputPath == "" do (
            outputPath = (scriptDir + "renders\\" + (getFilenameFile sceneFile) + "_" + targetColor + ".png")
        )
        makeDir (getFilenamePath outputPath) all:true

        -- Check if RenderMask can be used with provided baseImage
        if baseImagePath != undefined and baseImagePath != "" and (doesFileExist baseImagePath) then (
            format "Tekli Render: RenderMask hizlandirmasi uygulaniyor...\n"
            local maskNodes = #()
            join maskNodes (automator.getPartsByRole "pleksi")
            join maskNodes (automator.getPartsByRole "kulp")
            join maskNodes (automator.getPartsByRole "ayak_detay")
            select maskNodes
            vr.imageSampler_renderMask_type = 2
            if isProperty vr #progressive_show_mask do vr.progressive_show_mask = true

            local maskOut = (getFilenamePath outputPath + "mask_" + getFilenameFile outputPath + ".png")
            img = render camera:renderCam outputSize:[width,height] vfb:false progressbar:true cancelled:&cancelled
            if img != undefined and not cancelled do (
                img.filename = maskOut
                save img
                close img

                -- Composite
                try (
                    local bBase = openBitmap baseImagePath
                    local bComp = bitmap width height
                    copy bBase bComp
                    close bBase

                    local bMask = openBitmap maskOut
                    pasteBitmap bMask bComp (box2 0 0 width height) [0,0] type:#composite
                    close bMask

                    bComp.filename = outputPath
                    save bComp
                    close bComp
                    writeStatus "completed" "RenderMask render tamamlandi." pct:100 img:outputPath
                ) catch (
                    format "Compositing hatasi: %\n" (getCurrentException())
                )
            )
        ) else (
            -- Standard Full Render
            vr.imageSampler_renderMask_type = 0
            img = render camera:renderCam outputSize:[width,height] vfb:false progressbar:true cancelled:&cancelled
            if img != undefined and not cancelled do (
                img.filename = outputPath
                save img
                close img
                writeStatus "completed" "Render basariyla tamamlandi." pct:100 img:outputPath
            )
        )

        vr.imageSampler_renderMask_type = 0 -- Reset
    )
)
