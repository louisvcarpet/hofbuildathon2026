
from langgraph.graph import StateGraph, START, END
from ai_mailroom.node1_filter.chatbot import MailRoomChatBot
from ai_mailroom.node2_tool.client import MCPClient
from ai_mailroom.node3_verify.output_checker import OutputChecker
from ai_mailroom.node4_display.display import testDisplay
from state import MailRoomState
from ai_mailroom.node1_filter.request_prompt import FILTER_PROMPT
from ai_mailroom.node3_verify.output_checker import CHECKER_PROMPT
from ai_mailroom.node2_tool.client_prompt import CLIENTPROMPT
import asyncio


def router(state: MailRoomState):
    """
    Router function to determine the next node based on the output checker state.
    """
    # if state.tryout > state.maxtry:
    #     state.output_checker = "yes"
    #     state.result = "I am sorry, our database cannot answer your question. Please try again later with more specific info."
    #     return END
    print("output_checker:", state.output_checker)
    if state.tryout > state.maxtry:
        state.output_checker = "yes"
        state.result = "I am sorry, our database cannot answer your question. Please try again later with more specific info."
        return "display"
    elif state.output_checker == "yes":
        return "display"
    elif state.output_checker == "no":
        return "client"
    # return END
    
async def mailbot(user_input: str):

    chatNode  = MailRoomChatBot(prompt=FILTER_PROMPT, user_input=user_input)
    clientNode = MCPClient(prompt =CLIENTPROMPT)
    checkerNode = OutputChecker(prompt=CHECKER_PROMPT)
    displayNode = testDisplay()
    workflow = StateGraph(MailRoomState)
    workflow.add_node("chat", chatNode)
    workflow.add_node("client", clientNode)
    workflow.add_node("verify", checkerNode)
    workflow.add_node("display", displayNode)
  
    workflow.add_edge(START, "chat")
    workflow.add_edge("chat", "client")
    workflow.add_edge("client", "verify")
    workflow.add_conditional_edges(
        "verify", 
        router, 
        {
            "display": "display",
            "client": "client"
        }
    )
    # workflow.set_finish_point(END)  # <-- Add this line
    workflow.add_edge("display", END)
   
    mailroom  = workflow.compile()
    return await mailroom.ainvoke(MailRoomState(user_input=user_input))
    
if __name__ == "__main__":
    import asyncio
    result = asyncio.run(mailbot("How many packages does Frank Lin have?"))
    print(result)

