# core/tools.py

import os
import pickle
import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from langchain.tools import tool

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send'] # Add others as needed

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh_token(Request())
        else:
            # Path to your credentials.json file
            credentials_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'credentials.json')
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service


def list_latest_gmail_messages(count: int = 5) -> str:
    """
    Lists the latest unread Gmail messages from the user's inbox.
    Args:
        count (int): The number of latest messages to retrieve. Defaults to 5.
    Returns:
        str: A formatted string containing subject and sender of the latest messages.
             Returns an error message if the service cannot be initialized.
    """
    try:
        service = get_gmail_service()
        # Call the Gmail API to get messages
        results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=count).execute()
        messages = results.get('messages', [])

        if not messages:
            return "No unread messages found."
        
        output = "Latest unread Gmail messages:\n"
        for msg in messages:
            msg_details = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            headers = msg_details['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
            sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
            output += f"- From: {sender}, Subject: {subject}\n"
        return output
    except Exception as e:
        return f"Error retrieving Gmail messages: {e}"


def list_latest_messages_id(count: int = 5) -> str:
    """
    Lists the IDs of the latest unread Gmail messages from the user's inbox.
    Args:
        count (int): The number of latest messages to retrieve. Defaults to 5.
    Returns:
        str: A formatted string containing the IDs of the latest messages.
             Returns an error message if the service cannot be initialized.
    """
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=count).execute()
        messages = results.get('messages', [])

        if not messages:
            return "No unread messages found."

        output = "Latest unread Gmail message IDs:\n"
        for msg in messages:
            output += f"- Message ID: {msg['id']}\n"
        return output
    except Exception as e:
        return f"Error retrieving Gmail message IDs: {e}"

def get_gmail_message_content(message_id: str) -> str:
    """
    Retrieves the content of a specific Gmail message by its ID.
    Args:
        message_id (str): The ID of the Gmail message.
    Returns:
        str: The plain text content of the message. Returns an error message if not found or error.
    """
    try:
        service = get_gmail_service()
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        # Function to decode message parts
        def get_parts(parts):
            body_data = []
            for part in parts:
                if part.get('body') and part['body'].get('data'):
                    data = part['body']['data']
                    body_data.append(base64.urlsafe_b64decode(data).decode('utf-8'))
                elif part.get('parts'):
                    body_data.extend(get_parts(part['parts']))
            return body_data

        payload = msg['payload']
        if 'parts' in payload:
            content = "\n".join(get_parts(payload['parts']))
        elif 'body' in payload and payload['body'].get('data'):
            content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        else:
            content = "No content found for this message."

        # Attempt to get relevant headers for context
        headers = payload['headers']
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
        sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')

        return f"Subject: {subject}\nFrom: {sender}\n\n{content[:500]}..." # Truncate for brevity
    except Exception as e:
        return f"Error retrieving message content for ID {message_id}: {e}"


def send_gmail_message(to: str, subject: str, body: str, reply_to_id: str | None = None) -> str:
    """
    Sends a Gmail message to a recipient.
    Args:
        to (str): The recipient's email address.
        subject (str): The subject of the email.
        body (str): The plain text content of the email.
        reply_to_id (str, optional): The ID of the message to reply to, if this is a reply.
                                     This will set the In-Reply-To and References headers.
    Returns:
        str: Success message or error message.
    """
    try:
        service = get_gmail_service()

        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        if reply_to_id:
            # Get headers of the message being replied to
            original_message = service.users().messages().get(userId='me', id=reply_to_id, format='metadata', metadataHeaders=['Message-ID', 'In-Reply-To', 'References']).execute()
            
            # Extract Message-ID from original message to use as In-Reply-To
            original_message_id = next((h['value'] for h in original_message['payload']['headers'] if h['name'] == 'Message-ID'), None)
            if original_message_id:
                message['In-Reply-To'] = original_message_id
                # Build References header: existing References + original_message_id
                original_references = next((h['value'] for h in original_message['payload']['headers'] if h['name'] == 'References'), '')
                message['References'] = f"{original_references} {original_message_id}".strip()

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send the message
        sent_message = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        return f"Message sent successfully to {to} with ID: {sent_message['id']}"
    except Exception as e:
        return f"Error sending message: {e}"


if __name__ == "__main__":
    # Example usage
    print(list_latest_gmail_messages(2))
    # Replace 'your_message_id_here' with an actual message ID to test get_gmail_message_content
    # print(get_gmail_message_content('your_message_id_here'))
    
    # List latest message IDs
    print(list_latest_messages_id(2))