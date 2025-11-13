from threading import Thread
from datetime import datetime
import time
# import the three bots into this file
from anaplasma_files.anaplasma_bot import start_anaplasma
from audrey_files.audrey_bot import start_audrey
from athena_files.athena_bot import start_athena
from giardia_files.giardia_bot import start_giardia
from strep_files.strep_bot import start_strep
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
    # targets = []
    threads = []
    print("**select bots**")
    print("1. athena")
    print("2. audrey")
    print("3. anaplasma")
    print("4. giardiasis")
    print("5. strep")
    selection()
    try:
        for  target in targets:
            print(f"selected: {target.__name__.replace("start_", "") }")
        
        codes = []
        username = input('Enter your SOM username ("first_name.last_name"):')
        passcode = input('Enter your RSA passcode:')
        codes.append(passcode)
        for _ in range(len(targets) - 1):
            passcode = input('Enter your RSA passcode for the next bot:')    
            codes.append(passcode)
        for i in range(len(targets)):
            # use the credentials and pass it as a param into each both
            # make sure the bots are triggered each using a thread
            thread = Thread(target=targets[i], args=(username, codes[i]))
            threads.append(thread)
            thread.start()


            time.sleep(30)
            # log the errors into a file
            # [01/08/2025]
            # BOTname - error information
        for thread in threads:
            thread.join()

    except Exception as e:
        with open("error_log.txt", "a") as log:
            log.write(f"{datetime.now().date().strftime('%m_%d_%Y')} - {str(e)}")


if __name__ == '__main__':
    print("waking bots...")
    run_bots()
    print("putting bots to sleep...")
