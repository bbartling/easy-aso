import rdflib
from rdflib.namespace import Namespace


def read_rdf_file(file_path):
    g = rdflib.Graph()
    # Bind the bacnet namespace
    BACNET = Namespace("http://data.ashrae.org/bacnet/2020#")
    g.bind("bacnet", BACNET)
    g.parse(file_path, format="turtle")
    return g


def extract_point_details(graph, point_uri):
    BACNET = Namespace("http://data.ashrae.org/bacnet/2020#")
    point_details = {}
    for s, p, o in graph.triples((point_uri, None, None)):
        point_details[str(p)] = str(o)
    return point_details


def extract_device_configurations(graph):
    devices = {}
    BACNET = Namespace("http://data.ashrae.org/bacnet/2020#")
    for s, p, o in graph:
        if p == BACNET.contains:
            device_id = str(s).split("//")[1]
            devices[device_id] = devices.get(device_id, {})
            point_uri = rdflib.URIRef(o)
            devices[device_id][str(point_uri)] = extract_point_details(graph, point_uri)
    return devices


def replay_configurations(devices):
    for device_id, points in devices.items():
        print(f"Device ID: {device_id}")
        for point_uri, details in points.items():
            print(f"  Point URI: {point_uri}")
            for prop, value in details.items():
                print(f"    {prop}: {value}")
        print("")


def main():
    rdf_file_path = "./raw_graph_models/vav_10"
    graph = read_rdf_file(rdf_file_path)
    print("file loaded sucess")
    device_configurations = extract_device_configurations(graph)
    replay_configurations(device_configurations)


if __name__ == "__main__":
    main()
