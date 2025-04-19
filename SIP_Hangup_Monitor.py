#!/usr/bin/env python3.6

"""
Connects to Asterisk AMI using the specified parameters (host, port, user, password).
Initiates an outgoing call to the specified number via the SIP channel.
Waits for the Hangup event.
If the Hangup event relates to a call with CallerIDNum and ConnectedLineNum equal to '0145133055', it sends an email with the details of Cause and Cause-txt to the specified address via SMTP.
If the Hangup event does not relate to the desired call, it is ignored and waiting continues.
After the first suitable Hangup, the script terminates.
If the script runs for more than 10 minutes, it exits with an error.

Подключается к Asterisk AMI по заданным параметрам (host, port, user, password).
Инициирует исходящий звонок на заданный номер через SIP-канал.
Ожидает событие Hangup.
Если событие Hangup относится к вызову с CallerIDNum и ConnectedLineNum равными '0145133055', то отправляет email с деталями Cause и Cause-txt на указанный адрес через SMTP.
Если событие Hangup не относится к нужному вызову — игнорировать и продолжать ждать.
После первого подходящего Hangup скрипт завершает работу.
Если скрипт работает больше 10 минут — завершить выполнение с ошибкой.

"""
from email.mime.text import MIMEText
from asterisk.ami import AMIClient, SimpleAction, EventListener
from asterisk.ami.event import Event
import time
import sys
from notify_email import send_error_email
from notify_telegram import send_error_telegram

shutdown_requested = False

# Setup Asterisk AMI
AMI_HOST = '127.0.0.1'
AMI_PORT = 5038
AMI_USER = 'monitor'
AMI_PASS = 'PASS'

SMTP_SERVER = '172.14.1.1'
SMTP_PORT = 25
SMTP_USER = 'mesw@spo.com'
SMTP_PASS = ''
EMAIL_TO = 'ten@spo.com'

# Notification settings
NOTIFY_EMAIL = True
NOTIFY_TELEGRAM = False
USE_TLS_EMAIL = False  # Set to True if your SMTP server requires TLS

# Telegram settings
TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID'


def notify(cause, cause_txt, channel, exten):
    if NOTIFY_EMAIL:
        send_error_email(
            SMTP_SERVER, SMTP_PORT, SMTP_USER, EMAIL_TO,
            cause, cause_txt, channel, exten,
            use_tls=USE_TLS_EMAIL, smtp_password=SMTP_PASS
        )
    if NOTIFY_TELEGRAM:
        send_error_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, cause, cause_txt, channel, exten)

def main():
    global shutdown_requested
    start_time = time.time()
    client = AMIClient(address=AMI_HOST, port=AMI_PORT)
    client.login(username=AMI_USER, secret=AMI_PASS)
    print('Login successful!')

    action = SimpleAction(
        'Originate',
        Channel='SIP/YourTRUNK/1231',  # or SIP/100
        Context='from-internal',
        Exten='4444',
        Priority=1,
        CallerID='0145133055',
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
                    if (event['CallerIDNum'] == '0145133055' and event['ConnectedLineNum'] == '0145133055'):
                        if isinstance(event, Event) and 'Cause' in event.keys:
                            cause = event['Cause']
                            if 'Cause-txt' in event.keys:
                                cause_txt = event['Cause-txt']
                            else:
                                cause_txt = 'N/A'
                            channel = event.get('Channel', 'N/A')
                            exten = event.get('Exten', 'N/A')
                            print(f">>> Extracted from Event: Cause={cause}, Cause-txt={cause_txt}, Channel={channel}, Exten={exten}")
                            notify(cause, cause_txt, channel, exten)
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
                print('[ERROR] Script has been running for more than 1 minutes, exiting!')
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
