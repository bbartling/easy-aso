import rdflib
from rdflib import RDF, Namespace, Graph, URIRef, Literal


# Define namespaces
BACNET = Namespace("http://data.ashrae.org/bacnet/2020#")
BRICK = Namespace("https://brickschema.org/schema/Brick#")
BLDG = Namespace("http://example.com/mybuilding#")

# Constants
BUILDING_NAME = "Building1"

# The air handling unit serving the VAV boxes
AHU_NAME = "AHU1"

# device type
DEVICE_TYPE = BRICK.Variable_Air_Volume_Box

# Rooms served by the device
ROOM_NUMBERS = ["410", "411", "412"]

# Raw file name
VAV_BOX = "vav_10"

# Define point type mappings to Brick classes
point_type_mappings = {
    "Zone Air Temperature Sensor": ["ZN-T", BRICK.Temperature_Sensor],
    "Zone Temperature Setpoint": ["ZN-SP", BRICK.Temperature_Setpoint],
    "Supply Air Temperature Sensor": ["DA-T", BRICK.Temperature_Sensor],
    "Heating Coil Valve Command": ["HTG-O", BRICK.Valve_Command],
    "Air Damper Command": ["DPR-O", BRICK.Damper_Command],
    "Air Flow Sensor": ["SA-F", BRICK.Air_Flow_Sensor],
    "Supply Air Flow Setpoint": ["SAFLOW-SP", BRICK.Air_Flow_Setpoint],
    "Occupancy Sensor": ["OCC-C", BRICK.Occupancy_Sensor],
}


def read_rdf_file(file_path):
    g = rdflib.Graph()
    g.parse(file_path, format="turtle")
    return g

def extract_device_configurations(graph):
    devices = {}
    for s, p, o in graph:
        if p == BACNET.contains:
            device_id = str(s).split("//")[1]
            devices[device_id] = devices.get(device_id, {})
            point_uri = rdflib.URIRef(o)
            devices[device_id][str(point_uri)] = {str(p): str(o) for s, p, o in graph.triples((point_uri, None, None))}
    return devices


def get_brick_class_uri_by_key(key):
    for entity, details in point_type_mappings.items():
        if details[0] == key:
            return details[1]  # Return the BRICK class URI directly
    return None  # Return None if not found
    
    
def process_and_save_rdf(devices, output_file_path):

    g = Graph()
    g.bind("brick", BRICK)
    g.bind("bldg", BLDG)
    g.bind("bacnet", BACNET)

    ahu_uri = BLDG[AHU_NAME]
    g.add((ahu_uri, RDF.type, BRICK.Air_Handler_Unit))

    # Adjust the flat_point_mappings to replace underscores with hyphens in keys
    flat_point_mappings = {name.replace("_", "-"): brick_class for brick_class, names in point_type_mappings.items() for name in names}
    
    print("flat_point_mappings: ",flat_point_mappings)

    for device_id, points in devices.items():
        device_uri = BLDG[f"VAV_{device_id}"]
        g.add((device_uri, RDF.type, DEVICE_TYPE))
        g.add((ahu_uri, BRICK.feeds, device_uri))

        for room_number in ROOM_NUMBERS:
            room_uri = BLDG[f"Room-{room_number}"]
            g.add((room_uri, RDF.type, BRICK.Room))
            g.add((device_uri, BRICK.serves, room_uri))

        for point_uri, details in points.items():
            point_name = details.get(f"{BACNET}object-name", "")
            brick_class_uri = get_brick_class_uri_by_key(point_name)
            if brick_class_uri:
                # Generate a unique new_point_uri for each point
                new_point_uri = BLDG[f"{point_name}_{device_id}"]  # Example of generating a unique URI
                g.add((new_point_uri, RDF.type, brick_class_uri))
                # Optionally add BACnet properties to the new entity
                for prop, value in details.items():
                    g.add((new_point_uri, URIRef(prop), Literal(value)))
            else:
                print(f"Skipping unmapped point: {point_name}")

            g.serialize(destination=output_file_path, format="turtle")



def main():
    rdf_file_path = f"./raw_graph_models/{VAV_BOX}"
    graph = read_rdf_file(rdf_file_path)
    device_configurations = extract_device_configurations(graph)
    output_file_path = f"./processed_graph_models/processed_{VAV_BOX}"
    process_and_save_rdf(device_configurations, output_file_path)

if __name__ == "__main__":
    main()
