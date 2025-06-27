from typing import Literal

# Import llm
from langchain_google_genai import ChatGoogleGenerativeAI

# Schema for the router output
from schemas import RouterSchema, State, StateInput
from prompts import default_background, triage_system_prompt, agent_system_prompt, default_response_preferences, default_cal_preferences

# Import tools
from tools.gmail_tools import (
    list_latest_gmail_messages,
    list_latest_messages_id,
    get_gmail_message_content,
    send_gmail_message
)

# Load the env file
from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv(), override=True)


# Initialize the LLM for user with router / structure output
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, api_key=os.getenv("GOOGLE_API_KEY"))
llm_router = llm.with_structured_output(RouterSchema)


# Initialize the LLM, enforcing tool use for agent
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, api_key=os.getenv("GOOGLE_API_KEY"))
llm_with_tools = llm.bind_tools(tools=[list_latest_gmail_messages,list_latest_messages_id, get_gmail_message_content,send_gmail_message], tool_choice="any")



AGENT_TOOLS_PROMPT = """
1. **list_latest_gmail_messages**: List the latest Gmail messages in the user's inbox.
2. **list_latest_messages_id**: List the IDs of the latest messages in the user's inbox.
3. **get_gmail_message_content**: Retrieve the content of a specific Gmail message
4. **send_gmail_message**: Send a Gmail message to a specified recipient.
"""

# Node
def llm_call(state: State):
    """
    LLM decides whether to call a tool or not
    """
    return {
        "messages": [
            llm_with_tools.invoke(
                [
                    {"role": "system", "content": agent_system_prompt.format(
                        tools_prompt=AGENT_TOOLS_PROMPT,
                        background=default_background,
                        response_preferences=default_response_preferences, 
                        cal_preferences=default_cal_preferences)
                    },
                    
                ]
                + state["messages"]
            )
        ]
    }

if __name__ == "__main__":
    result = llm_router.invoke(input="Classify the following email:\n\nSubject: Meeting Request\nFrom:haviethung300409@gmail.com")
    print(result)