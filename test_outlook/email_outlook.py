import imaplib, email, ssl, datetime, time, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from llama_index import StorageContext, load_index_from_storage
from llama_index import (
    VectorStoreIndex,
    get_response_synthesizer,
)
from llama_index.retrievers import VectorIndexRetriever
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.indices.postprocessor import SimilarityPostprocessor

from flask import Flask, request, jsonify

from dotenv import load_dotenv
load_dotenv()
recipient_email = os.getenv("RECIPIENT_EMAIL")
password = os.getenv("PASSWORD")
outlook_server = os.getenv("OUTLOOK_SERVER")

# app = Flask(__name__)
# # Production configurations
# app.config['SECRET_KEY'] = 'OutlookGTP'  # Change this to a secure key
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Set max request size to 16 MB
# # Ensure a secure random key for session management
# app.secret_key = app.config['SECRET_KEY']

# @app.route('/process_emails', methods=['GET', 'POST'])
# def process_emails():
#     if request.method == 'POST':
#         try:
#             # Fetch environment variables
#             recipient_email = os.getenv("RECIPIENT_EMAIL")
#             password = os.getenv("PASSWORD")
#             outlook_server = os.getenv("OUTLOOK_SERVER")

#             if recipient_email and password and outlook_server:
#                 server = connect_to_outlook(recipient_email, password, outlook_server)
#                 message_ids = fetch_unread_emails(server)

#                 for msg_id in message_ids:
#                     process_outlook_email(server, msg_id)

#                 server.logout()
#                 print('Replied in drafts')
#                 return jsonify({'message': 'DRaft response successful'}), 200
#             else:
#                 return jsonify({'error': 'Invalid or missing environment variables'}), 400
#         except Exception as e:
#             # Log the exception
#             print(f"Error: {str(e)}")
#             return jsonify({'error': 'An error occurred'}), 500
#     else:
#         return jsonify({'error': 'Invalid request method'})

def connect_to_outlook(recipient_email, password, outlook_server):
    # outlook_server = 'outlook.office365.com'
    # email_address = 'pepeette@outlook.com'
    # password = 'edpfdfjvfqwjjmkr'

    context = ssl.create_default_context()
    server = imaplib.IMAP4_SSL(outlook_server, 993, ssl_context=context)
    # server.login(email_address, password)
    server.login(recipient_email, password)
    server.select('inbox')
    return server

def fetch_unread_emails(server):
    cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=20)).strftime('%d-%b-%Y')
    status, messages = server.search(None, f'(UNSEEN SINCE "{cutoff_date}")')
    message_ids = messages[0].split()
    return message_ids

def ai_responder(message):
    index_dir = './index'
    storage_context = StorageContext.from_defaults(persist_dir = index_dir)
    index = load_index_from_storage(storage_context)
    # configure retriever
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=2,
    )

    # configure response synthesizer
    response_synthesizer = get_response_synthesizer()
    # assemble query engine
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
        node_postprocessors=[
            SimilarityPostprocessor(similarity_cutoff=0.7)
        ]

    )
    
    max_query_length = 3000
    if len(message) > max_query_length:
        message = message[:max_query_length]

    query = (
         f'Below is an email received from a Rockwoord Glass client or prospect.'
        f'You are Rockwoord-Glass company customer service representative.'
        f'Your goal is to reply to this email received in an email formatted manner.'
        f'Do write the reply bearing in mind these strict requirements : '
        f'- Reply in less than 150 words'
        f'- Properly format the email response'
        f'- Use the appropriate tone to appear more professional and expert than the client'
        f'- Make very simple sentences. Use bullet points when appropriate.'
        f'- Focus the reply on the next action.'

        f'Please start the email with a short and warm introduction. Add the introduction if you need to.'
        f'At Rockwoord Glass, we are number 1 bespoke design and manufacturing glass and ceramic bottles.'
        f'We service the biggest names as well as the tailored demands. '
        
        f'Here is the email received to reply to :'
        f'EMAIL RECEIVED: {message}'
        # f'As Rockwoord Glass customer service representative, '
        # f'please reply to the email "{message}" in an email format with salesy, polite and succinct manner.'
    )

    # query
    response = query_engine.query(query)
    email_response = response.response
    return email_response

def send_email(subject, new_body, sender, recipient_email, password, outlook_server, text_content):
    separator = "\n\n----------------- Original Message -----------------\n\n" 
    # Construct full body with new content, separator, and original message
    full_body = f"{new_body}\n\n{separator}\n\n{text_content}"

    # Create plain text email message
    message = MIMEText(full_body)

    # Set email fields
    message["From"] = recipient_email
    message["To"] = sender
    message["Subject"] = f"re: {subject}"
    message.add_header('X-Unsent', '1') 
    # Connect to Outlook
    imap = imaplib.IMAP4_SSL(outlook_server, 993)
    imap.login(recipient_email, password)

    # Select drafts folder
    draft_folder = 'Drafts'
    imap.select(draft_folder)
    imap.store("1:*", "+FLAGS", "\\Draft")
    # Append full email to drafts  
    imap.append(draft_folder, '', 
              imaplib.Time2Internaldate(time.time()), 
              message.as_string().encode('utf8'))

    imap.logout()
  
def process_outlook_email(server, msg_id):
    # Get original message
    status, data = server.fetch(msg_id, '(RFC822)')
    original_msg = email.message_from_bytes(data[0][1])
    sender = original_msg['From']
    subject = original_msg['Subject']
    
    # Extract text content from original message
    text_content = ""
    for part in original_msg.walk():
        if part.get_content_type() == "text/plain":
            text_content += part.get_payload(decode=True).decode('utf-8')

    new_body = ai_responder(text_content)
    
    # Pass original message text to attach
    send_email(subject, new_body, sender, recipient_email, password, outlook_server, text_content)

def reply_to_outlook_emails():
    try:
        server = connect_to_outlook(recipient_email, password, outlook_server)
        message_ids = fetch_unread_emails(server)

        for msg_id in message_ids:
            process_outlook_email(server, msg_id)

        server.logout()
    
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    reply_to_outlook_emails()
    print('done')
    # app.run(host='0.0.0.0', port=5012)