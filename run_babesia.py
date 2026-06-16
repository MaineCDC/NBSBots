"""One-off runner: launch Chrome (debug port 9223) and run babesia in
record-only mode against the NBS test site. Credentials passed via env vars
BABESIA_USER / BABESIA_PASS so they aren't hard-coded."""
import os
from threading import Event

from start_bots import launch_chrome
from babesia_files.babesia_bot import start_babesia

if __name__ == "__main__":
    username = os.environ["BABESIA_USER"]
    passcode = os.environ["BABESIA_PASS"]

    print("launching chrome...")
    chrome_process = launch_chrome()

    login_complete = Event()
    print("starting babesia (record-only)...")
    start_babesia(username, passcode, login_complete, False)
    print("babesia run finished.")
