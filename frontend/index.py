from dash import html, dcc, Input, Output
from app import app
import schedule_management
import current_schedule

# Define the layout of the app
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Callback to switch between the different pages
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/current-schedule':
        return current_schedule.layout
    elif pathname == '/' or pathname == '/schedule-management':
        return schedule_management.layout
    else:
        # You can have a default page or redirect to one of the existing pages
        return "404 Page Not Found"

if __name__ == '__main__':
    app.run_server(host="0.0.0.0", debug=True, port=8050)
