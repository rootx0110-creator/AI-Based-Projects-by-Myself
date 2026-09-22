/*
  Bundled detection rules for the Threat Actor TTP Profiler.
  Targets on-disk indicators commonly associated with commodity
  malware, RATs, C2 infrastructure and ransomware.
*/
rule win_obfuscated_powershell_payload
{
    meta:
        description = "Encoded / obfuscated PowerShell invocation strings"
    strings:
        $a = "powershell -enc"
        $b = "encodedcommand"
        $c = "Invoke-Expression"
        $d = "FromBase64String"
    condition:
        uint16(0) == 0x5A4D and 1 of them
}

rule generic_mimikatz_cred_access
{
    meta:
        description = "Credential dumping indicators (Mimikatz / sekurlsa)"
        reference = "MITRE ATT&CK T1003"
    strings:
        $a = "sekurlsa"
        $b = "logonpasswords"
        $c = "mimikatz"
        $d = "kerberos::"
        $e = "lsass"
    condition:
        uint16(0) == 0x5A4D and 2 of them
}

rule lsass_process_memory_dump
{
    meta:
        description = "LSASS memory access / minidump strings"
        reference = "MITRE ATT&CK T1003.001"
    strings:
        $a = "comsvcs.dll"
        $b = "minidump"
        $c = "lsass.dmp"
        $d = "MiniDumpWriteDump"
    condition:
        uint16(0) == 0x5A4D and (2 of them)
}

rule remote_thread_injection
{
    meta:
        description = "Process injection APIs (CreateRemoteThread family)"
        reference = "MITRE ATT&CK T1055"
    strings:
        $a = "CreateRemoteThread"
        $b = "VirtualAllocEx"
        $c = "WriteProcessMemory"
        $d = "SetThreadContext"
        $e = "NtCreateThreadEx"
    condition:
        uint16(0) == 0x5A4D and 2 of them
}

rule process_hollowing_present
{
    meta:
        description = "Process hollowing APIs"
        reference = "MITRE ATT&CK T1055.012"
    strings:
        $a = "ZwUnmapViewOfSection"
        $b = "NtUnmapViewOfSection"
        $c = "NtWriteVirtualMemory"
    condition:
        uint16(0) == 0x5A4D and any of them
}

rule c2_http_beacon
{
    meta:
        description = "HTTP-based C2 indicators"
        reference = "MITRE ATT&CK T1071.001"
    strings:
        $a = "HttpSendRequest"
        $b = "InternetOpen"
        $c = "WinHttpOpen"
        $d = "user-agent"
        $e = "Authorization: Basic"
    condition:
        3 of them
}

rule generic_socket_c2
{
    meta:
        description = "Raw socket C2 indicators"
        reference = "MITRE ATT&CK T1095 / T1071"
    strings:
        $a = "ws2_32"
        $b = "WSAStartup"
        $c = "socket"
        $d = "gethostbyname"
        $e = "connect"
    condition:
        uint16(0) == 0x5A4D and 2 of them
}

rule keylogging_api_set
{
    meta:
        description = "Keylogging API set (GetAsyncKeyState etc.)"
        reference = "MITRE ATT&CK T1056.001"
    strings:
        $a = "GetAsyncKeyState"
        $b = "SetWindowsHookEx"
        $c = "GetKeyboardState"
        $d = "WH_KEYBOARD_LL"
    condition:
        uint16(0) == 0x5A4D and 2 of them
}

rule screen_capture_api_set
{
    meta:
        description = "Screen capture API set"
        reference = "MITRE ATT&CK T1113"
    strings:
        $a = "BitBlt"
        $b = "CreateCompatibleDC"
        $c = "GetDC"
        $d = "StretchBlt"
        $e = "PrintWindow"
    condition:
        uint16(0) == 0x5A4D and 2 of them
}

rule anti_debug_anti_vm
{
    meta:
        description = "Debugger / sandbox evasion strings"
        reference = "MITRE ATT&CK T1622 / T1497"
    strings:
        $a = "IsDebuggerPresent"
        $b = "CheckRemoteDebuggerPresent"
        $c = "vmware"
        $d = "virtualbox"
        $e = "sandboxie"
        $f = "wireshark"
    condition:
        2 of them
}

