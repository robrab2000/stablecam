#!/usr/bin/env python3
"""
Comprehensive integration test runner for StableCam.

This script runs all integration tests with proper setup, reporting,
and cleanup. It can be used for local development or CI/CD pipelines.
"""

import sys
import os
import subprocess
import argparse
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class IntegrationTestRunner:
    """Runner for StableCam integration tests."""
    
    def __init__(self, verbose: bool = False, parallel: bool = False):
        self.verbose = verbose
        self.parallel = parallel
        self.project_root = Path(__file__).parent.parent
        self.results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{timestamp}] {level}: {message}")
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
        """Run a command and return results."""
        if cwd is None:
            cwd = self.project_root
            
        self.log(f"Running: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': duration,
                'command': ' '.join(cmd)
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timed out after 5 minutes',
                'duration': time.time() - start_time,
                'command': ' '.join(cmd)
            }
        except Exception as e:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': time.time() - start_time,
                'command': ' '.join(cmd)
            }
    
    def check_dependencies(self) -> bool:
        """Check that required dependencies are installed."""
        self.log("Checking dependencies...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.log("Python 3.8+ required", "ERROR")
            return False
        
        # Check pytest is available
        result = self.run_command([sys.executable, "-m", "pytest", "--version"])
        if not result['success']:
            self.log("pytest not available", "ERROR")
            return False
        
        # Check StableCam package is installed
        result = self.run_command([sys.executable, "-c", "import stablecam"])
        if not result['success']:
            self.log("StableCam package not installed", "ERROR")
            return False
        
        self.log("Dependencies check passed")
        return True
    
    def setup_test_environment(self) -> bool:
        """Set up the test environment."""
        self.log("Setting up test environment...")
        
        # Set environment variables
        os.environ["STABLECAM_TEST_MODE"] = "1"
        os.environ["STABLECAM_LOG_LEVEL"] = "WARNING"
        
        # Create test directories
        test_dir = self.project_root / "test_output"
        test_dir.mkdir(exist_ok=True)
        
        self.log("Test environment setup complete")
        return True
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests."""
        self.log("Running unit tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--cov=stablecam",
            "--cov-report=xml:test_output/unit_coverage.xml",
            "--cov-report=term-missing",
            "-m", "not slow and not integration",
            "--junitxml=test_output/unit_results.xml"
        ]
        
        if self.parallel:
            cmd.extend(["-n", "auto"])
        
        result = self.run_command(cmd)
        self.results['unit_tests'] = result
        
        if result['success']:
            self.log("Unit tests passed")
        else:
            self.log("Unit tests failed", "ERROR")
            if self.verbose:
                self.log(f"STDOUT: {result['stdout']}")
                self.log(f"STDERR: {result['stderr']}")
        
        return result
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        self.log("Running integration tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/test_integration.py",
            "-v",
            "--tb=short",
            "-m", "integration",
            "--maxfail=5",
            "--junitxml=test_output/integration_results.xml"
        ]
        
        result = self.run_command(cmd)
        self.results['integration_tests'] = result
        
        if result['success']:
            self.log("Integration tests passed")
        else:
            self.log("Integration tests failed", "ERROR")
            if self.verbose:
                self.log(f"STDOUT: {result['stdout']}")
                self.log(f"STDERR: {result['stderr']}")
        
        return result
    
    def run_performance_tests(self, quick: bool = True) -> Dict[str, Any]:
        """Run performance tests."""
        self.log("Running performance tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/test_performance.py",
            "-v",
            "--tb=short",
            "--maxfail=3",
            "--junitxml=test_output/performance_results.xml"
        ]
        
        if quick:
            cmd.extend(["-m", "not slow"])
        else:
            cmd.extend(["-m", "slow"])
        
        result = self.run_command(cmd)
        self.results['performance_tests'] = result
        
        if result['success']:
            self.log("Performance tests passed")
        else:
            self.log("Performance tests failed", "ERROR")
            if self.verbose:
                self.log(f"STDOUT: {result['stdout']}")
                self.log(f"STDERR: {result['stderr']}")
        
        return result
    
    def run_tui_tests(self) -> Dict[str, Any]:
        """Run TUI integration tests."""
        self.log("Running TUI tests...")
        
        # Check if Textual is available
        result = self.run_command([sys.executable, "-c", "import textual"])
        if not result['success']:
            self.log("Textual not available, skipping TUI tests", "WARNING")
            return {'success': True, 'skipped': True, 'reason': 'Textual not available'}
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/test_integration.py::TestTUIIntegration",
            "tests/test_tui.py",
            "-v",
            "--tb=short",
            "-m", "tui",
            "--maxfail=3",
            "--junitxml=test_output/tui_results.xml"
        ]
        
        result = self.run_command(cmd)
        self.results['tui_tests'] = result
        
        if result['success']:
            self.log("TUI tests passed")
        else:
            self.log("TUI tests failed", "ERROR")
            if self.verbose:
                self.log(f"STDOUT: {result['stdout']}")
                self.log(f"STDERR: {result['stderr']}")
        
        return result
    
    def run_cross_platform_tests(self) -> Dict[str, Any]:
        """Run cross-platform compatibility tests."""
        self.log("Running cross-platform compatibility tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/test_integration.py::TestCrossPlatformCompatibility",
            "-v",
            "--tb=short",
            "--maxfail=3",
            "--junitxml=test_output/cross_platform_results.xml"
        ]
        
        result = self.run_command(cmd)
        self.results['cross_platform_tests'] = result
        
        if result['success']:
            self.log("Cross-platform tests passed")
        else:
            self.log("Cross-platform tests failed", "ERROR")
            if self.verbose:
                self.log(f"STDOUT: {result['stdout']}")
                self.log(f"STDERR: {result['stderr']}")
        
        return result
    
    def run_end_to_end_tests(self) -> Dict[str, Any]:
        """Run end-to-end scenario tests."""
        self.log("Running end-to-end scenario tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/test_integration.py::TestEndToEndScenarios",
            "tests/test_integration.py::TestSystemIntegration",
            "-v",
            "--tb=short",
            "--maxfail=2",
            "--junitxml=test_output/e2e_results.xml"
        ]
        
        result = self.run_command(cmd)
        self.results['end_to_end_tests'] = result
        
        if result['success']:
            self.log("End-to-end tests passed")
        else:
            self.log("End-to-end tests failed", "ERROR")
            if self.verbose:
                self.log(f"STDOUT: {result['stdout']}")
                self.log(f"STDERR: {result['stderr']}")
        
        return result
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report."""
        self.log("Generating test report...")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r.get('success', False))
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(r.get('duration', 0) for r in self.results.values())
        
        report = {
            'summary': {
                'total_test_suites': total_tests,
                'passed_test_suites': passed_tests,
                'failed_test_suites': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'total_duration': total_duration
            },
            'results': self.results,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'platform': {
                'python_version': sys.version,
                'platform': sys.platform
            }
        }
        
        # Save report to file
        report_file = self.project_root / "test_output" / "integration_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Test report saved to {report_file}")
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """Print test summary."""
        summary = report['summary']
        
        print("\n" + "="*60)
        print("INTEGRATION TEST SUMMARY")
        print("="*60)
        print(f"Total Test Suites: {summary['total_test_suites']}")
        print(f"Passed: {summary['passed_test_suites']}")
        print(f"Failed: {summary['failed_test_suites']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print("="*60)
        
        # Print individual results
        for test_name, result in self.results.items():
            status = "PASS" if result.get('success', False) else "FAIL"
            duration = result.get('duration', 0)
            print(f"{test_name:30} {status:6} ({duration:.2f}s)")
        
        print("="*60)
        
        if summary['failed_test_suites'] > 0:
            print("\nFAILED TEST DETAILS:")
            for test_name, result in self.results.items():
                if not result.get('success', False):
                    print(f"\n{test_name}:")
                    if result.get('stderr'):
                        print(f"  Error: {result['stderr'][:200]}...")
        
        print()
    
    def run_all_tests(self, include_performance: bool = False, 
                     include_slow: bool = False) -> bool:
        """Run all integration tests."""
        self.log("Starting comprehensive integration test run")
        
        if not self.check_dependencies():
            return False
        
        if not self.setup_test_environment():
            return False
        
        # Run test suites
        test_suites = [
            ("Unit Tests", lambda: self.run_unit_tests()),
            ("Integration Tests", lambda: self.run_integration_tests()),
            ("Cross-Platform Tests", lambda: self.run_cross_platform_tests()),
            ("TUI Tests", lambda: self.run_tui_tests()),
            ("End-to-End Tests", lambda: self.run_end_to_end_tests()),
        ]
        
        if include_performance:
            test_suites.append(
                ("Performance Tests", lambda: self.run_performance_tests(quick=not include_slow))
            )
        
        # Run each test suite
        for suite_name, suite_func in test_suites:
            self.log(f"Starting {suite_name}...")
            try:
                suite_func()
            except Exception as e:
                self.log(f"Error running {suite_name}: {e}", "ERROR")
                self.results[suite_name.lower().replace(' ', '_')] = {
                    'success': False,
                    'error': str(e),
                    'duration': 0
                }
        
        # Generate and display report
        report = self.generate_report()
        self.print_summary(report)
        
        # Return overall success
        return report['summary']['failed_test_suites'] == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run StableCam integration tests")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("-p", "--parallel", action="store_true",
                       help="Run tests in parallel where possible")
    parser.add_argument("--performance", action="store_true",
                       help="Include performance tests")
    parser.add_argument("--slow", action="store_true",
                       help="Include slow performance tests")
    parser.add_argument("--suite", choices=[
        "unit", "integration", "performance", "tui", 
        "cross-platform", "e2e", "all"
    ], default="all", help="Test suite to run")
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner(verbose=args.verbose, parallel=args.parallel)
    
    success = False
    
    if args.suite == "all":
        success = runner.run_all_tests(
            include_performance=args.performance,
            include_slow=args.slow
        )
    elif args.suite == "unit":
        result = runner.run_unit_tests()
        success = result['success']
    elif args.suite == "integration":
        result = runner.run_integration_tests()
        success = result['success']
    elif args.suite == "performance":
        result = runner.run_performance_tests(quick=not args.slow)
        success = result['success']
    elif args.suite == "tui":
        result = runner.run_tui_tests()
        success = result['success']
    elif args.suite == "cross-platform":
        result = runner.run_cross_platform_tests()
        success = result['success']
    elif args.suite == "e2e":
        result = runner.run_end_to_end_tests()
        success = result['success']
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()