#!/bin/bash

# Polymarket Bot Health Check Script
# This script checks if services are running and restarts them if needed

LOG_FILE="/usr/local/var/log/polymarket_healthcheck.log"
BOT_SERVICE="com.polymarket.bot"
SIGNAL_SERVICE="com.signal.daemon"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_and_restart_service() {
    local service_name=$1
    local plist_file=$2
    
    # Check if service is loaded and running
    local status=$(launchctl list | grep "$service_name" 2>/dev/null)
    
    if [[ -z "$status" ]]; then
        log "ERROR: $service_name not loaded, loading it..."
        launchctl load "$plist_file"
        sleep 2
    else
        local pid=$(echo "$status" | awk '{print $1}')
        local exit_code=$(echo "$status" | awk '{print $2}')
        
        if [[ "$pid" == "-" ]] || [[ "$exit_code" != "0" ]]; then
            log "WARNING: $service_name not running properly (PID: $pid, Exit: $exit_code), restarting..."
            launchctl unload "$plist_file" 2>/dev/null
            sleep 2
            launchctl load "$plist_file"
            sleep 3
        else
            log "OK: $service_name running (PID: $pid)"
        fi
    fi
}

test_functionality() {
    log "Testing bot functionality..."
    
    # Test 1: Check if signal daemon HTTP API responds
    if ! curl -s --connect-timeout 5 http://localhost:8080/api/v1/check > /dev/null 2>&1; then
        log "ERROR: Signal daemon HTTP API not responding"
        return 1
    fi
    
    # Test 2: Check if bot can send a test (commented out to avoid spam)
    # Uncomment this line if you want to test sending:
    # python3 /Users/suyash/Project_2/polymarket_bot/monitor.py --send-summary --config /Users/suyash/Project_2/polymarket_bot/config.yaml > /dev/null 2>&1
    
    # Test 3: Check if log file is being updated (recent activity)
    local bot_log="/usr/local/var/log/pmarket.log"
    if [[ -f "$bot_log" ]]; then
        # Check if log has been updated in last 2 hours (7200 seconds)
        local last_update=$(stat -f "%m" "$bot_log" 2>/dev/null || echo 0)
        local current_time=$(date +%s)
        local time_diff=$((current_time - last_update))
        
        if [[ $time_diff -gt 7200 ]]; then
            log "WARNING: Bot log not updated in $((time_diff/60)) minutes"
            return 1
        fi
    fi
    
    log "OK: All functionality tests passed"
    return 0
}

# Main health check
log "=== Starting health check ==="

# Check and restart services
check_and_restart_service "$SIGNAL_SERVICE" "$HOME/Library/LaunchAgents/com.signal.daemon.plist"
check_and_restart_service "$BOT_SERVICE" "$HOME/Library/LaunchAgents/com.polymarket.bot.plist"

# Wait a bit for services to stabilize
sleep 5

# Test functionality
if ! test_functionality; then
    log "ERROR: Functionality tests failed, forcing restart of both services..."
    
    launchctl unload "$HOME/Library/LaunchAgents/$BOT_SERVICE.plist" 2>/dev/null
    launchctl unload "$HOME/Library/LaunchAgents/$SIGNAL_SERVICE.plist" 2>/dev/null
    sleep 3
    
    launchctl load "$HOME/Library/LaunchAgents/$SIGNAL_SERVICE.plist"
    sleep 3
    launchctl load "$HOME/Library/LaunchAgents/$BOT_SERVICE.plist"
    sleep 5
    
    # Test again
    if test_functionality; then
        log "SUCCESS: Services restarted and working"
    else
        log "CRITICAL: Services still not working after restart!"
    fi
else
    log "SUCCESS: All services healthy"
fi

log "=== Health check complete ==="