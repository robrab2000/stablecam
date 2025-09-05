"""
Performance benchmarking tests for StableCam.

This module contains performance tests that measure and validate the performance
characteristics of StableCam under various load conditions and device scenarios.
"""

import pytest
import time
import threading
import tempfile
import statistics
from pathlib import Path
from unittest.mock import Mock, patch
from typing import List, Dict, Any
from datetime import datetime, timedelta

from stablecam import StableCam, CameraDevice, DeviceStatus
from stablecam.registry import DeviceRegistry


class PerformanceBenchmark:
    """Utility class for performance benchmarking."""
    
    def __init__(self):
        self.results = {}
    
    def time_operation(self, name: str, operation, *args, **kwargs):
        """Time an operation and store the result."""
        start_time = time.perf_counter()
        result = operation(*args, **kwargs)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        self.results[name] = duration
        return result, duration
    
    def time_multiple_operations(self, name: str, operation, iterations: int, *args, **kwargs):
        """Time multiple iterations of an operation."""
        times = []
        results = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            result = operation(*args, **kwargs)
            end_time = time.perf_counter()
            
            times.append(end_time - start_time)
            results.append(result)
        
        self.results[name] = {
            'times': times,
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0
        }
        
        return results, times
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return self.results.copy()


class TestDetectionPerformance:
    """Performance tests for device detection operations."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        registry_path.unlink()
        yield registry_path
        if registry_path.exists():
            registry_path.unlink()
    
    def create_test_cameras(self, count: int) -> List[CameraDevice]:
        """Create test camera devices for performance testing."""
        return [
            CameraDevice(
                system_index=i,
                vendor_id=f"{(0x1000 + i):04x}",
                product_id=f"{(0x2000 + i):04x}",
                serial_number=f"PERF{i:06d}",
                port_path=f"/dev/video{i}",
                label=f"Performance Test Camera {i}",
                platform_data={"test_index": i, "benchmark": True}
            )
            for i in range(count)
        ]
    
    @pytest.mark.slow
    @pytest.mark.parametrize("device_count", [1, 5, 10, 25, 50, 100])
    def test_detection_scaling_performance(self, temp_registry, device_count):
        """Test detection performance scaling with device count."""
        cameras = self.create_test_cameras(device_count)
        benchmark = PerformanceBenchmark()
        
        with StableCam(registry_path=temp_registry) as manager:
            # Mock the detector to return our test cameras
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                # Warm up
                manager.detect()
                
                # Benchmark detection with mocked cameras
                _, detection_time = benchmark.time_operation(
                    f"detect_{device_count}_devices",
                    manager.detect
                )
                
                # Verify all devices detected within the patched context
                detected = manager.detect()
                assert len(detected) == device_count
                
                # Performance assertions
                assert detection_time < 1.0, f"Detection of {device_count} devices took {detection_time:.3f}s"
                
                # Calculate performance metrics
                devices_per_second = device_count / detection_time
                assert devices_per_second > 10, f"Detection rate too slow: {devices_per_second:.1f} devices/sec"
    
    @pytest.mark.slow
    def test_detection_consistency_performance(self, temp_registry):
        """Test detection performance consistency over multiple iterations."""
        device_count = 10
        iterations = 20
        cameras = self.create_test_cameras(device_count)
        benchmark = PerformanceBenchmark()
        
        with StableCam(registry_path=temp_registry) as manager:
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                # Benchmark multiple detection calls
                results, times = benchmark.time_multiple_operations(
                    "detection_consistency",
                    manager.detect,
                    iterations
                )
                
                # Verify consistency
                stats = benchmark.results["detection_consistency"]
                
                # All detections should succeed
                assert all(len(result) == device_count for result in results)
                
                # Performance should be consistent (low standard deviation)
                cv = stats['std_dev'] / stats['mean']  # Coefficient of variation
                assert cv < 0.5, f"Detection time too variable: CV={cv:.3f}"
                
                # No detection should be extremely slow
                assert stats['max'] < 0.5, f"Slowest detection: {stats['max']:.3f}s"
                
                # Average should be reasonable
                assert stats['mean'] < 0.1, f"Average detection time: {stats['mean']:.3f}s"
    
    @pytest.mark.slow
    def test_concurrent_detection_performance(self, temp_registry):
        """Test detection performance under concurrent access."""
        device_count = 15
        thread_count = 5
        cameras = self.create_test_cameras(device_count)
        
        results = {}
        errors = []
        
        def detection_worker(worker_id):
            try:
                with StableCam(registry_path=temp_registry) as manager:
                    with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                        start_time = time.perf_counter()
                        detected = manager.detect()
                        end_time = time.perf_counter()
                        
                        results[worker_id] = {
                            'time': end_time - start_time,
                            'count': len(detected)
                        }
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
        
        # Start concurrent detection threads
        threads = []
        start_time = time.perf_counter()
        
        for i in range(thread_count):
            thread = threading.Thread(target=detection_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10.0)
        
        total_time = time.perf_counter() - start_time
        
        # Verify no errors
        assert len(errors) == 0, f"Concurrent detection errors: {errors}"
        
        # Verify all workers completed
        assert len(results) == thread_count
        
        # Verify performance
        detection_times = [r['time'] for r in results.values()]
        avg_detection_time = statistics.mean(detection_times)
        max_detection_time = max(detection_times)
        
        assert avg_detection_time < 0.2, f"Average concurrent detection time: {avg_detection_time:.3f}s"
        assert max_detection_time < 0.5, f"Slowest concurrent detection: {max_detection_time:.3f}s"
        assert total_time < 2.0, f"Total concurrent test time: {total_time:.3f}s"


class TestRegistryPerformance:
    """Performance tests for device registry operations."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        registry_path.unlink()
        yield registry_path
        if registry_path.exists():
            registry_path.unlink()
    
    def create_test_cameras(self, count: int) -> List[CameraDevice]:
        """Create test camera devices."""
        return [
            CameraDevice(
                system_index=i,
                vendor_id=f"{(0x3000 + i):04x}",
                product_id=f"{(0x4000 + i):04x}",
                serial_number=f"REG{i:06d}",
                port_path=f"/dev/video{i}",
                label=f"Registry Test Camera {i}",
                platform_data={"registry_test": True}
            )
            for i in range(count)
        ]
    
    @pytest.mark.slow
    @pytest.mark.parametrize("device_count", [10, 50, 100, 250, 500])
    def test_registration_bulk_performance(self, temp_registry, device_count):
        """Test bulk device registration performance."""
        cameras = self.create_test_cameras(device_count)
        benchmark = PerformanceBenchmark()
        
        with StableCam(registry_path=temp_registry) as manager:
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                # Benchmark bulk registration
                start_time = time.perf_counter()
                stable_ids = []
                
                for camera in cameras:
                    stable_id = manager.register(camera)
                    stable_ids.append(stable_id)
                
                registration_time = time.perf_counter() - start_time
                
                # Performance assertions
                devices_per_second = device_count / registration_time
                assert devices_per_second > 50, f"Registration rate: {devices_per_second:.1f} devices/sec"
                assert registration_time < device_count * 0.01, f"Registration too slow: {registration_time:.3f}s"
                
                # Verify all devices registered
                assert len(stable_ids) == device_count
                assert len(set(stable_ids)) == device_count  # All unique
                
                # Verify registry state
                devices = manager.list()
                assert len(devices) == device_count
    
    @pytest.mark.slow
    def test_registry_lookup_performance(self, temp_registry):
        """Test registry lookup performance with many devices."""
        device_count = 200
        cameras = self.create_test_cameras(device_count)
        benchmark = PerformanceBenchmark()
        
        with StableCam(registry_path=temp_registry) as manager:
            # Register devices
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                stable_ids = []
                for camera in cameras:
                    stable_id = manager.register(camera)
                    stable_ids.append(stable_id)
            
            # Benchmark lookups
            lookup_iterations = 100
            
            # Test get_by_id performance
            _, lookup_times = benchmark.time_multiple_operations(
                "get_by_id_lookups",
                lambda: manager.get_by_id(stable_ids[len(stable_ids) // 2]),  # Middle device
                lookup_iterations
            )
            
            # Test list performance
            _, list_times = benchmark.time_multiple_operations(
                "list_all_devices",
                manager.list,
                lookup_iterations
            )
            
            # Performance assertions
            stats = benchmark.results
            
            # Individual lookups should be fast
            avg_lookup_time = stats["get_by_id_lookups"]["mean"]
            assert avg_lookup_time < 0.001, f"Average lookup time: {avg_lookup_time:.6f}s"
            
            # List operations should be reasonable
            avg_list_time = stats["list_all_devices"]["mean"]
            assert avg_list_time < 0.01, f"Average list time: {avg_list_time:.6f}s"
    
    @pytest.mark.slow
    def test_registry_persistence_performance(self, temp_registry):
        """Test registry file I/O performance."""
        device_count = 100
        cameras = self.create_test_cameras(device_count)
        benchmark = PerformanceBenchmark()
        
        # Test initial registry creation and population
        with StableCam(registry_path=temp_registry) as manager:
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                _, creation_time = benchmark.time_operation(
                    "registry_creation_and_population",
                    lambda: [manager.register(camera) for camera in cameras]
                )
        
        # Test registry loading performance
        load_iterations = 10
        _, load_times = benchmark.time_multiple_operations(
            "registry_loading",
            lambda: StableCam(registry_path=temp_registry),
            load_iterations
        )
        
        # Close managers to avoid resource leaks
        for manager in _:
            manager.stop()
        
        # Performance assertions
        stats = benchmark.results
        
        # Creation should be reasonable
        assert creation_time < 2.0, f"Registry creation time: {creation_time:.3f}s"
        
        # Loading should be fast
        avg_load_time = stats["registry_loading"]["mean"]
        assert avg_load_time < 0.1, f"Average registry load time: {avg_load_time:.3f}s"


class TestMonitoringPerformance:
    """Performance tests for device monitoring operations."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        registry_path.unlink()
        yield registry_path
        if registry_path.exists():
            registry_path.unlink()
    
    def create_test_cameras(self, count: int) -> List[CameraDevice]:
        """Create test camera devices."""
        return [
            CameraDevice(
                system_index=i,
                vendor_id=f"{(0x5000 + i):04x}",
                product_id=f"{(0x6000 + i):04x}",
                serial_number=f"MON{i:06d}",
                port_path=f"/dev/video{i}",
                label=f"Monitor Test Camera {i}",
                platform_data={"monitor_test": True}
            )
            for i in range(count)
        ]
    
    @pytest.mark.slow
    def test_monitoring_loop_performance(self, temp_registry):
        """Test monitoring loop performance with many devices."""
        device_count = 30
        cameras = self.create_test_cameras(device_count)
        
        monitoring_times = []
        event_count = 0
        
        def track_events(device):
            nonlocal event_count
            event_count += 1
        
        with StableCam(registry_path=temp_registry, poll_interval=0.05) as manager:
            # Register devices
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                for camera in cameras:
                    manager.register(camera)
            
            # Track monitoring performance
            original_check = manager._check_device_changes
            
            def timed_check():
                start_time = time.perf_counter()
                result = original_check()
                end_time = time.perf_counter()
                monitoring_times.append(end_time - start_time)
                return result
            
            manager._check_device_changes = timed_check
            manager.on("on_status_change", track_events)
            
            # Run monitoring
            manager.run()
            time.sleep(1.0)  # Monitor for 1 second
            manager.stop()
        
        # Performance analysis
        assert len(monitoring_times) > 10, "Should have multiple monitoring cycles"
        
        avg_time = statistics.mean(monitoring_times)
        max_time = max(monitoring_times)
        
        # Each monitoring cycle should be fast
        assert avg_time < 0.02, f"Average monitoring cycle: {avg_time:.6f}s"
        assert max_time < 0.05, f"Slowest monitoring cycle: {max_time:.6f}s"
        
        # Should handle the device count efficiently
        devices_per_second = device_count / avg_time
        assert devices_per_second > 1000, f"Monitoring rate: {devices_per_second:.0f} devices/sec"
    
    @pytest.mark.slow
    def test_event_emission_performance(self, temp_registry):
        """Test event emission performance under load."""
        device_count = 20
        cameras = self.create_test_cameras(device_count)
        
        event_times = []
        event_counts = {"connect": 0, "disconnect": 0, "status_change": 0}
        
        def time_event(event_type):
            def handler(device):
                start_time = time.perf_counter()
                event_counts[event_type] += 1
                # Simulate some event processing work
                time.sleep(0.0001)  # 0.1ms
                end_time = time.perf_counter()
                event_times.append(end_time - start_time)
            return handler
        
        with StableCam(registry_path=temp_registry, poll_interval=0.02) as manager:
            # Set up event handlers
            manager.on("on_connect", time_event("connect"))
            manager.on("on_disconnect", time_event("disconnect"))
            manager.on("on_status_change", time_event("status_change"))
            
            # Register devices
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                for camera in cameras:
                    manager.register(camera)
            
            manager.run()
            
            # Simulate device changes to trigger events
            scenarios = [
                cameras[:10],  # Half disconnected
                cameras,       # All reconnected
                cameras[5:15], # Different subset
                cameras,       # All back
            ]
            
            for scenario in scenarios:
                with patch.object(manager.detector, 'detect_cameras', return_value=scenario):
                    time.sleep(0.1)  # Let monitoring detect changes
            
            manager.stop()
        
        # Performance analysis
        assert len(event_times) > 0, "Should have emitted events"
        assert sum(event_counts.values()) > 0, "Should have processed events"
        
        # Event processing should be fast
        if event_times:
            avg_event_time = statistics.mean(event_times)
            max_event_time = max(event_times)
            
            assert avg_event_time < 0.001, f"Average event processing: {avg_event_time:.6f}s"
            assert max_event_time < 0.005, f"Slowest event processing: {max_event_time:.6f}s"
    
    @pytest.mark.slow
    def test_memory_usage_monitoring_performance(self, temp_registry):
        """Test memory usage during extended monitoring."""
        import gc
        import psutil
        import os
        
        device_count = 25
        cameras = self.create_test_cameras(device_count)
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with StableCam(registry_path=temp_registry, poll_interval=0.01) as manager:
            # Register devices
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                for camera in cameras:
                    manager.register(camera)
            
            # Start monitoring
            manager.run()
            
            # Run for extended period with device changes
            start_time = time.time()
            change_count = 0
            
            while time.time() - start_time < 2.0:  # Run for 2 seconds
                # Alternate between different device configurations
                if change_count % 2 == 0:
                    active_cameras = cameras[:device_count//2]
                else:
                    active_cameras = cameras
                
                with patch.object(manager.detector, 'detect_cameras', return_value=active_cameras):
                    time.sleep(0.05)
                    change_count += 1
            
            manager.stop()
        
        # Force garbage collection
        gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 50, f"Memory grew by {memory_growth:.1f} MB"
        
        # Memory growth per device should be minimal
        memory_per_device = memory_growth / device_count
        assert memory_per_device < 1.0, f"Memory per device: {memory_per_device:.3f} MB"


class TestStressPerformance:
    """Stress tests for extreme performance scenarios."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        registry_path.unlink()
        yield registry_path
        if registry_path.exists():
            registry_path.unlink()
    
    @pytest.mark.slow
    def test_extreme_device_count_stress(self, temp_registry):
        """Stress test with extreme number of devices."""
        device_count = 1000  # Extreme number
        
        # Create devices in batches to avoid memory issues
        batch_size = 100
        
        with StableCam(registry_path=temp_registry) as manager:
            total_registration_time = 0
            
            for batch_start in range(0, device_count, batch_size):
                batch_end = min(batch_start + batch_size, device_count)
                batch_cameras = [
                    CameraDevice(
                        system_index=i,
                        vendor_id=f"{(0x7000 + i):04x}",
                        product_id=f"{(0x8000 + i):04x}",
                        serial_number=f"STRESS{i:06d}",
                        port_path=f"/dev/video{i}",
                        label=f"Stress Test Camera {i}",
                        platform_data={"stress_test": True, "batch": batch_start // batch_size}
                    )
                    for i in range(batch_start, batch_end)
                ]
                
                # Time batch registration
                with patch.object(manager.detector, 'detect_cameras', return_value=batch_cameras):
                    start_time = time.perf_counter()
                    
                    for camera in batch_cameras:
                        manager.register(camera)
                    
                    batch_time = time.perf_counter() - start_time
                    total_registration_time += batch_time
                    
                    # Batch should complete in reasonable time
                    assert batch_time < 5.0, f"Batch {batch_start//batch_size} took {batch_time:.3f}s"
            
            # Verify all devices registered
            devices = manager.list()
            assert len(devices) == device_count
            
            # Total registration should be reasonable
            devices_per_second = device_count / total_registration_time
            assert devices_per_second > 100, f"Overall registration rate: {devices_per_second:.1f} devices/sec"
    
    @pytest.mark.slow
    def test_rapid_change_stress(self, temp_registry):
        """Stress test with rapid device connection changes."""
        device_count = 50
        cameras = [
            CameraDevice(
                system_index=i,
                vendor_id=f"{(0x9000 + i):04x}",
                product_id=f"{(0xa000 + i):04x}",
                serial_number=f"RAPID{i:06d}",
                port_path=f"/dev/video{i}",
                label=f"Rapid Change Camera {i}",
                platform_data={"rapid_test": True}
            )
            for i in range(device_count)
        ]
        
        change_count = 0
        error_count = 0
        
        def count_changes(device):
            nonlocal change_count
            change_count += 1
        
        with StableCam(registry_path=temp_registry, poll_interval=0.01) as manager:
            # Register all devices
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                for camera in cameras:
                    manager.register(camera)
            
            manager.on("on_status_change", count_changes)
            manager.run()
            
            # Rapid changes for 3 seconds
            import random
            start_time = time.time()
            
            while time.time() - start_time < 3.0:
                try:
                    # Random subset of devices
                    active_count = random.randint(0, device_count)
                    active_cameras = random.sample(cameras, active_count)
                    
                    with patch.object(manager.detector, 'detect_cameras', return_value=active_cameras):
                        time.sleep(0.005)  # Very rapid changes
                        
                except Exception:
                    error_count += 1
            
            manager.stop()
        
        # Verify system handled rapid changes
        assert error_count == 0, f"Errors during rapid changes: {error_count}"
        assert change_count > 50, f"Too few status changes detected: {change_count}"
        
        # Verify final system state
        final_devices = manager.list()
        assert len(final_devices) == device_count