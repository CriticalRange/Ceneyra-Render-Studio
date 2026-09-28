fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Core.ms")
fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Engine.ms")
global CRS_UI
(
    local root = getFilenamePath (getSourceFileName())
    local f = createFile (root + "test-results.txt") encoding:#utf8
    try (
        fileIn (root + "CRS_Core.ms")
        fn CRS_testScene = ( local path = (dotNetClass "System.Environment").GetEnvironmentVariable "CRS_TEST_SCENE"; if path == undefined or path == "" do throw "Set CRS_TEST_SCENE to a disposable scene copy before running tests."; if not doesFileExist path do throw ("CRS_TEST_SCENE not found: " + path); path )
        fn assertTrue value message = (if not value do throw ("FAIL: " + message))
        format "PASS core compile\n" to:f
        local loaded = loadMaxFile (CRS_testScene()) quiet:true
        assertTrue loaded "copy loaded"
        local d = CRS_seedKA1546()
        assertTrue (d.bindings[2].nodes.count == 4) "four doors"
        assertTrue (d.cameras.count == 2) "two cameras, no targets"
        assertTrue (d.variants.count == 10) "ten catalogue variants"
        local door = maxOps.getNodeByHandle 36662
        local original = door.material
        local laser = getSubMtl original 2
        CRS_apply d d.variants[2]
        assertTrue ((getSubMtl door.material 2) == laser or (getSubMtl door.material 2).name == laser.name) "laser kept"
        assertTrue ((getSubMtl original 1).name == "21 - Default") "original material untouched"
        CRS_restore d
        assertTrue (door.material == original) "material references restored"
        CRS_buildJobs d #(1,2,3,4,5,6,7,8,9,10) #(1,2)
        assertTrue (d.jobs.count == 20) "full queue"
        d.activeRoles = #(3)
        CRS_buildJobs d #(1,2,3,4,5,6,7,8,9,10) #(1,2)
        assertTrue (d.jobs.count == 4) "plexi-only queue deduplicated"
        d.activeRoles = #(1,2,3,4,5)
        local path = CRS_join root "tests"
        CRS_mkdir path
        CRS_saveProfile d (CRS_join path "roundtrip.xml") (CRS_join path "roundtrip.mat")
        local restored = CRS_readProfile (CRS_join path "roundtrip.xml") (CRS_join path "roundtrip.mat")
        assertTrue (restored.variants[3].code == "BTG") "XML code roundtrip"
        assertTrue (restored.bindings[2].faceID == 1) "XML faceID roundtrip"
        assertTrue (restored.palette.count == 7) "material library roundtrip"
        local countBefore = door.modifiers.count
        CRS_uvw (CRS_nodes d.bindings[2].nodes) channel:1
        CRS_uvw (CRS_nodes d.bindings[2].nodes) channel:1
        assertTrue (door.modifiers.count == countBefore+1) "UVW idempotent"
        local mesh = snapshotAsMesh door
        assertTrue (meshop.getMapSupport mesh 1) "UVW output channel"
        free mesh
        local n = CRS_resolve d.bindings[2].nodes[1]
        assertTrue (n == door) "reference match"
        local blocked = false
        try (CRS_token "../escape") catch (blocked = true)
        assertTrue blocked "unsafe filenames blocked"
        d.activeRoles = #(6)
        local laserVariant = CRS_Variant code:"TEST" label:"Laser" finish:"TEST" mats:#("KEEP","KEEP","KEEP","KEEP","KEEP","LASER")
        CRS_apply d laserVariant
        assertTrue ((getSubMtl door.material 2).name == (CRS_material d "LASER").name) "laser slot replace"
        assertTrue ((getSubMtl door.material 1).name == "21 - Default") "laser edit preserves surface"
        CRS_restore d
        d.activeRoles = #(1,2,3,4,5)
        CRS_uvw (CRS_nodes d.bindings[2].nodes) channel:2
        mesh = snapshotAsMesh door
        assertTrue (meshop.getMapSupport mesh 2) "independent laser UV channel"
        assertTrue (mesh.numfaces == 268) "face topology unchanged"
        free mesh
        blocked = false
        try (CRS_uvw #((CRS_nodes d.bindings[3].nodes)[1])) catch (blocked = true)
        assertTrue blocked "external instances protected"
        local stale = CRS_Ref handle:999999 label:"missing" kind:"Editable_mesh"
        blocked = false
        try (CRS_resolve stale) catch (blocked = true)
        assertTrue blocked "stale bindings blocked"
        local oldCode = d.variants[2].code
        d.variants[2].code = d.variants[1].code
        blocked = false
        try (CRS_check d #(1,2) #(1)) catch (blocked = true)
        d.variants[2].code = oldCode
        assertTrue blocked "duplicate output codes blocked"
        local oldKey = d.variants[1].mats[1]
        d.variants[1].mats[1] = "DOES_NOT_EXIST"
        blocked = false
        try (CRS_check d #(1) #(1)) catch (blocked = true)
        d.variants[1].mats[1] = oldKey
        assertTrue blocked "missing materials blocked"
        format "PASS bindings, materials, laser preservation, queue dedup, XML+MAT, UVW, path validation\n" to:f
        format "PASS laser-only edits, channel 2, topology, instance protection, stale nodes, duplicate codes, missing materials\n" to:f
        for p in getPropNames renderers.current where matchPattern (p as string) pattern:"*prev*" do format "PROPERTY % = %\n" p (getProperty renderers.current p) to:f
        fileIn (root + "CRS_UI.ms")
        format "PASS UI compile\n" to:f
        CRS_Data = d
        createDialog CRS_UI
        assertTrue (CRS_UI.variants.Items.Count == 10) "UI populated"
        assertTrue (CRS_UI.roles.Items.Count == 6) "UI roles"
        try (
            windows.processPostedMessages()
            local screen = windows.snapshot CRS_UI.hwnd
            screen.filename = CRS_join path "panel.png"
            save screen
            close screen
        ) catch (format "UI screenshot unavailable: %\n" (getCurrentException()) to:f)
        destroyDialog CRS_UI
        format "PASS UI open, populate, close\n" to:f
        format "ALL TESTS PASSED\n" to:f
    ) catch (format "ERROR %\nSTACK %\n" (getCurrentException()) (getCurrentExceptionStackTrace()) to:f)
    close f
)
