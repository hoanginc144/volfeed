"""Process block trade data"""


def process_block_trade(d):
    """Process block trade data"""
    blocktrade_dict = {}
    for row in d:
        row_id = row["id"]
        # Correct use of pop to remove greeks_live_url and store its value separately
        # Remove and capture the greeks_live_url and time_of_trade value
        greeks_live_url = row.pop("greeks_live_url", None)
        time_of_trade = row.pop("time_of_trade", None)
        row["current_pnl"] = round(row["current_pnl"], 2)

        if row_id not in blocktrade_dict:
            blocktrade_dict[row_id] = {
                "id": row_id,
                "total_pnl": 0,
                "time_of_trade": time_of_trade,
                "net_premium_btc": 0.0001,
                "roi": 0,
                "telegram_message_url": f"https://t.me/greekslive_notifications2/{row_id}",
                "legs": []
            }

        # Appending the modified row (without greeks_live_url) and updating total_pnl
        blocktrade_dict[row_id]["legs"].append(row)
        blocktrade_dict[row_id]["total_pnl"] += row["current_pnl"]

        # If direction is buy, add the premium to net_premium_btc, otherwise subtract
        blocktrade_dict[row_id]["net_premium_btc"] += -row["total_premium_btc"] if row["direction"].lower() == "buy" else \
            row["total_premium_btc"]

        # Calculate ROI which is total_pnl divided by absolute value of net_premium_btc
        blocktrade_dict[row_id]["roi"] = round(
            blocktrade_dict[row_id]["total_pnl"] / abs(blocktrade_dict[row_id]["net_premium_btc"]) * 100, 2)

        # Pre-sort and assign leg_ids in one pass to avoid multiple list comprehensions
        # Also, move sorting to list creation to avoid additional list conversion
        data = sorted(
            (blocktrade for blocktrade in blocktrade_dict.values()),
            key=lambda x: x["time_of_trade"],
            reverse=True
        )

        # Now iterate over the already sorted data
        for blocktrade in data:
            for i, leg in enumerate(blocktrade["legs"]):
                leg["leg_id"] = i
    return data[:200]
