from dash import html, dcc, Output, Input, callback
import requests, json
from app import app

layout = html.Div([
    html.H1("Current Schedule", className='header'),
    html.Button('Refresh Schedule', id='refresh-schedule', className='button'),
    html.Div(id='current-schedule-display', className='schedule-display'),
    dcc.Link('Go back to Schedule Management', href='/', className='link')
])

@callback(
    Output('current-schedule-display', 'children'),
    Input('refresh-schedule', 'n_clicks'),
    prevent_initial_call=True
)



def display_current_schedule(n_clicks):
    if n_clicks is not None:
        try:
            response = requests.get("http://localhost:8080/get_schedule")
            response.raise_for_status()  # Raises an HTTPError for bad requests

            # Print response content for debugging
            print("Response Content: ", response.content)
            print("Response Headers: ", response.headers)

            # Parse the JSON response into a dictionary
            schedule = response.json()

            schedule_display = [html.H4("Weekly Schedule:")]
            for day, times in schedule.items():
                # Handling null values and formatting the schedule
                start_time = times.get('start', 'Not set') if times.get('start') is not None else 'Not set'
                end_time = times.get('end', 'Not set') if times.get('end') is not None else 'Not set'
                formatted_time = f"{day}: Start - {start_time}, End - {end_time}"
                schedule_display.append(html.Div(formatted_time))

            # For displaying the schedule, use a table
            schedule_table = html.Table([
                html.Thead(html.Tr([html.Th("Day"), html.Th("Start Time"), html.Th("End Time")])),
                html.Tbody([
                    html.Tr([
                        html.Td(day),
                        html.Td(times.get('start', 'Not set')),
                        html.Td(times.get('end', 'Not set'))
                    ]) for day, times in schedule.items()
                ])
            ], className='schedule-table')

            return schedule_table
        
        except requests.HTTPError as e:
            print(f"HTTP Error: {e}")
            return html.Div("Failed to load schedule")
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return html.Div("Failed to parse schedule data")
        except Exception as e:
            print(f"General Error: {e}")
            return html.Div("An error occurred while loading the schedule")