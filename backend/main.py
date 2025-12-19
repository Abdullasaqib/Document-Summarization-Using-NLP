from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.parser import parse_document
from backend.summarizer import summarizer_instance
import shutil
import os

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Document Summarizer API")

# Mount frontend directory to serve static files
# We resolve the path relative to this file (backend/main.py) -> ../frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# CORS setup to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import StreamingResponse

@app.post("/summarize")
async def summarize_document_endpoint(file: UploadFile = File(...)):
    try:
        content = await file.read()
        try:
            text = parse_document(file.filename, content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        if not text.strip():
             raise HTTPException(status_code=400, detail="Could not extract text from document.")
        
        print(f"DEBUG: Parsed text length: {len(text)}")

        # Streaming Response
        def iter_summary():
            print("DEBUG: Starting stream generation...")
            for chunk in summarizer_instance.summarize_stream(text):
                print(f"DEBUG: Yielding chunk of length {len(chunk)}")
                yield chunk
            print("DEBUG: Stream finished.")

        return StreamingResponse(iter_summary(), media_type="text/plain")

    except Exception as e:
        print(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve frontend on root
# IMPORTANT: This must be after all other routes so it doesn't mask them
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
