from fastapi import FastAPI, Request
from llama_cpp import Llama
import uvicorn

app = FastAPI()

llm = Llama(
    model_path="models/wizardcoder/wizardcoder-python-34b-v1.0.Q4_K_M.gguf",
    n_ctx=4096,
    n_threads=8,
    n_gpu_layers=100,
    n_batch=512,
)

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")
    output = llm(prompt, max_tokens=256)
    return {"response": output["choices"][0]["text"]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5005)
