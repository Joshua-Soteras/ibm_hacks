from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

IBM_API_KEY = os.getenv("IBM_API_KEY")

@app.get("/")
def root():
    return {"message": f"Hello, World!"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)