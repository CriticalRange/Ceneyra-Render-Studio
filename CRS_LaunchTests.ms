fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Core.ms")
fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Engine.ms")
(
    local f = createFile (CRS_join CRS_Root "launch-test-results.txt") encoding:#utf8
    try (
        fn CRS_testScene = ( local path = (dotNetClass "System.Environment").GetEnvironmentVariable "CRS_TEST_SCENE"; if path == undefined or path == "" do throw "Set CRS_TEST_SCENE to a disposable scene copy before running tests."; if not doesFileExist path do throw ("CRS_TEST_SCENE not found: " + path); path )
        fn check value message = (if not value do throw ("FAIL: " + message))
        check (loadMaxFile (CRS_testScene()) quiet:true) "load copy"
        local d = CRS_seedKA1546()
        d.width = 120; d.height = 180; d.quality = 1; d.mode = 2; d.masks = true; d.activeRoles = #(2)
        CRS_buildJobs d #(2,3) #(1)
        local dir = CRS_makeRun d (CRS_join CRS_Root "launch-tests")
        format "RUN %\n" dir to:f; flush f
        CRS_control dir "stop"
        local p = CRS_launch dir
        check (p.WaitForExit 240000) "stop worker exited"
        local status = (CRS_loadXml (CRS_join dir "status.xml")).DocumentElement
        check (CRS_get status "state" == "stopped") "stop before first job"
        check (CRS_get status "done" == "0") "stop wrote no completed jobs"
        format "PASS separate worker launch / stop\n" to:f; flush f
        CRS_control dir "run"
        p = CRS_launch dir
        check (p.WaitForExit 240000) "render worker exited"
        check (p.ExitCode == 0) "worker exit success"
        status = (CRS_loadXml (CRS_join dir "status.xml")).DocumentElement
        check (CRS_get status "state" == "completed") "resume finished"
        check (CRS_get status "done" == "2") "two patches completed"
        for job in d.jobs do (
            local image = CRS_verifyDone dir job
            local b = openBitmap image
            local c = (getPixels b [0,0] 1)[1]
            check (c.r < 1 and c.g < 1 and c.b < 1) "mask exterior clear"
            close b
        )
        format "PASS resume / two real patches / cleared exterior / output hashes\n" to:f
        format "ALL LAUNCH TESTS PASSED\n" to:f
    ) catch (format "ERROR %\nSTACK %\n" (getCurrentException()) (getCurrentExceptionStackTrace()) to:f)
    close f
)
