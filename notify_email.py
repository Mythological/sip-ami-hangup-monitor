import smtplib
from email.mime.text import MIMEText

def send_error_email(smtp_server, smtp_port, smtp_user, email_to, cause, cause_txt, channel, exten, use_tls=False, smtp_password=None):
    subject = f'Asterisk: Call Hangup to {exten} (Cause: {cause})'
    body = (
        f'Call has been terminated.\n'
        f'Channel: {channel}\n'
        f'Exten: {exten}\n'
        f'Cause: {cause}\n'
        f'Cause-txt: {cause_txt}'
    )

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = email_to
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if use_tls:
                server.starttls()
                if smtp_password is not None:
                    server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, [email_to], msg.as_string())
        print(f'Email notification sent (Cause: {cause})!')
    except Exception as e:
        print(f'[ERROR] Failed to send email: {e}')
