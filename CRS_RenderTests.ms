fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Core.ms")
fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Engine.ms")
(
    local root = getFilenamePath (getSourceFileName())
    local f = createFile (root + "render-test-results.txt") encoding:#utf8
    try (
        fn CRS_testScene = ( local path = (dotNetClass "System.Environment").GetEnvironmentVariable "CRS_TEST_SCENE"; if path == undefined or path == "" do throw "Set CRS_TEST_SCENE to a disposable scene copy before running tests."; if not doesFileExist path do throw ("CRS_TEST_SCENE not found: " + path); path )
        fn check value message = (if not value do throw ("FAIL: " + message))
        check (loadMaxFile (CRS_testScene()) quiet:true) "load copy"
        local d = CRS_seedKA1546()
        CRS_uvw (CRS_nodes d.bindings[2].nodes) channel:1
        d.width = 160; d.height = 240; d.quality = 1; d.masks = true
        CRS_buildJobs d #(2) #(1)
        local dir = CRS_makeRun d (CRS_join root "render-tests")
        format "RUN %\n" dir to:f; flush f
        check (CRS_runQueue dir) "actual V-Ray full render"
        local image = CRS_verifyDone dir d.jobs[1]
        check (image != undefined) "completion marker"
        local b = openBitmap image
        check (b.width == 160 and b.height == 240) "render dimensions"
        close b
        format "PASS full render with two RGB mattes: %\n" image to:f; flush f
        local before = (dotNetClass "System.IO.File").GetLastWriteTimeUtc image
        check (CRS_runQueue dir) "resume completed queue"
        check ((dotNetClass "System.IO.File").GetLastWriteTimeUtc image == before) "resume skips finished image"
        format "PASS verified resume without overwrite\n" to:f; flush f
        check (loadMaxFile (CRS_testScene()) quiet:true) "reload copy"
        d = CRS_seedKA1546()
        d.width = 160; d.height = 240; d.quality = 1; d.mode = 2; d.masks = true; d.activeRoles = #(2)
        CRS_buildJobs d #(2) #(1)
        local patchDir = CRS_makeRun d (CRS_join root "render-tests")
        format "PATCH RUN %\n" patchDir to:f; flush f
        check (CRS_runQueue patchDir) "actual V-Ray Render Mask"
        local patch = CRS_verifyDone patchDir d.jobs[1]
        format "PASS mask patch: %\n" patch to:f
        format "ALL RENDER TESTS PASSED\n" to:f
    ) catch (format "ERROR %\nSTACK %\n" (getCurrentException()) (getCurrentExceptionStackTrace()) to:f)
    close f
)
