global CRS_UI, CRS_Window
try (closeRolloutFloater CRS_Window) catch()
try (destroyDialog CRS_UI) catch()
fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Core.ms")
fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Engine.ms")
fileIn ((getFilenamePath (getSourceFileName())) + "CRS_UI.ms")
CRS_Window = newRolloutFloater "CENEYRA | Render Stüdyosu" 1210 760
addRollout CRS_UI CRS_Window rolledUp:false
