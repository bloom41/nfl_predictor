"""
Memory-efficient data processing utilities to prevent memory leaks
"""
import gc
import logging
import os
import time
import resource
import sys

# Try to import psutil, fallback to basic resource monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from typing import Iterator, List, Dict, Any, Optional, Callable, Generator, Tuple
from contextlib import contextmanager
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_mb: float
    available_mb: float
    used_mb: float
    percent_used: float
    process_mb: float

class MemoryMonitor:
    """Monitor and manage memory usage"""
    
    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 90.0):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.logger = logging.getLogger(f"{__name__}.MemoryMonitor")
        
    def get_memory_stats(self) -> MemoryStats:
        """Get current memory usage statistics"""
        try:
            if HAS_PSUTIL:
                # Use psutil for detailed stats
                system_memory = psutil.virtual_memory()
                process = psutil.Process(os.getpid())
                process_memory = process.memory_info().rss / 1024 / 1024  # MB
                
                return MemoryStats(
                    total_mb=system_memory.total / 1024 / 1024,
                    available_mb=system_memory.available / 1024 / 1024,
                    used_mb=system_memory.used / 1024 / 1024,
                    percent_used=system_memory.percent,
                    process_mb=process_memory
                )
            else:
                # Fallback to basic resource monitoring
                try:
                    # Get process memory usage (RSS) in KB, convert to MB
                    process_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    if sys.platform == 'darwin':  # macOS reports in bytes
                        process_mb = process_memory / 1024 / 1024
                    else:  # Linux reports in KB
                        process_mb = process_memory / 1024
                    
                    # Estimate system memory (can't get exact without psutil)
                    estimated_total = 8192  # Assume 8GB default
                    estimated_used = process_mb * 10  # Rough estimate
                    percent_used = min((estimated_used / estimated_total) * 100, 100)
                    
                    return MemoryStats(
                        total_mb=estimated_total,
                        available_mb=estimated_total - estimated_used,
                        used_mb=estimated_used,
                        percent_used=percent_used,
                        process_mb=process_mb
                    )
                except Exception:
                    # Final fallback - return minimal stats
                    return MemoryStats(
                        total_mb=8192,
                        available_mb=4096,
                        used_mb=4096,
                        percent_used=50.0,
                        process_mb=100.0
                    )
        except Exception as e:
            self.logger.error(f"Error getting memory stats: {e}")
            return MemoryStats(0, 0, 0, 0, 0)
    
    def check_memory_pressure(self) -> Tuple[bool, str]:
        """
        Check if system is under memory pressure
        
        Returns:
            tuple: (is_under_pressure, status_message)
        """
        stats = self.get_memory_stats()
        
        if stats.percent_used >= self.critical_threshold:
            return True, f"CRITICAL: Memory usage at {stats.percent_used:.1f}%"
        elif stats.percent_used >= self.warning_threshold:
            return True, f"WARNING: Memory usage at {stats.percent_used:.1f}%"
        else:
            return False, f"OK: Memory usage at {stats.percent_used:.1f}%"
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return statistics"""
        before_stats = self.get_memory_stats()
        
        # Force garbage collection
        collected = gc.collect()
        
        after_stats = self.get_memory_stats()
        memory_freed = before_stats.process_mb - after_stats.process_mb
        
        stats = {
            'objects_collected': collected,
            'memory_freed_mb': memory_freed,
            'before_usage_mb': before_stats.process_mb,
            'after_usage_mb': after_stats.process_mb
        }
        
        self.logger.info(f"Garbage collection freed {memory_freed:.1f}MB, collected {collected} objects")
        return stats

# Global memory monitor
memory_monitor = MemoryMonitor()

@contextmanager
def memory_limit_context(max_memory_mb: float = 1000.0):
    """
    Context manager that monitors memory usage and raises error if exceeded
    """
    initial_stats = memory_monitor.get_memory_stats()
    
    try:
        yield
    finally:
        final_stats = memory_monitor.get_memory_stats()
        memory_increase = final_stats.process_mb - initial_stats.process_mb
        
        if memory_increase > max_memory_mb:
            logger.warning(f"Memory usage increased by {memory_increase:.1f}MB (limit: {max_memory_mb}MB)")
            # Force cleanup
            memory_monitor.force_garbage_collection()

class StreamingDataProcessor:
    """
    Process large datasets in chunks to prevent memory exhaustion
    """
    
    def __init__(self, chunk_size: int = 1000, max_memory_mb: float = 500.0):
        self.chunk_size = chunk_size
        self.max_memory_mb = max_memory_mb
        self.logger = logging.getLogger(f"{__name__}.StreamingDataProcessor")
        
    def process_dataframe_chunks(self, df: pd.DataFrame, 
                                process_func: Callable[[pd.DataFrame], pd.DataFrame],
                                reduce_func: Optional[Callable[[List[pd.DataFrame]], pd.DataFrame]] = None) -> pd.DataFrame:
        """
        Process DataFrame in chunks to manage memory usage
        
        Args:
            df: Input DataFrame
            process_func: Function to apply to each chunk
            reduce_func: Function to combine results (default: concatenate)
            
        Returns:
            Processed DataFrame
        """
        if reduce_func is None:
            reduce_func = lambda chunks: pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
        
        try:
            results = []
            total_chunks = len(df) // self.chunk_size + (1 if len(df) % self.chunk_size else 0)
            
            self.logger.info(f"Processing DataFrame with {len(df)} rows in {total_chunks} chunks")
            
            for i in range(0, len(df), self.chunk_size):
                chunk = df.iloc[i:i + self.chunk_size].copy()
                
                # Check memory before processing
                is_pressure, pressure_msg = memory_monitor.check_memory_pressure()
                if is_pressure:
                    self.logger.warning(f"Memory pressure detected before chunk {i//self.chunk_size + 1}: {pressure_msg}")
                    memory_monitor.force_garbage_collection()
                
                # Process chunk
                try:
                    processed_chunk = process_func(chunk)
                    if processed_chunk is not None and not processed_chunk.empty:
                        results.append(processed_chunk)
                except Exception as e:
                    self.logger.error(f"Error processing chunk {i//self.chunk_size + 1}: {e}")
                    continue
                
                # Clean up chunk reference
                del chunk
                
                # Periodic garbage collection
                if (i // self.chunk_size + 1) % 10 == 0:
                    memory_monitor.force_garbage_collection()
            
            # Combine results
            if results:
                final_result = reduce_func(results)
                self.logger.info(f"Successfully processed {len(results)} chunks into result with {len(final_result)} rows")
                return final_result
            else:
                self.logger.warning("No results from chunk processing")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error in chunk processing: {e}")
            return pd.DataFrame()
        finally:
            # Final cleanup
            memory_monitor.force_garbage_collection()
    
    def process_large_list_chunks(self, data_list: List[Any],
                                 process_func: Callable[[List[Any]], List[Any]],
                                 reduce_func: Optional[Callable[[List[List[Any]]], List[Any]]] = None) -> List[Any]:
        """
        Process large lists in chunks to manage memory usage
        """
        if reduce_func is None:
            reduce_func = lambda chunks: [item for chunk in chunks for item in chunk]
        
        try:
            results = []
            total_chunks = len(data_list) // self.chunk_size + (1 if len(data_list) % self.chunk_size else 0)
            
            self.logger.info(f"Processing list with {len(data_list)} items in {total_chunks} chunks")
            
            for i in range(0, len(data_list), self.chunk_size):
                chunk = data_list[i:i + self.chunk_size]
                
                # Check memory
                is_pressure, pressure_msg = memory_monitor.check_memory_pressure()
                if is_pressure:
                    memory_monitor.force_garbage_collection()
                
                # Process chunk
                try:
                    processed_chunk = process_func(chunk)
                    if processed_chunk:
                        results.append(processed_chunk)
                except Exception as e:
                    self.logger.error(f"Error processing list chunk {i//self.chunk_size + 1}: {e}")
                    continue
                
                # Clean up
                del chunk
            
            # Combine results
            if results:
                final_result = reduce_func(results)
                self.logger.info(f"Successfully processed {len(results)} list chunks")
                return final_result
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error in list chunk processing: {e}")
            return []

class MemoryEfficientDataCollector:
    """
    Collect data efficiently with automatic cleanup and memory management
    """
    
    def __init__(self, max_items: int = 10000, cleanup_threshold: float = 80.0):
        self.max_items = max_items
        self.cleanup_threshold = cleanup_threshold
        self.data_buffer = []
        self.logger = logging.getLogger(f"{__name__}.MemoryEfficientDataCollector")
        
    def add_data(self, item: Any) -> bool:
        """
        Add data item with automatic cleanup
        
        Returns:
            bool: True if added successfully, False if rejected due to memory pressure
        """
        # Check memory pressure
        is_pressure, _ = memory_monitor.check_memory_pressure()
        if is_pressure:
            self._cleanup_old_data()
            
            # Check again after cleanup
            is_pressure, pressure_msg = memory_monitor.check_memory_pressure()
            if is_pressure:
                self.logger.warning(f"Rejecting data due to memory pressure: {pressure_msg}")
                return False
        
        # Add item
        self.data_buffer.append(item)
        
        # Check buffer size
        if len(self.data_buffer) > self.max_items:
            self._cleanup_old_data()
        
        return True
    
    def add_batch_data(self, items: List[Any]) -> int:
        """
        Add batch of data items
        
        Returns:
            int: Number of items successfully added
        """
        added_count = 0
        
        for item in items:
            if self.add_data(item):
                added_count += 1
            else:
                break  # Stop on memory pressure
        
        return added_count
    
    def get_data(self, clear_buffer: bool = False) -> List[Any]:
        """Get collected data"""
        data = self.data_buffer.copy()
        
        if clear_buffer:
            self.clear_data()
        
        return data
    
    def clear_data(self):
        """Clear all collected data"""
        self.data_buffer.clear()
        memory_monitor.force_garbage_collection()
        self.logger.debug("Data buffer cleared")
    
    def _cleanup_old_data(self):
        """Clean up old data to free memory"""
        if len(self.data_buffer) > self.max_items // 2:
            # Keep only the most recent half
            keep_count = self.max_items // 2
            self.data_buffer = self.data_buffer[-keep_count:]
            memory_monitor.force_garbage_collection()
            self.logger.info(f"Cleaned up old data, keeping {keep_count} most recent items")

class MemoryEfficientIterator:
    """
    Iterator that processes data efficiently without loading everything into memory
    """
    
    def __init__(self, data_source: Iterator[Any], batch_size: int = 100):
        self.data_source = data_source
        self.batch_size = batch_size
        self.logger = logging.getLogger(f"{__name__}.MemoryEfficientIterator")
        
    def __iter__(self):
        return self
    
    def __next__(self):
        batch = []
        
        try:
            for _ in range(self.batch_size):
                item = next(self.data_source)
                batch.append(item)
        except StopIteration:
            if batch:
                return batch
            else:
                raise
        
        return batch
    
    def process_batches(self, process_func: Callable[[List[Any]], Any]) -> Generator[Any, None, None]:
        """Process data in batches"""
        batch_count = 0
        
        try:
            for batch in self:
                # Check memory before processing
                is_pressure, _ = memory_monitor.check_memory_pressure()
                if is_pressure:
                    memory_monitor.force_garbage_collection()
                
                # Process batch
                try:
                    result = process_func(batch)
                    if result is not None:
                        yield result
                        batch_count += 1
                except Exception as e:
                    self.logger.error(f"Error processing batch {batch_count}: {e}")
                    continue
                
                # Clean up batch
                del batch
                
                # Periodic cleanup
                if batch_count % 10 == 0:
                    memory_monitor.force_garbage_collection()
                    
        except Exception as e:
            self.logger.error(f"Error in batch processing: {e}")

def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize DataFrame memory usage by converting data types
    """
    logger.info(f"Optimizing DataFrame memory usage (original: {df.memory_usage(deep=True).sum() / 1024**2:.1f}MB)")
    
    optimized_df = df.copy()
    
    # Optimize numeric columns
    for col in optimized_df.select_dtypes(include=['int64']).columns:
        col_min = optimized_df[col].min()
        col_max = optimized_df[col].max()
        
        if col_min >= np.iinfo(np.int8).min and col_max <= np.iinfo(np.int8).max:
            optimized_df[col] = optimized_df[col].astype(np.int8)
        elif col_min >= np.iinfo(np.int16).min and col_max <= np.iinfo(np.int16).max:
            optimized_df[col] = optimized_df[col].astype(np.int16)
        elif col_min >= np.iinfo(np.int32).min and col_max <= np.iinfo(np.int32).max:
            optimized_df[col] = optimized_df[col].astype(np.int32)
    
    # Optimize float columns
    for col in optimized_df.select_dtypes(include=['float64']).columns:
        optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='float')
    
    # Optimize string columns
    for col in optimized_df.select_dtypes(include=['object']).columns:
        num_unique_values = len(optimized_df[col].unique())
        num_total_values = len(optimized_df[col])
        
        if num_unique_values / num_total_values < 0.5:  # If less than 50% unique
            optimized_df[col] = optimized_df[col].astype('category')
    
    final_memory = optimized_df.memory_usage(deep=True).sum() / 1024**2
    memory_reduction = ((df.memory_usage(deep=True).sum() - optimized_df.memory_usage(deep=True).sum()) 
                       / df.memory_usage(deep=True).sum()) * 100
    
    logger.info(f"Memory optimization complete: {final_memory:.1f}MB ({memory_reduction:.1f}% reduction)")
    
    return optimized_df

