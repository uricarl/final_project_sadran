from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import HTMLResponse, FileResponse
from datetime import date
import shutil
import os
from scheduler_engine.scheduler import sadran

app = FastAPI()

UPLOAD_DIR = "api_server/db/uploads"
RESULT_DIR = "api_server/db/assigned_shifts"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

last_generated_file: str | None = None


@app.get("/", response_class=HTMLResponse)
def index():
    with open("api_server/ui/index.html", encoding="utf-8") as f:
        return f.read()


@app.post("/run-scheduling", response_class=HTMLResponse)
async def run_scheduling(
    tasks_file: UploadFile = File(...),
    employees_file: UploadFile = File(...),
    work_date: date = Form(...)
):
    global last_generated_file

    try:
        task_path = os.path.join(UPLOAD_DIR, tasks_file.filename)
        emp_path = os.path.join(UPLOAD_DIR, employees_file.filename)

        with open(task_path, "wb") as f:
            shutil.copyfileobj(tasks_file.file, f)

        with open(emp_path, "wb") as f:
            shutil.copyfileobj(employees_file.file, f)

        tasks_file.file.close()
        employees_file.file.close()

        # קריאה לפונקציית השיבוץ
        result_path = sadran(task_path, emp_path, RESULT_DIR, work_date)

        # שמירה מלאה של הנתיב
        last_generated_file = os.path.abspath(result_path)

        return """
        <html lang="he" dir="rtl">
        <body>
            <h2 style="color:green">✔ השיבוץ הסתיים בהצלחה</h2>
            <a href="/download-result">⬇ הורדת קובץ השיבוץ</a><br><br>
            <a href="/">⬅ חזרה</a>
        </body>
        </html>
        """

    except Exception as e:
        return f"""
        <html lang="he" dir="rtl">
        <body>
            <h2 style="color:red">שגיאה:</h2>
            <pre>{e}</pre>
            <a href="/">⬅ חזרה</a>
        </body>
        </html>
        """


@app.get("/download-result")
def download_result():
    if last_generated_file and os.path.exists(last_generated_file):
        return FileResponse(
            path=last_generated_file,
            filename=os.path.basename(last_generated_file),
            media_type="text/csv"
        )

    return HTMLResponse("לא נוצר קובץ או שהקובץ נמחק מהשרת")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)