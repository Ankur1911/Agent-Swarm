db_query = {
        "type": "function",
        "function": {
            "name": "db_query_tool",
            "description": "Retrieve a single field for a user from the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The user's unique identifier"},
                    "field": {
                        "type": "string", 
                        "enum": ["email", "user_name", "payment_status", "order_status"],
                        "description": "The database column to retrieve"
                    }
                },
                "required": ["user_id", "field"]
            }
        }
    }


contact_support = {
        "type": "function",
        "function": {
            "name": "contact_support_tool",
            "description": "Notify the support team and return confirmation to user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The user's unique identifier"},
                    "question": {"type": "string", "description": "The user's original question"}
                },
                "required": ["user_id", "question"]
            }
        }
    }

send_slack_notification = {
        "type": "function",
        "function": {
            "name": "send_slack_notification_tool",
            "description": "Use this when Found some suspicious or illegal activity in the user query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User's id."},
                    "message": {"type": "string", "description": "User's original question."}
                },
                "required": ["user_id", "message"]
            }
        }
    }
get_news = {
        "type": "function",
        "function": {
            "name": "get_news_tool",
            "description": "Use this to get the latest news on a specific topic or city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The topic to get news about."}
                },
                "required": ["topic"]
            }
        }
    }

duckduckgo_tool = {
        "type": "function",
        "function": {
            "name": "duckduckgo_search_tool",
            "description": "Use this when no relevant company document is found. It performs a general-purpose web search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "User's original question."}
                },
                "required": ["query"]
            }
        }
    }