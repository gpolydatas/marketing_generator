!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "Marketing Content Generator"
OutFile "MarketingContentGeneratorSetup.exe"
InstallDir "$PROGRAMFILES\MarketingContentGenerator"

RequestExecutionLevel admin

!define PYTHON_URL "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
!define PYTHON_INSTALLER "python-installer.exe"

; Modern UI Configuration
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Main Application" SecMain
    SetOutPath "$INSTDIR"
    
    ; Check for Python and install if needed
    Call CheckAndInstallPython
    
    ; Create batch file with the ACTUAL install directory
; Create batch file with simpler admin elevation
	FileOpen $0 "$INSTDIR\MarketingContentGenerator.bat" w
	FileWrite $0 "@echo off$\r$\n"
	FileWrite $0 "$\r$\n"
	FileWrite $0 ":: Check for admin rights$\r$\n"
	FileWrite $0 "net session >nul 2>&1$\r$\n"
	FileWrite $0 "if %errorlevel% neq 0 ($\r$\n"
	FileWrite $0 "    echo Requesting administrator privileges...$\r$\n"
	FileWrite $0 "    powershell -Command $\"Start-Process -FilePath '%~s0' -Verb RunAs$\"$\r$\n"
	FileWrite $0 "    exit /b$\r$\n"
	FileWrite $0 ")$\r$\n"
	FileWrite $0 "$\r$\n"
	FileWrite $0 "cd /d $\"$INSTDIR$\"$\r$\n"
	FileWrite $0 "echo Starting Marketing Content Generator...$\r$\n"
	FileWrite $0 "streamlit run $\"launcher.py$\"$\r$\n"
	FileWrite $0 "if errorlevel 1 ($\r$\n"
	FileWrite $0 "    echo.$\r$\n"
	FileWrite $0 "    echo Application exited with error.$\r$\n"
	FileWrite $0 "    pause$\r$\n"
	FileWrite $0 ")$\r$\n"
	FileClose $0
    
    ; Install your application files
    File "*.py"
    File "*.yaml"
    File "requirements.txt"
    
    ; Install dependencies during setup
    Call InstallDependencies
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\Marketing Content Generator"
    CreateShortcut "$SMPROGRAMS\Marketing Content Generator\Marketing Content Generator.lnk" "$INSTDIR\MarketingContentGenerator.bat" "" "$INSTDIR\MarketingContentGenerator.bat" 0
    CreateShortcut "$DESKTOP\Marketing Content Generator.lnk" "$INSTDIR\MarketingContentGenerator.bat" "" "$INSTDIR\MarketingContentGenerator.bat" 0
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Write registry entries for Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MarketingContentGenerator" \
        "DisplayName" "Marketing Content Generator"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MarketingContentGenerator" \
        "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MarketingContentGenerator" \
        "Publisher" "Your Company Name"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MarketingContentGenerator" \
        "DisplayVersion" "1.0.0"
SectionEnd

Function CheckAndInstallPython
    DetailPrint "Checking for existing Python installation..."
    
    ; Method 1: Check if 'python' command works in PATH
    nsExec::ExecToStack 'python --version'
    Pop $0
    Pop $1
    ${If} $0 == 0
        DetailPrint "Found Python in PATH: $1"
        Return
    ${EndIf}
    
    ; Python not found, download and install
    DetailPrint "Python not found. Downloading Python 3.11..."
    NSISdl::download /TIMEOUT=30000 "${PYTHON_URL}" "${PYTHON_INSTALLER}"
    Pop $0
    ${If} $0 != "success"
        MessageBox MB_OK "Failed to download Python installer. Please install Python manually from python.org"
        Abort
    ${EndIf}
    
    DetailPrint "Installing Python..."
    ExecWait '"${PYTHON_INSTALLER}" /quiet InstallAllUsers=1 PrependPath=1' $0
    ${If} $0 != 0
        MessageBox MB_OK "Python installation failed with error: $0"
        Abort
    ${EndIf}
    
    DetailPrint "Python installed successfully"
FunctionEnd

Function InstallDependencies
    DetailPrint "Installing Python dependencies..."
    
    ; Install requirements ONCE during setup
    nsExec::ExecToStack 'python -m pip install -r "$INSTDIR\requirements.txt"'
    Pop $0
    Pop $1
    
    ${If} $0 != 0
        DetailPrint "Pip install output: $1"
        MessageBox MB_OK|MB_ICONEXCLAMATION "Some dependencies failed to install. The application may not work correctly."
    ${Else}
        DetailPrint "Dependencies installed successfully"
    ${EndIf}
FunctionEnd

Section "Uninstall"
    ; Remove shortcuts
    Delete "$SMPROGRAMS\Marketing Content Generator\Marketing Content Generator.lnk"
    Delete "$DESKTOP\Marketing Content Generator.lnk"
    RMDir "$SMPROGRAMS\Marketing Content Generator"
    
    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MarketingContentGenerator"
    
    ; Remove installation directory
    RMDir /r "$INSTDIR"
SectionEnd

Function .onInit
    ; Check if running as admin
    UserInfo::GetAccountType
    pop $0
    ${If} $0 != "admin"
        MessageBox MB_OK|MB_ICONEXCLAMATION "This installer requires administrator privileges."
        SetErrorLevel 740 ; ERROR_ELEVATION_REQUIRED
        Quit
    ${EndIf}
FunctionEnd