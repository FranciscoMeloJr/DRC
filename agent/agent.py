#!/usr/bin/env python3
import os
import json
import sys
import requests

# Add the 'agent' directory to the path so it can find advisor_api
agent_dir = os.path.dirname(os.path.abspath(__file__))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

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

def call_model(messages, tools=None, debug=True):
    """Call the Models.corp API"""
    api_url = os.getenv('MODEL_API')
    model_id = os.getenv('MODEL_ID')
    api_key = os.getenv('USER_KEY')

    if not all([api_url, model_id, api_key]):
        raise ValueError("Set MODEL_API, MODEL_ID, and USER_KEY environment variables")
    else:
        if debug:
            print("================= Critical ============")
            print (api_url)
            print (model_id)
            print (api_key)
            print("================= Critical ============")

    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
            response = requests.post(
                f"{api_url}/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json=payload,
                timeout=30 # Add a timeout just in case
            )
            
            # Check if the status is 200 OK
            if response.status_code != 200:
                print(f"API Error {response.status_code}: {response.text}")
                return {"error": f"HTTP {response.status_code}"}

            return response.json()
    except Exception as e:
            print(f"Connection Failed: {e}")
            raise

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

#def chat_with_tools(user_message, messages=None):
def chat_with_tools(user_message, messages=None, **kwargs):
    # 1. THE GUARD: Immediate check for environment keys
    required_keys = ["MODEL_API", "MODEL_ID", "USER_KEY"]
    if not all(os.getenv(k) for k in required_keys):
        return -1, [] 

    context = kwargs.get('context')
    if messages is None:
        messages = []

    # Inject context into system message
    if len(messages) == 0 and context:
        messages.append({
            "role": "system", 
            "content": f"You are the DRC Advisor. Use this analysis context: {json.dumps(context)} to answer."
        })

    messages.append({"role": "user", "content": user_message})

    try:
        # 2. WRAP THE NETWORK CALL: This is where the DNS error happens
        response = call_model(messages, TOOLS)
        
        assistant_message = response["choices"][0]["message"]
        messages.append(assistant_message)

        # Check for Tool Calls
        tool_calls = assistant_message.get("tool_calls")
        if tool_calls:
            for tool_call in tool_calls:
                result = execute_tool_call(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "content": json.dumps(result)
                })
            # Second call after tool execution
            response = call_model(messages)
            assistant_message = response["choices"][0]["message"]
            messages.append(assistant_message)

        return assistant_message["content"], messages

    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
        # 3. GRACEFUL FAIL: Catch the DNS/VPN error ([Errno -2])
        error_msg = (
            "📡 **Connectivity Issue**: I cannot reach the Granite AI endpoint. "
            "Please check your VPN or network connection. I can still see your "
            "local analysis, but I can't synthesize a professional reply right now."
        )
        print(f"[AGENT ERROR]: {str(e)}") # Log the technical detail to your terminal
        return error_msg, messages

    except Exception as e:
        # Catch-all for other logic errors
        print(f"[CRITICAL ERROR]: {str(e)}")
        return f"🤖 **Agent Error**: {str(e)}", messages

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

