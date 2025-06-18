from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools.custom_tools import get_news_tool, send_slack_notification_tool
from shared.utils.load_prompt import load_prompt_template

class GeneralAgent:
    def __init__(self, llm: AzureChatOpenAI):
        self.llm = llm
        self.prompt_template = load_prompt_template("shared/prompts/general_agent_prompt.txt")
        self.tools = [get_news_tool, send_slack_notification_tool]

    def run(self, state):
        prompt = ChatPromptTemplate.from_template(self.prompt_template)
        chain = prompt | self.llm.bind_tools(self.tools) | StrOutputParser()
        response = chain.invoke(state)
        return {"messages": [("ai", response)]}