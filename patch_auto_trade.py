#!/usr/bin/env python3
"""
Phase 4: Auto Paper Trade Open
Modify scheduled_multi_strategy_scan() to auto-open paper trades
Usage: python3 patch_auto_trade.py
"""

import shutil
from datetime import datetime

SCHEDULER_PY = "/home/tjiesar/10 Projects/idx-walkforward-5001/scheduler.py"
BACKUP_SUFFIX = f".phase4_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Find and replace the Telegram notification section
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OLD_TELEGRAM_SECTION = '''    if len(flow_confirmed) > 0:
        msg = f"<b>🎯 Multi-Strategy Scan @ {time_str}</b>\\n\\n📊 Total scanned: {len(tickers)}\\n✅ Pass strategies: {len(intersection_results)}\\n🟢 Flow confirmed: {len(flow_confirmed)}\\n\\n<b>Signals:</b>\\n"
        for r in flow_confirmed[:10]:
            flow = r.get('flow', {})
            score_emoji = "🟢" if flow['score'] >= 3 else "🟡"
            msg += f"\\n{score_emoji} <b>{r['ticker']}</b>\\n  Flow: {flow['score']:+d} ({flow['verdict']})\\n  SM: {flow['smart_money']}\\n"
            first_reason = r['signal_reasons'][0] if r['signal_reasons'] else "N/A"
            msg += f"  {first_reason[:60]}...\\n"
        if len(flow_confirmed) > 10:
            msg += f"\\n... +{len(flow_confirmed) - 10} more signals"
        send_telegram(msg)
    else:
        msg = f"📊 Multi-Strategy Scan @ {time_str}\\nNo flow-confirmed signals.\\n(Strategy pass: {len(intersection_results)}, Flow threshold: +{flow_threshold})"
        send_telegram(msg)'''

NEW_TELEGRAM_SECTION = '''    # Step 7: Auto-open paper trades for flow-confirmed signals
    auto_trade_results = []
    if len(flow_confirmed) > 0:
        from paper_trade import open_trade
        
        for r in flow_confirmed:
            ticker = r['ticker']
            try:
                # Get latest price from signal details
                signal_details = r.get('signal_details', {})
                # Try first strategy's price
                first_strategy = r['strategies'][0]
                entry_price = signal_details.get(first_strategy, {}).get('price')
                
                if not entry_price:
                    print(f"[{time_str}] {ticker}: No price found, skipping")
                    continue
                
                # Open paper trade
                trade_result = open_trade(ticker, float(entry_price))
                
                if 'error' in trade_result:
                    print(f"[{time_str}] {ticker}: {trade_result['error']}")
                    auto_trade_results.append({
                        'ticker': ticker,
                        'success': False,
                        'reason': trade_result['error']
                    })
                else:
                    print(f"[{time_str}] {ticker}: Paper trade opened - ID {trade_result['id']}, {trade_result['lots']} lots @ {entry_price}")
                    auto_trade_results.append({
                        'ticker': ticker,
                        'success': True,
                        'trade_id': trade_result['id'],
                        'entry_price': entry_price,
                        'lots': trade_result['lots'],
                        'tp_price': trade_result['tp_price'],
                        'sl_price': trade_result['sl_price'],
                        'capital_used': trade_result['capital_used']
                    })
            except Exception as e:
                print(f"[{time_str}] {ticker}: Trade open error: {e}")
                auto_trade_results.append({
                    'ticker': ticker,
                    'success': False,
                    'reason': str(e)
                })
    
    # Step 8: Send enhanced Telegram notification
    trades_opened = [t for t in auto_trade_results if t['success']]
    trades_failed = [t for t in auto_trade_results if not t['success']]
    
    if len(flow_confirmed) > 0:
        msg = f"<b>🎯 Multi-Strategy Scan @ {time_str}</b>\\n\\n"
        msg += f"📊 Total scanned: {len(tickers)}\\n"
        msg += f"✅ Pass strategies: {len(intersection_results)}\\n"
        msg += f"🟢 Flow confirmed: {len(flow_confirmed)}\\n"
        msg += f"📈 Trades opened: {len(trades_opened)}\\n\\n"
        
        if len(trades_opened) > 0:
            msg += "<b>✅ Paper Trades Opened:</b>\\n"
            for t in trades_opened[:5]:
                msg += f"\\n<b>{t['ticker']}</b>\\n"
                msg += f"  Entry: Rp {t['entry_price']:,.0f} x {t['lots']} lots\\n"
                msg += f"  TP: Rp {t['tp_price']:,.0f} (+{((t['tp_price']/t['entry_price']-1)*100):.1f}%)\\n"
                msg += f"  SL: Rp {t['sl_price']:,.0f} ({((t['sl_price']/t['entry_price']-1)*100):.1f}%)\\n"
                msg += f"  Capital: Rp {t['capital_used']:,.0f}\\n"
            if len(trades_opened) > 5:
                msg += f"\\n... +{len(trades_opened) - 5} more trades\\n"
        
        if len(trades_failed) > 0:
            msg += f"\\n<b>⚠️ Failed ({len(trades_failed)}):</b>\\n"
            for t in trades_failed[:3]:
                msg += f"  • {t['ticker']}: {t['reason'][:40]}\\n"
        
        # Add signals without trades
        no_trade = [r for r in flow_confirmed if r['ticker'] not in [t['ticker'] for t in auto_trade_results]]
        if len(no_trade) > 0:
            msg += f"\\n<b>📊 Other Signals ({len(no_trade)}):</b>\\n"
            for r in no_trade[:3]:
                flow = r.get('flow', {})
                msg += f"  • {r['ticker']}: Flow {flow['score']:+d}\\n"
        
        send_telegram(msg)
    else:
        msg = f"📊 Multi-Strategy Scan @ {time_str}\\n"
        msg += f"No flow-confirmed signals.\\n"
        msg += f"(Strategy pass: {len(intersection_results)}, Flow threshold: +{flow_threshold})"
        send_telegram(msg)'''

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print("=" * 60)
    print("Phase 4: Auto Paper Trade Open")
    print("=" * 60)
    
    # Backup
    backup = SCHEDULER_PY + BACKUP_SUFFIX
    shutil.copy2(SCHEDULER_PY, backup)
    print(f"✓ Backup created: {backup}")
    
    # Read
    with open(SCHEDULER_PY, 'r') as f:
        content = f.read()
    
    print("\nApplying patch...")
    print("-" * 60)
    
    # Patch: Replace Telegram section with auto-trade version
    if OLD_TELEGRAM_SECTION in content:
        content = content.replace(OLD_TELEGRAM_SECTION, NEW_TELEGRAM_SECTION)
        print("✓ Added auto paper trade opening logic")
        print("✓ Enhanced Telegram notification with trade details")
    elif "auto_trade_results" in content:
        print("⊘ Auto-trade logic already exists")
    else:
        print("✗ Could not find Telegram section to replace")
        print("   Manual intervention needed")
        return 1
    
    # Write back
    with open(SCHEDULER_PY, 'w') as f:
        f.write(content)
    
    print("-" * 60)
    print("✓ Phase 4 complete!")
    print("\nNext steps:")
    print("  1. sudo systemctl restart idx-walkforward")
    print("  2. Test manual:")
    print("     python3 -c 'from scheduler import scheduled_multi_strategy_scan; scheduled_multi_strategy_scan()'")
    print("  3. Check paper trades:")
    print("     sqlite3 data/walkforward.db 'SELECT * FROM paper_trades WHERE status=\"OPEN\"'")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
