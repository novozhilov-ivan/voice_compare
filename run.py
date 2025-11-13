#!/usr/bin/env python
"""
Launch script for Voice Speaker Recognition application
"""
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

if __name__ == "__main__":
    import uvicorn
    from app import app

    print("=" * 60)
    print("🎤 Voice Speaker Recognition System")
    print("=" * 60)
    print("\nStarting server...")
    print("Web Interface: http://localhost:8000/static/index.html")
    print("API Docs: http://localhost:8000/docs")
    print("\nPress CTRL+C to stop")
    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
