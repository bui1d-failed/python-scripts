import ctypes
from ctypes import wintypes
import sys

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CreateMutex = kernel32.CreateMutexW
CreateMutex.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
CreateMutex.restype = wintypes.HANDLE

GetLastError = kernel32.GetLastError
GetLastError.restype = wintypes.DWORD

mutex_name = "ROBLOX_singletonEvent"

handle = CreateMutex(None, False, mutex_name)

error = GetLastError()
if error == 183:
    sys.exit(0)
else:
    print("done.")


input("Press enter continue...")
