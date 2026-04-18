import gc
import logging
import os
import psutil

logger = logging.getLogger(__name__)

def get_mem_usage_mb() -> float:
    """Return current process resident set size in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def cleanup_memory(label: str = "General"):
    """
    Force garbage collection and log memory usage.
    Call this between heavy AI pipeline steps.
    """
    before = get_mem_usage_mb()
    gc.collect()
    after = get_mem_usage_mb()
    
    logger.info(f"[{label}] Memory Cleanup: {before:.1f}MB → {after:.1f}MB (Saved {before-after:.1f}MB)")
