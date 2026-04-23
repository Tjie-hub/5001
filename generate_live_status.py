#!/usr/bin/env python3
"""
generate_live_status.py — Fetch and display live trading system status

Queries idx-walkforward (5001) and idx-monitor (5000) for:
- Signal counts
- Open trades
- VPIN levels
- Scheduler status
- System health

Usage:
    python3 generate_live_status.py              # Default: 192.168.31.120
    python3 generate_live_status.py --host localhost
    python3 generate_live_status.py --json       # JSON output for scripting
    python3 generate_live_status.py --timeout 5  # Custom timeout
"""

import requests
import json
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Optional

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class SystemStatusMonitor:
    def __init__(self, host: str = "192.168.31.120", timeout: int = 10, json_output: bool = False):
        self.host = host
        self.timeout = timeout
        self.json_output = json_output
        self.base_5001 = f"http://{host}:5001"
        self.base_5000 = f"http://{host}:5000"
        self.status_data = {}

    def fetch_json(self, url: str) -> Optional[Dict]:
        """Safely fetch JSON from endpoint"""
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.Timeout:
            return None
        except Exception as e:
            if not self.json_output:
                print(f"{RED}[ERROR]{RESET} {url}: {str(e)[:50]}")
            return None

    def fetch_post(self, url: str, data: Dict) -> Optional[Dict]:
        """Safely fetch JSON via POST"""
        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.Timeout:
            return None
        except Exception as e:
            if not self.json_output:
                print(f"{RED}[ERROR]{RESET} {url}: {str(e)[:50]}")
            return None

    def check_service_5001(self) -> bool:
        """Check if idx-walkforward service is responding"""
        result = self.fetch_post(f"{self.base_5001}/api/backtest/scan_all", {"filter_mode": "all"})
        if result:
            self.status_data['walkforward'] = result
            return True
        return False

    def check_service_5000(self) -> bool:
        """Check if idx-monitor service is responding"""
        result = self.fetch_json(f"{self.base_5000}/api/monitor/paper_summary")
        if result:
            self.status_data['monitor'] = result
            return True
        return False

    def check_prices(self) -> Optional[Dict]:
        """Get live prices and VPIN"""
        return self.fetch_json(f"{self.base_5000}/api/monitor/prices")

    def get_color_status(self, is_running: bool) -> str:
        """Return colored status indicator"""
        return f"{GREEN}✓ RUNNING{RESET}" if is_running else f"{RED}✗ OFFLINE{RESET}"

    def format_color(self, value: float, threshold_green: float = 0.5, threshold_yellow: float = 0.3) -> str:
        """Color-code numeric values"""
        if value >= threshold_green:
            return f"{GREEN}{value:.2f}{RESET}"
        elif value >= threshold_yellow:
            return f"{YELLOW}{value:.2f}{RESET}"
        else:
            return f"{RED}{value:.2f}{RESET}"

    def print_table(self, title: str, data: List[Dict], columns: List[str]):
        """Pretty print a table"""
        if not data:
            print(f"{YELLOW}[WARNING]{RESET} No data for {title}")
            return

        print(f"\n{BOLD}{title}{RESET}")
        print("─" * 80)

        # Print headers
        header = " | ".join(f"{col:^15}" for col in columns)
        print(header)
        print("─" * 80)

        # Print rows
        for row in data[:10]:  # Limit to top 10
            values = []
            for col in columns:
                val = row.get(col, "—")
                if isinstance(val, float):
                    values.append(f"{val:^15.2f}")
                else:
                    values.append(f"{str(val):^15}")
            print(" | ".join(values))

        if len(data) > 10:
            print(f"... and {len(data) - 10} more")

    def print_status_text(self):
        """Print human-readable status"""
        print(f"\n{BOLD}╔═══════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}║  Trading System Status — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ║{RESET}")
        print(f"{BOLD}╚═══════════════════════════════════════════╝{RESET}")

        # Check services
        walkforward_ok = self.check_service_5001()
        monitor_ok = self.check_service_5000()

        print(f"\n{BOLD}Services:{RESET}")
        print(f"  idx-walkforward (5001):  {self.get_color_status(walkforward_ok)}")
        print(f"  idx-monitor (5000):      {self.get_color_status(monitor_ok)}")

        if not (walkforward_ok or monitor_ok):
            print(f"\n{RED}[CRITICAL] Both services offline. Check systemctl status.{RESET}")
            return

        # Walkforward stats
        if walkforward_ok and 'walkforward' in self.status_data:
            wf = self.status_data['walkforward']
            print(f"\n{BOLD}Scan Results:{RESET}")
            print(f"  Total tickers:   {wf.get('total', 0)}")
            print(f"  Signals found:   {YELLOW}{wf.get('passed_signal', 0)}{RESET}")
            print(f"  WF filtered:     {wf.get('passed_wf', 0)} (≥50% consistency)")

            # Top signals
            if wf.get('results'):
                signals = [r for r in wf['results'] if r.get('has_signal')]
                if signals:
                    top_5 = sorted(signals, key=lambda x: x.get('sharpe', 0), reverse=True)[:5]
                    print(f"\n{BOLD}Top 5 Signals (by Sharpe):{RESET}")
                    for i, sig in enumerate(top_5, 1):
                        sharpe = sig.get('sharpe', 0)
                        color = self.format_color(sharpe, 1.5, 0.8)
                        print(f"  {i}. {sig['ticker']:6} | Sharpe {color} | WF {sig.get('wf_score', 0):.2f} | Regime: {sig.get('regime', '?')}")

        # Monitor stats
        if monitor_ok and 'monitor' in self.status_data:
            mon = self.status_data['monitor']
            print(f"\n{BOLD}Paper Trading:{RESET}")
            print(f"  Open trades:     {len(mon.get('open_trades', []))}")
            print(f"  Closed trades:   {mon.get('closed_trades', 0)}")
            print(f"  Total P&L:       {YELLOW}{mon.get('total_pnl', 0):,} IDR{RESET}")
            print(f"  Win rate:        {self.format_color(mon.get('win_rate', 0) / 100, 0.7, 0.5)} %")
            print(f"  Capital left:    {BLUE}{mon.get('capital_remaining', 0):,} IDR{RESET}")

            # Open trades detail
            if mon.get('open_trades'):
                print(f"\n{BOLD}Open Positions:{RESET}")
                for trade in mon['open_trades']:
                    pnl = trade.get('pnl_pct', 0)
                    pnl_color = GREEN if pnl > 0 else RED
                    print(f"  {trade['ticker']:6} | Entry {trade.get('entry_price', 0):>8.0f} | Current {trade.get('current_price', 0):>8.0f} | P&L {pnl_color}{pnl:+.2f}%{RESET} | Days {trade.get('days_held', 0)}")

        # VPIN data
        prices = self.check_prices()
        if prices and prices.get('prices'):
            high_vpin = [p for p in prices['prices'] if p.get('vpin', 0) > 0.6]
            if high_vpin:
                print(f"\n{BOLD}High VPIN Activity (> 0.6):{RESET}")
                for p in sorted(high_vpin, key=lambda x: x.get('vpin', 0), reverse=True)[:5]:
                    vpin_color = self.format_color(p['vpin'], 0.7, 0.5)
                    print(f"  {p['ticker']:6} | VPIN {vpin_color} | Regime: {p.get('vpin_regime', '?')}")

        print(f"\n{BOLD}Next Scheduler Run:{RESET} Check systemctl to see when next scan is triggered")
        print()

    def print_json(self):
        """Print status as JSON"""
        output = {
            "timestamp": datetime.now().isoformat(),
            "host": self.host,
            "services": {
                "idx_walkforward_5001": self.check_service_5001(),
                "idx_monitor_5000": self.check_service_5000()
            },
            "data": self.status_data
        }
        print(json.dumps(output, indent=2, default=str))

    def run(self):
        """Execute status check"""
        if self.json_output:
            self.print_json()
        else:
            self.print_status_text()


def main():
    parser = argparse.ArgumentParser(
        description="Monitor live trading system status",
        epilog="Example: python3 generate_live_status.py --host 192.168.31.120 --timeout 10"
    )
    parser.add_argument("--host", default="192.168.31.120", help="System host (default: 192.168.31.120)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of text")

    args = parser.parse_args()

    monitor = SystemStatusMonitor(
        host=args.host,
        timeout=args.timeout,
        json_output=args.json
    )
    monitor.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[INTERRUPTED]{RESET} Status check cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"{RED}[FATAL ERROR]{RESET} {str(e)}", file=sys.stderr)
        sys.exit(1)
