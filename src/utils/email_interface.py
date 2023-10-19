from nylas import APIClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get environment variables
CLIENT_ID = os.getenv('Client-Id')
CLIENT_SECRET = os.getenv('Client-Secret')
ACCESS_TOKEN = os.getenv('Access-Token')

# Create nylas API instance
nylas = APIClient(
    CLIENT_ID,
    CLIENT_SECRET,
    ACCESS_TOKEN,
)

def send_email(recipient: str, subject: str, body: str):
    # Create new draft
    draft = nylas.drafts.create()
    draft.subject = subject
    draft.body = body
    draft.to = [{'name': 'Lif Platforms', 'email': recipient}] 

    # Send new draft
    draft.send()

    return 'OK'