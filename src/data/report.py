"""
report.py - plain-English summary of the Kalshi bot's trades.

Run in the Render Shell:   python report.py
Read-only: it never changes the database.
"""
import glob
import sqlite3
import sys


def find_db():
    patterns = ["data/*.db", "data/*.sqlite", "data/*.sqlite3", "*.db"]
    for p in patterns:
        found = glob.glob(p)
        if found:
            return found[0]
    return None


def main():
    db = find_db()
    if not db:
        print("No database found yet. The bot may not have traded yet.")
        sys.exit(0)

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    tables = [r[0] for r in con.execute(
        "select name from sqlite_master where type='table'")]

    print("=" * 50)
    print(f"Database: {db}")
    for t in tables:
        n = con.execute(f"select count(*) from {t}").fetchone()[0]
        print(f"  table {t}: {n} rows")
    print("=" * 50)

    if "trades" not in tables:
        print("No 'trades' table found. Tables are listed above.")
        return

    cols = [r[1] for r in con.execute("pragma table_info(trades)")]
    print("trades columns:", ", ".join(cols))

    pnl_col = "pnl" if "pnl" in cols else next(
        (c for c in cols if "pnl" in c.lower()), None)

    total = con.execute("select count(*) from trades").fetchone()[0]
    print(f"\nTotal trade records: {total}")

    if pnl_col:
        rows = con.execute(
            f"select {pnl_col} from trades where {pnl_col} is not null"
        ).fetchall()
        vals = [float(r[0]) for r in rows]
        if vals:
            wins = sum(1 for v in vals if v > 0)
            losses = sum(1 for v in vals if v < 0)
            flat = len(vals) - wins - losses
            print(f"Closed trades with P&L: {len(vals)}")
            print(f"  Wins:   {wins}")
            print(f"  Losses: {losses}")
            print(f"  Flat:   {flat}")
            print(f"  Win rate: {wins / len(vals) * 100:.1f}%")
            print(f"  Total P&L:   ${sum(vals):+.2f}")
            print(f"  Average P&L: ${sum(vals) / len(vals):+.2f} per trade")
        else:
            print("No closed trades with a P&L value yet.")
    else:
        print("No P&L column found. See the column list above.")

    # Last 10 trades
    print("\nLast 10 trades (newest first):")
    preferred = [c for c in cols if c.lower() in (
        "ticker", "side", "price", "entry_price", "quantity", "count",
        "fees", "pnl", "created_at", "timestamp", "exit_reason")]
    show = preferred or cols[:8]
    for r in con.execute("select * from trades order by rowid desc limit 10"):
        parts = [f"{c}={r[c]}" for c in show]
        print("  - " + " | ".join(str(p)[:40] for p in parts))

    if "outcomes" in tables:
        n = con.execute("select count(*) from outcomes").fetchone()[0]
        print(f"\nMarket settlements recorded: {n}")

    print("\nReminder: paper trades are simulated. Nothing here is on Kalshi.")


if __name__ == "__main__":
    main()
