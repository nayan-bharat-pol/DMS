import os
import google.generativeai as genai

# Set up proxy authentication
os.environ["HTTP_PROXY"] = "http://mio1na:PassioM@!2022@10.171.234.13:8080"
os.environ["HTTPS_PROXY"] = "http://mio1na:PassioM@!2022@10.171.234.13:8080"

# Configure Gemini API
genai.configure(api_key=os.getenv("AIzaSyBlzuF6xA2jKzTTywVU00nnCuauw7affPA"))