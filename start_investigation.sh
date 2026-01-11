#!/bin/bash
# Biscuit Telemetry Investigation - Auto Runner
# Run with: sudo ./start_investigation.sh

INVESTIGATION_DIR=~/biscuit-investigation
EVIDENCE_DIR="$INVESTIGATION_DIR/evidence_$(date +%Y%m%d_%H%M%S)"
BISCUIT_IP="10.0.0.148"

echo "=========================================="
echo "  BISCUIT TELEMETRY INVESTIGATION"
echo "  Started: $(date)"
echo "=========================================="

# Create evidence directory
mkdir -p "$EVIDENCE_DIR"
cd "$EVIDENCE_DIR"

echo "[*] Evidence directory: $EVIDENCE_DIR"
echo "[*] Target IP: $BISCUIT_IP"
echo ""

# Start full packet capture
echo "[1/4] Starting full packet capture..."
tcpdump -i en0 host $BISCUIT_IP -w full_capture.pcap &
TCPDUMP_FULL_PID=$!
echo "      PID: $TCPDUMP_FULL_PID"

# Start DNS-specific capture
echo "[2/4] Starting DNS capture..."
tcpdump -i en0 host $BISCUIT_IP and port 53 -w dns_capture.pcap &
TCPDUMP_DNS_PID=$!
echo "      PID: $TCPDUMP_DNS_PID"

# Start external-only capture (non-LAN traffic)
echo "[3/4] Starting external traffic capture..."
tcpdump -i en0 "host $BISCUIT_IP and not net 10.0.0.0/8 and not net 192.168.0.0/16" -w external_only.pcap &
TCPDUMP_EXT_PID=$!
echo "      PID: $TCPDUMP_EXT_PID"

# Log file
LOG_FILE="$EVIDENCE_DIR/investigation.log"
echo "Investigation started: $(date)" > "$LOG_FILE"
echo "Biscuit IP: $BISCUIT_IP" >> "$LOG_FILE"
echo "Evidence dir: $EVIDENCE_DIR" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "[4/4] Starting connection monitor..."
echo ""
echo "=========================================="
echo "  CAPTURES RUNNING - DO NOT CLOSE"
echo "  Press Ctrl+C when done investigating"
echo "=========================================="
echo ""

# Monitor loop - log when Biscuit comes online and any connections
while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    # Check if Biscuit is online
    if ping -c 1 -W 1 $BISCUIT_IP > /dev/null 2>&1; then
        # Log active connections
        CONNECTIONS=$(netstat -an 2>/dev/null | grep $BISCUIT_IP || echo "none")
        if [ "$CONNECTIONS" != "none" ]; then
            echo "[$TIMESTAMP] Biscuit ONLINE - Connections detected" | tee -a "$LOG_FILE"
        fi
    else
        echo "[$TIMESTAMP] Waiting for Biscuit..."
    fi

    sleep 10
done

# Cleanup on exit
trap "echo 'Stopping captures...'; kill $TCPDUMP_FULL_PID $TCPDUMP_DNS_PID $TCPDUMP_EXT_PID 2>/dev/null; echo 'Done. Evidence saved to $EVIDENCE_DIR'" EXIT
