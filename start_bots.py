from threading import Event
from datetime import datetime
import time, os
# import the three bots into this file
from anaplasma_files.anaplasma_bot import start_anaplasma
from audrey_files.audrey_bot import start_audrey
from athena_files.athena_bot import start_athena
from giardia_files.giardia_bot import start_giardia
from strep_files.strep_bot import start_strep
import subprocess
import socket
import atexit
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


CHROME_PORT = 9223
USER_DATA_DIR = os.getcwd() + r"\chrome-bot-profile"


def kill_bot_profile_chrome():
    """Terminate only Chrome processes using the bot profile dir.

    A prior run that crashed, was Ctrl-C'd, or got interrupted by sleep can leave
    a Chrome bound to USER_DATA_DIR alive. The next launch then forwards its args
    to that survivor and exits without ever opening the remote-debugging port,
    producing "Chrome didn't open port ...". We match on the profile path in the
    command line so the user's normal Chrome (a different --user-data-dir) is
    never touched.
    """
    # Match the profile by folder name; the full path may render with different
    # slashes in the command line, so the trailing dir name is the stable token.
    profile_token = os.path.basename(USER_DATA_DIR)  # "chrome-bot-profile"
    ps_command = (
        "Get-CimInstance Win32_Process -Filter \"name='chrome.exe'\" | "
        "Where-Object { $_.CommandLine -like '*" + profile_token + "*' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_command],
            timeout=30,
        )
    except Exception as e:
        print(f"kill_bot_profile_chrome: cleanup failed (continuing): {e}")


def clear_profile_locks():
    """Remove stale singleton/lock files that can block a fresh Chrome launch."""
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"):
        path = os.path.join(USER_DATA_DIR, name)
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            print(f"clear_profile_locks: could not remove {name} (continuing): {e}")


def find_chrome_binary():
    """Locate Chrome on the system. Adjust paths for your OS."""
    candidates = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        #"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",        # Windows
    ]
    for c in candidates:
        path = shutil.which(c) if "/" not in c and "\\" not in c else c
        if path:
            return path
    raise RuntimeError("Chrome not found")


def wait_for_port(port, host="127.0.0.1", timeout=30):
    """Block until Chrome's debug port is accepting connections."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    raise TimeoutError(f"Chrome didn't open port {port} in {timeout}s")


def launch_chrome():
    """Start Chrome with remote debugging enabled.

    Retries to survive a stale bot-profile Chrome left over from a prior run: if
    the debug port never opens (because a survivor stole our args and we exited),
    kill those leftovers, clear stale locks, and relaunch.
    """
    chrome = find_chrome_binary()
    print(f"Launching: {chrome}")
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

    # Reap the whole bot-profile Chrome tree on exit, not just our Popen handle.
    atexit.register(kill_bot_profile_chrome)

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        # Start from a clean profile so the new process actually owns it (and so
        # it doesn't forward its args to a survivor and exit without a port).
        kill_bot_profile_chrome()
        clear_profile_locks()

        process = subprocess.Popen(
            [
                chrome,
                f"--remote-debugging-port={CHROME_PORT}",
                f"--user-data-dir={USER_DATA_DIR}",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        try:
            wait_for_port(CHROME_PORT)
            return process
        except TimeoutError as e:
            print(f"launch_chrome: attempt {attempt}/{max_attempts} failed: {e}")
            if attempt == max_attempts:
                raise


# run the get credentials function
bots = {
    1: start_athena,
    2: start_audrey,
    3: start_anaplasma,
    4: start_giardia,
    5: start_strep
}
targets = []
def selection():
    select = input("Enter selections as space-separated numbers..: ")
    selected = map(int, select.split())

    for option in selected:
        if option in bots:
            targets.append(bots[option])
        else:
            print(f"Invalid selection {option}")
            targets.clear()
            selection()


def run_bots():
    print("**select bots**")
    print("1. athena")
    print("2. audrey")
    print("3. anaplasma")
    print("4. giardiasis")
    print("5. strep")
    selection()

    
    login_complete = Event()
    try:
        for target in targets:
            print(f"selected: {target.__name__.replace('start_', '') }")

        username = input('Enter your SOM username ("first_name.last_name"):')
        passcode = input('Enter your RSA passcode:')
        chrome_process = launch_chrome()

        # Run the selected bots SEQUENTIALLY, sharing one Chrome session: each bot
        # runs to completion (it ends itself once its queue has no more cases) and
        # only then does the next bot in the list start. The first bot performs the
        # login; the rest reuse the established session (is_logged_in=True). The
        # @error_handle decorator on each start_* already catches and logs per-bot
        # exceptions, so a bot that fails won't stop the chain -- we still move on
        # to the next one.
        for i, target in enumerate(targets):
            is_logged_in = i > 0  # first bot logs in, rest reuse the session
            name = target.__name__.replace('start_', '')
            print(f"starting bot {i + 1}/{len(targets)}: {name}")
            target(username, passcode, login_complete, is_logged_in)
            print(f"finished bot {name}; moving to the next bot...")

    except Exception as e:
        with open("error_log.txt", "a") as log:
            log.write(f"{datetime.now().date().strftime('%m_%d_%Y')} - {str(e)}")
    # finally:
    #     chrome_process.terminate()
    #     chrome_process.wait()


if __name__ == '__main__':
    print("waking bots...")
    run_bots()
    print("putting bots to sleep...")
