from dash import html, dcc
from dash.dependencies import Input, Output, State
import requests
import json
from app import app

days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
time_slots = [f"{hour:02d}:00" for hour in range(24)]

layout = html.Div([
    html.H1("Weekly Schedule Manager", className='header'),
    html.Div([
        html.Div([
            html.H3(day, className='day-title'),
            dcc.Dropdown(
                id=f'{day}-start-time',
                options=[{'label': time, 'value': time} for time in time_slots],
                placeholder='Start Time',
                className='dropdown'
            ),
            dcc.Dropdown(
                id=f'{day}-end-time',
                options=[{'label': time, 'value': time} for time in time_slots],
                placeholder='End Time',
                className='dropdown'
            )
        ], className="day-schedule") 
        for day in days_of_week
    ], className='schedule-container'),
    html.Div([  # Wrap the button in a Div for centering
        html.Button('Submit Schedule', id='submit-schedule', className='button')
    ], className='button-container'),
    html.Div(id='output-state', className='output-state'),
    dcc.Link('Go to Current Schedule', href='/current-schedule', className='link')
], className='container')

# Callback for submitting the schedule
@app.callback(
    Output('output-state', 'children'),
    Input('submit-schedule', 'n_clicks'),
    [State(f'{day}-start-time', 'value') for day in days_of_week] + [State(f'{day}-end-time', 'value') for day in days_of_week]
)
def update_output(n_clicks, *args):
    if n_clicks:
        schedule = {day: {'start': args[i], 'end': args[i+len(days_of_week)]} for i, day in enumerate(days_of_week)}
        # Send schedule to server or process it here
        response = requests.post("http://localhost:8080/update_schedule", json=json.dumps(schedule))
        return 'Schedule updated!'
    return 'Enter schedule and click submit'
