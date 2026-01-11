#!/bin/bash
# Auto-Investigation Script for Biscuit Telemetry
# Waits for Biscuit, then performs comprehensive investigation

BISCUIT_IP="10.0.0.148"
EVIDENCE_DIR=~/biscuit-investigation/evidence_$(date +%Y%m%d_%H%M%S)
SSH_CMD="sshpass -p '123' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 unitree@$BISCUIT_IP"

echo "============================================"
echo "  BISCUIT TELEMETRY AUTO-INVESTIGATION"
echo "  Started: $(date)"
echo "============================================"

mkdir -p "$EVIDENCE_DIR"
cd "$EVIDENCE_DIR"

# Wait for Biscuit to come online
echo "[*] Waiting for Biscuit at $BISCUIT_IP..."
while ! ping -c 1 -W 2 $BISCUIT_IP > /dev/null 2>&1; do
    sleep 10
done

echo "[!] BISCUIT ONLINE at $(date)"
echo "[*] Waiting 90 seconds for full boot..."
sleep 90

echo ""
echo "============================================"
echo "  STARTING INVESTIGATION"
echo "============================================"
echo ""

# Test SSH
echo "[1/10] Testing SSH connection..."
if ! $SSH_CMD "echo 'SSH OK'" > /dev/null 2>&1; then
    echo "ERROR: SSH failed. Check credentials."
    exit 1
fi
echo "       SSH connection successful!"

# Process Investigation
echo "[2/10] Capturing running processes..."
$SSH_CMD "ps aux" > processes_all.txt 2>&1
$SSH_CMD "ps aux | grep -iE 'telemetry|upload|sync|mqtt|webrtc|cloud|report|beacon|phone|unitree'" > processes_suspicious.txt 2>&1
echo "       Saved to processes_*.txt"

# Network Connections
echo "[3/10] Capturing network connections..."
$SSH_CMD "netstat -an 2>/dev/null || ss -an" > connections_all.txt 2>&1
$SSH_CMD "netstat -an 2>/dev/null | grep ESTABLISHED | grep -v '10.0.0\|192.168\|127.0.0'" > connections_external.txt 2>&1
echo "       Saved to connections_*.txt"

# Systemd Services
echo "[4/10] Listing systemd services..."
$SSH_CMD "systemctl list-units --type=service --all" > services_all.txt 2>&1
$SSH_CMD "ls -la /etc/systemd/system/ /lib/systemd/system/" > services_files.txt 2>&1
echo "       Saved to services_*.txt"

# Config Files
echo "[5/10] Searching config files for telemetry endpoints..."
$SSH_CMD "grep -r 'unitree.com\|\.cn\|cloud\|api\|mqtt\|telemetry' /etc/ 2>/dev/null" > config_etc.txt 2>&1
$SSH_CMD "grep -r 'unitree.com\|\.cn\|cloud\|api\|mqtt\|telemetry' /opt/ 2>/dev/null" > config_opt.txt 2>&1
$SSH_CMD "grep -r 'unitree.com\|\.cn\|cloud\|api\|mqtt\|telemetry' /home/ 2>/dev/null" > config_home.txt 2>&1
echo "       Saved to config_*.txt"

# Hardcoded IPs
echo "[6/10] Finding hardcoded external IPs..."
$SSH_CMD "grep -rE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' /opt/ 2>/dev/null | grep -v '127.0.0\|10.0.0\|192.168\|0.0.0.0'" > hardcoded_ips.txt 2>&1
echo "       Saved to hardcoded_ips.txt"

# Log Files
echo "[7/10] Finding log files..."
$SSH_CMD "find /var/log /home /opt -name '*.log' 2>/dev/null" > log_files.txt 2>&1
$SSH_CMD "ls -la /home/unitree/" > unitree_home.txt 2>&1
echo "       Saved to log_files.txt, unitree_home.txt"

# Cron Jobs
echo "[8/10] Checking scheduled tasks..."
$SSH_CMD "crontab -l 2>/dev/null; cat /etc/crontab 2>/dev/null; ls -la /etc/cron.d/ 2>/dev/null" > cron_jobs.txt 2>&1
echo "       Saved to cron_jobs.txt"

# DNS/Hosts
echo "[9/10] Checking DNS configuration..."
$SSH_CMD "cat /etc/hosts; echo '---'; cat /etc/resolv.conf" > dns_config.txt 2>&1
echo "       Saved to dns_config.txt"

# Binary Analysis
echo "[10/10] Finding and analyzing binaries..."
$SSH_CMD "find / -name '*unitree*' -type f 2>/dev/null" > binaries_unitree.txt 2>&1
$SSH_CMD "find / -name '*telemetry*' -type f 2>/dev/null" > binaries_telemetry.txt 2>&1
$SSH_CMD "lsof -i -P -n 2>/dev/null | head -100" > lsof_network.txt 2>&1
echo "       Saved to binaries_*.txt, lsof_network.txt"

echo ""
echo "============================================"
echo "  INVESTIGATION COMPLETE"
echo "  Evidence saved to: $EVIDENCE_DIR"
echo "  Completed: $(date)"
echo "============================================"
echo ""

# Summary
echo "=== QUICK SUMMARY ==="
echo ""
echo "Suspicious processes:"
cat processes_suspicious.txt | head -10
echo ""
echo "External connections:"
cat connections_external.txt | head -10
echo ""
echo "Telemetry configs found:"
wc -l config_*.txt
echo ""

echo "Review full evidence in: $EVIDENCE_DIR"
