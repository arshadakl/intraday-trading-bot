"""Paper Trading Simulator - Simulates trades without real money."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from src.utils.timezone import now_ist, now_ist_date


@dataclass
class PaperPosition:
    """Represents a paper trading position."""

    symbol: str
    token: str
    entry_price: float
    quantity: int
    entry_time: datetime
    stop_loss: float
    target: float
    direction: str = "LONG"  # LONG or SHORT
    current_price: float = 0.0
    pnl: float = 0.0
    status: str = "OPEN"
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    exit_reason: str = ""


@dataclass
class PaperTrade:
    """Represents a completed paper trade."""

    symbol: str
    token: str
    entry_price: float
    exit_price: float
    quantity: int
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    exit_reason: str
    direction: str


class PaperTrader:
    """Simulates trading without real money and persists open positions."""

    def __init__(self, initial_balance: float = 100000.0):
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.positions: Dict[str, PaperPosition] = {}
        self.trades: List[PaperTrade] = []
        self.daily_pnl = 0.0
        self.trade_count = 0

        self.data_dir = Path("data/paper_trades")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.positions_file = self.data_dir / "open_positions.json"
        self._load_positions()

        logger.info(f"Paper Trader initialized with balance: {initial_balance:,.2f}")

    def _save_positions(self) -> None:
        """Save open positions to JSON file for persistence."""
        try:
            positions_data = {
                "updated_at": now_ist().isoformat(),
                "available_balance": self.available_balance,
                "daily_pnl": self.daily_pnl,
                "positions": {
                    symbol: {
                        "symbol": pos.symbol,
                        "token": pos.token,
                        "entry_price": pos.entry_price,
                        "quantity": pos.quantity,
                        "entry_time": pos.entry_time.isoformat(),
                        "stop_loss": pos.stop_loss,
                        "target": pos.target,
                        "current_price": pos.current_price,
                        "direction": pos.direction,
                    }
                    for symbol, pos in self.positions.items()
                },
            }

            with open(self.positions_file, "w", encoding="utf-8") as f:
                json.dump(positions_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving positions: {e}")

    def _calculate_costs(self, value: float, is_buy: bool = True) -> float:
        """
        Calculate realistic Indian intraday transaction costs.
        - STT: 0.025% on sell
        - Transaction Charges: 0.00345%
        - Stamp Duty: 0.003% on buy
        - SEBI Charges: 0.0001%
        - GST: 18% on (Transaction Charges + SEBI)
        """
        stt = value * 0.00025 if not is_buy else 0.0
        trans_charges = value * 0.0000345
        stamp_duty = value * 0.00003 if is_buy else 0.0
        sebi_charges = value * 0.000001
        gst = (trans_charges + sebi_charges) * 0.18
        return stt + trans_charges + stamp_duty + sebi_charges + gst

    def _load_positions(self) -> None:
        """Load persisted positions from JSON file on startup."""
        if not self.positions_file.exists():
            return

        try:
            with open(self.positions_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.available_balance = data.get("available_balance", self.initial_balance)
            self.daily_pnl = data.get("daily_pnl", 0.0)

            positions_data = data.get("positions", {})
            for symbol, pos_data in positions_data.items():
                self.positions[symbol] = PaperPosition(
                    symbol=pos_data["symbol"],
                    token=pos_data["token"],
                    entry_price=pos_data["entry_price"],
                    quantity=pos_data["quantity"],
                    entry_time=datetime.fromisoformat(pos_data["entry_time"]),
                    stop_loss=pos_data["stop_loss"],
                    target=pos_data["target"],
                    current_price=pos_data.get("current_price", pos_data["entry_price"]),
                    direction=pos_data.get("direction", "LONG"),
                )
        except Exception as e:
            logger.error(f"Error loading positions: {e}")

    def set_balance(self, balance: float) -> None:
        self.initial_balance = balance
        self.available_balance = balance
        logger.info(f"Paper balance set to {balance:,.2f}")

    def get_available_balance(self) -> float:
        return self.available_balance

    def get_total_balance(self) -> float:
        position_value = 0.0
        for pos in self.positions.values():
            if pos.direction == "SHORT":
                unrealized = (pos.entry_price - pos.current_price) * pos.quantity
                position_value += (pos.entry_price * pos.quantity) + unrealized
            else:
                position_value += pos.current_price * pos.quantity
        return self.available_balance + position_value

    def place_buy_order(
        self,
        symbol: str,
        token: str,
        price: float,
        quantity: int,
        stop_loss: float,
        target: float,
    ) -> bool:
        """Simulate long entry (BUY)."""
        if symbol in self.positions:
            logger.warning(f"Position already exists for {symbol}")
            return False

        executed_price = price * 1.002  # 0.2% adverse slippage for buy
        order_value = executed_price * quantity
        costs = self._calculate_costs(order_value, is_buy=True)
        required = order_value + costs

        if required > self.available_balance:
            logger.warning(f"Insufficient balance for {symbol}. Required: {required:,.2f}")
            return False

        self.positions[symbol] = PaperPosition(
            symbol=symbol,
            token=token,
            entry_price=executed_price,
            quantity=quantity,
            entry_time=now_ist(),
            stop_loss=stop_loss,
            target=target,
            direction="LONG",
            current_price=executed_price,
        )

        self.available_balance -= required
        self.trade_count += 1
        self._save_positions()
        logger.info(f"[PAPER] BUY {quantity} {symbol} @ {executed_price:.2f} | SL: {stop_loss:.2f} | Target: {target:.2f}")
        return True

    def place_sell_order(self, symbol: str, price: float, reason: str = "MANUAL") -> bool:
        """Simulate long exit (SELL)."""
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return False
        position = self.positions[symbol]
        if position.direction != "LONG":
            logger.warning(f"Cannot use long exit SELL for non-long position: {symbol}")
            return False

        executed_price = price * 0.9995  # 0.05% adverse slippage for sell
        sale_value = executed_price * position.quantity
        costs = self._calculate_costs(sale_value, is_buy=False)

        pnl = (executed_price - position.entry_price) * position.quantity
        pnl_percent = ((executed_price - position.entry_price) / position.entry_price) * 100

        self.available_balance += sale_value - costs
        self.daily_pnl += pnl - costs

        self.trades.append(
            PaperTrade(
                symbol=symbol,
                token=position.token,
                entry_price=position.entry_price,
                exit_price=executed_price,
                quantity=position.quantity,
                entry_time=position.entry_time,
                exit_time=now_ist(),
                pnl=pnl,
                pnl_percent=pnl_percent,
                exit_reason=reason,
                direction="LONG",
            )
        )

        del self.positions[symbol]
        self._save_positions()
        logger.info(f"[PAPER] SELL {symbol} @ {executed_price:.2f} | P&L: {pnl:+.2f}%")
        return True

    def place_short_order(
        self,
        symbol: str,
        token: str,
        price: float,
        quantity: int,
        stop_loss: float,
        target: float,
    ) -> bool:
        """Simulate short entry (SELL)."""
        if symbol in self.positions:
            logger.warning(f"Position already exists for {symbol}")
            return False

        executed_price = price * 0.9995  # 0.05% adverse slippage for short sell
        order_value = executed_price * quantity
        entry_costs = self._calculate_costs(order_value, is_buy=False)
        required_margin = order_value + entry_costs

        if required_margin > self.available_balance:
            logger.warning(f"Insufficient balance for short {symbol}. Required: {required_margin:,.2f}")
            return False

        self.positions[symbol] = PaperPosition(
            symbol=symbol,
            token=token,
            entry_price=executed_price,
            quantity=quantity,
            entry_time=now_ist(),
            stop_loss=stop_loss,
            target=target,
            direction="SHORT",
            current_price=executed_price,
        )

        # Reserve notional + costs as margin for simplicity
        self.available_balance -= required_margin
        self.trade_count += 1
        self._save_positions()
        logger.info(f"[PAPER] SHORT {quantity} {symbol} @ {executed_price:.2f} | SL: {stop_loss:.2f} | Target: {target:.2f}")
        return True

    def place_cover_order(self, symbol: str, price: float, reason: str = "MANUAL") -> bool:
        """Simulate short exit (BUY to cover)."""
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return False
        position = self.positions[symbol]
        if position.direction != "SHORT":
            logger.warning(f"Cannot cover non-short position: {symbol}")
            return False

        executed_price = price * 1.002  # 0.2% adverse slippage for buy cover
        cover_value = executed_price * position.quantity
        exit_costs = self._calculate_costs(cover_value, is_buy=True)

        pnl = (position.entry_price - executed_price) * position.quantity
        pnl_percent = ((position.entry_price - executed_price) / position.entry_price) * 100

        entry_notional = position.entry_price * position.quantity
        self.available_balance += entry_notional + pnl - exit_costs
        self.daily_pnl += pnl - exit_costs

        self.trades.append(
            PaperTrade(
                symbol=symbol,
                token=position.token,
                entry_price=position.entry_price,
                exit_price=executed_price,
                quantity=position.quantity,
                entry_time=position.entry_time,
                exit_time=now_ist(),
                pnl=pnl,
                pnl_percent=pnl_percent,
                exit_reason=reason,
                direction="SHORT",
            )
        )

        del self.positions[symbol]
        self._save_positions()
        logger.info(f"[PAPER] COVER {symbol} @ {executed_price:.2f} | P&L: {pnl:+.2f}")
        return True

    def update_price(self, symbol: str, price: float) -> Optional[str]:
        """Update current price and check stop loss/target trigger."""
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        position.current_price = price
        if position.direction == "SHORT":
            position.pnl = (position.entry_price - price) * position.quantity
            if price >= position.stop_loss:
                return "STOP_LOSS"
            if price <= position.target:
                return "TARGET"
            return None

        position.pnl = (price - position.entry_price) * position.quantity
        if price <= position.stop_loss:
            return "STOP_LOSS"
        if price >= position.target:
            return "TARGET"
        return None

    def get_positions(self) -> List[Dict]:
        return [
            {
                "symbol": pos.symbol,
                "token": pos.token,
                "entry_price": pos.entry_price,
                "quantity": pos.quantity,
                "current_price": pos.current_price,
                "pnl": pos.pnl,
                "stop_loss": pos.stop_loss,
                "target": pos.target,
                "entry_time": pos.entry_time.isoformat(),
                "status": pos.status,
                "direction": pos.direction,
            }
            for pos in self.positions.values()
        ]

    def get_trades_today(self) -> List[Dict]:
        today = now_ist_date()
        return [
            {
                "symbol": trade.symbol,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "quantity": trade.quantity,
                "pnl": trade.pnl,
                "pnl_percent": trade.pnl_percent,
                "exit_reason": trade.exit_reason,
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat(),
                "direction": trade.direction,
            }
            for trade in self.trades
            if trade.exit_time.date() == today
        ]

    def get_daily_summary(self) -> Dict:
        today_trades = self.get_trades_today()
        return {
            "initial_balance": self.initial_balance,
            "current_balance": self.get_total_balance(),
            "available_balance": self.available_balance,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_percent": (self.daily_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0.0,
            "total_trades": len(today_trades),
            "winning_trades": len([t for t in today_trades if t["pnl"] > 0]),
            "losing_trades": len([t for t in today_trades if t["pnl"] < 0]),
            "open_positions": len(self.positions),
        }

    def save_daily_report(self) -> None:
        today = now_ist().strftime("%Y-%m-%d")
        report = {
            "date": today,
            "summary": self.get_daily_summary(),
            "trades": self.get_trades_today(),
            "open_positions": self.get_positions(),
        }
        filepath = self.data_dir / f"{today}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Daily report saved to {filepath}")

    def reset_daily(self) -> None:
        self.daily_pnl = 0.0
        self.trade_count = 0
        logger.info("Daily counters reset")
