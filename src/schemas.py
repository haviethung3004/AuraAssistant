from pydantic import BaseModel, Field
from typing_extensions import TypedDict, Literal
from langgraph.graph import MessagesState

class RouterSchema(BaseModel):
    """
    Schema for the router output
    """
    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )
    classification: Literal["ignore", "respond", "notify"] = Field(
        description="The classification of an email: 'ignore' for irrelevant emails, "
        "'notify' for important information that doesn't need a response, "
        "'respond' for emails that need a reply",
    )


class StateInput(TypedDict):
    """
    Input for the state
    """
    # This is the input to the state
    email_input: dict  # The input email to be processed by the state


class State(MessagesState):
    """
    State for the task processing
    """
    email_input: dict
    classification_decision: Literal["ignore", "respond", "notify"]