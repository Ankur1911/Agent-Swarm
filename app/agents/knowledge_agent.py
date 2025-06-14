import os
import requests
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFacePipeline, HuggingFaceEmbeddings
from transformers import pipeline
import json
from dotenv import load_dotenv

from utils.load_prompt import load_prompt_template
from utils.tools import duckduckgo_tool

load_dotenv()

# Tool Function for DuckDuckGo Search
def duckduckgo_search_tool(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            return {"tool_name":"duckduckgo_search_tool","Response":"\n".join(r['body'] for r in results)}
    except Exception as e:
        return f"Error during search: {e}"

TOOLS = [duckduckgo_tool]

class KnowledgeAgent:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': 'cpu'}
        )
        text_generation_pipeline = pipeline(
            "text-generation", 
            model="pierreguillou/gpt2-small-portuguese",
            max_new_tokens=150,
            temperature=0.7,
            do_sample=True,
            return_full_text=False,
            pad_token_id=50256,
            truncation=True
        )

        self.generator = HuggingFacePipeline(pipeline=text_generation_pipeline)
        self.vectorstore = None
        self.pages = [
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
        self.prompt_template_path = "app/prompts/knowledge_agent_prompt.txt"
        self._build_knowledge_base()

    def _scrape(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            texts = soup.find_all(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div'])
            return "\n".join(t.get_text().strip() for t in texts if len(t.get_text().strip()) > 10)
        except Exception as e:
            print(f"Scrape error for {url}: {e}")
            return ""

    def _chunk_text(self, text, chunk_size=500):
        words = text.split()
        return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

    # Build the knowledge base by scraping the pages and chunking the text
    def _build_knowledge_base(self):
        chunks = []
        for page in self.pages:
            content = self._scrape(page)
            if content:
                for chunk in self._chunk_text(content):
                    chunks.append({"content": chunk, "source": page})
                print(f"Scraped {len(chunks)} chunks from {page}")
            
        texts = [c["content"] for c in chunks]
        metadatas = [{"source": c["source"]} for c in chunks]
        if texts:
            self.vectorstore = FAISS.from_texts(texts=texts, embedding=self.embeddings, metadatas=metadatas)

    # Generate a response using the GPT-4 API
    def generate_with_gpt4_api(self, messages, tools=None):
        api_url = os.getenv("API_ENDPOINT")
        api_key = os.getenv("API_KEY")
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        payload = {
            "model": "gpt-4o-chatgmp",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 150
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        res = requests.post(api_url, headers=headers, data=json.dumps(payload))
        if res.status_code == 200:
            return res.json()
        return {"error": res.text}

    # Handle the user's message by searching the knowledge base and generating a response
    def handle(self, user_id:str, message:str):
        if not self.vectorstore:
            return "Knowledge base is not initialized."
        docs = self.vectorstore.similarity_search(message, k=3)

        if docs:
            context = "\n\n".join(doc.page_content for doc in docs)
            prompt = load_prompt_template(self.prompt_template_path)
            final_prompt = prompt.format(context=context)
            messages = [
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": f"QUESTION: {message}"}
            ]
            result = self.generate_with_gpt4_api(messages,TOOLS)

            message = result["choices"][0]["message"]
            if message.get("tool_calls"):
                tool_call = message["tool_calls"][0] 
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                if function_name == "duckduckgo_search_tool":
                    return duckduckgo_search_tool(function_args['query'])
            
            return {"tool_name":"RAG","Response":message.get('content', 'No response')}

        else:
            return duckduckgo_search_tool(message)
