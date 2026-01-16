# AGENTS.md — DIY BACnet RPC Server (Microservice Contract)

This container is a **BACnet/IP + JSON-RPC gateway microservice** intended to be used in **Docker-based IoT edge deployments**.

* **BACnet/IP side (UDP 47808):** behaves like a BACnet device on the LAN.
* **HTTP side (TCP 8080):** exposes a **JSON-RPC API** (with Swagger UI) for agents to:

  * update *server-owned* sensor values
  * read the current “server point table”
  * discover and interact with *external BACnet devices* (read/write/RPM/whois, etc.)

The IoT contractor is responsible for writing agents (any language) that call these HTTP endpoints.

---

## 0) Quick start: where is the API?

* Swagger UI: `http://<edge-host>:8080/docs`
* OpenAPI JSON: `http://<edge-host>:8080/openapi.json`

This is a **JSON-RPC API** (not REST). Requests are `POST` with a JSON body containing:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "some_method",
  "params": { }
}
```

---

## 1) Networking expectations (Docker)

### BACnet/IP requires host networking

Run this container with **host networking** so BACnet broadcasts and interface binding work:

```bash
docker run --network host ...
```

(Bridged/NAT Docker networking usually breaks BACnet/IP discovery.)

### Multi-NIC edge devices

If the edge device has multiple NICs (IT vs OT), bind BACnet to the correct NIC using an explicit address when launching the server (recommended). Your repo README already documents this usage. 

---

## 2) Concept model: “server points” vs “client BACnet”

There are two worlds:

### A) Server point table (CSV-defined)

On startup, the container loads a CSV defining the BACnet objects it hosts (AV/BV, units, default value, commandable Y/N). 

* **Commandable = N** points are “server-owned sensors”

  * IoT agents should push values into these using: `server_update_points`
* **Commandable = Y** points are “BACnet commandable points”

  * agents should *not* directly update these via `server_update_points`
  * these are meant to be written from BACnet clients / supervisory logic via BACnet priority arrays (or through your client write wrapper when targeting external devices)

### B) BACnet client actions (external devices on the LAN)

This server also provides “client_*” RPC calls to:

* discover BACnet devices
* read properties
* write properties (including override / release)
* read multiple (RPM pattern)
* inspect priority arrays
* perform supervisory checks

---

## 3) API calling rules (important)

### 3.1 Params wrappers vary by method

Do **not** assume every method uses `params.request`.

Common patterns:

* `params.request` wrapper:

  * `client_read_property`
  * `client_write_property`
  * `client_read_multiple`
  * `client_whois_range`
  * `client_read_point_priority_array`

* `params.instance` wrapper:

  * `client_point_discovery`
  * `client_supervisory_logic_checks`

* `params.update` wrapper:

  * `server_update_points`

* empty params (or omitted):

  * `server_hello`
  * `server_read_all_values`
  * `server_read_commandable`
  * `client_whois_router_to_network`

Always confirm payload shape in Swagger.

### 3.2 Response shapes vary

Many endpoints return something like `{ success, message, data }`, but some return a raw object/array (example: priority array read).
Do **not** hard-code a single response schema for all calls—parse based on the endpoint.

### 3.3 JSON-RPC error handling

If you send the wrong params shape or method name, expect JSON-RPC-style errors such as:

* invalid params
* method not found
* parse error
* invalid request
* internal error

Agents should log the full response body (including `error.code`/`error.message`) for diagnostics.

---

## 4) Server endpoints (server-owned point table)

These endpoints operate on the **CSV-defined points hosted by this server**.

### 4.1 `server_hello` (health check)

Use this on agent startup to confirm the service is reachable.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "server_hello",
  "params": {}
}
```

### 4.2 `server_read_all_values` (snapshot)

Returns the current values of all server points.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "server_read_all_values",
  "params": {}
}
```

### 4.3 `server_read_commandable` (capabilities)

Returns which server points are commandable (from the CSV).

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "server_read_commandable",
  "params": {}
}
```

### 4.4 `server_update_points` (push sensor data)

Used by IoT agents to update **Commandable=N** points (server-owned sensors).

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "4",
  "method": "server_update_points",
  "params": {
    "update": {
      "outdoor-temp": 55.4,
      "space-temp": 71.2,
      "co2-ppm": 612
    }
  }
}
```

**Notes**

* This is a bulk update map: `point_name -> value`
* If you attempt to update **Commandable=Y** points here, the server may ignore/reject them (design intent: commandable points are controlled via BACnet override mechanics).
* Use `server_read_all_values` after update to verify.

---

## 5) BACnet client endpoints (interacting with external devices)

These endpoints target **real BACnet devices** on the BACnet LAN.

### 5.1 `client_whois_range` (discovery sweep)

Scan a device-instance range for responses.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "10",
  "method": "client_whois_range",
  "params": {
    "request": {
      "start_instance": 1000,
      "end_instance": 200000
    }
  }
}
```

