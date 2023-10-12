import subprocess
import pwinput

def get_pass(text, default):
    deftext = default[:4] + "..." if default else ""
    return pwinput.pwinput(f"{text} [{deftext}]: ") or default

def get_input(text, default):
    return input(f"{text} [{default or ''}]: ") or default

seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
def convert_to_seconds(s):
    return int(s[:-1]) * seconds_per_unit[s[-1]]

def shell(command, timeout=10):
        
    _process = subprocess.Popen(
        command,
        shell=True,
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        # creationflags=DETACHED_PROCESS
    )

    try:
        stdout, stderr = _process.communicate(timeout=timeout)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return[255, None]

    return [_process.returncode, stdout]
