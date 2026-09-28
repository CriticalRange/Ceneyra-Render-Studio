fileIn ((getFilenamePath (getSourceFileName())) + "Ceneyra_Render_Studio.ms")
global CRS_GuiTestTimer
(
    local f = createFile (CRS_join CRS_Root "gui-test-results.txt") encoding:#utf8
    try (
        fn CRS_testScene = ( local path = (dotNetClass "System.Environment").GetEnvironmentVariable "CRS_TEST_SCENE"; if path == undefined or path == "" do throw "Set CRS_TEST_SCENE to a disposable scene copy before running tests."; if not doesFileExist path do throw ("CRS_TEST_SCENE not found: " + path); path )
        if not (loadMaxFile (CRS_testScene()) quiet:true) do throw "Copy did not load"
        local folder = CRS_mkdir (CRS_join CRS_Root "work")
        local target = CRS_join folder ("GUI_TEST_" + CRS_guid() + ".max")
        if not (saveMaxFile target useNewFile:true quiet:true) do throw "Test work copy failed"
        closeRolloutFloater CRS_Window
        CRS_Data = CRS_seedKA1546()
        CRS_Window = newRolloutFloater "CENEYRA | Render Studio" 1210 760
        addRollout CRS_UI CRS_Window rolledUp:false
        CRS_UI.variants.SelectedIndex = 2
        CRS_UI.viewportPreview()
        CRS_UI.detailsDialog()
        destroyDialog CRS_Details
        CRS_UI.spCamera.value = 3
        CRS_UI.btnCameraNo.pressed()
        if CRS_Data.cameras[1].number != 3 do throw "Camera numbering event failed"
        CRS_UI.spCamera.value = 1
        CRS_UI.btnCameraNo.pressed()
        CRS_UI.summarize()
        format "PASS launcher / scrollable panel / viewport preview / details / camera numbering / queue calculation\n" to:f
        global CRS_GuiCapture
        fn CRS_GuiCapture sender args = (
            CRS_GuiTestTimer.Stop()
            local f = createFile (CRS_join CRS_Root "gui-capture-results.txt") encoding:#utf8
            try (
                local b = windows.snapshot CRS_Window.hwnd
                b.filename = CRS_join CRS_Root "tests\\panel-live.png"
                save b
                close b
                format "PASS screenshot\n" to:f
            ) catch (format "ERROR %\n" (getCurrentException()) to:f)
            close f
            quitMax #noPrompt
        )
        CRS_GuiTestTimer = dotNetObject "System.Windows.Forms.Timer"
        CRS_GuiTestTimer.Interval = 5000
        dotNet.addEventHandler CRS_GuiTestTimer "Tick" CRS_GuiCapture
        CRS_GuiTestTimer.Start()
    ) catch (format "ERROR %\nSTACK %\n" (getCurrentException()) (getCurrentExceptionStackTrace()) to:f; close f; quitMax #noPrompt)
    close f
)
