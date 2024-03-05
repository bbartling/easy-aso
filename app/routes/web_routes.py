from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.models.models import WritePropertyRequest


"""
https://192.168.0.102:8000/occupancy
https://192.168.0.102:8000/bacnet/whois/201201
https://192.168.0.102:8000/bacnet/read/201201/analog-input,2
https://192.168.0.102:8000/bacnet/write/201201/analog-value,300/present-value/99
"""


def setup_routes(app: FastAPI, bacnet_app):

    # for testing purposes
    @app.get("/hello")
    async def hello_world():
        return {"message": "Hello!"}

    @app.get("/bacpypes/config")
    async def bacpypes_config():
        return await bacnet_app.config()

    @app.get("/bacnet/whois/{device_instance}")
    async def bacnet_whois(device_instance):
        return await bacnet_app.who_is(device_instance)

    @app.get("/bacnet/read/{device_instance}/{object_identifier}")
    async def bacnet_read_present_value(device_instance, object_identifier):
        return await bacnet_app.read_present_value(device_instance, object_identifier)

    @app.get("/bacnet/read/{device_instance}/{object_identifier}/{property_identifier}")
    async def bacnet_read_property(
        device_instance, object_identifier, property_identifier
    ):
        return await bacnet_app.read_property(
            device_instance, object_identifier, property_identifier
        )

    @app.post("/bacnet/write")
    async def bacnet_write_property(request: WritePropertyRequest):
        # Extract values from the request object
        device_instance = request.device_instance
        object_identifier = request.object_identifier
        property_identifier = request.property_identifier
        value = request.value
        priority = request.priority

        # Call the write property function with the extracted values
        return await bacnet_app.write_property(
            device_instance, object_identifier, property_identifier, value, priority
        )

    async def get_current_user(token: str = Depends(bacnet_app.oauth2_scheme)):
        user = bacnet_app.users.get(token)
        if not user:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )
        return user

    async def get_current_active_user(request: Request):
        username = request.session.get("user")
        if not username or username not in bacnet_app.users:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return {"username": username}

    @app.get("/", response_class=HTMLResponse)
    async def read_index(request: Request):
        user_logged_in = (
            "user" in request.session and request.session["user"] in bacnet_app.users
        )
        return bacnet_app.templates.TemplateResponse(
            "index.html", {"request": request, "user_logged_in": user_logged_in}
        )

    @app.post("/token")
    async def login(form_data: OAuth2PasswordRequestForm = Depends()):
        user_dict = bacnet_app.users.get(form_data.username)
        if not user_dict or user_dict["password"] != form_data.password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return {"access_token": form_data.username, "token_type": "bearer"}

    @app.get("/logout")
    async def logout(request: Request):
        request.session.pop("user", None)
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    @app.get("/login", response_class=HTMLResponse)
    async def login_form(request: Request):
        return bacnet_app.templates.TemplateResponse("login.html", {"request": request})

    @app.post("/login")
    async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
        user_dict = bacnet_app.users.get(form_data.username)
        if not user_dict or user_dict["password"] != form_data.password:
            return bacnet_app.templates.TemplateResponse(
                "login.html", {"request": request, "error": "Invalid credentials"}
            )
        request.session["user"] = form_data.username
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def read_dashboard(
        request: Request, user: dict = Depends(get_current_active_user)
    ):
        return bacnet_app.templates.TemplateResponse(
            "dashboard.html", {"request": request, "user": user}
        )

    @app.get("/schedule", response_class=HTMLResponse)
    async def read_schedule(
        request: Request, user: dict = Depends(get_current_active_user)
    ):
        return bacnet_app.templates.TemplateResponse(
            "schedule.html",
            {
                "request": request,
                "schedule": bacnet_app.in_memory_schedule,
                "user": user,
            },
        )

    @app.get("/manage-schedule", response_class=HTMLResponse)
    async def manage_schedule(
        request: Request, user: dict = Depends(get_current_active_user)
    ):

        return bacnet_app.templates.TemplateResponse(
            "manage_schedule.html",
            {
                "request": request,
                "days_of_week": bacnet_app.days_of_week,
                "time_slots": bacnet_app.time_slots,
                "schedule": bacnet_app.in_memory_schedule,
                "user": user,
            },
        )

    @app.post("/manage-schedule")
    async def update_schedule(
        request: Request, user: dict = Depends(get_current_active_user)
    ):
        form_data = await request.form()
        schedule_data = {}
        error = False

        for day in bacnet_app.days_of_week:
            start_time_key = f"{day}-start-time"
            end_time_key = f"{day}-end-time"
            start_time = form_data.get(start_time_key)
            end_time = form_data.get(end_time_key)

            if start_time and end_time and start_time >= end_time:
                error = True
                break

            schedule_data[day] = {"start": start_time, "end": end_time}

        if error:
            return bacnet_app.templates.TemplateResponse(
                "manage_schedule.html",
                {
                    "request": request,
                    "error": "End time must be later than start time",
                    "user": user,
                    "schedule": schedule_data,
                },
            )

        # Save the updated schedule both in-memory and to file
        bacnet_app.in_memory_schedule = schedule_data
        bacnet_app.save_schedule(schedule_data)

        return RedirectResponse(url="/schedule", status_code=status.HTTP_302_FOUND)

    @app.get("/occupancy")
    async def check_occupancy():
        occupancy_status = await bacnet_app.check_occupancy_status()

        return JSONResponse(
            content={
                "status": "success",
                "data": occupancy_status
            }
        )