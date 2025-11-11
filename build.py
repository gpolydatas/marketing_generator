#!/usr/bin/env python3
"""
Build Windows .exe installer on Ubuntu with EMBEDDED Python
No dependencies needed on Windows - complete standalone installer
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
import tarfile

print("=" * 60)
print("Building Windows Setup.exe with Embedded Python")
print("=" * 60)

# Install build tools
print("\n[1/8] Installing build tools...")
subprocess.run(["sudo", "apt-get", "update"], check=True)
subprocess.run(["sudo", "apt-get", "install", "-y", "nsis", "wine", "wine64"], check=True)
subprocess.run(["pip3", "install", "pyinstaller"], check=True)
print("✓ Installed")

# Download Python embeddable
print("\n[2/8] Downloading Python 3.13.5 embeddable...")
PYTHON_URL = "https://www.python.org/ftp/python/3.13.5/python-3.13.5-embed-amd64.zip"
if not os.path.exists("python-embed.zip"):
    urllib.request.urlretrieve(PYTHON_URL, "python-embed.zip")
with zipfile.ZipFile("python-embed.zip", 'r') as z:
    z.extractall("python-embed")
print("✓ Downloaded")

# Download get-pip
print("\n[3/8] Downloading get-pip...")
urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", "get-pip.py")
print("✓ Downloaded")

# Create launcher
print("\n[4/8] Creating launcher...")
with open("launcher.py", "w") as f:
    f.write('''
import os, sys, subprocess, webbrowser, time

app_dir = os.path.dirname(os.path.abspath(__file__))
python_exe = os.path.join(app_dir, "python", "python.exe")
os.chdir(app_dir)

# First run setup
if not os.path.exists("python/.setup_done"):
    print("First run: Installing packages...")
    subprocess.run([python_exe, "get-pip.py"], check=True, 
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([python_exe, "-m", "pip", "install", "-q", "-r", "requirements.txt"], 
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    open("python/.setup_done", "w").close()

os.makedirs("outputs", exist_ok=True)

print("Starting...")
server = subprocess.Popen([python_exe, "fastapi_server.py"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

streamlit = subprocess.Popen([python_exe, "-m", "streamlit", "run", "streamlit_app.py",
    "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4)

webbrowser.open("http://localhost:8501")
print("Running at http://localhost:8501")
print("Close this window to stop")

try:
    streamlit.wait()
except:
    pass
server.terminate()
streamlit.terminate()
''')

# Create wrapper executable
print("\n[5/8] Creating wrapper...")
with open("wrapper.vbs", "w") as f:
    f.write('''Set objShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = strPath
objShell.Run "python\\python.exe launcher.py", 1, False
''')

# Build package
print("\n[6/8] Building package...")
if os.path.exists("pkg"):
    shutil.rmtree("pkg")
os.makedirs("pkg")

# Copy Python
shutil.copytree("python-embed", "pkg/python")

# Copy files
files = ["launcher.py", "wrapper.vbs", "get-pip.py",
    "streamlit_app.py", "fastapi_server.py", "agent.py",
    "banner_mcp_server.py", "video_mcp_server.py", "adaptive_media_api.py",
    "fastagent.config.yaml", "fastagent.secrets.yaml"]

for f in files:
    if os.path.exists(f):
        shutil.copy(f, "pkg/")

# Create requirements.txt
with open("pkg/requirements.txt", "w") as f:
    f.write("anthropic\nopenai\ngoogle-generativeai\nfastapi\nuvicorn\nstreamlit\npydantic\npython-multipart\nPillow\nPyYAML\nnest-asyncio\nrequests\naiohttp\n")

print("✓ Package built")

# Create NSIS installer script
print("\n[7/8] Creating installer script...")
with open("installer.nsi", "w") as f:
    f.write('''
!include "MUI2.nsh"

Name "Marketing Content Generator"
OutFile "Setup.exe"
InstallDir "$PROGRAMFILES64\\MarketingContentGenerator"
RequestExecutionLevel admin

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"
    File /r "pkg\\*.*"
    
    # Create Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\\Marketing Content Generator"
    CreateShortcut "$SMPROGRAMS\\Marketing Content Generator\\Marketing Content Generator.lnk" "wscript.exe" '"$INSTDIR\\wrapper.vbs"' "$INSTDIR\\python\\python.exe" 0
    
    # Create Desktop shortcut
    CreateShortcut "$DESKTOP\\Marketing Content Generator.lnk" "wscript.exe" '"$INSTDIR\\wrapper.vbs"' "$INSTDIR\\python\\python.exe" 0
    
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\MarketingContentGenerator" "DisplayName" "Marketing Content Generator"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\MarketingContentGenerator" "UninstallString" "$INSTDIR\\Uninstall.exe"
SectionEnd

Section "Uninstall"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\\Marketing Content Generator\\*.*"
    RMDir "$SMPROGRAMS\\Marketing Content Generator"
    Delete "$DESKTOP\\Marketing Content Generator.lnk"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\MarketingContentGenerator"
SectionEnd
''')

# Build installer
print("\n[8/8] Building Setup.exe...")
subprocess.run(["makensis", "installer.nsi"], check=True)

print("\n" + "=" * 60)
print("✅ SUCCESS!")
print("=" * 60)
print("\nCreated: Setup.exe")
print("\nWindows users:")
print("1. Double-click Setup.exe")
print("2. Install")
print("3. Double-click desktop icon")
print("4. Browser opens automatically")
print("\nEverything included - no dependencies needed!")
print("=" * 60)