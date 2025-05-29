from fastapi import FastAPI, Request
from llama_cpp import Llama
import uvicorn
import logging
from typing import List, Dict, Any

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Initialize conversation history
conversation_history: List[Dict[str, str]] = []

# Placeholder functions for file I/O
def handle_file_upload(file_data: bytes) -> str:
    # Placeholder: Log received file info
    # In a real scenario, save the file and return a reference/path
    logging.info(f"File upload hook: Received file of {len(file_data)} bytes.")
    return "placeholder_file_id_or_path"

def handle_file_download(file_id: str) -> bytes:
    # Placeholder: Log file ID
    # In a real scenario, retrieve the file and return its content
    logging.info(f"File download hook: Requested file ID {file_id}.")
    return b"placeholder_file_content"

# Initialize Llama model
try:
    llm = Llama(
        model_path="models/swallow/swallow-70b-instruct.Q4_K_M.gguf",
        n_ctx=4096,
        n_threads=8,
        n_gpu_layers=100,  # Adjust based on your GPU capabilities
        n_batch=512,
        verbose=False # To reduce llama.cpp logs unless necessary for debugging
    )
    logging.info("Llama model loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load Llama model: {e}")
    # Depending on the desired behavior, you might want to exit or raise the exception
    # For now, we'll let it proceed and potentially fail at request time if llm is not initialized.
    llm = None


@app.post("/v1/completions")
async def completions(request: Request):
    global conversation_history
    if llm is None:
        logging.error("LLM not initialized. Cannot process request.")
        return {"error": "LLM not initialized"}, 500

    try:
        body = await request.json()
        user_prompt = body.get("prompt", "")
        max_tokens = body.get("max_tokens", 512)
        temperature = body.get("temperature", 0.7)
        # model_name = body.get("model", "swallow") # model_name can be used if routing to different models

        logging.info(f"Received request for /v1/completions with prompt: '{user_prompt[:100]}...'")

        # Construct prompt with history
        history_prompt = ""
        for entry in conversation_history:
            if entry["role"] == "user":
                history_prompt += f"User: {entry['content']}\n"
            elif entry["role"] == "assistant":
                history_prompt += f"AI: {entry['content']}\n"
        
        full_prompt = history_prompt + f"User: {user_prompt}"
        logging.info(f"Constructed prompt for LLM (last 200 chars): ...{full_prompt[-200:]}")

        # Add user's prompt to history
        conversation_history.append({"role": "user", "content": user_prompt})

        # Call the LLM
        output = llm(
            full_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            # stop=["User:", "AI:"] # Optional: define stop sequences if needed
        )
        logging.info(f"LLM output received: {output}")

        ai_response_text = ""
        if output and "choices" in output and len(output["choices"]) > 0:
            ai_response_text = output["choices"][0]["text"].strip()
        else:
            logging.error(f"Unexpected LLM output format: {output}")
            ai_response_text = "Error: Could not generate a valid response."


        # Add AI's response to history
        conversation_history.append({"role": "assistant", "content": ai_response_text})
        
        # Keep history to a manageable size (e.g., last 10 exchanges)
        if len(conversation_history) > 20: # 10 user + 10 assistant messages
            conversation_history = conversation_history[-20:]


        response_payload = {
            "choices": [
                {
                    "text": ai_response_text
                }
            ]
        }
        # Optionally include other fields from the LLM output if needed by the client
        # response_payload["id"] = output.get("id")
        # response_payload["model"] = output.get("model")
        # response_payload["usage"] = output.get("usage")

        return response_payload

    except Exception as e:
        logging.error(f"Error processing request: {e}", exc_info=True)
        return {"error": "Internal server error"}, 500

if __name__ == "__main__":
    logging.info("Starting Swallow server on port 5006...")
    # Note: Llama model is loaded above, before uvicorn.run
    if llm is None:
        logging.error("LLM failed to load. Server might not function correctly.")
    uvicorn.run(app, host="0.0.0.0", port=5006)
