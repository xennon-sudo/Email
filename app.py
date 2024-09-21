import smtplib
import ssl
import time
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, jsonify
import openai

# Set the OpenAI base URL
openai.base_url = 'https://api.pawan.krd/cosmosrp/v1/'

app = Flask(__name__)

class MailBot:
    def __init__(self, api_key, api_role, mail_host, password, sender_email, sent_folder, inbox_folder, check_interval=60):
        self.api_key = api_key
        self.api_role = api_role
        self.mail_host = mail_host
        self.password = password
        self.sender_email = sender_email
        self.sent_folder = sent_folder
        self.inbox_folder = inbox_folder
        self.check_interval = check_interval

    def reply_to_emails(self):
        print("Connecting to the mailbox...")
        mail = imaplib.IMAP4_SSL(self.mail_host)
        mail.login(self.sender_email, self.password)
        mail.select(self.inbox_folder)

        # Search for unread emails
        print("Searching for unread emails...")
        status, messages = mail.search(None, 'UNSEEN')
        message_ids = messages[0].split()

        if not message_ids:
            print("No new unread messages.")
            mail.logout()
            return

        # Process the latest message
        latest_msg_id = message_ids[-1]
        print(f"Processing latest message ID: {latest_msg_id.decode()}")
        status, data = mail.fetch(latest_msg_id, '(RFC822)')
        raw_email = data[0][1]
        email_message = email.message_from_bytes(raw_email)

        sender = email_message['From']
        subject = email_message['Subject']
        print(f"From: {sender}, Subject: {subject}")

        body = self.get_email_body(email_message)
        print(f"Body extracted: {body[:30]}...")

        new_body = self.ai_responder(body)
        print("Response generated.")

        self.send_email(subject, new_body, sender)
        print("Reply sent.")
        mail.logout()

    def get_email_body(self, email_message):
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == 'text/plain' and 'attachment' not in part.get('Content-Disposition'):
                    body = part.get_payload(decode=True).decode(errors='replace')
                    break
        else:
            body = email_message.get_payload(decode=True).decode(errors='replace')
        return body

    def send_email(self, subject, body, receiver_email):
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.mail_host, 465, context=context) as server:
            server.login(self.sender_email, self.password)
            server.sendmail(self.sender_email, receiver_email, message.as_string())

    def ai_responder(self, message):
        openai.api_key = self.api_key
        input_tokens = len(message.split())
        max_tokens = max(0, 16384 - input_tokens - 512)

        if max_tokens <= 0:
            return "Error: Input too long."

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.api_role},
                {"role": "user", "content": message}
            ],
            temperature=0.8,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content

mail_operator = MailBot(
    "Your_API_Key",
    "You are a service assistant named Tusti. Please try to respond my mail as Aritra's Assistant.",
    "smtp.gmail.com",
    "ebfo wbum eifv hexm",
    "aritradmn@gmail.com",
    "Sent",
    "INBOX"
)

@app.route('/start', methods=['POST'])
def start():
    mail_operator.reply_to_emails()
    return jsonify({"status": "Checked for emails!"})

if __name__ == "__main__":
    app.run()
