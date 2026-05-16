"""BLE advertisement parser for OKOK/Scale format.

Protocol analysis based on observed data from ED:67:27:47:C3:1F:

HA passes manufacturer_data[8394] as raw bytes.
The BLE advertisement includes the scale's MAC as the LAST 6 bytes.
Actual payload = data[:-6], MAC = data[-6:].

Payload format (13 bytes without MAC):
  [0]    = 0x0B (frame type, constant)
  [1-4]  = 0x00 (reserved/sequence)
  [5]    = protocol version (0x01 observed)
  [6]    = measurement type
           0x04 = real-time impedance (scale stabilizing)
           0x05 = finalized measurement (weight + impedance + HR)
  [7+]   = measurement data (varies by type)

Type 0x04 (real-time impedance):
  [7-8]  = impedance in Ohms (uint16 LE)
  [9-11] = 0x00 padding
  [12]   = checksum

Type 0x05 (finalized measurement):
  [7-8]  = weight raw (uint16 LE)
           divisor: if raw > 3000 → ÷100 (e.g. 8439 → 84.39 kg)
                    else → ÷10 (e.g. 691 → 69.1 kg)
  [9-10] = impedance * 10 in 0.1 Ohm (uint16 LE, e.g. 5052 → 505.2 Ω)
  [11]   = heart rate (single byte, 0 if not measured)
  [12]   = checksum
"""

import struct
import logging

_LOGGER = logging.getLogger(__name__)

MANUFACTURER_ID_OKOK = 0x20CA  # 8394 decimal

FRAME_TYPE = 0x0B
MEAS_TYPE_IMPEDANCE = 0x04  # Real-time impedance only
MEAS_TYPE_FULL = 0x05       # Weight + impedance + HR


def parse_okok_advertisement(data: bytes) -> dict | None:
    """Parse BLE manufacturer data from OKOK scale.

    Args:
        data: Raw bytes from manufacturer_data[8394].
              May include MAC address as last 6 bytes.

    Returns:
        dict with weight_kg, impedance, heart_rate, raw_hex, status
        or None if not a valid OKOK packet.
    """
    if len(data) < 7:
        _LOGGER.debug("Parser: data too short (%d bytes)", len(data))
        return None

    # Strip trailing MAC address if present (6 bytes at the end)
    payload = data
    if len(data) >= 13:
        potential_mac = data[-6:]
        # MAC bytes are typically non-zero and in a valid range
        if all(b != 0 for b in potential_mac[:3]):
            payload = data[:-6]
            _LOGGER.debug(
                "Parser: stripped MAC suffix %s, payload len %d",
                ":".join(f"{b:02X}" for b in potential_mac),
                len(payload),
            )

    if len(payload) < 7:
        _LOGGER.debug("Parser: payload too short after MAC strip (%d bytes)", len(payload))
        return None

    # Verify frame type
    if payload[0] != FRAME_TYPE:
        _LOGGER.debug("Parser: unexpected frame type 0x%02X", payload[0])
        return _parse_fallback(data)

    result = {
        "raw_hex": data.hex(),
        "impedance": 0,
        "heart_rate": 0,
        "status": payload[0],
    }

    version = payload[5] if len(payload) > 5 else 0
    meas_type = payload[6] if len(payload) > 6 else 0

    _LOGGER.debug(
        "Parser: frame=0x%02X, version=%d, meas_type=0x%02X, payload_len=%d",
        payload[0], version, meas_type, len(payload),
    )

    if meas_type == MEAS_TYPE_IMPEDANCE:
        # Type 0x04: real-time impedance only (no stabilized weight)
        result["measurement_type"] = "impedance"
        if len(payload) >= 9:
            imp_raw = struct.unpack_from("<H", payload, 7)[0]
            result["impedance"] = imp_raw if 0 < imp_raw < 5000 else 0
            _LOGGER.debug("Parser: impedance-only, imp=%d Ω", imp_raw)
        return result

    elif meas_type == MEAS_TYPE_FULL:
        # Type 0x05: comprehensive measurement
        result["measurement_type"] = "full"

        if len(payload) >= 9:
            weight_raw = struct.unpack_from("<H", payload, 7)[0]
            # Heuristic divisor: if raw > 3000, use ÷100; else ÷10
            # This handles different scale firmware versions:
            #   691 / 10  = 69.1 kg
            #   8439 / 100 = 84.39 kg
            weight_divisor = 100 if weight_raw > 3000 else 10
            result["weight_kg"] = round(weight_raw / weight_divisor, 1)
            _LOGGER.debug(
                "Parser: weight_raw=%d → %.1f kg (÷%d)",
                weight_raw, result["weight_kg"], weight_divisor,
            )

        if len(payload) >= 11:
            imp_raw = struct.unpack_from("<H", payload, 9)[0]
            result["impedance"] = round(imp_raw / 10.0, 1) if imp_raw > 0 else 0
            _LOGGER.debug("Parser: impedance_raw=%d → %.1f Ω", imp_raw, result["impedance"])

        if len(payload) >= 12:
            hr = payload[11]
            result["heart_rate"] = hr if 30 <= hr <= 220 else 0
            _LOGGER.debug("Parser: heart_rate=%d", hr)

        return result

    else:
        _LOGGER.debug("Parser: unknown meas_type 0x%02X, trying fallback", meas_type)
        return _parse_fallback(data)


def _parse_fallback(data: bytes) -> dict | None:
    """Last resort: scan for weight-like values in raw bytes."""
    if len(data) < 4:
        return None

    result = {
        "raw_hex": data.hex(),
        "impedance": 0,
        "heart_rate": 0,
        "status": data[0] if data else 0,
    }

    # Strip MAC if present
    payload = data[:-6] if len(data) >= 13 else data

    # Scan for uint16le values that could be weight (30-200 kg => 300-2000 in 0.1kg)
    for i in range(len(payload) - 1):
        val = struct.unpack_from("<H", payload, i)[0]
        if 300 <= val <= 2500:
            result["weight_kg"] = round(val / 10.0, 1)
            # Look for impedance nearby
            for j in range(i + 2, min(i + 6, len(payload) - 1)):
                imp_val = struct.unpack_from("<H", payload, j)[0]
                if 100 <= imp_val <= 5000:
                    result["impedance"] = round(imp_val / 10.0, 1)
                    return result
            return result
        elif 3000 <= val <= 25000:
            result["weight_kg"] = round(val / 100.0, 1)
            for j in range(i + 2, min(i + 6, len(payload) - 1)):
                imp_val = struct.unpack_from("<H", payload, j)[0]
                if 100 <= imp_val <= 5000:
                    result["impedance"] = round(imp_val / 10.0, 1)
                    return result
            return result

    _LOGGER.debug("fallback: no weight-like value found in %s", data.hex())
    return None