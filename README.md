# SIP AMI Hangup Monitor

This project provides a Python script for monitoring and managing SIP (Session Initiation Protocol) call hangups. The script automates the detection and handling of SIP call hangup events, which is essential for maintaining call quality, troubleshooting, and ensuring reliable telecommunication services in any organization.

**The script specifically uses the `CallerIDNum` and `ConnectedLineNum` fields from SIP events to identify and process hangup events related to a particular outgoing call. Only hangup events where both these fields match the target values will trigger the email notification and script termination. All other hangups are ignored, allowing the script to continue monitoring until the relevant event occurs.**

## Features

- Monitors SIP call activity and detects hangup events.
- Uses `CallerIDNum` and `ConnectedLineNum` to accurately identify the relevant hangup event for the target call.
- Logs and reports SIP hangup events for further analysis.
- Can be integrated with other monitoring systems or used as a standalone tool.
- Configurable parameters for adapting to different SIP server environments.

## Requirements

- Python 3.6 or higher
- The following Python libraries:
  - `asterisk-ami` (for Asterisk AMI connection)
  - `requests` (for Telegram notifications)

## Installation

1. **Clone the repository:**
   ```bash
   cd /opt
   git clone https://github.com/Mythological/sip-ami-hangup-monitor.git
   cd sip-ami-hangup-monitor
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install required libraries:**
   ```bash
   pip3.8 install -r requirements.txt
   ```

## Usage

1. **Configure the script and notifications:**
   - Edit configuration variables in the `.env` file (such as SIP server address, credentials, call parameters, notification settings, etc.).
   - The variables `ORIGINATE_CALLERID`, `ORIGINATE_CHANNEL`, `ORIGINATE_CONTEXT`, `ORIGINATE_EXTEN`, and `ORIGINATE_PRIORITY` control outgoing call parameters and event filtering.
   - Choose notification method by setting `NOTIFY_EMAIL` and/or `NOTIFY_TELEGRAM` in `.env`.
   - For email notifications, set SMTP and email parameters in `.env`.
   - For Telegram notifications, set your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.
   - To restrict notifications to specific Q.850 cause codes, set the `NOTIFY_CAUSES` variable in `.env`:
     - `NOTIFY_CAUSES= [21,34]` — Notify only if cause is 21 (Call Rejected) or 34 (No Circuit/Channel Available), etc.
     - `NOTIFY_CAUSES=None` — Do not send any notifications for any cause.
     - `NOTIFY_CAUSES=ALL` — (Default) Send notifications for any cause.

     You can find the list of Q.850 cause codes and their SIP mappings in the `q850_sip_codes.txt` file.
   - Notification logic is modularized: see `notify_email.py` and `notify_telegram.py` for details.

2. **Run the script:**
   ```bash
   python SIP_Hangup_Monitor.py
   ```

3. **Logs and Output:**
   - The script will output logs to the console or to a file, depending on the logging configuration.

### Example crontab entry

To run the script automatically at 05:30 every day and log output to a file, add the following line to your crontab (edit with `crontab -e`):

```
30 05 * * *         /opt/sip-ami-hangup-monitor/venv/bin/python3.8 /opt/sip-ami-hangup-monitor/SIP_Hangup_Monitor.py >> /opt/sip-ami-hangup-monitor/cron.log 2>&1
```

## Notes

- Ensure you have network access to the SIP server you intend to monitor.
- For production use, consider running the script as a background service or with a process manager.
- You can extend notification logic by editing or adding modules like `notify_email.py` and `notify_telegram.py`.

## License

MIT License
