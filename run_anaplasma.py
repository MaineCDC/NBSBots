"""One-off runner: run the Anaplasma bot against PRODUCTION NBS, reusing the
Chrome ALREADY running on debug port 9223 and its warm (already-logged-in)
session. It does NOT relaunch Chrome -- that would restart the browser and could
drop the RSA SecurID session. Just log in by hand in the open Chrome window
first, then run this.

The Anaplasma driver connects to the existing Chrome via debuggerAddress, and
log_in() now detects the already-warm session and skips the RSA form, so no
passcode is needed here. ANAPLASMA_USER / ANAPLASMA_PASS are optional and only
used as a fallback if the session is NOT warm.
"""
import os
from threading import Event

from anaplasma_files.anaplasma_bot import start_anaplasma

if __name__ == "__main__":
    # Only used if the session turns out not to be warm; harmless placeholders
    # otherwise since log_in() skips the form when already authenticated.
    username = os.environ.get("ANAPLASMA_USER", "x")
    passcode = os.environ.get("ANAPLASMA_PASS", "x")

    login_complete = Event()
    print("starting anaplasma (production, reusing warm session)...")
    start_anaplasma(username, passcode, login_complete, False)
    print("anaplasma run finished.")
