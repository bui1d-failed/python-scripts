import ctypes
import ctypes.wintypes as wintypes
import requests

config = {
    "automatic_update": True,
}

# You can update this manually for faster performance, if you dont want automatic offsets updates
offsets = {
    "TaskSchedulerMaxFPS": 0x1B0,
    "TaskSchedulerPointer": 0x78E3008
}

OFFSETS_URL = "https://offsets.ntgetwritewatch.workers.dev/offsets.json" # not my own offsets and website

if config["automatic_update"]:
    def fetch_offsets():
        resp = requests.get(OFFSETS_URL)
        resp.raise_for_status()
        data = resp.json()

        offsets = {}
        for index, value in data.items():
            if isinstance(value, str) and value.startswith("0x"):
                offsets[index] = int(value, 16)
            else:
                offsets[index] = value
        return offsets

    offsets = fetch_offsets()

if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_ulonglong):
    ULONG_PTR = ctypes.c_ulonglong
else:
    ULONG_PTR = ctypes.c_ulong

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
TH32CS_SNAPMODULE    = 0x00000008
TH32CS_SNAPMODULE32  = 0x00000010

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ULONG_PTR),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.CHAR * wintypes.MAX_PATH),
    ]

CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
Process32First = kernel32.Process32First
Process32Next = kernel32.Process32Next
OpenProcess = kernel32.OpenProcess

class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.CHAR * 256),
        ("szExePath", wintypes.CHAR * wintypes.MAX_PATH),
    ]

CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
Module32First = kernel32.Module32First
Module32Next = kernel32.Module32Next

def get_pid_by_name(target_name: str):
    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

    if not Process32First(snapshot, ctypes.byref(entry)):
        return None

    while True:
        exe_name = entry.szExeFile.decode(errors="ignore")
        if exe_name.lower() == target_name.lower():
            return entry.th32ProcessID
        if not Process32Next(snapshot, ctypes.byref(entry)):
            break
    return None

def get_window_title_by_pid(pid: int):
    titles = []

    def enum_proc(hwnd, lparam):
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value == pid:
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                titles.append(buffer.value)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    enum_func = WNDENUMPROC(enum_proc)
    user32.EnumWindows(enum_func, 0)

    return titles

def get_base_module(pid: int):
    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    me32 = MODULEENTRY32()
    me32.dwSize = ctypes.sizeof(MODULEENTRY32)

    if not Module32First(snapshot, ctypes.byref(me32)):
        return None

    base_addr = ctypes.addressof(me32.modBaseAddr.contents)
    module_name = me32.szModule.decode(errors="ignore")
    exe_path = me32.szExePath.decode(errors="ignore")

    return base_addr, module_name, exe_path

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)
]
ReadProcessMemory.restype = wintypes.BOOL

WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.LPCVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)
]
WriteProcessMemory.restype = wintypes.BOOL

class ProcessMemory:
    def __init__(self, handle):
        self.handle = handle

    def read_uintptr(self, address: int) -> int:
        size = ctypes.sizeof(ctypes.c_void_p)
        buffer = (ctypes.c_byte * size)()
        read = ctypes.c_size_t(0)

        success = ReadProcessMemory(self.handle,
                                    ctypes.c_void_p(address),
                                    buffer,
                                    size,
                                    ctypes.byref(read))
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())

        if size == 8:
            return ctypes.c_uint64.from_buffer(buffer).value
        else:
            return ctypes.c_uint32.from_buffer(buffer).value

    def read_double(self, address: int) -> float:
        buf = ctypes.c_double()
        read = ctypes.c_size_t(0)
        success = ReadProcessMemory(self.handle,
                                    ctypes.c_void_p(address),
                                    ctypes.byref(buf),
                                    ctypes.sizeof(buf),
                                    ctypes.byref(read))
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.value

    def write_double(self, address: int, value: float):
        buf = ctypes.c_double(value)
        written = ctypes.c_size_t(0)
        success = WriteProcessMemory(self.handle,
                                     ctypes.c_void_p(address),
                                     ctypes.byref(buf),
                                     ctypes.sizeof(buf),
                                     ctypes.byref(written))
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())
        return written.value

print("[+] Press enter to uncap FPS")
while True:
    targetFPS = 9999.0
    userSetFps = input("\n[?] Set New FPS: ")
    if userSetFps.strip():
        try:
            targetFPS = float(userSetFps)
        except ValueError:
            print("[!] Invalid FPS")
            exit()

    pid = get_pid_by_name("RobloxPlayerBeta.exe")
    if not pid:
        print("Exiting, no game process found")
        exit()

    print("\n[*] Process ID:", pid)

    handle = OpenProcess(PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION, False, pid)
    pm = ProcessMemory(handle)

    base_addr, module_name, exe_path = get_base_module(pid)
    task_scheduler_ptr = pm.read_uintptr(base_addr + offsets["TaskSchedulerPointer"])

    # write memory
    pm.write_double(task_scheduler_ptr + offsets["TaskSchedulerMaxFPS"], 1.0 / targetFPS)
    print("[+] Write success:", targetFPS)

    newfps = pm.read_double(task_scheduler_ptr + offsets["TaskSchedulerMaxFPS"])
    print("[+] New FPS:", 1.0 / newfps)
