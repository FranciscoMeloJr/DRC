#!/usr/bin/env python3
import os
import json
import requests
from advisor_api import analise_yaml

# Tool definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analise_yaml",
            "description": "Analise the yaml configuration file from infinispan or DG and provide advices",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "yaml configuration file to be analised"
                    }
                },
                "required": ["yaml_input"]
            }
        }
    }
]

# Map tool names to actual functions
AVAILABLE_FUNCTIONS = {
    "analise_yaml": analise_yaml
}

def call_model(messages, tools=None):
    """Call the Models.corp API"""
    api_url = os.getenv('MODEL_API')
    model_id = os.getenv('MODEL_ID')
    api_key = os.getenv('USER_KEY')

    if not all([api_url, model_id, api_key]):
        raise ValueError("Set MODEL_API, MODEL_ID, and USER_KEY environment variables")

    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    response = requests.post(
        f"{api_url}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json=payload
    )

    return response.json()

def execute_tool_call(tool_call):
    """Execute a tool call and return the result"""
    function_name = tool_call["function"]["name"]
    function_args = json.loads(tool_call["function"]["arguments"])

    print(f"[Tool called: {function_name}({', '.join(f'{k}={repr(v)}' for k, v in function_args.items())})]")

    # Get the actual function
    function_to_call = AVAILABLE_FUNCTIONS.get(function_name)

    if not function_to_call:
        return {"error": f"Unknown function: {function_name}"}

    # Execute the function
    result = function_to_call(**function_args)

    return result

def chat_with_tools(user_message, messages=None):
    """Handle a conversation turn with tool calling support"""
    if messages is None:
        messages = []

    # Add user message
    messages.append({"role": "user", "content": user_message})

    # Call model with tools available
    response = call_model(messages, TOOLS)

    assistant_message = response["choices"][0]["message"]
    messages.append(assistant_message)

    # Check if model wants to call tools
    tool_calls = assistant_message.get("tool_calls")

    if tool_calls:
        # Execute each tool call
        for tool_call in tool_calls:
            result = execute_tool_call(tool_call)

            # Add tool response to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": tool_call["function"]["name"],
                "content": json.dumps(result)
            })

        # Call model again with tool results
        response = call_model(messages)
        assistant_message = response["choices"][0]["message"]
        messages.append(assistant_message)

    return assistant_message["content"], messages

def main():
    """Interactive assistant with tool calling"""
    print("=== AI DG 8/Infinispan analyzer ===")
    print("Enter the yaml file configuration")
    print("Type 'quit' to exit\n")

    messages = []

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ['quit', 'exit']:
            print("Goodbye!")
            break

        if not user_input:
            continue

        try:
            response, messages = chat_with_tools(user_input, messages)
            print(f"AI: {response}\n")
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()

