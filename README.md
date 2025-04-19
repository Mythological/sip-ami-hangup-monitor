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
   pip install -r requirements.txt
   ```

## Usage

1. **Configure the script and notifications:**
   - Edit configuration variables at the top of `SIP_Hangup_Monitor.py` (such as SIP server address, credentials, etc.).
   - Set the appropriate values for `CallerIDNum` and `ConnectedLineNum` to match your target call.
   - Choose notification method by setting `NOTIFY_EMAIL` and/or `NOTIFY_TELEGRAM`.
   - For email notifications, set SMTP and email parameters.
   - For Telegram notifications, set your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
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
30 05 * * *         /opt/sip-ami-hangup-monitor/venv/bin/python3.6 /opt/sip-ami-hangup-monitor/SIP_Hangup_Monitor.py >> /opt/sip-ami-hangup-monitor/cron.log 2>&1
```

## Notes

- Ensure you have network access to the SIP server you intend to monitor.
- For production use, consider running the script as a background service or with a process manager.
- You can extend notification logic by editing or adding modules like `notify_email.py` and `notify_telegram.py`.

## License

MIT License