rule schedule_persistence
{
    meta:
        description = "Scheduled task persistence"
        reference = "MITRE ATT&CK T1053.005"
    strings:
        $a = "schtasks"
        $b = "/create"
        $c = "\\Tasks\\"
        $d = "Task Scheduler"
    condition:
        uint16(0) == 0x5A4D and 2 of them
}

rule service_persistence
{
    meta:
        description = "Windows service creation"
        reference = "MITRE ATT&CK T1543.003"
    strings:
        $a = "CreateService"
        $b = "OpenSCManager"
        $c = "StartService"
        $d = "/system32/drivers"
    condition:
        uint16(0) == 0x5A4D and 2 of them
}

rule runkey_registry_persistence
{
    meta:
        description = "Registry Run key manipulation"
        reference = "MITRE ATT&CK T1547.001"
    strings:
        $a = "CurrentVersion\\Run"
        $b = "RegSetValueEx"
        $c = "RunOnce"
    condition:
        uint16(0) == 0x5A4D and any of them
}

rule ransomware_wannacry_family
{
    meta:
        description = "WannaCry / ransomware indicators"
        reference = "MITRE ATT&CK T1486 / T1490"
    strings:
        $a = "WanaCrypt0r"
        $b = "wncry"
        $c = "TaskDL.exe"
        $d = "mssecsvc.exe"
        $e = "VSSADMIN"
        $f = "deleteshadowcopy"
    condition:
        2 of them
}

rule generic_crypto_ransom
{
    meta:
        description = "Generic encryption-for-ransom indicators"
        reference = "MITRE ATT&CK T1486"
    strings:
        $a = "encrypt"
        $b = "decrypt"
        $c = "bitcoin"
        $d = ".locked"
        $e = "readme.txt"
        $f = "Recovery"
    condition:
        uint16(0) == 0x5A4D and 3 of them
}

rule filesystem_recovery_destruction
{
    meta:
        description = "System recovery disablement commands"
        reference = "MITRE ATT&CK T1490"
    strings:
        $a = "vssadmin"
        $b = "bcdedit"
        $c = "wbadmin"
        $d = "shadowcopy"
    condition:
        any of them
}

rule tool_transfer_certutil
{
    meta:
        description = "Certutil base64 tool transfer"
        reference = "MITRE ATT&CK T1140 / T1105"
    strings:
        $a = "certutil"
        $b = "-decode"
        $c = "-urlcache"
        $d = "bitsadmin"
    condition:
        any of them
}

rule wmi_execution
{
    meta:
        description = "WMI execution / query strings"
        reference = "MITRE ATT&CK T1047"
    strings:
        $a = "Win32_Process"
        $b = "root\\cimv2"
        $c = "WmiCreateProcess"
        $d = "wmic"
    condition:
        any of them
}

rule remote_access_tool
{
    meta:
        description = "Remote access software indicators"
        reference = "MITRE ATT&CK T1219"
    strings:
        $a = "teamviewer"
        $b = "anydesk"
        $c = "ammyy"
        $d = "radmin"
        $e = ".vnc"
    condition:
        any of them
}

rule packed_upx_section
{
    meta:
        description = "UPX packed binary"
        reference = "MITRE ATT&CK T1027"
    strings:
        $a = "UPX0"
        $b = "UPX1"
        $c = "UPX!"
    condition:
        uint16(0) == 0x5A4D and any of them
}

rule archive_collection
{
    meta:
        description = "Archive utilities for data staging"
        reference = "MITRE ATT&CK T1560"
    strings:
        $a = "7z.exe"
        $b = "winrar"
        $c = "rar a "
        $d = "tar.exe"
        $e = "zip a "
    condition:
        any of them
}

rule exfil_web_service
{
    meta:
        description = "Web service exfiltration endpoints"
        reference = "MITRE ATT&CK T1567"
    strings:
        $a = "pastebin.com"
        $b = "gist.github.com"
        $c = "transfer.sh"
        $d = "api.telegram.org"
        $e = "discordapp.com/api/webhooks"
        $f = "0x0.st"
    condition:
        any of them
}