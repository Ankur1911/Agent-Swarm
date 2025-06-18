from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools.custom_tools import duckduckgo_search_tool, RAGTool
from shared.utils.load_prompt import load_prompt_template

class KnowledgeAgent:
    def __init__(self, llm: AzureChatOpenAI):
        self.llm = llm
        self.prompt_template = load_prompt_template("shared/prompts/knowledge_agent_prompt.txt")
        rag_tool_instance = RAGTool()
        self.tools = [duckduckgo_search_tool,rag_tool_instance.rag_tool]

    def run(self, state):
        prompt = ChatPromptTemplate.from_template(self.prompt_template)
        chain = prompt | self.llm.bind_tools(self.tools) | StrOutputParser()
        response = chain.invoke(state)
        return {"messages": [("ai", response)]}