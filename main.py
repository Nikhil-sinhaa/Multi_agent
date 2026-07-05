import os
from typing import TypedDict,Annotated
import operator
import asyncio
import psycopg
from langgraph.graph import StateGraph, START,END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import(
    AnyMessage,
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage
)
from langchain_groq import ChatGroq
#from tools.tavily_tool import tavily_search
from mcp.client import tavily_mcp_search
from tools.flight_tool import search_flight

from dotenv import load_dotenv
load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
)
DATABASE_URL = os.getenv("DATABASE_URL")

from mcp_client import(
    tavily_mcp_search,
    aviation_mcp_call,
    get_airports,
    get_airlines
)
class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage],operator.add]
    user_query:str
    flight_results:str
    hotel_results:str
    itinerary:str
    llm_calls:int

# def flight_agent(state:TravelState):
#     query = f"best hotel for {state['user_query']}"
#     flight_data = search_flight(query)
#     return {
#         "flight_results":flight_data,
#         "messages" : [
#             AIMessage(content= f"Flight results fetched")
#         ],
#         "llm_calls" : state.get("llm_calls",0) + 1
#     }

FLIGHT_AGENT_PROMPT = """
You are an expert travel agent.
User Query:
{query}

Airport Information:
{airport_data}

Airline Information:
{airline_data}

Generate:
1. Likely departure airport
2. Likely arrival airport
3. Airlines serving this route
4. Typical flight duration
5. Estimated airfare range
6. Peak season pricing warinin
7. Booking advice

Return concise travel guidance.
"""

def flight_agent(state: TravelState):
    print("\nINSIDE FLIGHT AGENT\n")
    query = state["user_query"]

    try:

        airports = asyncio.run(
            aviation_mcp_call(
                "list_airport"
            )
        )
        airlines = asyncio.run(
            aviation_mcp_call(
                "list_airlines"
            )
        )

        prompt = FLIGHT_AGENT_PROMPT.format(
            query = query,
            airport_data = str(airports)[:3000],
            airline_data = str(airlines)[:3000]
        )

        response = llm.invoke([
            SystemMessage(
                content="You are an expert travel flight planner"
            )
        ])
    
def hotel_agent(state:TravelState):
    query = state["user_query"]
   # hotel_data = tavily_search(query)
    hotel_data =asyncio.run(
        tavily_mcp_search(query)
         )
    return {
        "hotel_results":hotel_data,
        "messages" : [
            AIMessage(content= f"Hotel results fetched")
        ],
        "llm_calls" : state.get("llm_calls",0) + 1
    }
     
def itinerary_agent(state:TravelState):
    prompt = f"""
    Create a travel itinerary.
    User Query:
    {state['user_query']
    }
    Flight Results:
    {state['flight_results']}
    Hotel Results:
    {state['hotel_results']}
    """
    response = llm.invoke([
        SystemMessage(
            content= "you are expert travel planner"

        ),
        HumanMessage(content = prompt)
    ])
    return {
        "itinerary":response.content,
        "messages":[response],
        "llm_calls":state.get("llm_calls",0)+1
    }
def final_agent(state:TravelState):
    final_prompt = f""" 
    Generate final travel response.

    Flights:
    {state['flight_results']}

    Hotels:
    {state['hotel_results']}

    itinerary:{
    state['itinerary']
    }
    """
    response = llm.invoke([HumanMessage(content = final_prompt)])

    return {
        "messages" : [response],
        "llm_calls": state.get("llm_calls",0) + 1
    }


graph = StateGraph(TravelState)
graph.add_node("flight_agent",flight_agent)
graph.add_node("hotel_agent",hotel_agent)
graph.add_node("itinerary_agent",itinerary_agent)
graph.add_node("final_agent",final_agent)

graph.add_edge(START ,"flight_agent")
graph.add_edge("flight_agent","hotel_agent")
graph.add_edge("hotel_agent","itinerary_agent")
graph.add_edge("itinerary_agent","final_agent")
graph.add_edge("final_agent",END)

_conn = psycopg.connect(DATABASE_URL, autocommit=True)
checkpointer = PostgresSaver(_conn)
checkpointer.setup()
app = graph.compile(checkpointer=checkpointer)
# if __name__ == "__main__":
#     config = {
#         "configurable":{
#             "thread_id":"user_1 "
#         }
#     }
import uuid
config = {
    "configurable":{
        "thread_id":str(uuid.uuid4())
    }
}
user_input = input("Enter traval request: ")
result = app.invoke(
        {
            "messages":[
                HumanMessage(content = user_input)
            ],
            "user_query":user_input,
            "flight_results":"",
            "hotel_results":"",
            "itinerary":"",
            "llm_calls":0
        },
        config = config
    )
    print("\nFinal Repsonse:\n")

    for msg in result["messages"]:
        print(msg.content)