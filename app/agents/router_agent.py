import json
import requests
from config import get_settings
from utils.load_prompt import load_prompt_template
from agents.knowledge_agent import KnowledgeAgent
from agents.customer_support_agent import SupportAgent
from agents.general_agent import GeneralAgent
from agents.personality_layer import PersonalityLayer

# Init agents
print("Initializing agents...")
knowledge_agent = KnowledgeAgent()
support_agent = SupportAgent()
general_agent = GeneralAgent()
personality_layer = PersonalityLayer()

class RouterAgent:
    def __init__(self):
        self.agents = {
            "KnowledgeAgent": knowledge_agent,
            "CustomerSupportAgent": support_agent,
            "GeneralAgent": general_agent,
            "PersonalityLayer": personality_layer
        }
        self.agent_prompt_path = "app/prompts/router_agent_prompt.txt"

    # Call the LLM to decide which agent to use based on user input
    def decide_agent(self, user_input):
        cfg = get_settings()
        system_prompt = load_prompt_template(self.agent_prompt_path)
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        }
        try:
            resp = requests.post(str(cfg.API_ENDPOINT), headers=cfg.llm_headers(), json=payload)
            resp.raise_for_status()
            response = resp.json()
            agent_name = response["choices"][0]["message"]["content"].strip()
            return agent_name if agent_name in self.agents else "KnowledgeAgent"
        except Exception as e:
            print(f"[Router Error] {e}")
            return "KnowledgeAgent" 

    # Run the chosen agent based on LLM decision
    def run(self, user_id, user_input):
        chosen_agent_name = self.decide_agent(user_input)
        agent = self.agents[chosen_agent_name]
        
        if chosen_agent_name == "CustomerSupportAgent":
            raw_response = agent.handle(user_id, user_input)
        elif chosen_agent_name == "KnowledgeAgent":
            raw_response = agent.handle(user_id, user_input)
        elif chosen_agent_name == "GeneralAgent":
            raw_response = agent.handle(user_id, user_input)
        else:
            print("Not able to answer this question, please try again later.")

        tool_output=""
        agent_workflow = [{"agent_name": "RouterAgent","tool_calls": {"LLM": chosen_agent_name}}]
        if isinstance(raw_response, dict):
            tool_name = raw_response.get("tool_name", "llm_response")
            tool_output = raw_response.get("Response", "")
            agent_workflow.append([{
                "agent_name": chosen_agent_name,
                "tool_calls": {
                    tool_name: tool_output
                }
            }])
            source_response = tool_output
        else:
            tool_name = "llm_response"
            tool_output = raw_response
            agent_workflow.append([{
                "agent_name": chosen_agent_name,
                "tool_calls": {
                    tool_name: tool_output
                }
            }])
            source_response = tool_output
        
        response = personality_layer.run(tool_output, user_input)

        agent_workflow.append({
            "agent_name": "PersonalityLayer",
            "tool_calls": {"LLM": response}
        })

        return {
        "response": response,
        "source_agent_response": source_response,
        "agent_workflow": agent_workflow
        }