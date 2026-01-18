from fastapi import FastAPI
import uvicorn # יוצר ומרים את השרת
import os
from config import UPLOAD_DIR, RESULT_DIR
from controllers.api_controller import router #מייבא את הנתב שאחראי על האיפיאי בקונטרולר

app = FastAPI()

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

app.include_router(router) # מחבר את הנתב לאפליקציה


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)