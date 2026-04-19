import psutil
import time
import asyncio
from config import logger, CPU_THRESHOLD, CPU_CHECK_INTERVAL

async def monitor_system():
    """Monitors CPU usage and logs warnings if threshold is exceeded."""
    logger.info("🚀 System monitor started")
    while True:
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            if cpu_usage > CPU_THRESHOLD:
                logger.warning(f"🔥 High CPU usage detected: {cpu_usage}%")
            
            if memory.percent > 90:
                logger.warning(f"🚨 High Memory usage detected: {memory.percent}%")
                
            # Log periodic stats every 5 minutes regardless of threshold
            # (CPU_CHECK_INTERVAL is 30s by default, so every 10 iterations)
            # For simplicity, just log info every hour or use a counter
            
            await asyncio.sleep(CPU_CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Error in system monitor: {e}")
            await asyncio.sleep(60)
