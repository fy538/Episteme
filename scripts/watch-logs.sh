#!/bin/bash
# Watch and save Docker logs to files

# Create logs directory
mkdir -p logs

# Function to watch and save logs
watch_service() {
    SERVICE=$1
    LOG_FILE="logs/${SERVICE}.log"
    
    echo "Watching ${SERVICE} logs → ${LOG_FILE}"
    docker-compose logs -f $SERVICE >> $LOG_FILE 2>&1 &
}

# Watch all services
watch_service backend
watch_service celery
watch_service celery-beat
watch_service db
watch_service redis

echo "All logs being saved to logs/ directory"
echo ""
echo "Watch backend logs: tail -f logs/backend.log"
echo "Watch celery logs: tail -f logs/celery.log"
echo ""
echo "Press Ctrl+C to stop watching"

# Wait for Ctrl+C
wait