### 5.2 `client_read_property` (single property read)

Read one property from one BACnet object.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "11",
  "method": "client_read_property",
  "params": {
    "request": {
      "device_instance": 987654,
      "object_identifier": "analog-output,1",
      "property_identifier": "present-value"
    }
  }
}
```

### 5.3 `client_write_property` (write / override / release)

Write a property (usually `present-value`) to an external BACnet object.

**Write example (override)**

```json
{
  "jsonrpc": "2.0",
  "id": "12",
  "method": "client_write_property",
  "params": {
    "request": {
      "device_instance": 987654,
      "object_identifier": "analog-output,1",
      "property_identifier": "present-value",
      "value": 72.0,
      "priority": 12
    }
  }
}
```

**Release example (IMPORTANT)**
To release an override, write `"null"` (string) with the same priority:

```json
{
  "jsonrpc": "2.0",
  "id": "13",
  "method": "client_write_property",
  "params": {
    "request": {
      "device_instance": 987654,
      "object_identifier": "analog-output,1",
      "property_identifier": "present-value",
      "value": "null",
      "priority": 12
    }
  }
}
```

### 5.4 `client_read_multiple` (RPM pattern)

Efficiently read many object/property pairs from one device.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "14",
  "method": "client_read_multiple",
  "params": {
    "request": {
      "device_instance": 123456,
      "requests": [
        { "object_identifier": "analog-input,2", "property_identifier": "present-value" },
        { "object_identifier": "analog-input,3", "property_identifier": "present-value" },
        { "object_identifier": "binary-output,1", "property_identifier": "status-flags" }
      ]
    }
  }
}
```

### 5.5 `client_read_point_priority_array` (override visibility)

Inspect the priority array for a point to see **who is commanding it** and at what priority.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "15",
  "method": "client_read_point_priority_array",
  "params": {
    "request": {
      "device_instance": 987654,
      "object_identifier": "analog-output,1"
    }
  }
}
```

### 5.6 `client_point_discovery`

Fetch point metadata / discovery info for a single device instance.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "16",
  "method": "client_point_discovery",
  "params": {
    "instance": { "device_instance": 987654 }
  }
}
```

### 5.7 `client_supervisory_logic_checks`

Runs “supervisory checks” and returns a structured summary.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "17",
  "method": "client_supervisory_logic_checks",
  "params": {
    "instance": { "device_instance": 987654 }
  }
}
```

### 5.8 `client_whois_router_to_network`

Router/network discovery helper.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": "18",
  "method": "client_whois_router_to_network",
  "params": {}
}
```

---

## 6) Minimal contractor workflows (what agents usually do)

### Workflow A: Push sensor data into hosted BACnet points

1. `server_hello`
2. `server_read_all_values` (optional sanity)
3. periodically call `server_update_points` with sensor readings
4. optionally `server_read_all_values` for verification

### Workflow B: “Non-invasive validation” against a real BAS controller

1. `client_whois_range` to discover the device instance
2. `client_read_multiple` to confirm you can read points
3. `client_read_point_priority_array` on one safe setpoint to see if overrides exist
4. Optionally test write/release at a safe priority (ex: 12) using `client_write_property`

### Workflow C: Supervisory insight / diagnostics

1. `client_supervisory_logic_checks`
2. log/store summary counts and point details for commissioning visibility

---

## 7) Implementation guidance for any language

Any HTTP client works. Contractor should:

* Use `POST` with `Content-Type: application/json`
* Use the Swagger UI to copy/paste exact request bodies
* Treat the API as **idempotent** where possible (send full updates rather than deltas when easy)
* Always implement:

  * timeout handling
  * retries (careful with writes)
  * structured logging of requests + responses

---

## 8) Safety notes (recommended best practices)

* Do not write to occupant-impacting setpoints unless there is a commissioning window + owner approval.
* Always prefer “read-only verification” first.
* When writing:

  * use a conservative priority (often 8 or 12 depending on site conventions)
  * always release what you override (`"null"` with matching priority)
  * verify override state using `client_read_point_priority_array`

---

## 9) Source of truth

Swagger/OpenAPI is the source of truth for:

* exact method names
* params shape
* schema types
* examples

Use: `http://<edge-host>:8080/docs`

