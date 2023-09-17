from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import utils.database_interface as database

app = FastAPI()

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
        return HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8005)