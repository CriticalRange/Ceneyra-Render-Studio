-- Ceneyra Render Studio - Variant & Material Automation Engine
-- Supports TV stand parts: kapak001, kapak002, dikme001L, dikme001R, govde*, pleksi*, ayak*, etc.
-- Automatically matches and replaces materials for Anthracite, White, Oak, Travertine, Gold, Silver.

global CRS_Automator

struct CRS_AutomatorStruct (
    fn toLowerStr str = (
        toLower (str as string)
    ),

    fn findSceneMaterial pattern = (
        local pat = "*" + (toLower pattern) + "*"
        -- 1. Check meditMaterials (1 to 24)
        for i = 1 to 24 do (
            local m = meditMaterials[i]
            if m != undefined and matchPattern (toLower m.name) pattern:pat do return m
        )
        -- 2. Check sceneMaterials
        for m in sceneMaterials do (
            if m != undefined and matchPattern (toLower m.name) pattern:pat do return m
        )
        -- 3. Check materials on scene geometry
        for n in geometry where n.material != undefined do (
            local m = n.material
            if matchPattern (toLower m.name) pattern:pat do return m
            if isKindOf m MultiMaterial do (
                for subMtl in m.materialList where subMtl != undefined do (
                    if matchPattern (toLower subMtl.name) pattern:pat do return subMtl
                )
            )
        )
        undefined
    ),

    fn getPartsByRole roleName = (
        local matched = #()
        local patList = #()
        local rLow = toLower roleName
        case rLow of (
            "kapak": patList = #("kapak*")
            "pleksi": patList = #("pleksi*")
            "tabla": patList = #("tabla*")
            "dikme": patList = #("dikme*")
            "raf": patList = #("raf*")
            "arkalik": patList = #("arkalik*")
            "govde": patList = #("tabla*", "dikme*", "raf*", "arkalik*", "govde*")
            "ayak": patList = #("ayak*")
            "ayak_detay": patList = #("ayak_detay*")
            "kulp": patList = #("kulp*")
            default: patList = #("*" + rLow + "*")
        )

        for n in geometry where not n.isHidden do (
            local lowName = toLower n.name
            if rLow == "ayak" and matchPattern lowName pattern:"ayak_detay*" do continue

            local isMatch = false
            for pat in patList while not isMatch do (
                if matchPattern lowName pattern:pat do isMatch = true
            )
            if isMatch do append matched n
        )
        matched
    ),

    fn resolveColorMaterial colName = (
        if colName == undefined or colName == "" do return undefined
        local cLow = toLower (colName as string)
        case cLow of (
            "anthracite": findSceneMaterial "antrasit"
            "antrasit": findSceneMaterial "antrasit"
            "white": (
                local m = findSceneMaterial "beyaz"
                if m == undefined do m = findSceneMaterial "white"
                m
            )
            "beyaz": (
                local m = findSceneMaterial "beyaz"
                if m == undefined do m = findSceneMaterial "white"
                m
            )
            "oak": (
                local m = findSceneMaterial "safir me"
                if m == undefined do m = findSceneMaterial "oak"
                m
            )
            "safir mese": (
                local m = findSceneMaterial "safir me"
                if m == undefined do m = findSceneMaterial "oak"
                m
            )
            "travertine": findSceneMaterial "traverten"
            "traverten": findSceneMaterial "traverten"
            "gold": (
                local m = findSceneMaterial "gold"
                if m == undefined do m = findSceneMaterial "altin"
                m
            )
            "altin": (
                local m = findSceneMaterial "gold"
                if m == undefined do m = findSceneMaterial "altin"
                m
            )
            "silver": (
                local m = findSceneMaterial "silver"
                if m == undefined do m = findSceneMaterial "gumus"
                m
            )
            "gumus": (
                local m = findSceneMaterial "silver"
                if m == undefined do m = findSceneMaterial "gumus"
                m
            )
            "black": (
                local m = findSceneMaterial "siyah"
                if m == undefined do m = findSceneMaterial "black"
                m
            )
            "siyah": (
                local m = findSceneMaterial "siyah"
                if m == undefined do m = findSceneMaterial "black"
                m
            )
            default: findSceneMaterial colName
        )
    ),

    fn applyUVW nodes channel:1 boxMode:true turn:0 = (
        if nodes == undefined do return 0
        local nodeList = if isKindOf nodes Array then nodes else #(nodes)
        if nodeList.count == 0 do return 0
        local applied = 0
        for n in nodeList do (
            if isValidNode n and superClassOf n == GeometryClass do (
                local modName = "CRS_UVW_" + channel as string
                local uv = undefined
                for m in n.modifiers where m.name == modName and classOf m == UVWMap do uv = m
                if uv == undefined do (
                    uv = UVWMap()
                    uv.name = modName
                    addModifier n uv
                )
                local bb = nodeGetBoundingBox n n.objectTransform
                local size = bb[2] - bb[1]
                local center = (bb[1] + bb[2]) / 2.0
                uv.mapChannel = channel
                uv.realWorldMapSize = false
                uv.maptype = if boxMode then 4 else 0 -- 4 = Box, 0 = Planar
                uv.width = amax size.x 0.001
                uv.length = amax size.y 0.001
                uv.height = amax size.z 0.001
                uv.gizmo.transform = (rotateZMatrix turn) * (matrix3 [1,0,0] [0,1,0] [0,0,1] center)
                applied += 1
            )
        )
        applied
    ),

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
    ),

    fn applyVariant targetColor:"ANTHRACITE" finishColor:"GOLD" \
                    mtlKapak:undefined mtlGovde:undefined mtlPleksi:undefined \
                    mtlAyak:undefined mtlAyakDetay:undefined mtlKulp:undefined = (
        local results = #()

        -- Resolve materials per part role with fallback to targetColor / finishColor
        local mKapak = if mtlKapak != undefined and mtlKapak != "" then (resolveColorMaterial mtlKapak) else (resolveColorMaterial targetColor)
        local mGovde = if mtlGovde != undefined and mtlGovde != "" then (resolveColorMaterial mtlGovde) else (resolveColorMaterial targetColor)
        local mPleksi = if mtlPleksi != undefined and mtlPleksi != "" then (resolveColorMaterial mtlPleksi) else (resolveColorMaterial finishColor)
        local mAyak = if mtlAyak != undefined and mtlAyak != "" then (resolveColorMaterial mtlAyak) else (resolveColorMaterial targetColor)
        local mAyakDetay = if mtlAyakDetay != undefined and mtlAyakDetay != "" then (resolveColorMaterial mtlAyakDetay) else (resolveColorMaterial finishColor)
        local mKulp = if mtlKulp != undefined and mtlKulp != "" then (resolveColorMaterial mtlKulp) else (resolveColorMaterial finishColor)

        -- 1. Kapaklar (kapak001...)
        local doors = getPartsByRole "kapak"
        if mKapak != undefined do (
            for d in doors where isValidNode d do (
                setDoorMaterial d mKapak faceID:1
                append results d.name
            )
            applyUVW doors channel:1 boxMode:true
        )

        -- 2. Gövde (tabla001..., dikme001..., raf001..., arkalik001...)
        local govde = getPartsByRole "govde"
        if mGovde != undefined do (
            for g in govde where isValidNode g do (
                g.material = mGovde
                append results g.name
            )
            applyUVW govde channel:1 boxMode:true
        )

        -- 3. Pleksiler (pleksi001...)
        local pleksis = getPartsByRole "pleksi"
        if mPleksi != undefined do (
            for p in pleksis where isValidNode p do (
                p.material = mPleksi
                append results p.name
            )
        )

        -- 4. Ayaklar (ayak001...)
        local legs = getPartsByRole "ayak"
        if mAyak != undefined do (
            for a in legs where isValidNode a do (
                a.material = mAyak
                append results a.name
            )
            applyUVW legs channel:1 boxMode:true
        )

        -- 5. Ayak Detayları (ayak_detay001...)
        local legDetays = getPartsByRole "ayak_detay"
        if mAyakDetay != undefined do (
            for ad in legDetays where isValidNode ad do (
                ad.material = mAyakDetay
                append results ad.name
            )
        )

        -- 6. Kulplar (kulp001...)
        local kulps = getPartsByRole "kulp"
        if mKulp != undefined do (
            for k in kulps where isValidNode k do (
                k.material = mKulp
                append results k.name
            )
        )

        redrawViews()
        format "CRS_Automator: % nesneye varyant uygulandi (Kapak: %, Govde: %, Pleksi: %, Ayak: %, AyakDetay: %, Kulp: %)\n" \
            results.count \
            (if mKapak != undefined then mKapak.name else "none") \
            (if mGovde != undefined then mGovde.name else "none") \
            (if mPleksi != undefined then mPleksi.name else "none") \
            (if mAyak != undefined then mAyak.name else "none") \
            (if mAyakDetay != undefined then mAyakDetay.name else "none") \
            (if mKulp != undefined then mKulp.name else "none")
        results
    ),

    fn standardizePartNames = (
        -- Helper to rename TV stand objects to standard format:
        -- kapak001, kapak002, dikme001L, dikme001R, govde001, pleksi001, ayak001, kulp001, etc.
        local doors = getPartsByRole "kapak"
        local dikmeler = getPartsByRole "dikme"
        local govde = getPartsByRole "govde"
        local plexi = getPartsByRole "pleksi"
        local legs = getPartsByRole "ayak"
        local kulps = getPartsByRole "kulp"

        for i = 1 to doors.count do (
            local numStr = formattedPrint i format:"03d"
            doors[i].name = "kapak" + numStr
        )
        for i = 1 to dikmeler.count do (
            local side = if (mod i 2) == 1 then "L" else "R"
            local numStr = formattedPrint (((i-1)/2)+1) format:"03d"
            dikmeler[i].name = "dikme" + numStr + side
        )
        for i = 1 to govde.count do (
            local numStr = formattedPrint i format:"03d"
            govde[i].name = "govde" + numStr
        )
        for i = 1 to plexi.count do (
            local numStr = formattedPrint i format:"03d"
            plexi[i].name = "pleksi" + numStr
        )
        for i = 1 to legs.count do (
            local numStr = formattedPrint i format:"03d"
            legs[i].name = "ayak" + numStr
        )
        for i = 1 to kulps.count do (
            local numStr = formattedPrint i format:"03d"
            kulps[i].name = "kulp" + numStr
        )
        format "CRS_Automator: Parca isimleri standartlastirildi: % kapak, % dikme, % govde, % pleksi, % ayak, % kulp\n" doors.count dikmeler.count govde.count plexi.count legs.count kulps.count
        true
    ),

    fn exportSceneInfo jsonPath = (
        local camList = for c in cameras where (superClassOf c == camera and classOf c != Targetobject) collect c
        local doorCount = (getPartsByRole "kapak").count
        local dikmeCount = (getPartsByRole "dikme").count
        local govdeCount = (getPartsByRole "govde").count
        local plexiCount = (getPartsByRole "pleksi").count
        local legCount = (getPartsByRole "ayak").count
        local kulpCount = (getPartsByRole "kulp").count

        local f = createFile jsonPath encoding:#utf8
        format "{\n" to:f
        format "  \"sceneFile\": \"%\",\n" (substituteString (maxFilePath + maxFileName) "\\" "\\\\") to:f
        format "  \"cameraCount\": %,\n" camList.count to:f
        format "  \"cameras\": [\n" to:f
        for i = 1 to camList.count do (
            local c = camList[i]
            local pos = c.pos
            local targetPos = if c.target != undefined then c.target.pos else [0,0,0]
            local camType = classOf c as string
            format "    {\n" to:f
            format "      \"name\": \"%\",\n" c.name to:f
            format "      \"type\": \"%\",\n" camType to:f
            format "      \"pos\": [%, %, %],\n" pos.x pos.y pos.z to:f
            format "      \"target\": [%, %, %]\n" targetPos.x targetPos.y targetPos.z to:f
            format "    }%\n" (if i < camList.count then "," else "") to:f
        )
        format "  ],\n" to:f
        format "  \"cameraNames\": [%],\n" (
            local s = ""
            for i = 1 to camList.count do (
                s += "\"" + camList[i].name + "\""
                if i < camList.count do s += ", "
            )
            s
        ) to:f
        format "  \"parts\": {\n" to:f
        format "    \"doors\": %,\n" doorCount to:f
        format "    \"dikmeler\": %,\n" dikmeCount to:f
        format "    \"govde\": %,\n" govdeCount to:f
        format "    \"pleksi\": %,\n" plexiCount to:f
        format "    \"legs\": %,\n" legCount to:f
        format "    \"kulps\": %\n" kulpCount to:f
        format "  }\n" to:f
        format "}\n" to:f
        close f
        true
    )
)

CRS_Automator = CRS_AutomatorStruct()
