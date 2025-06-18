import os
import json
import sqlite3
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from duckduckgo_search import DDGS
from langchain_core.tools import tool
from bs4 import BeautifulSoup
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

# --- Database Setup ---
DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_data (
    user_id TEXT PRIMARY KEY,
    email TEXT,
    user_name TEXT,
    payment_status TEXT,
    order_status TEXT
);
"""

def init_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(DB_SCHEMA)
    cur.executemany(
        "INSERT OR IGNORE INTO user_data VALUES (?,?,?,?,?);",
        [
            ("client789", "c789@example.com", "John Doe", "Paid", "Shipped"),
            ("client790", "c790@example.com", "Jane Doe", "Pending", "Processing"),
        ],
    )
    conn.commit()
    return conn

db_connection = init_db()

@tool
def db_query_tool(user_id: str, field: str) -> str:
    """Retrieve a single field for a user from the database."""
    cur = db_connection.cursor()
    cur.execute(f"SELECT {field} FROM user_data WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else "Not found"

# --- Email Support Tool ---
@tool
def contact_support_tool(user_id: str, question: str) -> str:
    """Notify the support team and return confirmation to the user."""
    support_email = os.getenv("SUPPORT_EMAIL")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    subject = f"Support Request from User {user_id}"
    body = f"User ID: {user_id}\nQuestion: {question}"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = support_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, support_email, message.as_string())
        return f"Support has been contacted for user {user_id} regarding: {question}"
    except Exception as e:
        return f"Error contacting support: {e}"

# --- News Tool ---
@tool
def get_news_tool(topic: str) -> str:
    """Get the latest news on a specific topic."""
    api_key = os.getenv("NEWS_API_KEY")
    url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json().get("articles", [])
        return "\n".join([f"- {article['title']}" for article in articles[:5]])
    return "Could not retrieve news."

# --- Slack Notification Tool ---
@tool
def send_slack_notification_tool(user_id: str, message: str) -> str:
    """Send a Slack notification for suspicious activity."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    payload = {"text": f"Suspicious activity from user {user_id}: {message}"}
    response = requests.post(webhook_url, json=payload)
    if response.status_code == 200:
        return "Slack notification sent."
    return "Failed to send Slack notification."

# --- Web Search Tool ---
@tool
def duckduckgo_search_tool(query: str) -> str:
    """Perform a web search using DuckDuckGo."""
    with DDGS() as ddgs:
        results = [r["body"] for r in ddgs.text(query, max_results=3)]
        return "\n".join(results)



# --- FAQ Data and Tool ---
faq_list = [
    {"question": "How can I Contact Support?", "answer": "You can contact support by support@example.com"},
    {"question": "How do I reset my password?", "answer": "You can reset your password by going to the settings page and clicking on 'Reset Password'."},
    {"question": "What is policy on refunds?", "answer": "Our refund policy allows you to request a refund within 30 days of purchase if you are not satisfied with the product."}
]

@tool
def faq_tool(question: str) -> str:
    """
    Use this tool to answer frequently asked questions.
    """
    for faq in faq_list:
        if faq["question"].lower() in question.lower():
            return faq["answer"]
    return "No answer found for this question in the FAQ."

# --- RAG Tool ---
class RAGTool:
    def __init__(self):
        self.vectorstore = self._build_knowledge_base()

    def _scrape(self, url: str) -> str:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            return " ".join(t.get_text().strip() for t in soup.find_all(['p', 'h1', 'h2']))
        except Exception as e:
            return f"Error scraping {url}: {e}"

    def _build_knowledge_base(self):
        pages = [
             "https://www.infinitepay.io",
            "https://www.infinitepay.io/maquininha",
            "https://www.infinitepay.io/maquininha-celular",
            "https://www.infinitepay.io/tap-to-pay",
            "https://www.infinitepay.io/pdv",
            "https://www.infinitepay.io/receba-na-hora",
            "https://www.infinitepay.io/gestao-de-cobranca",
            "https://www.infinitepay.io/gestao-de-cobranca-2",
            "https://www.infinitepay.io/link-de-pagamento",
            "https://www.infinitepay.io/loja-online",
            "https://www.infinitepay.io/boleto",
            "https://www.infinitepay.io/conta-digital",
            "https://www.infinitepay.io/conta-pj",
            "https://www.infinitepay.io/pix",
            "https://www.infinitepay.io/pix-parcelado",
            "https://www.infinitepay.io/emprestimo",
            "https://www.infinitepay.io/cartao",
            "https://www.infinitepay.io/rendimento"
        ]
        all_text = ""
        for page in pages:
            all_text += self._scrape(page)

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = text_splitter.split_text(all_text)

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return FAISS.from_texts(chunks, embeddings)

    @tool
    def rag_tool(self, query: str) -> str:
        """
        Use this tool to answer questions about the company's products and services.
        """
        if self.vectorstore:
            docs = self.vectorstore.similarity_search(query)
            return "\n".join([doc.page_content for doc in docs])
        return "Knowledge base not initialized."

# Instantiate the RAGTool to create the rag_tool
rag_tool_instance = RAGTool()
rag_tool = rag_tool_instance.rag_tool