from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import utils.database_interface as database
from utils import email_interface
import yaml
from contextlib import asynccontextmanager
import os
import json

# Define config variable for storing configurations
# This will be written to later by the FastAPI lifespan
global configuration
configuration = None

with open("access-tokens.yml", "r") as config:
    access_tokens = yaml.safe_load(config.read())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check if config exists
    # If yes, parse through is and add any necessary items to it
    # If no, create a new one and add the default config
    if os.path.isfile('config.yml'):
        # Read and parse config contents
        with open('config.yml', 'r') as file:
            contents = file.read()
            parsed_config = yaml.safe_load(contents)
            file.close()

        # Read and parse default config
        with open(f"{os.path.dirname(os.path.realpath(__file__))}/resources/config_template.json", 'r') as file:
            contents = file.read()
            parsed_contents = json.loads(contents)
            file.close()

        # Ensure all items in default config are present in current config
        # If not, add missing items to config
        for option in parsed_contents: 
            if option not in parsed_config: 
                parsed_config[option] = parsed_contents[option]

        # Write new config to file system
        with open('config.yml', 'w') as file:
            write_data = yaml.safe_dump(parsed_config)
            file.write(write_data)
            file.close()
    else:
        # Read and parse default config
        with open(f"{os.path.dirname(os.path.realpath(__file__))}/resources/config_template.json", 'r') as file:
            contents = file.read()
            parsed_contents = json.loads(contents)
            file.close()

        # Create new config file and write default config to it
        with open('config.yml', 'x') as file:
            write_data = yaml.safe_dump(parsed_contents)
            file.write(write_data)

    # Load final config
    with open('config.yml', 'r') as file:
        contents = file.read()
        parsed_contents = yaml.safe_load(contents)

        # Update config variable
        global configuration
        configuration = parsed_contents

        file.close()

    # Set config for database interface
    database.set_config(configuration)
    
    yield

app = FastAPI(lifespan=lifespan)

# Allow Cross-Origin Resource Sharing (CORS) for all origins
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get('/')
def main_route():
    return "Welcome to the Lif Mail Service"

@app.post('/waitlist/ringer')
async def ringer_waitlist(request: Request):
    data = await request.json()  # Parse JSON data from the request body
    email = data.get('email')

    # Add email to Ringer Waitlist
    status = database.add_to_ringer_waitlist(email)

    if status == "OK":
        return {'status': 'OK'}
    else:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.get('/get_ringer_waitlist_members/{access_token}')
def get_ringer_waitlist_members(access_token):
    if access_token == configuration['Access-Token']:
        emails = database.fetch_all_ringer_waitlist()

        return emails
    else:
        raise HTTPException(status_code=403, detail="Invalid Access Token")
    
@app.post('/service/send_email')
async def send_service_email(request: Request):
    # Get the raw request body in bytes
    raw_request_body = await request.body()

    # Convert raw bytes of request body to str
    request_body = raw_request_body.decode('UTF-8')

    # Get access token, recipient, and subject from request headers
    client_access_token = request.headers.get('access-token')
    recipient = request.headers.get('recipient')
    subject = request.headers.get('subject')

    if client_access_token in access_tokens['tokens']:
        # Send email
        if email_interface.send_email(recipient=recipient, subject=subject, body=request_body) == 'OK':
            JSONResponse(status_code=200, content="Success!")
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error!")
    else:
        raise HTTPException(status_code=401, detail="Invalid Token!")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8005)