# Biscuit (Unitree Go2 Pro) Telemetry Investigation Report

**Date:** January 11, 2026
**Investigator:** Automated via Claude
**Device:** Unitree Go2 Pro "Biscuit"
**IP Address:** 10.0.0.148
**Jailbreak:** Roboverse

---

## Executive Summary

**CONFIRMED: Biscuit is configured to send telemetry data to Unitree servers every 5 minutes (300 seconds).** The robot also reports online status every second and checks for remote commands every 5 seconds.

Due to the country setting (US), telemetry goes to `global-robot-mqtt.unitree.com` instead of `robot-mqtt.unitree.com` (China).

---

## Device Identity

| Property | Value |
|----------|-------|
| Serial/Code | B42D2000P5CC7FK5 |
| Hardware Rev | 20 |
| Firmware | 11421304 |
| Country | US |
| Bluetooth ID | 35813 |
| RF Code | *4C592 |

---

## Telemetry Configuration Found

**File:** `/unitree/module/robot_state/robot_state_service.json`

```json
{
    "MQTTAuth": 1,
    "MQTTAutoReconnect": true,
    "GetCmdInterval": 5,        // Check for commands every 5 seconds
    "ReportInterval": 300,       // TELEMETRY EVERY 5 MINUTES
    "OnlineReportInterval": 1,   // Online status every SECOND
}
```

---

## Telemetry Endpoints Discovered

| Domain | Purpose | Used When |
|--------|---------|-----------|
| `global-robot-mqtt.unitree.com` | MQTT telemetry server | Country != CN |
| `robot-mqtt.unitree.com` | MQTT telemetry server (China) | Country == CN |
| `gpt-proxy.unitree.com:6080` | AI/TTS token API | Voice features |
| `oss-global-cdn.unitree.com` | CDN for assets | Pet mode images |
| `api.siliconflow.cn` | Chinese LLM API | AI features |

---

## Data Types Being Transmitted

From WebRTC bridge analysis (`unitreeWebRTCClientMaster`):

- `Go2FrontVideoData_` - **Front camera video stream**
- `AudioData_` - **Microphone audio**
- `BmsState_` - Battery status
- `IMUState_` - Orientation/motion sensors
- `MotorState_` - Motor positions/torques
- `LowState_` - Low-level robot state
- `LidarState_` - LIDAR sensor data
- `SportModeState_` - Movement mode
- `UwbState_` - **Location tracking (UWB)**
- `WirelessController_` - Controller inputs
- `VoxelMapCompressed_` - 3D environment map

---

## Key Files Involved in Telemetry

1. `/unitree/module/net_switcher/net_switcher.py` - Network/MQTT management
2. `/unitree/module/robot_state/robot_state_service` - State reporting binary
3. `/unitree/module/robot_state/robot_state_service.json` - Config with intervals
4. `/unitree/module/webrtc_bridge/bin/unitreeWebRTCClientMaster` - Video/audio streaming
5. `/unitree/module/pet_go/myrequests.py` - API requests to Unitree

---

## Running Services

Key services found running:
- `master_service.service` - Main Unitree service controller
- `robot_state_service` - Telemetry reporter
- `net_switcher.py` - Network and MQTT management
- `webrtc_bridge` - Video/audio streaming
- `vui_service` - Voice UI (uses cloud TTS)

---

## Current Status

At time of investigation:
- **No active external connections detected** (only local SSH)
- Robot is on WiFi (10.0.0.148)
- 4G modem present but not active

This may indicate:
1. Telemetry blocked by Roboverse jailbreak
2. No internet route configured
3. Telemetry runs on timer (next report pending)

---

## How to Block Telemetry

### Option 1: DNS Sinkhole (Recommended)

Add to `/etc/hosts` on Biscuit:
```
127.0.0.1 robot-mqtt.unitree.com
127.0.0.1 global-robot-mqtt.unitree.com
127.0.0.1 gpt-proxy.unitree.com
127.0.0.1 oss-global-cdn.unitree.com
127.0.0.1 api.siliconflow.cn
127.0.0.1 www.unitree.com
```

### Option 2: Disable Services

```bash
# Stop and disable the reporting service
systemctl stop robot_state_service
systemctl disable robot_state_service

# Stop net switcher
pkill -f net_switcher.py
```

### Option 3: Firewall on Biscuit

```bash
# Block all outbound except local network
iptables -A OUTPUT -d 10.0.0.0/8 -j ACCEPT
iptables -A OUTPUT -d 192.168.0.0/16 -j ACCEPT
iptables -A OUTPUT -d 127.0.0.0/8 -j ACCEPT
iptables -A OUTPUT -j DROP
iptables-save > /etc/iptables.rules
```

### Option 4: Router Firewall

Block 10.0.0.148 from accessing the internet while allowing LAN traffic.

---

## Evidence Files

All evidence saved to: `~/biscuit-investigation/evidence_20260111/`

- `processes_all.txt` - All running processes
- `processes_suspicious.txt` - Telemetry-related processes
- `connections_established.txt` - Network connections
- `connections_external.txt` - External (non-LAN) connections
- `services_running.txt` - Systemd services
- `config_telemetry.txt` - Files mentioning telemetry endpoints
- `net_switcher_full.py` - Full MQTT management code

---

## Recommendations

1. **Immediate:** Add DNS sinkhole entries to block telemetry domains
2. **Verify:** Monitor network traffic for 24h to confirm blocking works
3. **Document:** Keep this report for Privacy Commissioner complaint if desired
4. **Share:** Consider sharing findings with security researchers

---

## Legal Notes

- This investigation was performed on personally-owned hardware
- Roboverse jailbreak provides legitimate root access
- Unitree's telemetry practices likely violate PIPEDA (Canada)
- FCC has banned Unitree imports (US) due to these concerns

---

*Report generated: 2026-01-11*
