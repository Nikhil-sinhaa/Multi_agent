import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AVIATION_STACK_API_KEY")
URL = "http://api.aviationstack.com/v1/flights"

def search_flight(query):
    url = URL
    params = {
        "access_key":API_KEY,
        "limit": 5
    }
    response = requests.get(url,params= params)

    data = response.json()
    #print(data)
    flights = []

    if "data" in data:
        for flight in data["data"][:5]:
            airline = flight.get("airline",{}).get("name")
            departure = flight.get("departure",{}).get("airport" , "Unknown") 
            arrival = flight.get("arrival",{}).get("airport","Unknown")
            status = flight.get("flight_status","Unknown")

            flights.append(
                f"""
                Airline: {airline}
                Departure: {departure}
                Arrival: {arrival}
                Status: {status}   
               """
            )
    return "\n".join(flights)
