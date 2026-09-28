fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Core.ms")
fileIn ((getFilenamePath (getSourceFileName())) + "CRS_Engine.ms")
(
    local dir = maxOps.mxsCmdLineArgs[#jobDir]
    if dir == undefined do throw "jobDir parametresi gerekli."
    if not (CRS_runQueue dir) do throw "Kuyruk basarisiz. status.xml dosyasini kontrol edin."
)
