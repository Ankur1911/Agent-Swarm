import requests
from config import get_settings
from utils.load_prompt import load_prompt_template


class PersonalityLayer:
    def __init__(self):
        self.personality_prompt_path = "app/prompts/personality_layer_prompt.txt"

    def run(self, raw_response, Question):
        cfg = get_settings()
        prompt=load_prompt_template(self.personality_prompt_path)
        prompt = prompt.format(raw_response=raw_response,user_message=Question)

        payload = {
            "messages": [
                {"role": "user", "content": prompt},
            ]
        }
        try:
            resp = requests.post(str(cfg.API_ENDPOINT), headers=cfg.llm_headers(), json=payload)
            resp.raise_for_status()
            final_resp = resp.json()
            return final_resp["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Personality Error] {e}")
            return raw_response