# Agent Swarm

## Table of Contents
1. [Introduction](#introduction)
2. [Agent Swarm Architecture](#agent-swarm-architecture)
3. [Agents](#agents)
   1. [Router Agent](#1-router-agent)
   2. [Knowledge Agent](#2-knowledge-agent)
      - [Knowledge Agent Explanation](#21-knowledge-agent-explanation) 
      - [RAG Pipeline Explanation](#22-rag-pipeline-explanation) 
   3. [Customer Support Agent](#3-customer-support-agent)
   4. [General Agent](#4-general-agent)
   5. [Personality Layer](#5-personality-layer)
4. [Configuration](#configuration)
5. [How to Run](#how-to-run)
6. [API Endpoints](#api-endpoints)
7. [Testing](#testing)
8. [Dockerization](#dockerization)
9. [Conclusion](#conclusion)

---

## Introduction
Welcome to the **Agent Swarm**! This project is a multi-agent system designed to handle various types of queries and generate responses by routing them to specialized agents. The architecture includes agents that handle queries related to **InfinitePay's products**, **customer support**, and **general queries** (e.g., news, etc.). 

The system also integrates **tools** such as the **Slack notification tool** for suspicious activities and **News retrieval tool** to fetch news based on topics or cities.

---

## Agent Swarm Architecture
The architecture of the Agent Swarm consists of the following main agents and components:

- **Router Agent**: Decides which specialized agent will handle a user's query.
- **Knowledge Agent**: Handles queries related to InfinitePay products and services.
- **Customer Support Agent**: Handles queries related to customer support.
- **General Agent**: Handles general-purpose queries and uses tools for specific needs like news and suspicious activities.
- **Personality Layer**: Enhances the response to be more user-friendly and empathetic.

![Agent Swarm Architecture](./images/agent-swarm-architecture.png)

---

## Agents

### 1. **Router Agent**
- **Role**: Decides which agent (KnowledgeAgent, CustomerSupportAgent, or GeneralAgent) should handle the incoming query based on its content.
- **Responsibilities**:
  - Routes the query to the appropriate agent.
  - Manages the workflow and data flow between agents.

### 2. **Knowledge Agent**

#### 2.1 Knowledge Agent Explanation

- **Role**: Answers questions based on publicly available content from the InfinitePay website (https://www.infinitepay.io/) or general search results.
- **Features**:
  - Uses a **Retrieval Augmented Generation (RAG)** pipeline to fetch data from the InfinitePay website.
  - If no data is found in the knowledge base, uses the **DuckDuckGo search tool**.

#### 2.2 **RAG Pipeline Explanation**

The **Knowledge Agent** uses a **Retrieval-Augmented Generation (RAG)** pipeline to handle queries efficiently. The pipeline is designed to retrieve relevant data from a pre-built knowledge base and then generate an accurate response using the retrieved information. This method ensures that the responses are grounded in factual data from InfinitePay's website and other external sources.

#### **How the RAG Pipeline Works**:
1. **Scraping Content**: The agent scrapes content from the specified InfinitePay website pages, extracting relevant sections such as headings, paragraphs, and lists.
2. **Text Chunking**: The scraped content is divided into smaller chunks of 500 words. This allows the information to be processed more efficiently and indexed for faster search results.
3. **Vectorization**: The text chunks are converted into vectors using a **HuggingFace** embeddings model (`paraphrase-multilingual-MiniLM-L12-v2`), which is used for similarity search. These vectors are stored in a **FAISS** vector database for quick retrieval.
4. **Similarity Search**: When a user submits a query, the system performs a similarity search on the vector database. It retrieves the top 3 matching documents based on their relevance to the query.
5. **Response Generation**: If relevant documents are found, they are passed to the **GPT-4 model** for response generation. If no relevant data is found in the knowledge base, the agent will use the **DuckDuckGo** search tool to search the web for relevant answers.
6. **Fallback**: If the similarity search fails to find relevant data, the system defaults to using the DuckDuckGo search tool to provide the most relevant information from external sources.

This process ensures that the **Knowledge Agent** provides accurate and contextually relevant responses to user queries, backed by the most up-to-date information from InfinitePay's website and the web.
  
#### Tools:
- **Web search using DuckDuckGo** for external general queries.

### 3. **Customer Support Agent**
- **Role**: Handles customer queries related to account issues, payment problems, and other support requests.
- **Features**:
  - Integrated with an **FAQ system** that checks the similarity of the query to frequently asked questions.
  - Uses internal **Database Tool** to retrieve user data and respond.
  - Uses **Email Tool** to notify the support team if necessary (Redirect mechanism to human).

#### Tools:
- **Database Tool** to access user data.
- **Email Tool** to notify the support team.

### 4. **General Agent**
- **Role**: Handles general-purpose queries, including those unrelated to InfinitePay or customer support.
- **Features**:
  - If the query is suspicious or illegal, the agent uses the **Slack notification tool** to alert the team (Guardrails for handle undesired questions).
  - If the query relates to news, the agent uses the **News Tool** to fetch relevant articles based on the user's city or topic(From newsdata.io API).

#### Tools:
- **Slack Notification Tool** for suspicious queries.
- **News Tool** to fetch articles based on a city or topic.

### 5. **Personality Layer**
- **Role**: Rewrites responses in a more natural, friendly, and empathetic tone to enhance user experience.

---

## Configuration

All runtime configuration is centralised in [`app/config.py`](app/config.py) using a Pydantic `Settings` model. Values are read from environment variables (and an optional `.env` file in the repo root) and **validated at startup** — if a required value is missing or malformed the process exits immediately with a clear `ConfigurationError` rather than failing later inside an agent.

### Required variables

These must always be set. The app will not boot without them.

| Variable       | Type | Description                                           |
|----------------|------|-------------------------------------------------------|
| `API_ENDPOINT` | URL  | Chat‑completions endpoint used by every agent.        |
| `API_KEY`      | str  | API key / bearer token for the LLM endpoint.          |

### Optional variables (feature‑gated)

These are **not needed for local development**. When unset, the associated feature is disabled gracefully (the agent returns a polite “not configured” message instead of crashing).

| Variable            | Type  | Enables                                           |
|---------------------|-------|---------------------------------------------------|
| `SLACK_WEBHOOK_URL` | URL   | Slack alerts for suspicious queries (GeneralAgent)|
| `NEWS_API_KEY`      | str   | newsdata.io lookups (GeneralAgent)                |
| `SUPPORT_EMAIL`     | email | Destination for escalated support tickets         |
| `SMTP_SERVER`       | str   | Outbound SMTP host                                |
| `SMTP_PORT`         | int   | Outbound SMTP port (1‑65535, e.g. `587`)          |
| `SENDER_EMAIL`      | email | From‑address for support emails                   |
| `SENDER_PASSWORD`   | str   | SMTP credential                                   |
| `ENVIRONMENT`       | str   | `development` (default) or `production`           |

> **SMTP is all‑or‑nothing.** If any of `SUPPORT_EMAIL`, `SMTP_SERVER`, `SMTP_PORT`, `SENDER_EMAIL`, `SENDER_PASSWORD` is set, they must *all* be set — partial configuration raises a validation error at startup.

### Accessing settings in code

Always go through the cached accessor — do **not** read `os.environ` directly or bind a module‑level `settings` global:

```python
from config import get_settings

def my_tool():
    cfg = get_settings()          # cached; same instance process‑wide
    requests.post(str(cfg.API_ENDPOINT), headers=cfg.llm_headers(), ...)
```

Feature flags derived from config: `cfg.slack_enabled`, `cfg.news_enabled`, `cfg.email_enabled`.

### Example `.env`

Copy [`.env.example`](.env.example) to `.env` and edit:

```env
# Required
API_ENDPOINT=https://your-llm-provider.example.com/v1/chat/completions
API_KEY=sk-your-api-key

# Optional – uncomment in production
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T000/B000/XXXX
# NEWS_API_KEY=pub_xxxxxxxxxxxxxxxx
# SUPPORT_EMAIL=support@example.com
# SMTP_SERVER=smtp.example.com
# SMTP_PORT=587
# SENDER_EMAIL=bot@example.com
# SENDER_PASSWORD=app-specific-password
```

### Local dev vs production

| Aspect          | Local development                                   | Production                                                 |
|-----------------|-----------------------------------------------------|------------------------------------------------------------|
| Source          | `.env` file in repo root                            | Real environment variables (container secrets, CI, etc.)  |
| Minimum config  | `API_ENDPOINT` + `API_KEY` only                     | All required **and** optional vars you rely on            |
| SMTP / Slack    | Usually unset — tools return a “not configured” stub | Fully configured; partial SMTP will block startup         |
| `ENVIRONMENT`   | `development` (default)                             | Set to `production`                                        |

---

## How to Run

1. **Clone the repository**:
    ```bash
    git clone https://github.com/Ankur1911/Agent-Swarm.git
    cd Agent-Swarm
    ```

2. **Install dependencies**:
    - Create a virtual environment:
      ```bash
      python3 -m venv myenv
      ```
    - Activate the virtual environment:
      ```bash
      # On Windows
      myenv\Scripts\activate
      # On Linux/macOS
      source myenv/bin/activate
      ```
    - Install the required dependencies:
      ```bash
      pip install -r requirements.txt
      ```
3. **Create a `.env` file** (see [Configuration](#configuration)):
   ```bash
   cp .env.example .env
   # then edit .env and set at least API_ENDPOINT and API_KEY
   ```
4. **Run the FastAPI application**:
    ```bash
    python main.py
    ```

5. **Access the application**:
    The app will be running on `http://localhost:8000`.

---

## API Endpoints

### POST `/ask`
- **Description**: Handles user queries by passing them to the appropriate agent for processing.
- **Request body**:
    ```json
    {
    "user_id":"client789",
    "message":"What are the rates for debit and credit card transactions?"
   }
    ```
- **Response**:
    ```json
    {
    "response": "Here are the transaction rates for card and payment link sales:\n\n- Credit card (one-time payment): 5.49%\n- Installments up to 6 times: 13.99%\n- Installments up to 12 times: 18.29%\n\nFor Pix transactions, there is no fee, so you can receive instant payments at 0.00%.",
    "source_agent_response": "As taxas para vendas no cartão e no Link de Pagamento são as seguintes:\n\n- Crédito à vista: 5,49%\n- Parcelado em 6x: 13,99%\n- Parcelado em 12x: 18,29%\n\nPara o serviço Pix, a taxa é zero, permitindo receber na hora por 0,00%.",
    "agent_workflow": [
        {
            "agent_name": "RouterAgent",
            "tool_calls": {
                "LLM": "KnowledgeAgent"
            }
        },
        [
            {
                "agent_name": "KnowledgeAgent",
                "tool_calls": {
                    "RAG": "As taxas para vendas no cartão e no Link de Pagamento são as seguintes:\n\n- Crédito à vista: 5,49%\n- Parcelado em 6x: 13,99%\n- Parcelado em 12x: 18,29%\n\nPara o serviço Pix, a taxa é zero, permitindo receber na hora por 0,00%."
                }
            }
        ],
        {
            "agent_name": "PersonalityLayer",
            "tool_calls": {
                "LLM": "Here are the transaction rates for card and payment link sales:\n\n- Credit card (one-time payment): 5.49%\n- Installments up to 6 times: 13.99%\n- Installments up to 12 times: 18.29%\n\nFor Pix transactions, there is no fee, so you can receive instant payments at 0.00%."
            }
        }
    ]
}
    ```

---

## Testing
#### Here are some [Test cases](test-cases.md)

1. **Configuration Tests**: Verify that the settings layer loads valid config, rejects missing required values, and catches malformed inputs (e.g. non‑integer `SMTP_PORT`). Run with:
    ```bash
    pytest app/tests/test_config.py -v
    ```
2. **Unit Tests**: Ensure the correct functioning of individual agents (KnowledgeAgent, CustomerSupportAgent, GeneralAgent).
3. **Integration Tests**: Test the interaction between agents (e.g., RouterAgent routing to the correct agent).
4. **API Tests**: Use tools like **Postman** or **Insomnia** to test the `/ask` endpoint.

---

## Dockerization

### Dockerfile
A **Dockerfile** is provided to containerize the application. You can build and run the container with the following commands:

1. **Build the Docker image**:
    ```bash
    docker build -t agent-swarm-app .
    ```

2. **Run the Docker container**:
    ```bash
    docker run -p 8000:8000 agent-swarm-app
    ```

3. **Access the application**:
    The app will be available at `http://localhost:8000`.

---

## Conclusion

This Agent Swarm is designed to effectively route queries to the appropriate agent based on their content. Each agent is specialized to handle different types of requests, from product-related queries to customer support and general inquiries. The system uses a variety of tools to enrich responses and ensure smooth user interaction.

For further development, consider enhancing the news-fetching capabilities, improving the suspicious query detection system, and adding more tools for a seamless user experience.

---


