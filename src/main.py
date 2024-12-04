from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import utils.database_interface as database
from utils import email_interface
import yaml
from contextlib import asynccontextmanager
import os
import json
import requests
import uuid
import secrets
import hashlib

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

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
    
@app.post('/admin/create_credentials')
async def create_credentials(request: Request, name: str = Form()):
    # Get auth info
    username = request.cookies.get("LIF_USERNAME")
    token = request.cookies.get("LIF_TOKEN")

    # Verify credentials with auth server
    auth_response = requests.post(
        f'{configuration['auth-url']}/auth/verify_token?permissions=mailservice.create_credentials',
        data={
            "username": username,
            "token": token
        }
    )

    if auth_response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid token!")
    elif auth_response.status_code == 403:
        raise HTTPException(status_code=403, detail="No permission!")
    elif auth_response.status_code != 200:
        raise HTTPException(status_code=500, detail='Internal server error')
    
    # Generate client id and secret
    client_id = str(uuid.uuid4())
    client_secret = secrets.token_hex(16)
    client_secret_salt = secrets.token_hex(16)
    client_secret_hash_object = hashlib.sha256(f"{client_secret}{client_secret_salt}".encode())
    client_secret_hash_hex = client_secret_hash_object.hexdigest()

    # Add credentials to database
    await database.credentials.create_credentials(
        name=name,
        client_id=client_id,
        client_secret_hash=client_secret_hash_hex,
        secret_salt=client_secret_salt
    )

    return {"name": name, "client_id": client_id, "client_secret": client_secret}

@app.api_route('/admin/modify_permissions/{client_id}', methods=["POST", "DELETE"])
async def modify_permissions(request: Request, client_id: str):
    # Get auth info
    username = request.cookies.get("LIF_USERNAME")
    token = request.cookies.get("LIF_TOKEN")

    # Verify credentials with auth server
    auth_response = requests.post(
        f'{configuration['auth-url']}/auth/verify_token?permissions=mailservice.modify_permissions',
        data={
            "username": username,
            "token": token
        }
    )

    if auth_response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid token!")
    elif auth_response.status_code == 403:
        raise HTTPException(status_code=403, detail="No permission!")
    elif auth_response.status_code != 200:
        raise HTTPException(status_code=500, detail='Internal server error')
    
    # Check if credentials exist
    if not await database.credentials.get_credentials(client_id=client_id):
        raise HTTPException(status_code=404, detail="Credentials not found")
    
    # Get Request Body
    request_body = await request.json()
    
    # Check request method
    if request.method == "DELETE":
        await database.permissions.remove_permissions(
            client_id=client_id,
            permissions=request_body
        )

        return "ok"
    else:
        await database.permissions.add_permissions(
            client_id=client_id,
            permissions=request_body
        )

        return "ok"
    
@app.get("/admin/get_permissions/{client_id}")
async def get_permissions(request: Request, client_id: str):
    # Get auth info
    username = request.cookies.get("LIF_USERNAME")
    token = request.cookies.get("LIF_TOKEN")

    # Verify credentials with auth server
    auth_response = requests.post(
        f'{configuration['auth-url']}/auth/verify_token?permissions=mailservice.view_permissions',
        data={
            "username": username,
            "token": token
        }
    )

    if auth_response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid token!")
    elif auth_response.status_code == 403:
        raise HTTPException(status_code=403, detail="No permission!")
    elif auth_response.status_code != 200:
        raise HTTPException(status_code=500, detail='Internal server error')
    
    # Get credentials and ensure they exist
    credentials = await database.credentials.get_credentials(client_id=client_id)

    if not credentials:
        raise HTTPException(status_code=404, detail="Credentials not found")
    
    # Get permissions
    permissions = await database.permissions.get_permissions(client_id=client_id)

    return {
        "name": credentials['name'],
        "client_id": credentials['client_id'],
        "permissions": permissions
    }

@app.delete('/admin/remove_credentials/{client_id}')
async def remove_credentials(request: Request, client_id: str):
    # Get auth info
    username = request.cookies.get("LIF_USERNAME")
    token = request.cookies.get("LIF_TOKEN")

    # Verify credentials with auth server
    auth_response = requests.post(
        f'{configuration['auth-url']}/auth/verify_token?permissions=mailservice.remove_credentials',
        data={
            "username": username,
            "token": token
        }
    )

    if auth_response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid token!")
    elif auth_response.status_code == 403:
        raise HTTPException(status_code=403, detail="No permission!")
    elif auth_response.status_code != 200:
        raise HTTPException(status_code=500, detail='Internal server error')
    
    # Check if credentials exist
    if not await database.credentials.get_credentials(client_id=client_id):
        raise HTTPException(status_code=404, detail="Credentials not found")
    
    # Delete credentials and all associated permission nodes from database
    await database.credentials.remove_credentials(client_id=client_id)

    return "ok"

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8005)