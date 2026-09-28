global CRS_Root
CRS_Root = getFilenamePath (getSourceFileName())

struct CRS_Ref (handle, label, kind)
struct CRS_Binding (label, nodes = #(), faceID = 0)
struct CRS_Swatch (key, label, mtl)
struct CRS_Variant (code, label, finish, mats = #())
struct CRS_Camera (node, number)
struct CRS_Job (id, variantIndex, cameraIndex)
struct CRS_Model (
    product = "KA1546", scene = "", bindings = #(), palette = #(), variants = #(), cameras = #(),
    baseline = #(), activeRoles = #(1,2,3,4,5), receivers = #(), jobs = #(),
    width = 2000, height = 3000, quality = 3, mode = 1, masks = true, frameTicks = 0,
    sourceHash = "", libraryHash = "", assets = #()
)
global CRS_Data = CRS_Model()

fn CRS_guid = ((dotNetClass "System.Guid").NewGuid()).ToString "N"
fn CRS_join root leaf = pathConfig.appendPath root leaf
fn CRS_mkdir p = (makeDir p all:true; p)
fn CRS_xml = (dotNetObject "System.Xml.XmlDocument")
fn CRS_attr el key value = el.SetAttribute key (value as string)
fn CRS_get el key = el.GetAttribute key
fn CRS_elements el xpath = (
    local nodes = el.SelectNodes xpath
    for i = 0 to nodes.Count-1 collect nodes.Item i
)
fn CRS_child doc parent tag = (local e = doc.CreateElement tag; parent.AppendChild e; e)
fn CRS_loadXml path = (
    local settings = dotNetObject "System.Xml.XmlReaderSettings"
    settings.DtdProcessing = (dotNetClass "System.Xml.DtdProcessing").Prohibit
    settings.XmlResolver = undefined
    local reader = (dotNetClass "System.Xml.XmlReader").Create path settings
    local doc = CRS_xml()
    try (doc.Load reader; reader.Close()) catch (reader.Close(); throw())
    doc
)
fn CRS_writeXml doc path = (
    local tmp = path + "." + CRS_guid() + ".tmp"
    doc.Save tmp
    local io = dotNetClass "System.IO.File"
    if doesFileExist path then io.Replace tmp path (path + ".bak") else io.Move tmp path
    path
)
fn CRS_hash path = (
    local stream = (dotNetClass "System.IO.File").OpenRead path
    local sha = (dotNetClass "System.Security.Cryptography.SHA256").Create()
    local result = ""
    try (result = (dotNetClass "System.BitConverter").ToString (sha.ComputeHash stream)) catch (stream.Close(); sha.Dispose(); throw())
    stream.Close()
    sha.Dispose()
    substituteString result "-" ""
)
fn CRS_token s = (
    if s == "" or not ((dotNetClass "System.Text.RegularExpressions.Regex").IsMatch s "^[A-Za-z0-9_-]+$") do throw ("Gecersiz kod: " + s + ". Harf, rakam, _ ve - kullanin.")
    s
)
fn CRS_nodeKind n = (classOf n.baseObject) as string
fn CRS_makeRef n = CRS_Ref handle:n.handle label:n.name kind:(CRS_nodeKind n)
fn CRS_resolve r = (
    local n = maxOps.getNodeByHandle r.handle
    if not isValidNode n or n.name != r.label or (CRS_nodeKind n) != r.kind do throw ("Nesne eslesmesi gecersiz: " + r.label + ". Sahneyi yeniden esleyin.")
    n
)
fn CRS_nodes refs = for r in refs collect CRS_resolve r
fn CRS_cameraNodes = for n in cameras where superClassOf n == camera collect n
fn CRS_material d key = (
    if key == "KEEP" do return undefined
    for p in d.palette where p.key == key do return p.mtl
    throw ("Palet materyali bulunamadi: " + key)
)
fn CRS_capture d = (
    d.baseline = #()
    local seen = #()
    for b in d.bindings do for n in CRS_nodes b.nodes where findItem seen n == 0 do (
        append seen n
        append d.baseline #(n,n.material,n.gbufferChannel)
    )
    d.scene = maxFilePath + maxFileName
    d
)
fn CRS_restore d = (
    for item in d.baseline where isValidNode item[1] do (item[1].material = item[2]; item[1].gbufferChannel = item[3])
    true
)
fn CRS_requireScene d = (
    if d.scene != maxFilePath + maxFileName do throw "Aktif sahne degisti. Once Sahneyi Esle tusuna basin."
    for b in d.bindings do CRS_nodes b.nodes
    true
)
fn CRS_setFaceMaterial n id m = (
    if id == 0 then n.material = m else (
        if not isKindOf n.material MultiMaterial do throw (n.name + ": Multi/Sub materyal gerekli.")
        local slot = findItem n.material.materialIDList id
        if slot == 0 do throw (n.name + ": materyal ID bulunamadi: " + id as string)
        local mm = copy n.material
        mm.materialList[slot] = m
        n.material = mm
    )
)
fn CRS_apply d v = (
    CRS_requireScene d
    CRS_restore d
    local changed = #()
    try (
        for i in d.activeRoles where i <= d.bindings.count do (
            local key = v.mats[i]
            if key != "KEEP" do (
                -- KA1546's white body, doors and painted legs have distinct source
                -- materials. "Beyaz (sahnedeki)" must retain each original one.
                local keepSceneWhite = d.product == "KA1546" and key == "WHITE"
                local m = if keepSceneWhite then undefined else CRS_material d key
                for n in CRS_nodes d.bindings[i].nodes do (
                    if not keepSceneWhite do CRS_setFaceMaterial n d.bindings[i].faceID m
                    appendIfUnique changed n
                )
            )
        )
    ) catch (CRS_restore d; throw())
    changed
)
fn CRS_makeBinding label handles id:0 = (
    local b = CRS_Binding label:label faceID:id
    for h in handles do (
        local n = maxOps.getNodeByHandle h
        if not isValidNode n do throw ("KA1546 nesnesi bulunamadi: " + h as string)
        append b.nodes (CRS_makeRef n)
    )
    b
)
fn CRS_autoBinding label nodes expected id:0 = (
    if nodes.count != expected do throw (label + ": " + expected as string + " nesne bekleniyor, " + nodes.count as string + " bulundu. Elle esleme kullanin.")
    local b = CRS_Binding label:label faceID:id
    for n in nodes do append b.nodes (CRS_makeRef n)
    b
)
fn CRS_walkMaps root visited files = (
    if root == undefined or findItem visited root > 0 do return false
    append visited root
    if isKindOf root Bitmaptexture and root.filename != "" do appendIfUnique files root.filename
    for i = 1 to getNumSubTexmaps root do CRS_walkMaps (getSubTexmap root i) visited files
    if isKindOf root Material and not isKindOf root TextureMap do for i = 1 to getNumSubMtls root do CRS_walkMaps (getSubMtl root i) visited files
    true
)
fn CRS_editorMaterial pattern label = (
    local first = undefined
    local ready = undefined
    for i = 1 to 24 do (
        local m = meditMaterials[i]
        if m != undefined and matchPattern (toLower m.name) pattern:pattern do (
            if first == undefined do first = m
            local files = #()
            CRS_walkMaps m #() files
            local complete = true
            for file in files where not doesFileExist file do complete = false
            if complete and ready == undefined do ready = m
        )
    )
    if ready != undefined do return copy ready
    if first != undefined do return copy first
    throw (label + " materyali Material Editor'da bulunamadi. Elle esleme kullanin.")
)
fn CRS_seedKA1546 = (
    local d = CRS_Model()
    -- Check for TV Stand naming format (kapak*, dikme*, govde*, etc.) first
    local tvDoors = for n in geometry where not isHidden n and (matchPattern (toLower n.name) pattern:"*kapak*" or matchPattern (toLower n.name) pattern:"group#5 *") collect n
    local tvDikme = for n in geometry where not isHidden n and matchPattern (toLower n.name) pattern:"*dikme*" collect n
    local tvBody = for n in geometry where not isHidden n and (
        matchPattern (toLower n.name) pattern:"*govde*" or matchPattern (toLower n.name) pattern:"*gövde*" or
        matchPattern (toLower n.name) pattern:"group#1 *" or matchPattern (toLower n.name) pattern:"group#2 *" or
        matchPattern (toLower n.name) pattern:"group#3 *" or matchPattern (toLower n.name) pattern:"group#4 *" or
        matchPattern (toLower n.name) pattern:"group#9 *") collect n
    local tvPleksi = for n in geometry where not isHidden n and (
        matchPattern (toLower n.name) pattern:"*pleksi*" or matchPattern (toLower n.name) pattern:"*plexi*" or
        matchPattern (toLower n.name) pattern:"group#6 *") collect n
    local tvLegs = for n in geometry where not isHidden n and (
        matchPattern (toLower n.name) pattern:"*ayak*" or matchPattern (toLower n.name) pattern:"190 eleganz ayak*") collect n
    local tvMetal = for n in geometry where not isHidden n and (
        matchPattern (toLower n.name) pattern:"*kulp*" or matchPattern (toLower n.name) pattern:"component#9 *") collect n

    local body = tvBody
    local doors = tvDoors
    local plexi = tvPleksi
    local legPaint = tvLegs
    local legMetal = tvMetal

    local white = undefined
    local laser = undefined

    if doors.count > 0 do (
        local door = doors[1]
        if isKindOf door.material MultiMaterial then (
            local id1 = findItem door.material.materialIDList 1
            local id2 = findItem door.material.materialIDList 2
            if id1 > 0 do white = copy door.material.materialList[id1]
            if id2 > 0 do laser = copy door.material.materialList[id2]
        ) else if door.material != undefined do (
            white = copy door.material
        )
    )

    if white == undefined do (
        try (white = CRS_editorMaterial "*beyaz*" "Beyaz") catch()
        if white == undefined do try (white = CRS_editorMaterial "*white*" "White") catch()
        if white == undefined and meditMaterials[1] != undefined do white = copy meditMaterials[1]
    )

    local bBody = CRS_Binding label:"Gövde"
    for n in body do append bBody.nodes (CRS_makeRef n)
    local bDoors = CRS_Binding label:"Kapak yüzeyi" faceID:(if (doors.count > 0 and isKindOf doors[1].material MultiMaterial) then 1 else 0)
    for n in doors do append bDoors.nodes (CRS_makeRef n)
    local bPlexi = CRS_Binding label:"Pleksi"
    for n in plexi do append bPlexi.nodes (CRS_makeRef n)
    local bLegs = CRS_Binding label:"Ayak boya"
    for n in legPaint do append bLegs.nodes (CRS_makeRef n)
    local bMetal = CRS_Binding label:"Ayak metal detayı"
    for n in legMetal do append bMetal.nodes (CRS_makeRef n)
    local bLaser = CRS_Binding label:"Lazer yüzleri" faceID:2
    for n in doors do append bLaser.nodes (CRS_makeRef n)

    d.bindings = #(bBody, bDoors, bPlexi, bLegs, bMetal, bLaser)

    local pAnthracite = undefined
    local pTravertine = undefined
    local pOak = undefined
    local pGold = undefined
    local pSilver = undefined

    try (pAnthracite = CRS_editorMaterial "*antrasit*" "Antrasit") catch()
    try (pTravertine = CRS_editorMaterial "*traverten*" "Traverten") catch()
    try (pOak = CRS_editorMaterial "*safir me?e*" "Safir meşe") catch()
    try (pGold = CRS_editorMaterial "*gold pleksi*" "Gold Pleksi") catch()
    try (pSilver = CRS_editorMaterial "*silver pleksi*" "Silver Pleksi") catch()

    d.palette = #(
        CRS_Swatch key:"WHITE" label:"Beyaz (sahnedeki)" mtl:white,
        CRS_Swatch key:"ANTHRACITE" label:"Antrasit gri" mtl:pAnthracite,
        CRS_Swatch key:"TRAVERTINE" label:"Traverten" mtl:pTravertine,
        CRS_Swatch key:"OAK" label:"Safir meşe" mtl:pOak,
        CRS_Swatch key:"GOLD" label:"Gold Pleksi" mtl:pGold,
        CRS_Swatch key:"SILVER" label:"Silver Pleksi" mtl:pSilver,
        CRS_Swatch key:"LASER" label:"Siyah lazer çizgisi" mtl:laser
    )

    local combos = #(#("B","Beyaz","WHITE","WHITE"), #("A","Antrasit","ANTHRACITE","ANTHRACITE"), #("BT","Beyaz / traverten","WHITE","TRAVERTINE"), #("AT","Antrasit / traverten","ANTHRACITE","TRAVERTINE"), #("DB","Doğal / beyaz","OAK","WHITE"))
    for finish in #("GOLD","SILVER") do for row in combos do (
        local suffix = if finish == "GOLD" then "G" else "S"
        append d.variants (CRS_Variant code:(row[1]+suffix) label:(row[2]+" / "+finish) finish:finish mats:#(row[3],row[4],finish,row[3],finish,"KEEP"))
    )
    local i = 0
    for n in CRS_cameraNodes() do (i += 1; append d.cameras (CRS_Camera node:(CRS_makeRef n) number:i))
    d.frameTicks = currentTime as integer
    CRS_capture d
)
fn CRS_emptyScene = (
    local d = CRS_Model product:"URUN"
    d.bindings = for s in #("Govde","Kapak yuzeyi","Pleksi","Ayak boya","Ayak metal detay","Lazer yuzleri") collect CRS_Binding label:s
    d.bindings[2].faceID = 1
    d.bindings[6].faceID = 2
    local i = 0
    for n in CRS_cameraNodes() do (i += 1; append d.cameras (CRS_Camera node:(CRS_makeRef n) number:i))
    d.frameTicks = currentTime as integer
    CRS_capture d
)
fn CRS_uvw nodes channel:1 boxMode:false turn:0 = (
    if nodes.count == 0 do throw "UVW icin nesne secin."
    for n in nodes do (
        if superClassOf n != GeometryClass do throw (n.name + ": geometri degil.")
        local instances = #()
        instanceMgr.getInstances n &instances
        for inst in instances where findItem nodes inst == 0 do throw (n.name + ": secim disinda instance var. Tum instance nesnelerini esleyin.")
    )
    local done = #()
    for n in nodes do (
        local bb = nodeGetBoundingBox n n.objectTransform
        local size = bb[2]-bb[1]
        local center = (bb[1]+bb[2])/2
        local modName = "CRS_UVW_" + channel as string
        local uv = undefined
        for m in n.modifiers where m.name == modName and classOf m == UVWMap do uv = m
        if uv == undefined do (uv = UVWMap(); uv.name = modName; addModifier n uv)
        if findItem done uv == 0 do (
            append done uv
            local evaluated = snapshotAsMesh n
            free evaluated
            uv.mapChannel = channel
            uv.realWorldMapSize = false
            uv.maptype = if boxMode then 4 else 0
            uv.axis = 2
            local u = [1,0,0]
            local v = [0,1,0]
            local width = size.x
            local height = size.y
            if not boxMode do (
                if size.x <= size.y and size.x <= size.z then (u = [0,1,0]; v = [0,0,1]; width = size.y; height = size.z)
                else if size.y <= size.z then (u = [1,0,0]; v = [0,0,1]; width = size.x; height = size.z)
            )
            uv.width = amax width 0.001
            uv.length = amax height 0.001
            uv.height = amax size.z 0.001
            uv.gizmo.transform = (rotateZMatrix turn) * (matrix3 u v (cross u v) center)
        )
    )
    redrawViews()
    done.count
)
fn CRS_boxForTextureVariant d v = (
    local updated = 0
    for role in #(1,2,4) do (
        if role <= d.bindings.count and findItem d.activeRoles role > 0 and findItem #("ANTHRACITE","TRAVERTINE","OAK") v.mats[role] > 0 do (
            updated += CRS_uvw (CRS_nodes d.bindings[role].nodes) channel:1 boxMode:true
        )
    )
    updated
)
fn CRS_missing d variants = (
    local visited = #()
    local files = #()
    for v in variants do for i in d.activeRoles where v.mats[i] != "KEEP" do CRS_walkMaps (CRS_material d v.mats[i]) visited files
    for file in files where not doesFileExist file collect file
)
fn CRS_check d variantIndices cameraIndices = (
    CRS_requireScene d
    CRS_token d.product
    if variantIndices.count == 0 do throw "En az bir varyant secin."
    if cameraIndices.count == 0 do throw "En az bir kamera secin."
    if d.activeRoles.count == 0 do throw "En az bir degisecek bolum secin."
    if d.width < 16 or d.height < 16 do throw "Cozunurluk en az 16 piksel olmali."
    local names = #()
    local camNumbers = #()
    for ci in cameraIndices do (
        local c = d.cameras[ci]
        local n = CRS_resolve c.node
        if superClassOf n != camera do throw "Kamera hedefi kamera olarak kullanilamaz."
        if c.number < 1 or findItem camNumbers c.number > 0 do throw "Kamera cikti numaralari benzersiz ve pozitif olmali."
        append camNumbers c.number
    )
    for i in d.activeRoles do (
        local b = d.bindings[i]
        if b.nodes.count == 0 do throw (b.label + ": nesne eslemesi bos.")
        for n in CRS_nodes b.nodes where b.faceID > 0 do (
            if not isKindOf n.material MultiMaterial do throw (b.label + ": Multi/Sub gerekli.")
            if findItem n.material.materialIDList b.faceID == 0 do throw (b.label + ": ID eslesmesi yok.")
        )
    )
    for a = 1 to d.bindings.count do for b = a+1 to d.bindings.count where b <= d.bindings.count and findItem d.activeRoles a > 0 and findItem d.activeRoles b > 0 do (
        for ra in d.bindings[a].nodes do for rb in d.bindings[b].nodes where ra.handle == rb.handle do (
            if d.bindings[a].faceID == 0 or d.bindings[b].faceID == 0 or d.bindings[a].faceID == d.bindings[b].faceID do throw "Ayni nesne/yuz birden fazla bolume atanmis."
        )
    )
    local variants = for vi in variantIndices collect d.variants[vi]
    for v in variants do (
        CRS_token v.code
        CRS_token v.finish
        if v.mats.count != 6 do throw "Varyantta alti materyal alani olmali."
        local name = toLower (v.finish + "_" + v.code)
        if findItem names name > 0 do throw ("Tekrarlanan cikti kodu: " + v.code)
        append names name
        for i in d.activeRoles do CRS_material d v.mats[i]
    )
    CRS_nodes d.receivers
    local outputs = #()
    for v in variants do for ci in cameraIndices do (
        local name = toLower (v.finish + "/" + d.product + v.code + d.cameras[ci].number as string)
        if findItem outputs name > 0 do throw ("Cikti adi cakismasi: " + name)
        append outputs name
    )
    local missing = CRS_missing d variants
    if missing.count > 0 do throw ("Kullanilan varyant materyalinde eksik doku:\n" + missing[1])
    true
)
fn CRS_buildJobs d variantIndices cameraIndices = (
    CRS_check d variantIndices cameraIndices
    d.jobs = #()
    local signatures = #()
    for ci in cameraIndices do for vi in variantIndices do (
        local v = d.variants[vi]
        local sig = ci as string
        for role in d.activeRoles do sig += "|" + v.mats[role]
        if findItem signatures sig == 0 do (
            append signatures sig
            append d.jobs (CRS_Job id:("j" + (d.jobs.count+1) as string) variantIndex:vi cameraIndex:ci)
        )
    )
    d.jobs
)
fn CRS_saveRef doc parent r = (
    local el = CRS_child doc parent "node"
    CRS_attr el "handle" r.handle; CRS_attr el "name" r.label; CRS_attr el "class" r.kind
    el
)
fn CRS_readRef el = CRS_Ref handle:((CRS_get el "handle") as integer) label:(CRS_get el "name") kind:(CRS_get el "class")
fn CRS_saveProfile d path libraryPath = (
    local lib = materialLibrary()
    for p in d.palette do append lib p.mtl
    if not (saveTempMaterialLibrary lib libraryPath) do throw "Materyal kutuphanesi kaydedilemedi."
    local doc = CRS_xml()
    local root = CRS_child doc doc "ceneyra"
    CRS_attr root "version" 1; CRS_attr root "product" d.product
    CRS_attr root "scene" d.scene; CRS_attr root "frame" d.frameTicks
    for prop in #(#width,#height,#quality,#mode,#masks) do CRS_attr root (prop as string) (getProperty d prop)
    local palette = CRS_child doc root "palette"
    for p in d.palette do (local e = CRS_child doc palette "material"; CRS_attr e "key" p.key; CRS_attr e "label" p.label)
    local bindings = CRS_child doc root "bindings"
    for i = 1 to d.bindings.count do (
        local b = d.bindings[i]
        local e = CRS_child doc bindings "binding"
        CRS_attr e "label" b.label; CRS_attr e "faceID" b.faceID; CRS_attr e "active" (findItem d.activeRoles i > 0)
        for r in b.nodes do CRS_saveRef doc e r
    )
    local receivers = CRS_child doc root "receivers"
    for r in d.receivers do CRS_saveRef doc receivers r
    local variants = CRS_child doc root "variants"
    for v in d.variants do (
        local e = CRS_child doc variants "variant"
        CRS_attr e "code" v.code; CRS_attr e "label" v.label; CRS_attr e "finish" v.finish
        for i = 1 to v.mats.count do CRS_attr e ("m"+i as string) v.mats[i]
    )
    local cameras = CRS_child doc root "cameras"
    for c in d.cameras do (local e = CRS_child doc cameras "camera"; CRS_attr e "number" c.number; CRS_saveRef doc e c.node)
    CRS_writeXml doc path
)
fn CRS_readProfile path libraryPath = (
    local doc = CRS_loadXml path
    local root = doc.DocumentElement
    if root.Name != "ceneyra" or CRS_get root "version" != "1" do throw "Desteklenmeyen profil."
    local lib = loadTempMaterialLibrary libraryPath
    if lib == undefined do throw "Materyal kutuphanesi acilamadi."
    local d = CRS_Model product:(CRS_get root "product") scene:(CRS_get root "scene") frameTicks:((CRS_get root "frame") as integer)
    for prop in #(#width,#height,#quality,#mode) do setProperty d prop ((CRS_get root (prop as string)) as integer)
    d.masks = CRS_get root "masks" == "true"
    local i = 0
    for e in CRS_elements root "palette/material" do (
        i += 1
        if i > lib.count do throw "Profil ve materyal kutuphanesi uyusmuyor."
        append d.palette (CRS_Swatch key:(CRS_get e "key") label:(CRS_get e "label") mtl:lib[i])
    )
    d.activeRoles = #()
    for e in CRS_elements root "bindings/binding" do (
        local b = CRS_Binding label:(CRS_get e "label") faceID:((CRS_get e "faceID") as integer)
        for r in CRS_elements e "node" do append b.nodes (CRS_readRef r)
        append d.bindings b
        if CRS_get e "active" == "true" do append d.activeRoles d.bindings.count
    )
    if d.bindings.count != 6 do throw "Profilde alti bolum olmali."
    for e in CRS_elements root "receivers/node" do append d.receivers (CRS_readRef e)
    for e in CRS_elements root "variants/variant" do (
        local v = CRS_Variant code:(CRS_get e "code") label:(CRS_get e "label") finish:(CRS_get e "finish")
        v.mats = for i = 1 to 6 collect CRS_get e ("m"+i as string)
        append d.variants v
    )
    for e in CRS_elements root "cameras/camera" do append d.cameras (CRS_Camera number:((CRS_get e "number") as integer) node:(CRS_readRef (e.SelectSingleNode "node")))
    d
)
