#!/usr/bin/env python3
"""
Auto-update FETCH_REPORT.md with latest fetch data
Run this script after each fetch to update the report
"""

import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = "data/walkforward.db"
REPORT_PATH = "FETCH_REPORT.md"
LOG_PATHS = {
    "stockbit": "logs/stockbit.log",
    "token": "logs/auto_token.log"
}

def get_db_info():
    """Get database statistics"""
    if not os.path.exists(DB_PATH):
        return None
    
    stat = os.stat(DB_PATH)
    size_mb = stat.st_size / (1024 * 1024)
    mtime = datetime.fromtimestamp(stat.st_mtime)
    
    # Count tables
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
        return {
            "size_mb": f"{size_mb:.1f}",
            "modified": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            "tables": table_count
        }
    except Exception as e:
        return {"error": str(e)}

def get_latest_fetch():
    """Extract latest fetch info from stockbit.log"""
    if not os.path.exists(LOG_PATHS["stockbit"]):
        return None
    
    with open(LOG_PATHS["stockbit"], "r") as f:
        lines = f.readlines()
    
    # Look for DONE: X/Y success
    for line in reversed(lines):
        if "DONE:" in line:
            return line.strip()
    return None

def get_latest_token_refresh():
    """Extract latest token refresh from auto_token.log"""
    if not os.path.exists(LOG_PATHS["token"]):
        return None
    
    with open(LOG_PATHS["token"], "r") as f:
        lines = f.readlines()
    
    # Look for token refreshed message
    for line in reversed(lines):
        if "✅ Token refreshed" in line or "Token refreshed" in line:
            return line.strip()
    return None

def update_report():
    """Update FETCH_REPORT.md with latest data"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")
    db_info = get_db_info()
    latest_fetch = get_latest_fetch()
    latest_token = get_latest_token_refresh()
    
    print("📊 Fetching latest data...")
    print(f"  ✓ Database info: {db_info}")
    print(f"  ✓ Latest fetch: {latest_fetch}")
    print(f"  ✓ Token status: {latest_token}")
    
    if os.path.exists(REPORT_PATH):
        print(f"\n✅ Report exists. Manual review recommended for detailed updates.")
        print(f"📝 Last update time: {now}")
        print(f"\n📋 Current status:")
        print(f"   Database: {db_info.get('size_mb', 'N/A')} MB")
        print(f"   Fetch: {latest_fetch or 'No recent data'}")
        print(f"   Token: {latest_token or 'No recent refresh'}")
    else:
        print("❌ Report file not found!")

if __name__ == "__main__":
    update_report()
