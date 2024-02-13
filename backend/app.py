from aiohttp import web
from datetime import datetime
import json

class ScheduleManager:
    def __init__(self, schedule_file):
        self.schedule_file = schedule_file
        self.schedule = {}
        self.load_from_file()

    def save_to_file(self):
        with open(self.schedule_file, 'w') as f:
            json.dump(self.schedule, f)

    def load_from_file(self):
        try:
            with open(self.schedule_file, 'r') as f:
                self.schedule = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.schedule = {}

    def update_schedule(self, data):
        self.schedule = data
        self.save_to_file()
        return "Schedule saved!"

    def check_run(self):
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour
        minute_block = now.minute // 15

        if str(weekday) in self.schedule and [hour, minute_block] in self.schedule[str(weekday)]:
            return {'run': True}
        else:
            return {'run': False}

    def get_schedule(self):
        return json.loads(self.schedule)

async def handle_update_schedule(request):
    try:
        data = await request.json()
        message = schedule_manager.update_schedule(data)
        return web.Response(status=200, text=message)
    except Exception as e:
        return web.Response(status=500, text=str(e))

async def handle_check_run(request):
    result = schedule_manager.check_run()
    return web.json_response(result)

async def handle_get_schedule(request):
    schedule = schedule_manager.get_schedule()
    print("schedule: \n", schedule)
    print("schedule: \n", type(schedule))
    return web.json_response(schedule, dumps=json.dumps)

if __name__ == "__main__":
    SCHEDULE_FILE = "schedule.json"
    schedule_manager = ScheduleManager(SCHEDULE_FILE)

    app = web.Application()
    app.router.add_post('/update_schedule', handle_update_schedule)
    app.router.add_get('/check_run', handle_check_run)
    app.router.add_get('/get_schedule', handle_get_schedule)

    web.run_app(app)
