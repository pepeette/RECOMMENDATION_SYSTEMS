# email_model.py
import smtplib
import ssl
import time
import imaplib
import email
import email.message
import email.charset
import os
import datetime
from llama_index import SimpleDirectoryReader
from llama_index import VectorStoreIndex
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)

@app.route('/create_model', methods=['POST'])  
def create_model():
    email_address = request.form.get('email')
    password = request.form.get('password')
    server = request.form.get('server')
    
    if email_address and password and server:
        download_emails(email_address, password, server)   
        print('Emails downloaded')  
        model_index = create_llama_model()   
        print('Model created')
        # Uncomment the following line if you want to upload the model to Azure Storage
        # upload_model(model_index)
        return jsonify({'message': 'Model created successfully'}), 200
    else:
        return jsonify({'error': 'Missing required parameters'}), 400

def download_emails(email_address, password, outlook_server):
    context = ssl.create_default_context()
    mail = imaplib.IMAP4_SSL(outlook_server, 993, ssl_context=context)
    mail.login(email_address, password)

    status, folder_list = mail.list()

    folder_names = [folder.decode('utf-8') for folder in folder_list]
    inbox_folder = 'inbox'  # folder_names[0]
    mail.select(inbox_folder)

    cutoff_date = (datetime.date.today() - datetime.timedelta(days=180)).strftime('%d-%b-%Y')
    status, email_ids = mail.search(None, f'ALL SINCE {cutoff_date}')

    email_threads_dir = os.path.join(os.path.dirname(__file__), 'email_threads')
    os.makedirs(email_threads_dir, exist_ok=True)

    for email_id in email_ids[0].split():
        status, email_data = mail.fetch(email_id, '(RFC822)')
        raw_email = email_data[0][1]
        email_message = email.message_from_bytes(raw_email)

        sender = email_message['From']
        subject = email_message['Subject']
        date = email_message['Date']

        email_filename = f'{email_threads_dir}/{email_id.decode("utf-8")}.txt'
        with open(email_filename, 'w', encoding='utf-8') as email_file:
            email_file.write(f'From: {sender}\n') 
            email_file.write(f'Subject: {subject}\n')
            email_file.write(f'Date: {date}\n\n')

            for part in email_message.walk():
                if part.get_content_type() == 'text/plain':
                    email_file.write(part.get_payload(decode=True).decode('utf-8'))

def create_llama_model():
    required_exts = [".txt"]
    reader = SimpleDirectoryReader(input_dir="./email_threads", required_exts=required_exts)   
    docs = reader.load_data()
    index = VectorStoreIndex.from_documents(docs)

    # Save the index to a specified directory
    index_dir = "./serialized_model"
    index.storage_context.persist(index_dir)
    return index

# Uncomment and modify this function if you want to upload the model to Azure Storage
# def upload_model(index):
#     account_name = os.environ["AZURE_STORAGE_ACCOUNT"]
#     account_key = os.environ["AZURE_STORAGE_KEY"]  
#     blob_service_client = BlobServiceClient(
#         account_url=f"https://{account_name}.blob.core.windows.net",
#         credential=account_key
#     )
#     container_client = blob_service_client.create_container("email-model")
#     if os.path.exists("./serialized_model"): 
#         with open("./serialized_model", "rb") as data:
#             blob_client = container_client.get_blob_client("model")
#             blob_client.upload_blob(data)

if __name__ == "__main__":
    context = ('cert.pem', 'key.pem')
    app.run(host='0.0.0.0', port=5011, ssl_context=context)
