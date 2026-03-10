from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
import os
import io
import base64
import requests

load_dotenv()

app = FastAPI(title="U&Me AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

personality_prompts = {
    "helpful": "helpful, accurate and friendly",
    "professional": "professional, formal and precise",
    "friendly": "very friendly, warm and encouraging",
    "funny": "funny, witty and humorous while still being helpful",
    "teacher": "a patient teacher who explains everything clearly with examples"
}

class ChatInput(BaseModel):
    message: str
    history: list = []
    document_text: str = ""
    image_base64: str = ""
    language: str = "English"
    personality: str = "helpful"

def extract_text_from_pdf(file_bytes):
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except:
        return ""

def extract_text_from_docx(file_bytes):
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except:
        return ""

def extract_text_from_txt(file_bytes):
    try:
        return file_bytes.decode("utf-8")
    except:
        return ""

def search_newsapi(query):
    try:
        if not NEWS_API_KEY:
            return ""
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "apiKey": NEWS_API_KEY,
            "pageSize": 3,
            "sortBy": "publishedAt",
            "language": "en"
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data.get("status") == "ok" and data.get("totalResults", 0) > 0:
            search_text = "Latest News:\n"
            for article in data["articles"][:3]:
                if article.get("title") and article.get("description"):
                    search_text += f"- {article['title']}: {article['description']}\n"
            return search_text
    except:
        pass
    return ""

def search_duckduckgo(query):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query + " 2025 2026", max_results=3))
            if results:
                search_text = "Web Search:\n"
                for r in results:
                    search_text += f"- {r['title']}: {r['body']}\n"
                return search_text
    except:
        pass
    return ""

def search_wikipedia(query):
    try:
        import wikipedia
        summary = wikipedia.summary(query, sentences=3)
        return f"Wikipedia: {summary}"
    except:
        pass
    return ""

def search_all(query):
    results = ""
    # Try NewsAPI first (most current)
    news = search_newsapi(query)
    if news:
        results += news + "\n"
    # Try DuckDuckGo
    ddg = search_duckduckgo(query)
    if ddg:
        results += ddg + "\n"
    # Try Wikipedia
    wiki = search_wikipedia(query)
    if wiki:
        results += wiki + "\n"
    return results

def needs_web_search(message):
    keywords = [
        "latest", "current", "today", "news", "recent",
        "2024", "2025", "2026", "who won", "price",
        "weather", "score", "result", "live", "trending",
        "captain", "president", "prime minister", "ceo",
        "match", "election", "stock", "movie", "released",
        "who is", "what is", "when did", "happening"
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in keywords)

@app.get("/")
def home():
    return {"message": "U&Me AI is running!"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        filename = file.filename.lower()

        if filename.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            image_base64 = base64.b64encode(file_bytes).decode("utf-8")
            extension = filename.split(".")[-1]
            if extension == "jpg":
                extension = "jpeg"
            return {
                "status": "success",
                "type": "image",
                "filename": file.filename,
                "image_base64": image_base64,
                "media_type": f"image/{extension}",
                "message": "Image uploaded successfully!"
            }
        elif filename.endswith(".pdf"):
            text = extract_text_from_pdf(file_bytes)
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(file_bytes)
        elif filename.endswith(".txt"):
            text = extract_text_from_txt(file_bytes)
        else:
            return {
                "status": "error",
                "message": "Supported files: PDF, DOCX, TXT, JPG, PNG!"
            }

        if not text:
            return {
                "status": "error",
                "message": "Could not read the document!"
            }

        return {
            "status": "success",
            "type": "document",
            "filename": file.filename,
            "text": text[:5000],
            "message": "Document uploaded successfully!"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/chat")
def chat(input: ChatInput):
    try:
        web_context = ""
        if needs_web_search(input.message):
            print(f"Searching all sources for: {input.message}")
            web_context = search_all(input.message)

        messages = [
            {
                "role": "system",
                "content": f"""You are U&Me AI. Your personality is {personality_prompts.get(input.personality, 'helpful and friendly')}.
                You can help with anything - answer questions, write code, translate languages,
                detect fake news, solve math, write essays, give advice, and much more.
                Always respond in {input.language} language.
                Today's date is March 2026.
                IMPORTANT: NEVER say 'as of my knowledge cutoff'.
                NEVER say 'I dont have current information'.
                When search results are provided ALWAYS use them for accurate answers.
                Always give complete and detailed answers."""
            }
        ]

        if web_context:
            messages.append({
                "role": "system",
                "content": f"Real time search results from multiple sources:\n{web_context}\nUse this to give the most accurate and current answer."
            })

        if input.document_text:
            messages.append({
                "role": "system",
                "content": f"User uploaded document:\n\n{input.document_text}\n\nAnswer questions based on this."
            })

        for msg in input.history:
            messages.append(msg)

        if input.image_base64:
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{input.image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": input.message if input.message else "What is in this image?"
                    }
                ]
            })
        else:
            messages.append({
                "role": "user",
                "content": input.message
            })

        model = "meta-llama/llama-4-scout-17b-16e-instruct" if input.image_base64 else "llama-3.3-70b-versatile"

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048,
            temperature=0.7
        )

        reply = response.choices[0].message.content

        return {
            "reply": reply,
            "status": "success",
            "web_searched": bool(web_context)
        }

    except Exception as e:
        return {
            "reply": "Sorry I encountered an error. Please try again!",
            "status": "error",
            "error": str(e)
        }
