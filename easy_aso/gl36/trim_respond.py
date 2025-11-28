"""
Guideline 36 Trim & Respond algorithms.

This module contains reusable functions and an example agent for
implementing ASHRAE Guideline 36 Trim & Respond logic in Python.  The
functions are deliberately stateless so they can be reused across
multiple AHUs, VAV boxes or even executed as AWS Lambda functions.  A
stateful agent class combines the zone request generators and
setpoint trim/respond logic with a BACnet client.

Two key components are provided:

* ``calculate_zone_requests`` – compute the number of cooling and
  static pressure requests from a single zone based on measured
  temperatures, airflows and damper commands.  The thresholds are
  derived from Guideline 36 Section 5.1.14.3 and Section 5.1.15
  (Trim & Respond variables).  Persistence and hysteresis must be
  implemented by the caller.
* ``calculate_trim_respond`` – adjust a setpoint up or down based on
  the number of requests.  This implements the Trim & Respond loop in
  Guideline 36.  Positive ``num_requests`` above ``ignored_requests``
  cause the setpoint to be increased by ``sp_trim``; otherwise the
  setpoint is decreased by ``sp_res``, bounded by ``sp_res_max``.

The accompanying ``GL36TrimRespondAgent`` uses these functions to
aggregate requests across multiple zones and update an AHU static
pressure setpoint via a BACnet client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Tuple

from ..agent import Agent
from ..bacnet_client import BACnetClient


def calculate_zone_requests(
    zone_temp: float,
    zone_setpoint: float,
    cooling_loop_pct: float,
    airflow: float,
    airflow_setpoint: float,
    damper_cmd_pct: float,
    *,
    use_imperial: bool = False,
) -> Tuple[int, int]:
    """Calculate cooling and static pressure requests for a single zone.

    Parameters
    ----------
    zone_temp: float
        The measured zone temperature (°C or °F depending on ``use_imperial``).
    zone_setpoint: float
        The zone cooling setpoint (°C or °F).  Requests are generated when
        the temperature exceeds the setpoint by a threshold.
    cooling_loop_pct: float
        The terminal load as a percentage (0–100 %).
    airflow: float
        The measured airflow.
    airflow_setpoint: float
        The airflow setpoint.
    damper_cmd_pct: float
        The commanded damper position as a percentage (0–100 %).
    use_imperial: bool
        If true, thresholds are interpreted as Fahrenheit; otherwise Celsius.

    Returns
    -------
    cooling_requests: int
        Number of cooling (supply air temperature) requests (0–3).
    pressure_requests: int
        Number of static pressure requests (0–3).

    Notes
    -----
    This function does not implement persistence or hysteresis.  The caller
    should accumulate requests over time according to GL36 rules.  The
    thresholds and hysteresis are derived from Guideline 36 and
    documented in README_TRIM_RESPOND.md.
    """
    # Temperature thresholds (use °C by default, convert to °C if imperial)
    if use_imperial:
        high_diff = 5.0  # °F
        med_diff = 3.0
    else:
        high_diff = 3.0  # °C
        med_diff = 2.0

    temp_diff = zone_temp - zone_setpoint

    # Cooling requests
    if temp_diff >= high_diff:
        cooling_requests = 3
    elif temp_diff >= med_diff:
        cooling_requests = 2
    elif cooling_loop_pct >= 95.0:
        cooling_requests = 1
    else:
        cooling_requests = 0

    # Pressure thresholds
    flow_ratio = airflow / airflow_setpoint if airflow_setpoint > 0 else 0.0
    if flow_ratio < 0.5 and damper_cmd_pct >= 95.0:
        pressure_requests = 3
    elif flow_ratio < 0.7 and damper_cmd_pct >= 95.0:
        pressure_requests = 2
    elif damper_cmd_pct >= 95.0:
        pressure_requests = 1
    else:
        pressure_requests = 0

    return cooling_requests, pressure_requests


def calculate_trim_respond(
    current_sp: float,
    sp_min: float,
    sp_max: float,
    num_requests: int,
    ignored_requests: int,
    sp_trim: float,
    sp_res: float,
    sp_res_max: float,
) -> float:
    """Adjust a setpoint according to the Trim & Respond algorithm.

    Parameters
    ----------
    current_sp: float
        The current setpoint value.
    sp_min: float
        The minimum allowed setpoint.
    sp_max: float
        The maximum allowed setpoint.
    num_requests: int
        The total number of requests (cooling or pressure) received.
    ignored_requests: int
        The number of ignored requests (I).  Only requests above this value
        trigger a trim.
    sp_trim: float
        The amount to increase the setpoint when requests are above the
        ignored threshold.
    sp_res: float
        The amount to decrease the setpoint when requests are at or below
        the ignored threshold.  This value should be negative for
        reducing the setpoint.
    sp_res_max: float
        The maximum magnitude of the response per interval.  The sign of
        ``sp_res_max`` should match ``sp_res``.

    Returns
    -------
    float
        The new setpoint, clamped to ``[sp_min, sp_max]``.
    """
    if num_requests > ignored_requests:
        delta = sp_trim
    else:
        delta = sp_res
    # Limit the response to the maximum allowed change
    if abs(delta) > abs(sp_res_max):
        delta = sp_res_max if delta > 0 else -sp_res_max
    new_sp = current_sp + delta
    # Clamp to bounds
    if new_sp < sp_min:
        new_sp = sp_min
    if new_sp > sp_max:
        new_sp = sp_max
    return new_sp


@dataclass
class GL36TrimRespondAgent(Agent):
    """Agent implementing a GL36 Trim & Respond reset loop.

    This agent periodically reads zone measurements via a BACnet client,
    aggregates the number of requests, calculates a new static pressure
    setpoint and writes it back to BACnet.  The setpoint logic is
    stateless and can therefore be reused across multiple devices or
    implemented as a serverless function.
    """

    bacnet: BACnetClient
    zone_addresses: Iterable[str]
    zone_temp_obj: str
    zone_sp_obj: str
    zone_loop_obj: str
    zone_flow_obj: str
    zone_flow_sp_obj: str
    zone_damper_obj: str
    sp_address: str
    sp_object: str
    sp_min: float
    sp_max: float
    sp_trim: float
    sp_res: float
    sp_res_max: float
    ignored_requests: int = 0
    use_imperial: bool = False
    update_interval: float = 60.0
    current_sp: float = field(default=0.0, init=False)

    #: The BACnet priority to use when writing the static pressure setpoint.
    #: A value of -1 corresponds to the default BACnet priority.  In BACnet
    #: lower numerical priorities have higher precedence.  Using the default
    #: ensures that subsequent reads will return the value we wrote.
    write_priority: int = -1

    async def on_start(self) -> None:
        # Read the initial setpoint from BACnet
        initial_sp = await self.bacnet.read_property(self.sp_address, self.sp_object)
        self.current_sp = initial_sp if initial_sp is not None else self.sp_max

    async def on_update(self) -> None:
        # Aggregate cooling and pressure requests across all zones
        total_requests = 0
        for addr in self.zone_addresses:
            zone_temp = await self.bacnet.read_property(addr, self.zone_temp_obj) or 0.0
            zone_spt = await self.bacnet.read_property(addr, self.zone_sp_obj) or 0.0
            zone_loop = await self.bacnet.read_property(addr, self.zone_loop_obj) or 0.0
            zone_flow = await self.bacnet.read_property(addr, self.zone_flow_obj) or 0.0
            zone_flow_sp = await self.bacnet.read_property(addr, self.zone_flow_sp_obj) or 1.0
            zone_damper = await self.bacnet.read_property(addr, self.zone_damper_obj) or 0.0
            cool_req, press_req = calculate_zone_requests(
                zone_temp,
                zone_spt,
                zone_loop,
                zone_flow,
                zone_flow_sp,
                zone_damper,
                use_imperial=self.use_imperial,
            )
            total_requests += cool_req + press_req
        # Compute the new setpoint
        new_sp = calculate_trim_respond(
            current_sp=self.current_sp,
            sp_min=self.sp_min,
            sp_max=self.sp_max,
            num_requests=total_requests,
            ignored_requests=self.ignored_requests,
            sp_trim=self.sp_trim,
            sp_res=self.sp_res,
            sp_res_max=self.sp_res_max,
        )
        # Write to BACnet if changed
        if abs(new_sp - self.current_sp) > 1e-6:
            self.current_sp = new_sp
            await self.bacnet.write_property(
                self.sp_address,
                self.sp_object,
                new_sp,
                priority=self.write_priority,
            )

    async def on_stop(self) -> None:
        # Nothing to clean up in the trim/respond agent
        pass
