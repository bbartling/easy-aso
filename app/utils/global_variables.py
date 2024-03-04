
from datetime import datetime
import asyncio
import datetime
import random
import time



# Initialize global variables to store the last update time and the current temperature
last_update_time = 0
current_temperature = -555.5  # Initialize with a default value

async def get_outside_air_temp():
    global last_update_time, current_temperature
    current_time = time.time()

    # Check if more than 60 seconds have passed since the last update
    if current_time - last_update_time > 60:
        
        await asyncio.sleep(0.01)
        current_temperature = random.uniform(50, 100)

        # Update the last update time
        last_update_time = current_time

    return current_temperature


async def check_occupancy_status(in_memory_schedule):
    now = datetime.datetime.now()
    current_day = now.strftime("%A")
    current_time = now.strftime("%H:%M")
    todays_schedule = in_memory_schedule.get(current_day, {"start": None, "end": None})

    is_occupied = False
    if todays_schedule["start"] and todays_schedule["end"]:
        is_occupied = todays_schedule["start"] <= current_time < todays_schedule["end"]
    
    return {
        "current_time": current_time,
        "current_day": current_day,
        "is_occupied": is_occupied,
        "schedule": todays_schedule,
    }



