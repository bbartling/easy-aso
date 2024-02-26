from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from fastapi.responses import JSONResponse
import json


# $ uvicorn main:app --host 0.0.0.

# Define days of the week and time slots
days_of_week = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]
time_slots = [f"{hour:02d}:00" for hour in range(24)]

# Load the default schedule with 7 AM to 5 PM for Monday to Friday
default_schedule = {
    day: {"start": "07:00", "end": "17:00"}
    if day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    else {"start": None, "end": None}
    for day in days_of_week
}

# Templates
templates = Jinja2Templates(directory="templates")

# FastAPI app setup
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variable to store the schedule in memory
in_memory_schedule = None

# Dummy user data - replace with a real database in production
users = {"admin": {"username": "admin", "password": "admin"}}

# OAuth2 token model
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# User authentication model
class User(BaseModel):
    username: str


# Dependency for user authentication
def get_current_user(token: str = Depends(oauth2_scheme)):
    username = users.get(token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return User(username=username)


def get_current_active_user(request: Request):
    username = request.session.get("user")
    if not username or username not in users:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return User(username=username)


def load_schedule():
    """Load the schedule from the JSON file into the cache."""
    try:
        with open("schedule.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return default_schedule  # Or return an empty dict


# Load the schedule at the start of the application
# Register the function to run at startup
in_memory_schedule = load_schedule()
print(" schedule loaded success")


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    user_logged_in = "user" in request.session and request.session["user"] in users
    return templates.TemplateResponse(
        "index.html", {"request": request, "user_logged_in": user_logged_in}
    )


# Token endpoint
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = users.get(form_data.username)
    if not user_dict or user_dict["password"] != form_data.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return {"access_token": form_data.username, "token_type": "bearer"}


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)  # Remove the user from session
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = users.get(form_data.username)
    if not user_dict or user_dict["password"] != form_data.password:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid credentials"}
        )

    request.session["user"] = form_data.username
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": user}
    )


@app.get("/schedule", response_class=HTMLResponse)
async def read_schedule(
    request: Request, user: User = Depends(get_current_active_user)
):
    return templates.TemplateResponse(
        "schedule.html",
        {"request": request, "schedule": in_memory_schedule, "user": user},
    )


@app.get("/manage-schedule", response_class=HTMLResponse)
async def manage_schedule(
    request: Request, user: User = Depends(get_current_active_user)
):
    return templates.TemplateResponse(
        "manage_schedule.html",
        {
            "request": request,
            "days_of_week": days_of_week,
            "time_slots": time_slots,
            "schedule": in_memory_schedule,
            "user": user,
        },
    )


@app.post("/manage-schedule")
async def update_schedule(
    request: Request, user: User = Depends(get_current_active_user)
):
    form_data = await request.form()
    schedule_data = {}
    error = False

    for day in days_of_week:
        start_time_key = f"{day}-start-time"
        end_time_key = f"{day}-end-time"
        start_time = form_data.get(start_time_key)
        end_time = form_data.get(end_time_key)

        if start_time >= end_time:
            error = True
            break

        schedule_data[day] = {"start": start_time, "end": end_time}

    if error:
        # Handle the error, e.g., return an error message to the form
        return templates.TemplateResponse(
            "manage_schedule.html",
            {
                "request": request,
                "error": "End time must be later than start time",
                "user": user,
                "schedule": schedule_data,
            },
        )

    # Save to a JSON file
    with open("schedule.json", "w") as file:
        json.dump(schedule_data, file, indent=4)

    return RedirectResponse(url="/schedule", status_code=status.HTTP_302_FOUND)


@app.get("/occupancy")
async def check_occupancy():
    now = datetime.now()
    current_day = now.strftime("%A")  # e.g., "Monday"
    current_time = now.strftime("%H:%M")

    # Retrieve today's schedule
    todays_schedule = in_memory_schedule.get(current_day, {"start": None, "end": None})

    # Check if current time is within the scheduled occupancy times
    is_occupied = False
    if todays_schedule["start"] and todays_schedule["end"]:
        is_occupied = todays_schedule["start"] <= current_time < todays_schedule["end"]

    # Return a JSON response
    return JSONResponse(content={
        "status": "success",
        "data": {
            "current_time": current_time,
            "current_day": current_day,
            "is_occupied": is_occupied,
            "schedule": todays_schedule
        }
    })
