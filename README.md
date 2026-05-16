# OKOK ADV BIA Scale (adv_bia_scale)

Home Assistant custom integration for Bluetooth BIA (Bioelectrical Impedance Analysis) scales that use the OKOK protocol (manufacturer ID 8394 / 0x20CA).

Supports real-time body composition measurements via passive BLE advertisement monitoring — no active Bluetooth connection required.

## Supported Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Weight | kg | Body weight |
| Impedance | Ω | Bioelectrical impedance |
| BMI | kg/m² | Body Mass Index |
| Body Fat | % | Body fat percentage |
| Muscle Mass | kg | Skeletal muscle mass |
| Bone Mass | kg | Bone mass estimate |
| Body Water | % | Total body water percentage |
| Visceral Fat | — | Visceral fat rating (1–59) |
| BMR | kcal/day | Basal Metabolic Rate |
| Metabolic Age | years | Metabolic age estimate |
| Protein | % | Body protein percentage |
| Subcutaneous Fat | % | Subcutaneous fat percentage |
| Fat-Free Mass | kg | Lean body mass |
| Body Type | — | Body type classification |
| Heart Rate | bpm | Heart rate (if measured) |

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ → Custom repositories
   - Repository URL: `https://github.com/blendmind/adv_bia_scale`
   - Category: Integration
2. Search for "OKOK ADV BIA Scale" and install
3. Restart Home Assistant

### Manual

1. Copy the `custom_components/adv_bia_scale/` directory to your HA config's `custom_components/` folder
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "OKOK ADV BIA Scale"
3. Fill in:
   - **MAC address** — your scale's Bluetooth MAC (e.g. `ED:67:27:47:C3:1F`)
   - **Name** — display name (default: "BIA Весы")
   - **Height** — your height in cm (50–250)
   - **Age** — your age in years (5–120)
   - **Gender** — Male / Female
   - **Activity level** — Sedentary / Light / Moderate / Active / Very Active

4. The integration will immediately start listening for BLE advertisements from the scale.

## Supported Scales

This integration works with BLE scales that broadcast manufacturer data under ID **8394** (0x20CA), commonly sold under brand names:

- OKOK Scale
- Etekcity Smart Scale (certain models)
- VeSync-compatible BIA scales
- Various rebranded Chinese BIA scales using the same protocol

### Protocol Details

The integration monitors passive BLE advertisements — **no pairing or connection required**. Two frame types are recognized:

- **Type 0x04** — Real-time impedance (while stepping on the scale). Weight is not available in this frame.
- **Type 0x05** — Final stabilized measurement with weight, impedance, and optional heart rate.

The scale's MAC address is appended to the end of each BLE payload and is automatically stripped during parsing.

## Updating Profile

To change your height, age, gender, or activity level:

1. Go to **Settings** → **Devices & Services** → **OKOK ADV BIA Scale**
2. Click **Configure** on your device entry
3. Update your profile values

All BIA calculations will be recalculated on the next measurement.

## Troubleshooting

### Sensors show "Unknown"

- **Step on the scale** — the integration only updates when it receives BLE advertisement data
- Make sure Bluetooth is enabled in Home Assistant
- Check that your scale's MAC address is correct
- Verify the scale has batteries and is within Bluetooth range

### Weight shows unrealistic values

The integration uses an adaptive divisor heuristic for weight values:
- Raw values ≤ 3000 → divided by 10 (e.g., 691 → 69.1 kg)
- Raw values > 3000 → divided by 100 (e.g., 8439 → 84.39 kg)

If weight looks wrong, file an issue with the raw hex from the debug log.

### Enabling Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.adv_bia_scale: debug
```

Then check `Settings` → `System` → `Logs` for detailed parsing information.

## Credits

- BIA calculation formulas based on standard bioelectrical impedance analysis research
- Protocol reverse-engineered from OKOK Scale BLE advertisements

## License

MIT License — see [LICENSE](LICENSE)