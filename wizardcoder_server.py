from fastapi import FastAPI, Request
from llama_cpp import Llama
import uvicorn
import logging
import re
from typing import List, Dict, Any, Optional

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Initialize conversation history and file references
conversation_history: List[Dict[str, str]] = []
file_references: Dict[str, str] = {}

# Placeholder functions for file I/O
def handle_file_upload(file_name: str, file_data: bytes) -> str:
    logging.info(f"File upload hook: Received file '{file_name}' of {len(file_data)} bytes.")
    # In a real scenario, save the file and store its actual path or content
    file_references[file_name] = f"placeholder_content_for_{file_name}"
    logging.info(f"Stored file reference for '{file_name}'. Current references: {list(file_references.keys())}")
    return file_name  # Or a generated file ID

def handle_file_download(file_id: str) -> Optional[str]:
    logging.info(f"File download hook: Requested file ID '{file_id}'.")
    content = file_references.get(file_id)
    if content:
        logging.info(f"Found content for file ID '{file_id}'.")
        return content
    else:
        logging.warning(f"No content found for file ID '{file_id}'.")
        return None # Or b"placeholder_file_content_not_found" if bytes were expected

# Initialize Llama model
try:
    llm = Llama(
        model_path="models/wizardcoder/wizardcoder-python-34b-v1.0.Q4_K_M.gguf",
        n_ctx=4096,
        n_threads=8,
        n_gpu_layers=100,  # Adjust based on your GPU
        n_batch=512,
        verbose=False # To reduce llama.cpp logs unless necessary for debugging
    )
    logging.info("WizardCoder Llama model loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load WizardCoder Llama model: {e}")
    llm = None

@app.post("/v1/completions")
async def completions(request: Request):
    global conversation_history
    global file_references # if we modify it within the request, e.g. via a simulated upload through prompt

    if llm is None:
        logging.error("LLM not initialized. Cannot process request.")
        return {"error": "LLM not initialized"}, 500

    try:
        body = await request.json()
        user_prompt = body.get("prompt", "")
        max_tokens = body.get("max_tokens", 512)
        temperature = body.get("temperature", 0.7)
        stop = body.get("stop", ["```"]) # Default stop sequence for code

        logging.info(f"Received request for /v1/completions with prompt (first 100 chars): '{user_prompt[:100]}...'")
        logging.info(f"Parameters: max_tokens={max_tokens}, temperature={temperature}, stop={stop}")

        # --- File Reference Simulation ---
        # Simple check for file mentions (e.g., "file.txt", "script.py")
        mentioned_files = re.findall(r"['\"]?([a-zA-Z0-9_.-]+\.(?:txt|py|md|json|csv|yaml|yml|sh|ipynb))['\"]?", user_prompt)
        file_context_info = ""
        if mentioned_files:
            logging.info(f"Detected potential file mentions in prompt: {mentioned_files}")
            for file_name in mentioned_files:
                if file_name in file_references:
                    # For simplicity, just note that the file is known.
                    # In a more complex scenario, you might include parts of file_references[file_name]
                    file_context_info += f"[File '{file_name}' is known. Content not directly injected for brevity.]\n"
                    logging.info(f"File '{file_name}' is in file_references.")
                else:
                    # Simulate an upload if the file is mentioned but not known - for testing file_references
                    # In a real app, uploads would be explicit.
                    # handle_file_upload(file_name, b"Simulated content for " + file_name.encode())
                    # file_context_info += f"[File '{file_name}' was mentioned and a placeholder reference created.]\n"
                    logging.info(f"File '{file_name}' mentioned but not in file_references.")


        # Construct prompt with history and file context
        history_prompt = ""
        for entry in conversation_history:
            if entry["role"] == "user":
                history_prompt += f"User: {entry['content']}\n"
            elif entry["role"] == "assistant":
                history_prompt += f"Assistant: {entry['content']}\n" # Changed from AI to Assistant for role consistency
        
        full_prompt = history_prompt + file_context_info + f"User: {user_prompt}"
        logging.info(f"Constructed prompt for LLM (last 300 chars): ...{full_prompt[-300:]}")

        # Add user's prompt to history
        conversation_history.append({"role": "user", "content": user_prompt})

        # Call the LLM
        output = llm(
            full_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )
        logging.info(f"LLM output received (type: {type(output)}): {str(output)[:200]}...") # Log snippet of output

        ai_response_text = ""
        if output and "choices" in output and len(output["choices"]) > 0:
            ai_response_text = output["choices"][0]["text"].strip()
        else:
            logging.error(f"Unexpected LLM output format: {output}")
            ai_response_text = "Error: Could not generate a valid response."


        # Add AI's response to history
        conversation_history.append({"role": "assistant", "content": ai_response_text})
        
        # Keep history to a manageable size (e.g., last 10 exchanges = 20 entries)
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]

        response_payload = {
            "choices": [
                {
                    "text": ai_response_text
                }
            ]
        }
        return response_payload

    except Exception as e:
        logging.error(f"Error processing /v1/completions request: {e}", exc_info=True)
        return {"error": "Internal server error"}, 500

if __name__ == "__main__":
    logging.info("Starting WizardCoder server on port 5005...")
    if llm is None:
        logging.error("WizardCoder LLM failed to load. Server might not function correctly.")
    uvicorn.run(app, host="0.0.0.0", port=5005)
