import csv
from collections import defaultdict
from datetime import datetime, timedelta
import time

DATE_ZERO = "08/01/2026" #  לשנות לפי היום לשיבוץ

#config
NOT_MANGERS_TASKS = [102, 103, 104, 400]
MUST_ONE_SHIFT_LEADS = [101, 301, 302, 601,	602]

# שמות העמודות – בדיוק כמו בקובץ
COL_TASK_ID = "מזהה משימה"
COL_DATE_START = "תאריך תחילה"
COL_TIME_START = "שעת התחלה"
COL_DATE_END = "תאריך סיום"
COL_TIME_END = "שעת סיום"
COL_WORKERS = "מספר עובדים"

# מנוחה מינימלית בין משמרות
MIN_REST = timedelta(minutes=180)


def date_by_delta(date_zero, days_to_add) -> str:
    if days_to_add == 0:
        return date_zero
    # 2. המרה ממחרוזת לאובייקט datetime
    date_obj = datetime.strptime(date_zero, "%d/%m/%Y")
    new_date_obj = date_obj + timedelta(days=int(days_to_add))
    # 4. המרה חזרה למחרוזת בפורמט המבוקש
    new_date_str = new_date_obj.strftime("%d/%m/%Y")
    return new_date_str  # פלט: 18/01/2026

 
def parse_dt(date_str, time_str):
    return datetime.strptime(date_str + " " + time_str, "%d/%m/%Y %H:%M")


def read_tasks(path):
    tasks = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            start = parse_dt(date_by_delta(DATE_ZERO,row[COL_DATE_START]), row[COL_TIME_START])
            end = parse_dt(date_by_delta(DATE_ZERO,row[COL_DATE_END]), row[COL_TIME_END])

            tasks.append({
                "task_id": int(row[COL_TASK_ID]),
                "start": start,
                "end": end,
                "needed": int(row[COL_WORKERS])
            })
    return tasks

def read_workers(path):
    employees = []
    manager = [] # "דוד"
    shift_leads = [] # ["דוד", "ברוך"]

    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            worker = row["עובד"]
            employees.append(worker)
            if "מנהל" in row["תפקיד"]:
                manager.append(worker)
            if "אחראי משמרת" in row["תפקיד"]:
                shift_leads.append(worker)
    return employees, manager, shift_leads


def write_output(path, tasks, assignment):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        writer.writerow([
            COL_TASK_ID,
            COL_DATE_START,
            COL_TIME_START,
            COL_DATE_END,
            COL_TIME_END,
            "עובדים"
        ])

        for t in tasks:
            names = assignment[id(t)]
            writer.writerow([
                t["task_id"],
                t["start"].strftime("%Y-%m-%d"),
                t["start"].strftime("%H:%M"),
                t["end"].strftime("%Y-%m-%d"),
                t["end"].strftime("%H:%M"),
                " ; ".join(names)
            ])


def no_overlap_or_touch(a, b):
    """אין חפיפה וגם לא סיום=התחלה"""
    return (a["end"] + MIN_REST) <= b["start"] or (b["end"] + MIN_REST) <= a["start"]


def schedule(tasks, employees, managers, shift_leads):

    # היסטוריית משמרות לעובד
    shifts_by_employee = defaultdict(list)

    # עומס כולל
    total_load = defaultdict(int)

    # עומס משימה 200 לאיזון אחראים
    load_200 = defaultdict(int)

    assignments = {}

    # מיון לפי התחלה
    tasks_sorted = sorted(tasks, key=lambda t: t["start"])

    for task in tasks_sorted:

        assigned = []

        # בונים רשימת מועמדים
        candidates = employees.copy()

        # כלל – מנהל לא עושה 101
        if task["task_id"] in NOT_MANGERS_TASKS:
            candidates = [c for c in candidates if c not in managers]

        for _ in range(task["needed"]):

            possible = []

            for emp in candidates:

                # לא ניתן לשבץ פעמיים לאותה משימה
                if emp in assigned:
                    continue

                # בודקים חפיפות
                ok = True
                for prev in shifts_by_employee[emp]:
                    if not no_overlap_or_touch(prev, task):
                        ok = False
                        break
                if not ok:
                    continue

                possible.append(emp)

            if not possible:
                raise RuntimeError(f"לא ניתן לשבץ מספיק עובדים למשימה {task['task_id']}")

            # משימה 200 – חייב להיות בדיוק אחראי אחד
            if task["task_id"] in MUST_ONE_SHIFT_LEADS: #== 200:

                # אם עדיין אין אחראי במשימה הזאת
                already_lead = any(p in shift_leads for p in assigned)

                if not already_lead:
                    # בוחרים אחראי עם הכי פחות 200
                    leads_available = [p for p in possible if p in shift_leads]
                    if not leads_available:
                        raise RuntimeError("משימה 200 ללא אחראי – כלל חובה")

                    emp = min(leads_available, key=lambda x: load_200[x])
                    load_200[emp] += 1

                else:
                    # ממלאים שאר המשבצות בעובדים רגילים
                    non_leads = [p for p in possible if p not in shift_leads]
                    if non_leads:
                        emp = min(non_leads, key=lambda x: total_load[x])
                    else:
                        emp = min(possible, key=lambda x: total_load[x])

            else:
                # כלל הוגנות כללי
                emp = min(possible, key=lambda x: total_load[x])

            assigned.append(emp)
            shifts_by_employee[emp].append(task)
            total_load[emp] += 1

        assignments[id(task)] = assigned

    return assignments


def sadran(tasks_file, workers_file, dirctory, work_date):
    global DATE_ZERO
    DATE_ZERO = work_date.strftime("%d/%m/%Y")
    tasks = read_tasks(tasks_file)
    employees, manager, shift_leads = read_workers(workers_file)
    assignment = schedule(tasks, employees, manager, shift_leads)
    timestamp = time.time()
    dt_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"tasks_assigned_{dt_str}.csv"
    full_path = f"{dirctory}/{file_name}"
    write_output(full_path, tasks, assignment)
    print(f"The file sucssfuly created: {file_name}")
    return full_path

# ===================== שימוש =====================

if __name__ == "__main__":

    print(sadran("csv_source/all_tasks_24.csv","workers_full.csv","assigned_shifts"))


    # # קריאת המשימות
    # tasks = read_tasks("csv_source/all_tasks_24.csv")
    # # tasks = read_tasks("tasks.csv")
    

    # # רשימת עובדים
    # employees, manager, shift_leads = read_workers("workers_full.csv")

    # assignment = schedule(tasks, employees, manager, shift_leads)
    # file_name = f"assigned_shifts/tasks_assigned_{int(time.time())}.csv"
    # write_output(file_name, tasks, assignment)

    # print(f"The file sucssfuly created: {file_name}")