import os
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from agents.general_agent import GeneralAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.support_agent import SupportAgent
from graph.state import AgentState
from tools.custom_tools import (
    db_query_tool, contact_support_tool, send_slack_notification_tool,
    get_news_tool, duckduckgo_search_tool, faq_tool, rag_tool
)
from shared.utils.load_prompt import load_prompt_template

class AgentGraph:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("API_ENDPOINT"),
            api_key=os.getenv("API_KEY"),
            api_version="2024-08-01-preview",
            azure_deployment="gpt-4o-chatgmp",
        )
        self.knowledge_agent = KnowledgeAgent(self.llm)
        self.support_agent = SupportAgent(self.llm)
        self.general_agent = GeneralAgent(self.llm)
        self.tools = [
            db_query_tool, contact_support_tool, send_slack_notification_tool,
            get_news_tool, duckduckgo_search_tool, faq_tool, rag_tool
        ]
        self.tool_node = ToolNode(self.tools)
        self.graph = self._build_graph()

    def _router(self, state):
        """
        This function acts as the main router. It is NOT a node, but the conditional
        logic that directs the graph from the entry point.
        """
        # This line was causing the error because 'state' did not have 'messages'.
        # Now it will, because this function receives the initial graph state.
        message_content = state["messages"][-1][1]

        router_prompt = load_prompt_template("shared/prompts/router_agent_prompt.txt")
        prompt = router_prompt.format(messages=message_content)
        response = self.llm.invoke(prompt)
        return response.content.strip()

    def _run_personality_layer(self, state):
        # This function remains the same.
        last_message = state["messages"][-1]
        raw_response = ""
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            # Handle the case where the last message is a tool result
            # We'll create a generic confirmation message.
            raw_response = "The requested action was completed successfully."
        elif hasattr(last_message, 'content'):
            raw_response = last_message.content
        else: # Fallback for other message types
            raw_response = str(last_message)


        user_question = state["messages"][0][1] # Get original user question
        personality_prompt_template = load_prompt_template("shared/prompts/personality_layer_prompt.txt")
        prompt = personality_prompt_template.format(raw_response=raw_response, user_message=user_question)
        final_response = self.llm.invoke(prompt)
        return {"messages": [final_response]}

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Add all the nodes
        workflow.add_node("knowledge_agent", self.knowledge_agent.run)
        workflow.add_node("support_agent", self.support_agent.run)
        workflow.add_node("general_agent", self.general_agent.run)
        workflow.add_node("tool_node", self.tool_node)
        workflow.add_node("personality_layer", self._run_personality_layer)

        # ** GRAPH FLOW CORRECTION **
        # The graph starts at the special "__start__" entry point.
        # From there, it uses the _router function to decide which agent to go to.
        workflow.add_conditional_edges(
            "__start__",
            self._router,
            {
                "KnowledgeAgent": "knowledge_agent",
                "SupportAgent": "support_agent",
                "GeneralAgent": "general_agent",
            }
        )

        # After an agent runs, we check if it needs to use a tool
        agent_to_tools_edge = {
            "tools": "tool_node",
            "__end__": "personality_layer" # If no tools, go directly to personality_layer
        }
        workflow.add_conditional_edges("knowledge_agent", tools_condition, agent_to_tools_edge)
        workflow.add_conditional_edges("support_agent", tools_condition, agent_to_tools_edge)
        workflow.add_conditional_edges("general_agent", tools_condition, agent_to_tools_edge)

        # After a tool is used, the output always goes to the personality layer
        workflow.add_edge("tool_node", "personality_layer")

        # The personality layer is the final step before the end
        workflow.add_edge("personality_layer", END)

        return workflow.compile()

    def run(self, query):
        return self.graph.invoke({"messages": [("user", query)]})