import os
from langchain_openai import AzureChatOpenAI
from shared.utils.load_prompt import load_prompt_template
from graph.agent_graph import AgentGraph
import langchain

langchain.debug = True

class PersonalityLayer:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("API_ENDPOINT"),
            api_key=os.getenv("API_KEY"),
            api_version="2024-08-01-preview",
            azure_deployment="gpt-4o-chatgmp",
        )
        self.prompt_template = load_prompt_template("shared/prompts/personality_layer_prompt.txt")

    def run(self, raw_response, question):
        prompt = self.prompt_template.format(raw_response=raw_response, user_message=question)
        response = self.llm.invoke(prompt)
        return response.content

if __name__ == "__main__":
    agent_graph = AgentGraph()
    personality_layer = PersonalityLayer()
    print("Welcome to the AI Agent! Type 'exit' to quit.")
    while True:
        query = input("You: ")
        if query.lower() == "exit":
            break

        agent_response = agent_graph.run(query)
        print(f"Agent: {agent_response}")
        final_response = personality_layer.run(agent_response, query)
        print(f"Bot: {final_response}")