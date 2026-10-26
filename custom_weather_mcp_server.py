from mcp.server.fastmcp import FastMCP  # Fixed: FastMCP (correct casing)
import requests
import os


from dotenv import load_dotenv
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("weather-mcp")  # Fixed: FastMCP (correct casing)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Define our custom weather tool
@mcp.tool()
def get_current_weather(city: str) -> dict:
    """Get the current weather for a specific city."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    
    if not api_key:
        return {"error": "OPENWEATHER_API_KEY not found in environment variables."}

    try:
        response = requests.get(
            base_url,
            params={"q": city, 
            "appid": api_key,
             "units": "metric"
             }
        )
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"]
        }
    
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@mcp.tool()  # Fixed: added @mcp.tool() decorator to expose it as an MCP tool
def get_forecast(city: str) -> dict:  # Fixed: colon instead of curly brace; added return type hint
    api_key = os.getenv("OPENWEATHER_API_KEY")  # Fixed: get api_key from env (was undefined)
    url = "http://api.openweathermap.org/data/2.5/forecast"  # Fixed: url is now a plain string, not a dict

    if not api_key:
        return {"error": "OPENWEATHER_API_KEY not found in environment variables."}

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric"  # Fixed: "metric" as a string (was bare variable)
    }
    response = requests.get(
        url,
        params=params
    )
    data = response.json()

    forecast = []

    for item in data["list"][:5]:

        forecast.append(
            {
                "datetime": item["dt_txt"],
                "temperature": item["main"]["temp"],
                "description": item["weather"][0]["description"]
            }
        )
    return {
        "city": city,
        "forecast": forecast
    }

# Entrypoint: run in stdio mode when launched as a subprocess by the MCP client
if __name__ == "__main__":
    mcp.run()