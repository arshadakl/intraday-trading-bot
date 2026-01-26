"""Transaction Cost Calculator for realistic P&L accounting"""

from typing import Dict
from loguru import logger


class TransactionCostCalculator:
    """
    Calculate all transaction costs for Indian equity intraday trading.
    
    Provides realistic P&L calculations including:
    - Brokerage fees
    - STT (Securities Transaction Tax)
    - Transaction charges (NSE/BSE)
    - GST (Goods and Services Tax)
    - SEBI charges
    - Stamp duty
    
    Supports multiple brokers with different fee structures.
    """
    
    # Fee structures by broker (Indian equity intraday)
    BROKER_FEES = {
        'zerodha': {
            'name': 'Zerodha',
            'brokerage_per_order': 20,  # Flat ₹20 or 0.03%, whichever is lower
            'brokerage_percent': 0.0003,  # 0.03%
            'stt_rate': 0.00025,  # 0.025% on sell side only
            'transaction_charge_rate': 0.0000345,  # NSE: 0.00345%
            'gst_rate': 0.18,  # 18% on brokerage + transaction charges
            'sebi_rate': 0.0000001,  # ₹10 per crore turnover
            'stamp_duty_rate': 0.00003  # 0.003% on buy side
        },
        'angel_one': {
            'name': 'Angel One',
            'brokerage_per_order': 20,  # Flat ₹20 per order
            'brokerage_percent': 0.0005,  # 0.05% (not used if flat is lower)
            'stt_rate': 0.00025,  # 0.025% on sell side
            'transaction_charge_rate': 0.0000345,  # NSE: 0.00345%
            'gst_rate': 0.18,
            'sebi_rate': 0.0000001,
            'stamp_duty_rate': 0.00003
        },
        'upstox': {
            'name': 'Upstox',
            'brokerage_per_order': 20,  # Flat ₹20 per order
            'brokerage_percent': 0.0005,
            'stt_rate': 0.00025,
            'transaction_charge_rate': 0.0000345,
            'gst_rate': 0.18,
            'sebi_rate': 0.0000001,
            'stamp_duty_rate': 0.00003
        }
    }
    
    def __init__(self, broker: str = 'zerodha'):
        """
        Initialize calculator for a specific broker.
        
        Args:
            broker: Broker name ('zerodha', 'angel_one', 'upstox')
        """
        if broker.lower() not in self.BROKER_FEES:
            logger.warning(
                f"Unknown broker '{broker}', using Zerodha defaults. "
                f"Available: {list(self.BROKER_FEES.keys())}"
            )
            broker = 'zerodha'
        
        self.broker = broker.lower()
        self.fees = self.BROKER_FEES[self.broker]
        logger.debug(f"Transaction calculator initialized for {self.fees['name']}")
    
    def calculate_costs(self, quantity: int, buy_price: float,
                       sell_price: float) -> Dict:
        """
        Calculate all transaction costs for an intraday trade.
        
        Args:
            quantity: Number of shares
            buy_price: Entry price
            sell_price: Exit price
        
        Returns:
            Dict with total costs and detailed breakdown
        """
        # Edge case: Invalid inputs
        if quantity <= 0 or buy_price <= 0 or sell_price <= 0:
            logger.error(
                f"Invalid trade parameters: qty={quantity}, "
                f"buy={buy_price}, sell={sell_price}"
            )
            return {
                'total': 0,
                'breakdown': {},
                'error': 'Invalid parameters'
            }
        
        # Calculate turnovers
        buy_turnover = buy_price * quantity
        sell_turnover = sell_price * quantity
        total_turnover = buy_turnover + sell_turnover
        
        # 1. Brokerage (both buy and sell sides)
        buy_brokerage = min(
            self.fees['brokerage_per_order'],
            buy_turnover * self.fees['brokerage_percent']
        )
        sell_brokerage = min(
            self.fees['brokerage_per_order'],
            sell_turnover * self.fees['brokerage_percent']
        )
        total_brokerage = buy_brokerage + sell_brokerage
        
        # 2. STT (Securities Transaction Tax) - only on sell side for intraday
        stt = sell_turnover * self.fees['stt_rate']
        
        # 3. Transaction charges (NSE/BSE)
        transaction_charges = total_turnover * self.fees['transaction_charge_rate']
        
        # 4. GST (on brokerage + transaction charges)
        gst_base = total_brokerage + transaction_charges
        gst = gst_base * self.fees['gst_rate']
        
        # 5. SEBI charges (₹10 per crore turnover)
        sebi_charges = total_turnover * self.fees['sebi_rate']
        
        # 6. Stamp duty (on buy side only)
        stamp_duty = buy_turnover * self.fees['stamp_duty_rate']
        
        # Calculate total
        total_cost = (
            total_brokerage + stt + transaction_charges +
            gst + sebi_charges + stamp_duty
        )
        
        breakdown = {
            'brokerage': round(total_brokerage, 2),
            'stt': round(stt, 2),
            'transaction_charges': round(transaction_charges, 2),
            'gst': round(gst, 2),
            'sebi_charges': round(sebi_charges, 2),
            'stamp_duty': round(stamp_duty, 2)
        }
        
        return {
            'total': round(total_cost, 2),
            'breakdown': breakdown,
            'buy_turnover': round(buy_turnover, 2),
            'sell_turnover': round(sell_turnover, 2),
            'total_turnover': round(total_turnover, 2)
        }
    
    def calculate_net_pnl(self, quantity: int, buy_price: float,
                          sell_price: float) -> Dict:
        """
        Calculate net P&L after all transaction costs.
        
        This is the REAL profit/loss you'll see in your account.
        
        Args:
            quantity: Number of shares
            buy_price: Entry price
            sell_price: Exit price
        
        Returns:
            Dict with gross P&L, costs, net P&L, and percentages
        """
        # Gross P&L (before costs)
        gross_pnl = (sell_price - buy_price) * quantity
        
        # Calculate costs
        costs = self.calculate_costs(quantity, buy_price, sell_price)
        
        # Check for errors
        if 'error' in costs:
            return {
                'gross_pnl': 0,
                'costs': costs,
                'net_pnl': 0,
                'net_pnl_percent': 0,
                'error': costs['error']
            }
        
        # Net P&L (after costs)
        net_pnl = gross_pnl - costs['total']
        
        # Calculate percentages
        investment = buy_price * quantity
        gross_pnl_percent = (gross_pnl / investment * 100) if investment > 0 else 0
        net_pnl_percent = (net_pnl / investment * 100) if investment > 0 else 0
        
        # Cost as % of investment
        cost_percent = (costs['total'] / investment * 100) if investment > 0 else 0
        
        return {
            'gross_pnl': round(gross_pnl, 2),
            'costs': costs,
            'net_pnl': round(net_pnl, 2),
            'gross_pnl_percent': round(gross_pnl_percent, 2),
            'net_pnl_percent': round(net_pnl_percent, 2),
            'cost_percent': round(cost_percent, 2),
            'investment': round(investment, 2),
            'breakeven_price': round(buy_price + (costs['total'] / quantity), 2)
        }
    
    def get_minimum_profit_for_breakeven(self, quantity: int, 
                                        buy_price: float) -> Dict:
        """
        Calculate minimum price movement needed to break even.
        
        Useful for understanding if a stock has enough volatility
        to justify trading it.
        
        Args:
            quantity: Number of shares
            buy_price: Entry price
        
        Returns:
            Dict with breakeven details
        """
        if quantity <= 0 or buy_price <= 0:
            return {'error': 'Invalid parameters'}
        
        # Estimate costs (assume sell price = buy price)
        costs = self.calculate_costs(quantity, buy_price, buy_price)
        
        # Minimum profit needed
        min_profit_per_share = costs['total'] / quantity
        breakeven_price = buy_price + min_profit_per_share
        
        # As percentage
        min_profit_percent = (min_profit_per_share / buy_price * 100)
        
        return {
            'buy_price': round(buy_price, 2),
            'breakeven_price': round(breakeven_price, 2),
            'min_profit_points': round(min_profit_per_share, 2),
            'min_profit_percent': round(min_profit_percent, 2),
            'total_costs': costs['total'],
            'quantity': quantity
        }
