import os
import requests
from dotenv import load_dotenv
from utils.load_prompt import load_prompt_template

load_dotenv()

API_ENDPOINT = os.getenv("API_ENDPOINT")
API_KEY = os.getenv("API_KEY")

HEADERS = {
    "Content-Type": "application/json",
    "api-key": API_KEY
}

class PersonalityLayer:
    def __init__(self):
        self.personality_prompt_path = "app/prompts/personality_layer_prompt.txt"

    def run(self, raw_response, Question):
        prompt=load_prompt_template(self.personality_prompt_path)
        prompt = prompt.format(raw_response=raw_response,user_message=Question)

        payload = {
            "messages": [
                {"role": "user", "content": prompt},
            ]
        }
        try:
            resp = requests.post(API_ENDPOINT, headers=HEADERS, json=payload)
            resp.raise_for_status()
            final_resp = resp.json()
            return final_resp["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Personality Error] {e}")
            return raw_response