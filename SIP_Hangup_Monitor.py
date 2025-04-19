#!/usr/bin/env python3.6

"""
Connects to Asterisk AMI using the specified parameters (host, port, user, password).
Initiates an outgoing call to the specified number via the SIP channel.
Waits for the Hangup event.
If the Hangup event relates to a call with CallerIDNum and ConnectedLineNum equal to '0145133055', it sends an email with the details of Cause and Cause-txt to the specified address via SMTP.
If the Hangup event does not relate to the desired call, it is ignored and waiting continues.
After the first suitable Hangup, the script terminates.
If the script runs for more than 1 minute, it exits with an error.

Подключается к Asterisk AMI по заданным параметрам (host, port, user, password).
Инициирует исходящий звонок на заданный номер через SIP-канал.
Ожидает событие Hangup.
Если событие Hangup относится к вызову с CallerIDNum и ConnectedLineNum равными '0145133055', то отправляет email с деталями Cause и Cause-txt на указанный адрес через SMTP.
Если событие Hangup не относится к нужному вызову — игнорировать и продолжать ждать.
После первого подходящего Hangup скрипт завершает работу.
Если скрипт работает больше 1 минуты — завершить выполнение с ошибкой.

"""
from email.mime.text import MIMEText
from asterisk.ami import AMIClient, SimpleAction, EventListener
from asterisk.ami.event import Event
import time
import sys
import os
from dotenv import load_dotenv
from notify_email import send_error_email
from notify_telegram import send_error_telegram

shutdown_requested = False

# Load environment variables from .env file
load_dotenv()

# Setup Asterisk AMI
AMI_HOST = os.getenv('AMI_HOST')
AMI_PORT = int(os.getenv('AMI_PORT', 5038))
AMI_USER = os.getenv('AMI_USER')
AMI_PASS = os.getenv('AMI_PASS')

SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 25))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
EMAIL_TO = os.getenv('EMAIL_TO')
USE_TLS_EMAIL = os.getenv('USE_TLS_EMAIL', 'False').lower() == 'true'

NOTIFY_EMAIL = os.getenv('NOTIFY_EMAIL', 'True').lower() == 'true'
NOTIFY_TELEGRAM = os.getenv('NOTIFY_TELEGRAM', 'False').lower() == 'true'

# Notify only for these Q.850 causes:
#   [21, 34] - send only if cause is 21 or 34
#   None     - do not send any notifications
#   'ALL'    - send for any cause
NOTIFY_CAUSES_ENV = os.getenv('NOTIFY_CAUSES', 'ALL')
if NOTIFY_CAUSES_ENV == 'ALL':
    NOTIFY_CAUSES = 'ALL'
elif NOTIFY_CAUSES_ENV.strip().lower() in ['none', 'null', '']:  # treat as None
    NOTIFY_CAUSES = None
else:
    try:
        NOTIFY_CAUSES = [int(x.strip()) for x in NOTIFY_CAUSES_ENV.split(',') if x.strip().isdigit()]
    except Exception:
        NOTIFY_CAUSES = 'ALL'

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Outgoing call parameters
ORIGINATE_CHANNEL = os.getenv('ORIGINATE_CHANNEL', 'SIP/YourTRUNK/1231')
ORIGINATE_CONTEXT = os.getenv('ORIGINATE_CONTEXT', 'from-internal')
ORIGINATE_EXTEN = os.getenv('ORIGINATE_EXTEN', '*43')
ORIGINATE_PRIORITY = int(os.getenv('ORIGINATE_PRIORITY', 1))
ORIGINATE_CALLERID = os.getenv('ORIGINATE_CALLERID', '0145133055')

# Use ORIGINATE_CALLERID for all relevant checks
CALLERIDNUM = ORIGINATE_CALLERID
CONNECTEDLINENUM = ORIGINATE_CALLERID

def notify(cause, cause_txt, channel, exten):
    if NOTIFY_EMAIL:
        send_error_email(
            SMTP_SERVER, SMTP_PORT, SMTP_USER, EMAIL_TO,
            cause, cause_txt, channel, exten,
            use_tls=USE_TLS_EMAIL, smtp_password=SMTP_PASS
        )
    if NOTIFY_TELEGRAM:
        send_error_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, cause, cause_txt, channel, exten)

def notify_if_cause_allowed(cause, cause_txt, channel, exten):
    try:
        cause_int = int(cause)
    except Exception:
        cause_int = None
    # Logic for NOTIFY_CAUSES
    if NOTIFY_CAUSES is None:
        print(f'[INFO] Notification skipped: NOTIFY_CAUSES is None')
        return
    if isinstance(NOTIFY_CAUSES, list) and cause_int not in NOTIFY_CAUSES:
        print(f'[INFO] Notification skipped: cause {cause} not in NOTIFY_CAUSES {NOTIFY_CAUSES}')
        return
    # 'ALL' or any other value will send notifications for any cause
    notify(cause, cause_txt, channel, exten)

def main():
    global shutdown_requested
    start_time = time.time()
    client = AMIClient(address=AMI_HOST, port=AMI_PORT)
    client.login(username=AMI_USER, secret=AMI_PASS)
    print('Login successful!')

    action = SimpleAction(
        'Originate',
        Channel=ORIGINATE_CHANNEL,
        Context=ORIGINATE_CONTEXT,
        Exten=ORIGINATE_EXTEN,
        Priority=ORIGINATE_PRIORITY,
        CallerID=ORIGINATE_CALLERID,
        Async='true'
    )
    print('Sending Originate action...')
    client.send_action(action)

    class HangupEventListener(EventListener):
        def on_Hangup(self, event, **kwargs):
            global shutdown_requested
            print('[DEBUG] Hangup event:', event) 
            cause = None
            cause_txt = None
            try:
                try:
                    if (event['CallerIDNum'] == CALLERIDNUM and event['ConnectedLineNum'] == CONNECTEDLINENUM):
                        if isinstance(event, Event) and 'Cause' in event.keys:
                            cause = event['Cause']
                            if 'Cause-txt' in event.keys:
                                cause_txt = event['Cause-txt']
                            else:
                                cause_txt = 'N/A'
                            channel = event.get('Channel', 'N/A')
                            exten = event.get('Exten', 'N/A')
                            print(f">>> Extracted from Event: Cause={cause}, Cause-txt={cause_txt}, Channel={channel}, Exten={exten}")
                            notify_if_cause_allowed(cause, cause_txt, channel, exten)
                        else:
                            print('[DEBUG] Skipped Hangup: no Cause in event')
                        shutdown_requested = True
                    else:
                        print('[DEBUG] Skipped Hangup: CallerIDNum/ConnectedLineNum do not match')
                except Exception as e:
                    print(f'[ERROR] Unexpected error while processing Hangup: {e}')
                print(f"[INFO] Hangup: Cause={cause}, Cause-txt={cause_txt}")
            except Exception as e:
                print(f'[ERROR] Unexpected error while processing Hangup: {e}')
            print(f"[INFO] Hangup: Cause={cause}, Cause-txt={cause_txt}")

    client.add_event_listener(HangupEventListener())
    print('Waiting for events...')
    try:
        while not shutdown_requested:
            time.sleep(0.5)
            if time.time() - start_time > 60:
                print('[ERROR] Script has been running for more than 1 minute, exiting!')
                client.logoff()
                sys.exit(1)
    except KeyboardInterrupt:
        print('\nTerminating due to Ctrl+C.')
    finally:
        print('Terminating script...')
        client.logoff()
        print('AMI client disconnected.')

if __name__ == '__main__':
    main()

