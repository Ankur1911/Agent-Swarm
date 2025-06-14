import os
import json
import requests
from dotenv import load_dotenv

from utils.load_prompt import load_prompt_template
from utils.tools import send_slack_notification, get_news
load_dotenv()

API_ENDPOINT = os.getenv("API_ENDPOINT")
API_KEY       = os.getenv("API_KEY")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

HEADERS = {
    "Content-Type": "application/json",
    "api-key": API_KEY
}

TOOLS = [send_slack_notification, get_news]

# Get news tool function to fetch latest news articles based on a topic
def get_news_tool(topic: str) -> str:
    try:
        url = f"https://newsdata.io/api/1/latest?apikey=pub_2d18ef10b18a49d198e4bb200a7b3e0e&q={topic}"
        
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        results = data.get("results", [])

        top_articles = results[:10]

        titles = [
        f"{i+1}. {article['title']}"
        for i, article in enumerate(top_articles)
        if "title" in article
        ]
    
        return {"tool_name":"get_news_tool","Response":"\n".join(titles)}

    except Exception as e:
        return f"Error retrieving news: {e}"

# Function to send a Slack notification when suspicious activity is detected    
def send_slack_notification_tool(user_id:str, message: str):
        
        payload = {
            "text": f"🚨 **Suspicious Activity Detected** 🚨 \n\nFrom : {user_id}\n\nMessage:{message}",
            "channel": "#alert"  # Slack channel name
        }
        
        try:
            response = requests.post(SLACK_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            return {"tool_name": "slack_notification", "Response": "Found suspecious activity. Slack notification sent to our team successfully."}
        except requests.exceptions.RequestException as e:
            print(f"Error sending Slack notification: {e}")


class GeneralAgent:
    def __init__(self):
        self.prompt_template_path = "app/prompts/general_agent_prompt.txt"

    def handle(self, user_id: str, question: str) -> str:

        system_prompt = load_prompt_template(self.prompt_template_path)

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {question} User ID: {user_id}"} 
            ],
            "tools" : TOOLS,
            "tool_choice" : "auto"
        }

        try:
            resp = requests.post(
                API_ENDPOINT,
                headers=HEADERS,
                json=payload
            )
            resp.raise_for_status()
            response_data = resp.json()
            
            message = response_data["choices"][0]["message"]
            if message.get("tool_calls"):
                tool_call = message["tool_calls"][0] 
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                if function_name == "send_slack_notification_tool":
                    return send_slack_notification_tool(function_args['user_id'],function_args['message'])
                if function_name == "get_news_tool":
                    return get_news_tool(function_args['topic'])
            elif message.get("content"):
                return {"tool_name":"llm_response","Response": message["content"]}
            else:
                return {"tool_name":"Error","Response":"No content found in the response."}
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return "Sorry, there was an error processing your request."
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return "Sorry, there was an error processing the response."
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "Sorry, an unexpected error occurred."

        return "No data found"