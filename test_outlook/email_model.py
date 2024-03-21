#create_model.py
import smtplib
import time
import ssl
import imaplib
import email
import email.message
import email.charset
import os
import datetime
from llama_index import SimpleDirectoryReader
from llama_index import (
    VectorStoreIndex,
    get_response_synthesizer,
)
from llama_index.retrievers import VectorIndexRetriever
from llama_index import StorageContext

from dotenv import load_dotenv
# Load environment variables from the .env file
load_dotenv()

# from flask import Flask, request, jsonify
# app = Flask(__name__)

# @app.route('/create_model', methods=['POST'])  
# def create_model():
#   email = request.form.get('email')
#   password = request.form.get('password')
#   server = request.form.get('server')
#   if email and password and server:    
#     download_emails(email, password, server)   
#     print('Emails downloaded')  
#     model_index = create_llama_model()   
#     print('Model created')
#     return jsonify({'message': 'Model created successfully'}), 200
#   else:
#     return jsonify({'error': 'Missing required parameters'}), 400

recipient_email = os.getenv("RECIPIENT_EMAIL")
password = os.getenv("PASSWORD")
outlook_server = os.getenv("OUTLOOK_SERVER")

def download_emails(recipient_email, password, outlook_server):
    # Connect to the server using SSL
    context = ssl.create_default_context()
    mail = imaplib.IMAP4_SSL(outlook_server, 993, ssl_context=context)
    mail.login(recipient_email, password)
    
    # Get the list of mailbox folders
    status, folder_list = mail.list()
        
    # Extract the folder names
    folder_names = []
    for folder in folder_list:
        folder_name = folder.decode('utf-8')
        folder_names.append(folder_name)
        
    inbox_folder = 'inbox'  #folder_names[0]
    mail.select(inbox_folder)
    
    # Calculate the cutoff time for messages (180 days ago)
    cutoff_date = (datetime.date.today() - datetime.timedelta(days=180)).strftime('%d-%b-%Y')
    
    # Search for emails from the past 180 days
    status, email_ids = mail.search(None, f'ALL SINCE {cutoff_date}')
    
    # Get the absolute path to the email_threads directory based on the script's location
    email_threads_dir = os.path.join(os.path.dirname(__file__), 'email_threads')

    # Ensure the directory exists
    os.makedirs(email_threads_dir, exist_ok=True)
    
    # Fetch and save each email thread
    for email_id in email_ids[0].split():
        status, email_data = mail.fetch(email_id, '(RFC822)')
        raw_email = email_data[0][1]
        email_message = email.message_from_bytes(raw_email)

        # Get email thread details
        sender = email_message['From']
        subject = email_message['Subject']
        date = email_message['Date']

        # Save email to a text file
        email_filename = f'{email_threads_dir}/{email_id.decode("utf-8")}.txt'
        with open(email_filename, 'w', encoding='utf-8') as email_file:
            email_file.write(f'From: {sender}\n') 
            email_file.write(f'Subject: {subject}\n')
            email_file.write(f'Date: {date}\n\n')

            for part in email_message.walk():
                if part.get_content_type() == 'text/plain':
                    email_file.write(part.get_payload(decode=True).decode('utf-8'))

def create_llama_model():
    # create index
    required_exts = [".txt"]
    reader = SimpleDirectoryReader(input_dir="./email_threads", required_exts=required_exts)   
    # reader = SimpleDirectoryReader(input_dir="/email_threads", required_exts=required_exts)   
    docs = reader.load_data()
    index = VectorStoreIndex.from_documents(docs)

    # save index
    index_dir = "index"
    index.storage_context.persist(index_dir)
    return index

def main():

    download_emails(recipient_email, password, outlook_server)
    print('email_threads_fetched')
    model_index = create_llama_model()
    print('model_tuned')

if __name__ == "__main__":
    main()
    # app.run(host='0.0.0.0', port=5011)






