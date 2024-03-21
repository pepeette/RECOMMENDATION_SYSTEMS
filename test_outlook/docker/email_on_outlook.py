# email_on_outlook.py
import imaplib
import email
import ssl
import datetime
import time
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from llama_index import (
    StorageContext,
    load_index_from_storage,
    VectorStoreIndex,
    get_response_synthesizer,
)
from llama_index.retrievers import VectorIndexRetriever
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.indices.postprocessor import SimilarityPostprocessor

load_dotenv()

app = Flask(__name__)

@app.route('/process_emails', methods=['POST'])
def process_emails():
    email_address = request.form.get('email')
    password = request.form.get('password')
    server = request.form.get('server')

    if email_address and password and server:
        server_conn = connect_to_outlook(email_address, password, server)
        message_ids = fetch_unread_emails(server_conn)

        for msg_id in message_ids:
            process_outlook_email(server_conn, msg_id, email_address, password, server)

        server_conn.logout()
        print('Replied in drafts')
        return jsonify({'message': 'Replied in drafts'}), 200
    else:
        return jsonify({'error': 'Invalid or missing environment variables'}), 400

def connect_to_outlook(email_address, password, server):
    context = ssl.create_default_context()
    server_conn = imaplib.IMAP4_SSL(server, 993, ssl_context=context)
    server_conn.login(email_address, password)
    server_conn.select('inbox')
    return server_conn

def fetch_unread_emails(server_conn):
    cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=20)).strftime('%d-%b-%Y')
    status, messages = server_conn.search(None, f'(UNSEEN SINCE "{cutoff_date}")')
    message_ids = messages[0].split()
    return message_ids

def ai_responder(message):
    #index_dir = './index'
    index_dir = "./serialized_model"
    storage_context = StorageContext.from_defaults(persist_dir = index_dir)
    index = load_index_from_storage(storage_context)
    # blob_client =BlobClient.from_connection_string(conn_str="<connection_string>", container="mycontainer", blob="serialized_model")

    # with blob_client.get_blob_client(blob="serialized_model/") as download_stream:  
    #     index = load_index_from_storage(download_stream)

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

def send_email(subject, new_body, sender, email_address, password, server, text_content):
    separator = "\n\n----------------- Original Message -----------------\n\n" 
    # Construct full body with new content, separator, and original message
    full_body = f"{new_body}\n\n{separator}\n\n{text_content}"

    # Create plain text email message
    message = MIMEText(full_body)

    # Set email fields
    message["From"] = email_address
    message["To"] = sender
    message["Subject"] = f"re: {subject}"
    message.add_header('X-Unsent', '1') 
    # Connect to Outlook
    imap = imaplib.IMAP4_SSL(server, 993)
    imap.login(email_address, password)

    # Select drafts folder
    draft_folder = 'Drafts'
    imap.select(draft_folder)
    imap.store("1:*", "+FLAGS", "\\Draft")
    # Append full email to drafts  
    imap.append(draft_folder, '', 
              imaplib.Time2Internaldate(time.time()), 
              message.as_string().encode('utf8'))

    imap.logout()
  
def process_outlook_email(server_conn, msg_id,email_address,password, server):
    # Get original message
    status, data = server_conn.fetch(msg_id, '(RFC822)')
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
    send_email(subject, new_body, sender, email_address, password, server, text_content)

# def reply_to_outlook_emails():
#     try:
#         server_conn = connect_to_outlook(email_address, password, server)
#         message_ids = fetch_unread_emails(server_conn)

#         for msg_id in message_ids:
#             process_outlook_email(server_conn, msg_id)

#         server_conn.logout()
    
#     except Exception as e:
#         print(f"An error occurred: {e}")


if __name__ == "__main__":
    # reply_to_outlook_emails()
    # print('done')
    context = ('cert.pem', 'key.pem')
    app.run(host='0.0.0.0', port=5012, ssl_context=context)