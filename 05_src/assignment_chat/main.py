from openai import OpenAI
from dotenv import load_dotenv
from assignment_chat.prompts import return_instructions_root
import json
import requests
from utils.logger import get_logger
import os
#https://github.com/public-apis/public-apis?tab=readme-ov-file#anime
#https://chandan-02.github.io/anime-facts-rest-api/

_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")


client = OpenAI()

open_ai_model = os.getenv("OPENAI_MODEL", "gpt-4")

tools = [
    {
        "type": "function",
        "name": "get_random_advice",
        "description": "This tool retrieves a random advice",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        },
        
    },

    {
        "type": "function",
        "name": "get_search_advice",
        "description": "This tool retrieves an advice through keywords",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Words that are included in an adivce",
                }
            },
            "required": ["keyword"],
            "additionalProperties": False
        },
        
    },
]

def get_random_advice():
    """
    An API call to generate random advice.
    """
    url = "https://api.adviceslip.com/advice"
    response = requests.get(url)
    result = json.loads(response.text)
    return result

def get_search_advice(keyword:str):
    """
    An API call to generate advice through keywords.
    """
    keyword = keyword.lower()
    url = "https://api.adviceslip.com/advice/search/"+keyword
    response = requests.get(url)
    result = json.loads(response.text)
    return result

def sanitize_history(history: list[dict]) -> list[dict]:
    clean_history = []
    for msg in history:
        clean_history.append({
            "role": msg.get("role"),
            "content": msg.get("content")
        })
    return clean_history


def advice_chat(message: str, history: list[dict] = []) -> str:
    _logs.info(f'User message: {message}')
    
    instructions = return_instructions_root()
    
    user_msg = {
        "role": "user",
        "content": message
    }
    
    conversation_input = sanitize_history(history) + [user_msg]
    
    response = client.responses.create(
        model=open_ai_model,  
        instructions=instructions,
        input=conversation_input,
        tools=tools,
        
    )

    conversation_input += response.output

    # Handle function calls if any
    for item in response.output:
        if item.type == "function_call":
            if item.name == "get_random_advice":
                # Call the advice function
                advice_result = get_random_advice()
                
                # Add function call result to conversation
                
                func_call_output = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                        "advice": advice_result
                    })
                }
                
                _logs.debug(f"Function call output: {func_call_output}")

                conversation_input = conversation_input + [func_call_output]
                
                # Make second API call with function result
                response = client.responses.create(
                    model=open_ai_model,
                    instructions=instructions,
                    tools=tools,
                    input=conversation_input
                )
                break
            
            elif item.name == "get_search_advice":
                args = json.loads(item.arguments)
                _logs.info(f'Function call args: {args}')
                
                # Call the advice function
                advice_result = get_search_advice(**args)
                
                # Add function call result to conversation
                
                func_call_output = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                        "advice": advice_result
                    })
                }
                
                _logs.debug(f"Function call output: {func_call_output}")

                conversation_input = conversation_input + [func_call_output]
                
                # Make second API call with function result
                response = client.responses.create(
                    model=open_ai_model,
                    instructions=instructions,
                    tools=tools,
                    input=conversation_input
                )
                break
    
    return response.output_text
