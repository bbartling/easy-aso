# server

* fastAPI and bacpypes3


```bash
$ python -m pip install fastapi bacpypes3
```

TODO
* setup graphql POST route to grab temp sensor info zones and central plant sensors to display on the dashboard based on Brick schema
* maybe remove bacnet rest API routes and just use one GraphQL POST route. If there were a graphic to adjust zone temp sensors with a Form input for sensor adjustments maybe think about a way to handle the BACnet write internally Vs a rest API route for BACnet read/writes.