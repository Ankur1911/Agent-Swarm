from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools.custom_tools import db_query_tool, contact_support_tool, faq_tool
from shared.utils.load_prompt import load_prompt_template

class SupportAgent:
    def __init__(self, llm: AzureChatOpenAI):
        self.llm = llm
        self.prompt_template = load_prompt_template("shared/prompts/customer_support_prompt.txt")
        self.tools = [db_query_tool, contact_support_tool, faq_tool]

    def run(self, state):
        prompt = ChatPromptTemplate.from_template(self.prompt_template)
        chain = prompt | self.llm.bind_tools(self.tools) | StrOutputParser()
        response = chain.invoke(state)
        return {"messages": [("ai", response)]}