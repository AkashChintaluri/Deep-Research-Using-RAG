#!/usr/bin/env python3
"""
Main Application Launcher
========================

This script starts both the frontend and backend services for the Deep Research Assistant.
It handles process management and provides a unified startup experience.
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
from typing import List, Optional

class ServiceManager:
    """Manages frontend and backend services."""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.running = True
        
    def start_backend(self) -> subprocess.Popen:
        """Start the backend FastAPI server."""
        print("🚀 Starting Backend Server...")
        
        backend_dir = Path("backend")
        if not backend_dir.exists():
            print("❌ Backend directory not found!")
            return None
            
        # Check if virtual environment exists, create if not
        venv_path = backend_dir / "venv"
        if not venv_path.exists():
            print("📦 Creating backend virtual environment...")
            try:
                subprocess.run([sys.executable, "-m", "venv", "venv"], cwd=str(backend_dir), check=True)
                print("✅ Virtual environment created")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to create virtual environment: {e}")
                return None
            
        # Activate virtual environment and start server
        if os.name == 'nt':  # Windows
            python_exe = venv_path / "Scripts" / "python.exe"
            uvicorn_exe = venv_path / "Scripts" / "uvicorn.exe"
        else:  # Unix/Linux/Mac
            python_exe = venv_path / "bin" / "python"
            uvicorn_exe = venv_path / "bin" / "uvicorn"
            
        if not python_exe.exists():
            print(f"❌ Python executable not found at {python_exe}")
            return None
            
        # Create logs directory if it doesn't exist
        logs_dir = backend_dir / "logs"
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)
            print("✅ Created logs directory")
        
        # Check and install backend dependencies
        print("📦 Installing backend dependencies...")
        try:
            # Check if requirements.txt exists
            requirements_file = backend_dir / "requirements.txt"
            if requirements_file.exists():
                print("Installing from requirements.txt...")
                result = subprocess.run([str(python_exe), "-m", "pip", "install", "-r", "requirements.txt"], 
                                      cwd=str(backend_dir), capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Backend dependencies installed successfully")
                else:
                    print(f"⚠️ Some dependencies failed to install, trying basic ones...")
                    print(f"Error: {result.stderr}")
                    # Try installing basic dependencies
                    basic_deps = ["fastapi", "uvicorn", "psycopg2-binary", "python-dotenv", "numpy", "pandas", "tqdm", "scikit-learn", "scipy", "faiss-cpu", "openai", "pinecone", "markdown", "reportlab", "arxiv"]
                    subprocess.run([str(python_exe), "-m", "pip", "install"] + basic_deps, 
                                 cwd=str(backend_dir), check=True)
                    print("✅ Basic dependencies installed")
            else:
                print("⚠️ No requirements.txt found, installing basic dependencies...")
                basic_deps = ["fastapi", "uvicorn", "psycopg2-binary", "python-dotenv", "numpy", "pandas", "tqdm", "scikit-learn", "scipy", "faiss-cpu", "openai", "pinecone", "markdown", "reportlab", "arxiv"]
                subprocess.run([str(python_exe), "-m", "pip", "install"] + basic_deps, 
                             cwd=str(backend_dir), check=True)
                print("✅ Basic dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install backend dependencies: {e}")
            print("Trying to continue with what's available...")
            
        try:
            # Start backend with uvicorn
            process = subprocess.Popen(
                [str(uvicorn_exe), "app:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd=str(backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Start a thread to monitor backend output
            threading.Thread(
                target=self._monitor_process,
                args=(process, "Backend"),
                daemon=True
            ).start()
            
            print("✅ Backend server started on http://localhost:8000")
            return process
            
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return None
    
    def start_frontend(self) -> subprocess.Popen:
        """Start the frontend React development server."""
        print("🎨 Starting Frontend Server...")
        
        frontend_dir = Path("frontend")
        if not frontend_dir.exists():
            print("❌ Frontend directory not found!")
            return None
            
        # Check if node_modules exists, install if not
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("📦 Installing frontend dependencies...")
            try:
                # Check if npm is available
                npm_cmd = "npm.cmd" if os.name == 'nt' else "npm"
                result = subprocess.run([npm_cmd, "install"], cwd=str(frontend_dir), 
                                      capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    print("✅ Frontend dependencies installed successfully")
                else:
                    print(f"❌ Failed to install frontend dependencies: {result.stderr}")
                    print("Please run: cd frontend && npm install")
                    return None
            except subprocess.TimeoutExpired:
                print("❌ npm install timed out. Please run: cd frontend && npm install")
                return None
            except FileNotFoundError:
                print("❌ npm not found! Please install Node.js from https://nodejs.org")
                return None
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install frontend dependencies: {e}")
                print("Please run: cd frontend && npm install")
                return None
            
        try:
            # Start frontend with npm
            if os.name == 'nt':  # Windows
                npm_cmd = "npm.cmd"
            else:  # Unix/Linux/Mac
                npm_cmd = "npm"
                
            process = subprocess.Popen(
                [npm_cmd, "run", "dev"],
                cwd=str(frontend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Start a thread to monitor frontend output
            threading.Thread(
                target=self._monitor_process,
                args=(process, "Frontend"),
                daemon=True
            ).start()
            
            print("✅ Frontend server started on http://localhost:5173")
            return process
            
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return None
    
    def _monitor_process(self, process: subprocess.Popen, service_name: str):
        """Monitor process output in a separate thread."""
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[{service_name}] {line.strip()}")
        except Exception as e:
            print(f"❌ Error monitoring {service_name}: {e}")
    
    def start_all(self):
        """Start both frontend and backend services."""
        print("🌟 Deep Research Assistant - Starting Services")
        print("=" * 50)
        print("This will automatically:")
        print("  • Create virtual environment if needed")
        print("  • Install backend dependencies")
        print("  • Install frontend dependencies")
        print("  • Start both servers")
        print("=" * 50)
        
        # Start backend
        print("\n🚀 Setting up Backend...")
        backend_process = self.start_backend()
        if backend_process:
            self.processes.append(backend_process)
            print("⏳ Waiting for backend to initialize...")
            time.sleep(3)  # Give backend time to start
        else:
            print("❌ Failed to start backend. Exiting...")
            return False
            
        # Start frontend
        print("\n🎨 Setting up Frontend...")
        frontend_process = self.start_frontend()
        if frontend_process:
            self.processes.append(frontend_process)
            print("⏳ Waiting for frontend to initialize...")
            time.sleep(3)  # Give frontend time to start
        else:
            print("❌ Failed to start frontend. Exiting...")
            return False
            
        print("\n🎉 All services started successfully!")
        print("=" * 50)
        print("🌐 Frontend: http://localhost:5173")
        print("🚀 Backend:  http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("🌍 Production: https://2i7mq7kfxp.us-east-1.awsapprunner.com")
        print("=" * 50)
        print("Press Ctrl+C to stop all services")
        print()
        
        return True
    
    def stop_all(self):
        """Stop all running processes."""
        print("\n🛑 Stopping all services...")
        
        for process in self.processes:
            if process.poll() is None:  # Process is still running
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                except Exception as e:
                    print(f"❌ Error stopping process: {e}")
        
        print("✅ All services stopped")
        self.running = False
    
    def wait_for_interrupt(self):
        """Wait for user interrupt (Ctrl+C)."""
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_all()

def main():
    """Main entry point."""
    # Check if we're in the right directory
    if not Path("backend").exists() or not Path("frontend").exists():
        print("❌ Please run this script from the project root directory")
        print("   (the directory containing both 'backend' and 'frontend' folders)")
        print(f"   Current directory: {os.getcwd()}")
        print("   Expected structure:")
        print("   ├── backend/")
        print("   ├── frontend/")
        print("   └── main.py")
        sys.exit(1)
    
    # Check for required tools
    print("🔍 Checking prerequisites...")
    
    # Check Python
    try:
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 9):
            print(f"❌ Python 3.9+ required, found {python_version.major}.{python_version.minor}")
            sys.exit(1)
        print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    except Exception as e:
        print(f"❌ Python check failed: {e}")
        sys.exit(1)
    
    # Check Node.js/npm
    try:
        npm_cmd = "npm.cmd" if os.name == 'nt' else "npm"
        result = subprocess.run([npm_cmd, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm {result.stdout.strip()}")
        else:
            print("❌ npm not found! Please install Node.js from https://nodejs.org")
            sys.exit(1)
    except FileNotFoundError:
        print("❌ npm not found! Please install Node.js from https://nodejs.org")
        sys.exit(1)
    
    print("✅ All prerequisites met!")
    
    # Create service manager
    manager = ServiceManager()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start all services
    if manager.start_all():
        manager.wait_for_interrupt()
    else:
        print("❌ Failed to start services")
        sys.exit(1)

if __name__ == "__main__":
    main()
