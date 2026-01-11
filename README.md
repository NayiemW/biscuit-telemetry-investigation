# Biscuit Telemetry Investigation

Private investigation into Unitree Go2 Pro ("Biscuit") telemetry and data collection practices.

## Summary

**CONFIRMED:** The Unitree Go2 Pro is configured to send telemetry data to Unitree servers:

| Data | Frequency | Destination |
|------|-----------|-------------|
| Full telemetry report | Every 5 minutes | `global-robot-mqtt.unitree.com` |
| Online status | Every 1 second | MQTT server |
| Command polling | Every 5 seconds | MQTT server |
| Video/Audio | Real-time | WebRTC when app connected |

## Data Types Collected

- Front camera video stream
- Microphone audio
- Battery/motor/sensor states
- Location (UWB tracking)
- LIDAR/3D environment maps
- Controller inputs
- Device identity (serial, firmware, etc.)

## Key Evidence Files

- `evidence_*/INVESTIGATION_REPORT.md` - Full detailed report
- `evidence_*/net_switcher_full.py` - MQTT telemetry code
- `evidence_*/processes_suspicious.txt` - Running telemetry processes
- `evidence_*/config_telemetry.txt` - Config files with server endpoints

## Telemetry Endpoints Discovered

```
robot-mqtt.unitree.com        - China MQTT server
global-robot-mqtt.unitree.com - Global MQTT server
gpt-proxy.unitree.com:6080    - AI/TTS API
api.siliconflow.cn            - Chinese LLM API
oss-global-cdn.unitree.com    - CDN
```

## How to Block

Add to `/etc/hosts` on the robot:
```
127.0.0.1 robot-mqtt.unitree.com
127.0.0.1 global-robot-mqtt.unitree.com
127.0.0.1 gpt-proxy.unitree.com
127.0.0.1 api.siliconflow.cn
```

## Legal Context

- FCC banned Unitree imports (Nov 2025) due to security concerns
- Likely violates PIPEDA (Canada) and GDPR (EU)
- Hidden telemetry with no opt-out

## Tools

- `start_investigation.sh` - Packet capture script (requires sudo)
- `auto_investigate.sh` - Automated SSH investigation

---

*Investigation performed: January 2026*
*Device: Unitree Go2 Pro with Roboverse jailbreak*
