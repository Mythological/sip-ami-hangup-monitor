import requests

def send_error_telegram(bot_token, chat_id, cause, cause_txt, channel, exten):
    body = (
        f'Asterisk: Call Hangup\n'
        f'Channel: {channel}\n'
        f'Exten: {exten}\n'
        f'Cause: {cause}\n'
        f'Cause-txt: {cause_txt}'
    )
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': body
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print('Telegram notification sent!')
        else:
            print(f'[ERROR] Failed to send Telegram message: {response.text}')
    except Exception as e:
        print(f'[ERROR] Exception while sending Telegram message: {e}')
