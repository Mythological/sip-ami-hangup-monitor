#!/usr/bin/env python3.8

"""
Connects to Asterisk AMI using the specified parameters (host, port, user, password).
Initiates an outgoing call to the specified number via the SIP channel.
Waits for the Hangup event.
If the Hangup event relates to a call with CallerIDNum or ConnectedLineNum equal to ORIGINATE_CALLERID, it sends a notification (email/telegram) with details of Cause and Cause-txt.
If the Hangup event does not relate to the desired call, it is ignored and waiting continues.
After the first suitable Hangup, the script logs off from AMI and terminates.
If the script runs for more than 1 minute, it exits with an error.

Подключается к Asterisk AMI по заданным параметрам (host, port, user, password).
Инициирует исходящий звонок на заданный номер через SIP-канал.
Ожидает событие Hangup.
Если событие Hangup относится к вызову с CallerIDNum или ConnectedLineNum равными '0145133055', то отправляет email с деталями Cause и Cause-txt на указанный адрес через SMTP.
Если событие Hangup не относится к нужному вызову — игнорировать и продолжать ждать.
После первого подходящего Hangup скрипт завершает работу.
Если скрипт работает больше 1 минуты — завершить выполнение с ошибкой.
Скрипт должен работать в виртуальном окружении (venv), использовать shebang для python3.6.

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

# Read configuration from .env
AMI_HOST = os.getenv('AMI_HOST')  # Asterisk AMI host address
AMI_PORT = int(os.getenv('AMI_PORT', 5038))  # AMI port
AMI_USER = os.getenv('AMI_USER')  # AMI username
AMI_PASS = os.getenv('AMI_PASS')  # AMI password

SMTP_SERVER = os.getenv('SMTP_SERVER')  # SMTP server for email notifications
SMTP_PORT = int(os.getenv('SMTP_PORT', 25))  # SMTP port
SMTP_USER = os.getenv('SMTP_USER')  # SMTP username
SMTP_PASS = os.getenv('SMTP_PASS')  # SMTP password
EMAIL_TO = os.getenv('EMAIL_TO')  # Email recipient
USE_TLS_EMAIL = os.getenv('USE_TLS_EMAIL', 'False').lower() == 'true'  # Use TLS for SMTP

NOTIFY_EMAIL = os.getenv('NOTIFY_EMAIL', 'True').lower() == 'true'  # Enable email notifications
NOTIFY_TELEGRAM = os.getenv('NOTIFY_TELEGRAM', 'False').lower() == 'true'  # Enable Telegram notifications

# Parse NOTIFY_CAUSES from .env (comma separated list, None, or ALL)
NOTIFY_CAUSES_ENV = os.getenv('NOTIFY_CAUSES', 'ALL')
if NOTIFY_CAUSES_ENV == 'ALL':
    NOTIFY_CAUSES = 'ALL'
elif NOTIFY_CAUSES_ENV.strip().lower() in ['none', 'null', '']:
    NOTIFY_CAUSES = None
else:
    try:
        NOTIFY_CAUSES = [int(x.strip()) for x in NOTIFY_CAUSES_ENV.split(',') if x.strip().isdigit()]
    except Exception:
        NOTIFY_CAUSES = 'ALL'

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Telegram bot token
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')      # Telegram chat ID

# Outgoing call parameters (originate action)
ORIGINATE_CHANNEL = os.getenv('ORIGINATE_CHANNEL', 'SIP/YourTRUNK/1231')  # SIP channel
ORIGINATE_CONTEXT = os.getenv('ORIGINATE_CONTEXT', 'from-internal')        # Dialplan context
ORIGINATE_EXTEN = os.getenv('ORIGINATE_EXTEN', '*43')                      # Extension to call
ORIGINATE_PRIORITY = int(os.getenv('ORIGINATE_PRIORITY', 1))               # Dialplan priority
ORIGINATE_CALLERID = os.getenv('ORIGINATE_CALLERID', '0145133055')         # CallerID number for both call and event match


def notify(cause, cause_txt, channel, exten):
    """
    Send notifications via email and/or Telegram based on configuration.
    """
    if NOTIFY_EMAIL:
        send_error_email(
            SMTP_SERVER, SMTP_PORT, SMTP_USER, EMAIL_TO,
            cause, cause_txt, channel, exten,
            use_tls=USE_TLS_EMAIL, smtp_password=SMTP_PASS
        )
    if NOTIFY_TELEGRAM:
        send_error_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, cause, cause_txt, channel, exten)

def notify_if_cause_allowed(cause, cause_txt, channel, exten):
    """
    Check if the hangup cause is in the allowed list and send notification if so.
    """
    try:
        cause_int = int(cause)
    except Exception:
        cause_int = None
    # If NOTIFY_CAUSES is None, do not send notifications
    if NOTIFY_CAUSES is None:
        print(f'[INFO] Notification skipped: NOTIFY_CAUSES is None')
        return
    # If NOTIFY_CAUSES is a list, send only if cause is in the list
    if isinstance(NOTIFY_CAUSES, list) and cause_int not in NOTIFY_CAUSES:
        print(f'[INFO] Notification skipped: cause {cause} not in NOTIFY_CAUSES {NOTIFY_CAUSES}')
        return
    # If NOTIFY_CAUSES is 'ALL' or any other value, send notifications for any cause
    notify(cause, cause_txt, channel, exten)

def main():
    """
    Main entry point: connects to AMI, originates a call, and waits for Hangup events.
    """
    global shutdown_requested
    start_time = time.time()
    # Connect to Asterisk AMI
    client = AMIClient(address=AMI_HOST, port=AMI_PORT)
    client.login(username=AMI_USER, secret=AMI_PASS)
    print('Login successful!')

    # Initiate outgoing call via Originate action
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
        """
        EventListener for Hangup events. Checks if the event matches the target call and sends notification if needed.
        """
        def on_Hangup(self, event, **kwargs):
            global shutdown_requested
            print('[DEBUG] Hangup event:', event) 
            cause = None
            cause_txt = None
            try:
                try:
                    # Extract CallerIDNum and ConnectedLineNum from event
                    caller_id_num = event['CallerIDNum'] if 'CallerIDNum' in event else None
                    connected_line_num = event['ConnectedLineNum'] if 'ConnectedLineNum' in event else None
                    # Check if either matches ORIGINATE_CALLERID
                    if ORIGINATE_CALLERID in [caller_id_num, connected_line_num]:
                        if isinstance(event, Event) and 'Cause' in event.keys:
                            cause = event['Cause']
                            if 'Cause-txt' in event.keys:
                                cause_txt = event['Cause-txt']
                            channel = event['Channel'] if 'Channel' in event else 'N/A'
                            exten = event['Exten'] if 'Exten' in event else 'N/A'
                            print(f">>> Extracted from Event: Cause={cause}, Cause-txt={cause_txt}, Channel={channel}, Exten={exten}")
                            notify_if_cause_allowed(cause, cause_txt, channel, exten)
                        else:
                            print('[DEBUG] Skipped Hangup: no Cause in event')
                        # Log off client and stop script after handling the event
                        print('Logging off AMI client after catching Hangup...')
                        client.logoff()
                        shutdown_requested = True
                    else:
                        print('[DEBUG] Skipped Hangup: CallerIDNum/ConnectedLineNum do not match')
                        print(f"[INFO] Hangup: Cause={cause}, Cause-txt={cause_txt}")
                except Exception as e:
                    print(f'[ERROR] Exception in HangupEventListener: {e}')
            except Exception as e:
                print(f'[ERROR] Exception in HangupEventListener (outer): {e}')
            print(f"[INFO] Hangup: Cause={cause}, Cause-txt={cause_txt}")

    # Register Hangup event listener
    client.add_event_listener(HangupEventListener())
    print('Waiting for events...')
    try:
        # Main loop: waits for shutdown_requested or timeout
        while not shutdown_requested:
            time.sleep(0.5)
            # Exit if script runs more than 1 minute
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
