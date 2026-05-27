import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_temperature(city: str) -> str:
    """
    Get current temperature for a city using Open-Meteo API.

    Args:
        city: Name of the city to get temperature for

    Returns:
        Temperature in Celsius or error message
    """
    # Step 1: Get latitude & longitude
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    geo_response = requests.get(geo_url, verify=False)

    try:
        geo_data = geo_response.json()
    except ValueError:
        return f"Failed to parse geocoding response for city '{city}': {geo_response.text[:200]}"

    if geo_response.status_code != 200 or "results" not in geo_data:
        return f"City not found or geocoding failed for '{city}'."

    lat = geo_data["results"][0].get("latitude")
    lon = geo_data["results"][0].get("longitude")
    if lat is None or lon is None:
        return f"Could not determine coordinates for '{city}'."

    # Step 2: Fetch weather
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current_weather=true"
    )
    weather_response = requests.get(weather_url, verify=False)

    try:
        weather_data = weather_response.json()
    except ValueError:
        return f"Failed to parse weather response for '{city}': {weather_response.text[:200]}"

    current_weather = weather_data.get("current_weather")
    if not current_weather or "temperature" not in current_weather:
        return f"Could not retrieve current weather for '{city}'."

    temperature = current_weather["temperature"]
    return f"{temperature}°C"


# Tool schema for LLM
weather_tool_schema = {
    "name": "get_temperature",
    "description": "Get the current temperature in a given city.",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "The city to get the temperature for.",
            }
        },
        "required": ["city"],
    },
}
