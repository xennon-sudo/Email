import os
import smtplib
import ssl
import time
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import openai

# Set the OpenAI base URL
openai.base_url = 'https://api.pawan.krd/cosmosrp/v1/'

class MailBot:
    def __init__(self, api_key, api_role, mail_host, password, sender_email, sent_folder, inbox_folder, check_interval=60):
        self.api_key = api_key
        self.api_role = api_role
        self.mail_host = mail_host
        self.password = password
        self.sender_email = sender_email
        self.sent_folder = sent_folder
        self.inbox_folder = inbox_folder
        self.check_interval = check_interval  # Interval to check for new emails
    
    def start(self):
        print("Starting MailBot...")
        while True:
            self.reply_to_emails(unread_messages=True)
            print(f"Waiting for {self.check_interval} seconds before checking for new emails...")
            time.sleep(self.check_interval)
    
    def reply_to_emails(self, unread_messages: bool):
        print("Connecting to the mailbox...")
        mail = imaplib.IMAP4_SSL(self.mail_host)
        mail.login(self.sender_email, self.password)
        mail.select(self.inbox_folder)

        # Search for unread emails
        print("Searching for unread emails...")
        status, messages = mail.search(None, 'UNSEEN' if unread_messages else 'ALL')
        message_ids = messages[0].split()

        if not message_ids:
            print("No new unread messages.")
            mail.logout()
            return  # Exit if there are no new messages

        # Get the latest unread message ID
        latest_msg_id = message_ids[-1]
        print(f"Processing latest message ID: {latest_msg_id.decode()}")

        # Fetch the email
        status, data = mail.fetch(latest_msg_id, '(RFC822)')
        raw_email = data[0][1]
        email_message = email.message_from_bytes(raw_email)

        # Extract email details
        sender = email_message['From']
        subject = email_message['Subject']
        print(f"From: {sender}, Subject: {subject}")

        # List of email addresses to skip
        skip_senders = [
            'subscribe@jooble.org',
            'mailer-daemon@google.com',
            # Add other addresses here as needed
        ]

        # Check if the sender is in the skip list
        if any(skip_sender in sender for skip_sender in skip_senders):
            print(f"Skipping sender: {sender}")
            mail.logout()
            return

        # Get the email body content
        body = self.get_email_body(email_message)
        print(f"Body extracted: {body[:30]}...")  # Print the first 30 characters for brevity

        # Generate answer with GPT
        print("Generating response using AI...")
        new_body = self.ai_responder(body)
        print("Response generated.")

        # Send email
        print(f"Sending reply to {sender}...")
        self.send_email(subject=subject, body=new_body, receiver_email=sender)
        print("Reply sent.")

        print("Logging out...")
        mail.logout()
    
    def get_email_body(self, email_message):
        body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                content = part.get_content_type()
                disposition = str(part.get('Content-Disposition'))
                if content == 'text/plain' and 'attachment' not in disposition:
                    body = part.get_payload(decode=True).decode(errors='replace')
                    break
        else:
            body = email_message.get_payload(decode=True).decode(errors='replace')

        return body
    
    def send_email(self, subject, body, receiver_email):
        # Create a multipart message and set headers
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = receiver_email
        message["Subject"] = subject

        # Add body to email
        message.attach(MIMEText(body, "plain"))

        # Log in to server using secure context and send email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.mail_host, 465, context=context) as server:
            server.login(self.sender_email, self.password)
            server.sendmail(self.sender_email, receiver_email, message.as_string())

        # Add email to sent folder
        with imaplib.IMAP4_SSL(self.mail_host) as imap:
            imap.login(self.sender_email, self.password)
            imap.append(self.sent_folder, '\\Seen', imaplib.Time2Internaldate(time.time()), message.as_bytes())
    
    def ai_responder(self, message):
        openai.api_key = self.api_key

        # Calculate the number of tokens in the input message
        input_tokens = len(message.split())
        
        # Set max_tokens to ensure total does not exceed the limit
        max_tokens = max(0, 16384 - input_tokens - 512)  # 512 for the response

        if max_tokens <= 0:
            print("Input is too long. Please reduce the size of the input message.")
            return "Error: Input too long."

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.api_role},
                {"role": "user", "content": message}
            ],
            temperature=0.8,
            max_tokens=max_tokens  # Set the maximum tokens for response
        )

        return response.choices[0].message.content

if __name__ == "__main__":
    # Load secrets from environment variables
    new_api_key = os.getenv("OPENAI_API_KEY")
    new_mail_host = os.getenv("MAIL_HOST", "smtp.gmail.com")  # Default to Gmail SMTP server
    new_password = os.getenv("MAIL_PASSWORD")  # Your app password
    new_your_email = os.getenv("YOUR_EMAIL")  # Your email address

    # GPT variables
    new_api_role = "You are a service assistant named Tusti. Please try to respond to my mail as Aritra's Assistant."

    # Email Variables
    new_sent_folder = 'Sent'
    new_inbox_folder = 'INBOX'

    # Instance of bot class
    mail_operator = MailBot(
        new_api_key, 
        new_api_role, 
        new_mail_host, 
        new_password, 
        new_your_email, 
        new_sent_folder, 
        new_inbox_folder
    )

    # Start the bot
    mail_operator.start()