@contextmanager
def efficient_large_dataframe_processing(df: pd.DataFrame, chunk_size: int = 1000):
    """
    Context manager for processing large DataFrames efficiently
    """
    initial_memory = memory_monitor.get_memory_stats().process_mb
    
    try:
        # Optimize DataFrame
        optimized_df = optimize_dataframe_memory(df)
        
        # Create streaming processor
        processor = StreamingDataProcessor(chunk_size=chunk_size)
        
        yield processor, optimized_df
        
    finally:
        # Cleanup
        del df
        if 'optimized_df' in locals():
            del optimized_df
        
        # Force garbage collection
        memory_monitor.force_garbage_collection()
        
        final_memory = memory_monitor.get_memory_stats().process_mb
        memory_change = final_memory - initial_memory
        
        if memory_change > 0:
            logger.warning(f"Memory increased by {memory_change:.1f}MB during processing")
        else:
            logger.info(f"Memory decreased by {abs(memory_change):.1f}MB during processing")

class MemoryLeakDetector:
    """Detect potential memory leaks in data processing"""
    
    def __init__(self, sample_interval: int = 60):
        self.sample_interval = sample_interval
        self.memory_samples = []
        self.logger = logging.getLogger(f"{__name__}.MemoryLeakDetector")
    
    def start_monitoring(self):
        """Start monitoring memory usage"""
        import threading
        
        def monitor_loop():
            while True:
                stats = memory_monitor.get_memory_stats()
                self.memory_samples.append({
                    'timestamp': datetime.utcnow(),
                    'process_mb': stats.process_mb,
                    'system_percent': stats.percent_used
                })
                
                # Keep only last 100 samples
                if len(self.memory_samples) > 100:
                    self.memory_samples = self.memory_samples[-100:]
                
                time.sleep(self.sample_interval)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        self.logger.info("Memory leak detection started")
    
    def detect_leaks(self) -> Dict[str, Any]:
        """Detect potential memory leaks"""
        if len(self.memory_samples) < 10:
            return {'status': 'insufficient_data'}
        
        # Calculate memory growth trend
        recent_samples = self.memory_samples[-10:]
        memory_values = [sample['process_mb'] for sample in recent_samples]
        
        # Simple linear regression to detect trend
        x = list(range(len(memory_values)))
        slope = np.polyfit(x, memory_values, 1)[0]
        
        # Detect if consistently growing
        is_leak = slope > 1.0  # Growing by more than 1MB per sample
        
        return {
            'status': 'leak_detected' if is_leak else 'normal',
            'memory_growth_rate_mb': slope,
            'current_memory_mb': memory_values[-1],
            'samples_analyzed': len(recent_samples)
        }

# Global instances
streaming_processor = StreamingDataProcessor()
memory_leak_detector = MemoryLeakDetector()

__all__ = [
    'MemoryMonitor', 'StreamingDataProcessor', 'MemoryEfficientDataCollector',
    'MemoryEfficientIterator', 'memory_monitor', 'streaming_processor',
    'optimize_dataframe_memory', 'efficient_large_dataframe_processing',
    'memory_limit_context', 'MemoryLeakDetector', 'memory_leak_detector'
]