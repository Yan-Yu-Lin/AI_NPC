from pydantic import BaseModel, Field
from typing import Literal, List, Union
from openai import OpenAI
import json

# Initialize OpenAI client
client = OpenAI()

# Simulate some dynamic data (like items in your NPC project)
events_data = [
    {"name": "Team Meeting", "date": "2025-03-01", "participants": ["Alice", "Bob"]},
    {"name": "Party", "date": "2025-03-05", "participants": ["Charlie", "Dave"]}
]

# Step 1: Dynamically generate CalendarEvent-like schemas
event_classes = {}

for event in events_data:
    # Extract event-specific details
    event_name = event["name"]
    event_date = event["date"]
    participant_names = tuple(event["participants"])  # Convert to tuple for Literal

    # Dynamically create a class for this event
    class_name = f"{event_name.replace(' ', '')}Event"  # e.g., "TeamMeetingEvent"
    NewEventClass = type(
        class_name,
        (BaseModel,),
        {
            "__annotations__": {
                "name": Literal[event_name],           # e.g., Literal["Team Meeting"]
                "date": Literal[event_date],          # e.g., Literal["2025-03-01"]
                "participants": List[Literal[participant_names]]  # e.g., List[Literal["Alice", "Bob"]]
            }
        }
    )
    event_classes[event_name] = NewEventClass

# Step 2: Define a union of all dynamically generated event classes
class CalendarEvent(BaseModel):
    event: Union[tuple(event_classes.values())]

# Step 3: Verify the generated schemas
print("=== Dynamically Generated Event Classes ===")
for name, cls in event_classes.items():
    print(f"Class Name: {name}")
    # Print schema as JSON for clarity
    schema = cls.model_json_schema()
    print(json.dumps(schema, indent=2))
    # Create an instance to test
    instance = cls(name=schema["properties"]["name"]["const"],
                  date=schema["properties"]["date"]["const"],
                  participants=schema["properties"]["participants"]["items"]["enum"])
    print(f"Example Instance: {instance}")
    print("---")

# Print the combined CalendarEvent schema
print("\n=== Combined CalendarEvent Schema ===")
print(json.dumps(CalendarEvent.model_json_schema(), indent=2))

# Step 4: Make an API request using the generated schema
response = client.beta.chat.completions.parse(
    model="gpt-4o-2024-11-20",
    messages=[
        {"role": "system", "content": "You are an assistant scheduling events."},
        {"role": "user", "content": "Schedule an event from the available options."}
    ],
    response_format=CalendarEvent
)

# Step 5: Print the API response
result = response.choices[0].message.parsed
print("\n=== API Response ===")
print(result)
print(f"Event Details: {result.event}")

