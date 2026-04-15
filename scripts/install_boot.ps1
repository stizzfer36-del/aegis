$repo = (Resolve-Path "$PSScriptRoot\..").Path
schtasks /Create /TN "AEGIS Chat" /SC ONLOGON /TR "python $repo\chat.py" /F
schtasks /Create /TN "AEGIS Lens" /SC ONLOGON /TR "cmd /c cd /d $repo\lens && npm start" /F
Write-Host "Scheduled tasks created."
