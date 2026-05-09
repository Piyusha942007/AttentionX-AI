import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

print("Listing models...")
for m in client.models.list():
    print(f" - {m.name}")
