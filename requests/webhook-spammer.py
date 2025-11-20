import requests
import time

session = requests.Session()
input_webhook = ""
input_delay = 0

input_webhook = input("webhook: ")
input_delay = input("delay (seconds): ")
input_mode = input("mode (1: @everyone 2: custom text): ")
if not (input_webhook or input_delay or input_mode):
    print("empty webhook / delay value")

while True:
    try:
        input_delay = float(input_delay)
        input_mode = int(input_mode)
        break
    except ValueError:
        print("invalid delay value")
        exit()

message = ""
if input_mode == 1:
    for _ in range(30):
        message += " @everyone @here"
elif input_mode == 2:
    message = input("message: ")
    if not message:
        print("invalid message content")
        exit()

data = {"content": message}
while True:
    if not input_webhook:
        break

    if float(input_delay) <= 0:
        time.sleep(0.1)
    else:
        time.sleep(float(input_delay))

    response = session.post(input_webhook, json = data)
    if response.status_code == 204:
        print(f"[+] message: '{message}' sent SUCCESSFULLY")
    else:
        print(f"[-] message: '{message}' FAILED to send")
