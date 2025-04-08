"""Queries for the rest api"""
Query = {
    "portfolio": """
                    WITH HourlyAverage AS (
                        SELECT
                            time_bucket('1 day', time) AS bucket,
                            last(equity, time) AS equity,
                            last(balance, time) AS balance,
                            last(options_pl, time) AS options_pl,
                            last(options_delta, time) AS options_delta,
                            last(options_theta, time) AS options_theta,
                            last(delta_total, time) AS delta_total,
                            last(options_gamma, time) AS options_gamma,
                            last(options_vega, time) AS options_vega
                        FROM
                            (SELECT
                                    CASE
                                        WHEN equity < 1 THEN equity + 0.65836855
                                        ELSE equity
                                    END AS equity,
                                    time,
                                    CASE
                                        WHEN balance < 1 THEN balance + 0.65836855
                                        ELSE balance
                                    END AS balance,
                                    options_pl,
                                    options_delta,
                                    options_theta,
                                    delta_total,
                                    options_gamma,
                                    options_vega
                                FROM
                                    btc_account_summary) AS temp
                        GROUP BY
                            bucket
                        ORDER BY
                            bucket DESC
                        LIMIT 30
                    )
                    SELECT *
                    FROM HourlyAverage
                    ORDER BY bucket ASC;
                    """,
    "market": "SELECT * FROM btc_option ORDER BY time DESC LIMIT 10",
    "blocktrade": """SELECT * FROM (SELECT
                        block_trade.id,
                        block_trade.direction,
                        block_trade.strike,
                        block_trade.option_type,
                        hd_tiny_expiry(block_trade.expiry_date),
                        block_trade.quantity,
                        block_trade.option_price as entry_price,
                        current_price.mark_price as current_mark_price,
                        CASE
                            WHEN direction = 'buy' THEN current_price.mark_price * block_trade.quantity - block_trade.option_price * block_trade.quantity
                            ELSE block_trade.option_price * block_trade.quantity - current_price.mark_price * block_trade.quantity
                            END AS current_pnl,
                        block_trade.time_of_trade,
                        block_trade.greeks_live_url
                    FROM block_trade
                    LEFT JOIN (SELECT strike, option_type, expiry_date, mark_price
                    FROM btc_option
                    WHERE btc_option.time = (SELECT time FROM btc_option ORDER BY time DESC LIMIT 1)) AS current_price
                    ON block_trade.strike = current_price.strike
                    AND block_trade.option_type = current_price.option_type
                    AND block_trade.expiry_date = current_price.expiry_date
                    ORDER BY block_trade.id DESC) AS pnl
                    WHERE current_mark_price IS NOT NULL""",
    "blocktrade2": """WITH RelevantPrices AS (
                        SELECT
                            bo.strike,
                            bo.option_type,
                            bo.expiry_date,
                            bo.mark_price,
                            bo.rn
                        FROM btc_latest_price bo
                        INNER JOIN (
                            SELECT DISTINCT
                                strike,
                                option_type,
                                expiry_date
                            FROM block_trade
                        ) bt ON bo.strike = bt.strike AND bo.option_type = bt.option_type AND bo.expiry_date = bt.expiry_date
                    )
                    SELECT
                        bt.id,
                        bt.direction,
                        bt.strike,
                        bt.option_type,
                        hd_tiny_expiry(bt.expiry_date),
                        bt.quantity,
                        bt.option_price AS entry_price,
                        rp.mark_price AS current_mark_price,
                        CASE
                            WHEN lower(bt.direction) = 'buy' THEN rp.mark_price * bt.quantity - bt.option_price * bt.quantity
                            ELSE bt.option_price * bt.quantity - rp.mark_price * bt.quantity
                        END AS current_pnl,
                        bt.total_premium_btc,
                        CASE
                            WHEN bt.expiry_date > CURRENT_DATE THEN false
                            ELSE true
                        END AS is_expired,
                        bt.time_of_trade,
                        bt.greeks_live_url
                    FROM block_trade bt
                    LEFT JOIN RelevantPrices rp
                        ON bt.strike = rp.strike
                        AND bt.option_type = rp.option_type
                        AND bt.expiry_date = rp.expiry_date
                        AND rp.rn = 1
                    ORDER BY bt.id DESC;"""
}
