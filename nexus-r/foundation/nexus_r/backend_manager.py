import asyncio
import json
import logging
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
import httpx
import threading

logger = logging.getLogger("nexus-r.backend_manager")

class BackendManager:
    """Manages the lifecycle of the Ollama backend engine."""
    
    _instance: Optional['BackendManager'] = None
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.port = 11434 if not test_mode else self._find_available_port(start=12000)
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self._lock = threading.Lock()
        self.base_url = f"http://127.0.0.1:{self.port}"
        
        # Test mode shouldn't write to standard logs to avoid clutter
        if not self.test_mode:
            self._log_event("manager_initialized", {"port": self.port, "test_mode": test_mode})

    @classmethod
    def get_instance(cls) -> 'BackendManager':
        if cls._instance is None:
            cls._instance = BackendManager()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: 'BackendManager'):
        cls._instance = instance

    def _log_event(self, event_type: str, data: dict):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": f"backend_{event_type}",
            "component": "ollama_manager",
            "data": data
        }
        # Print structured JSON to stdout so Electron or CLI can parse it
        # Prefix with [NEXUS_LIFECYCLE] to make it easy to parse
        print(f"[NEXUS_LIFECYCLE] {json.dumps(log_entry)}", flush=True)
        logger.info(f"Ollama Lifecycle: {event_type} - {data}")

    def _find_available_port(self, start: int = 11434, attempts: int = 100) -> int:
        for p in range(start, start + attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", p))
                    return p
                except OSError:
                    continue
        raise RuntimeError("No available ports found for Ollama backend.")

    def _is_ollama_responding(self, port: int) -> bool:
        try:
            # Synchronous check for startup
            response = httpx.get(f"http://127.0.0.1:{port}/", timeout=1.0)
            return response.status_code == 200 and "Ollama is running" in response.text
        except httpx.RequestError:
            return False

    def start(self, wait_ready: bool = True):
        with self._lock:
            if self.is_running:
                return

            if not self.test_mode:
                self._log_event("startup_check", {"port": self.port})
            
            # Check if it's already running on the target port
            if self._is_ollama_responding(self.port):
                if not self.test_mode:
                    self._log_event("already_running", {"port": self.port})
                self.is_running = True
                self.base_url = f"http://127.0.0.1:{self.port}"
                return

            # If port is in use but NOT by Ollama, we need a new port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", self.port)) == 0:
                    old_port = self.port
                    self.port = self._find_available_port(start=self.port + 1)
                    if not self.test_mode:
                        self._log_event("port_conflict", {"old_port": old_port, "new_port": self.port})
                    self.base_url = f"http://127.0.0.1:{self.port}"

            env = os.environ.copy()
            env["OLLAMA_HOST"] = f"127.0.0.1:{self.port}"
            
            if not self.test_mode:
                self._log_event("launching", {"port": self.port})
            
            try:
                # We use subprocess.DEVNULL for stdout/stderr to avoid spamming the console
                # unless we want to capture it, but Ollama logs a lot.
                self.process = subprocess.Popen(
                    ["ollama", "serve"],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            except FileNotFoundError:
                if not self.test_mode:
                    self._log_event("launch_failed", {"reason": "ollama executable not found"})
                raise RuntimeError("Ollama executable not found. Please install Ollama and add it to PATH.")

            self.is_running = True
            
        if wait_ready:
            self._wait_for_health()

    def _wait_for_health(self):
        max_retries = 30
        for i in range(max_retries):
            if not self.test_mode:
                self._log_event("health_check", {"attempt": i + 1, "max": max_retries})
            if self._is_ollama_responding(self.port):
                if not self.test_mode:
                    self._log_event("healthy", {"port": self.port})
                return
            time.sleep(1.0)
            
            # Check if process crashed early
            if self.process and self.process.poll() is not None:
                code = self.process.returncode
                if not self.test_mode:
                    self._log_event("crash_during_startup", {"exit_code": code})
                self.is_running = False
                raise RuntimeError(f"Ollama backend crashed during startup with code {code}.")

        self.is_running = False
        raise RuntimeError("Ollama backend failed to respond to health checks in time.")

    def ensure_running(self):
        """Called before every API request to verify backend is up."""
        with self._lock:
            # If we think it's running but the process died (if we own the process)
            if self.process and self.process.poll() is not None:
                code = self.process.returncode
                if not self.test_mode:
                    self._log_event("crash_detected", {"exit_code": code})
                self.is_running = False
                self.process = None

            if not self.is_running:
                if not self.test_mode:
                    self._log_event("auto_restart", {"reason": "not_running"})
                # Release lock to call start() which acquires it again is deadlock. 
                # Better to just call inner logic or release lock.
                pass
                
        # Call start outside lock to prevent deadlock
        if not self.is_running:
            self.start(wait_ready=True)
            return

        # Fast check if it's responding
        try:
            response = httpx.get(f"{self.base_url}/", timeout=2.0)
            if response.status_code != 200 or "Ollama is running" not in response.text:
                raise ValueError("Bad response")
        except (httpx.RequestError, ValueError):
            if not self.test_mode:
                self._log_event("unresponsive", {"url": self.base_url})
            # Try to restart
            self.stop()
            self.start(wait_ready=True)

    def stop(self):
        with self._lock:
            if self.process:
                if not self.test_mode:
                    self._log_event("shutdown", {"port": self.port})
                self.process.terminate()
                try:
                    self.process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                self.process = None
            self.is_running = False
