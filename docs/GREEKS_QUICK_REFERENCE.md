# Options Greeks - Quick Reference Card

## What Are Greeks?

Greeks measure option price sensitivity to various factors:

| Greek | Symbol | What It Measures | Typical Values |
|-------|--------|------------------|----------------|
| **Delta** | Δ | Price change per ₹1 move in underlying | 0 to 1 (calls)<br>-1 to 0 (puts) |
| **Gamma** | Γ | Rate of Delta change | 0 to ∞<br>Higher near ATM |
| **Theta** | Θ | Time decay per day | Negative (long)<br>Accelerates near expiry |
| **Vega** | ν | IV sensitivity (per 1% IV change) | 0 to ∞<br>Higher for ATM, longer expiry |
| **Rho** | ρ | Rate sensitivity (per 1% rate change) | Small for short-term options |

## Quick Commands

### 1. Get Greeks for One Option
```bash
curl "http://localhost:5010/greeks?apikey=YOUR_KEY&ticker=NIFTY26MAR24000CE:NFO"
```

### 2. Get Greeks for Multiple Options
```bash
curl -X POST http://localhost:5010/greeks/batch \
  -H "Content-Type: application/json" \
  -H "apikey: YOUR_KEY" \
  -d '{"tickers": ["NIFTY26MAR24000CE:NFO", "BANKNIFTY26MAR51000PE:NFO"]}'
```

### 3. Get LTP + Greeks
```bash
curl "http://localhost:5010/ltp?apikey=YOUR_KEY&tickers=NIFTY26MAR24000CE:NFO"
```

### 4. Get Historical Data + Greeks
```bash
curl "http://localhost:5010/historical_data?apikey=YOUR_KEY&tickers=NIFTY26MAR24000CE:NFO&from=2026-03-15%2009:15:00&to=2026-03-20%2015:30:00&interval=15minute"
```

### 5. Disable Greeks (Faster Response)
```bash
curl "http://localhost:5010/ltp?apikey=YOUR_KEY&tickers=NIFTY26MAR24000CE:NFO&greeks=false"
```

## Greeks Interpretation

### Delta (Δ) - Directional Exposure
- **Call Delta = 0.65**: Option price increases ₹0.65 for every ₹1 increase in underlying
- **Put Delta = -0.35**: Option price decreases ₹0.35 for every ₹1 increase in underlying
- **~65% probability** of expiring ITM (for 0.65 delta)
- **Position Delta**: Contracts × Delta × Lot Size = Equivalent shares

### Gamma (Γ) - Delta Acceleration
- **Gamma = 0.012**: Delta increases by 0.012 for every ₹1 move in underlying
- **High near ATM + expiry**: Position becomes more directional quickly
- **Low for deep ITM/OTM**: Delta changes slowly

### Theta (Θ) - Time Decay
- **Theta = -15.50**: Option loses ₹15.50 per day
- **Always negative for long options**: Time works against you
- **Accelerates near expiry**: Decay fastest in last 30 days
- **Higher for ATM options**: Maximum time value = Maximum decay

### Vega (ν) - Volatility Exposure
- **Vega = 125.30**: Option price increases ₹1.25 for 1% increase in IV
- **Long options = Long vega**: Benefit from IV increase
- **Short options = Short vega**: Benefit from IV decrease
- **Important during events**: Earnings, Fed meetings, market stress

### Rho (ρ) - Interest Rate Effect
- **Rho = 8.50**: Option price increases ₹0.085 for 1% increase in rates
- **Usually least important**: Especially for short-term options
- **Matters for LEAPS**: Long-dated options more sensitive

### Implied Volatility (IV)
- **IV = 28.5%**: Market expects ±28.5% annual volatility
- **Compare with HV**: IV > HV = expensive, IV < HV = cheap
- **Mean reverting**: High IV tends to fall, low IV tends to rise
- **Use for strategy**: Sell high IV, buy low IV

### Moneyness
- **ITM (In-The-Money)**: Has intrinsic value, higher delta
- **ATM (At-The-Money)**: Maximum time value, highest gamma/theta
- **OTM (Out-of-The-Money)**: Only time value, lower delta

## Common Use Cases

### 1. Delta Hedging
```
You're short 50 contracts of NIFTY 24000 CE (delta = 0.65)
Position Delta = 50 × 0.65 × 50 (lot size) = 1,625
Hedge: Buy 1,625 NIFTY futures or 33 lots (1,625 ÷ 50)
```

### 2. Bull Call Spread Greeks
```
Long 24000 CE: Delta +0.65, Theta -20, Vega +150
Short 24500 CE: Delta -0.35, Theta +15, Vega -100
Net: Delta +0.30, Theta -5, Vega +50
→ Moderately bullish, low time decay, slight IV exposure
```

### 3. Straddle Greeks
```
Long 24000 CE: Delta +0.50, Vega +200
Long 24000 PE: Delta -0.50, Vega +200
Net: Delta 0 (neutral), Vega +400 (long volatility)
→ Direction neutral, profits from big moves
```

### 4. Iron Condor Greeks
```
Short 23500 CE + Short 24500 CE + Long 23000 PE + Long 25000 CE
Net: Delta ≈ 0, Theta > 0, Vega < 0
→ Neutral, profits from time decay and IV crush
```

## Strategy Selection by Greeks

| Strategy Type | Delta | Theta | Vega | When to Use |
|---------------|-------|-------|------|-------------|
| **Long Call/Put** | High | Negative | Positive | Directional, expect big move |
| **Short Call/Put** | High | Positive | Negative | Directional, collect premium |
| **Long Straddle** | ~0 | Negative | Positive | Volatility increase expected |
| **Short Straddle** | ~0 | Positive | Negative | Low volatility, range-bound |
| **Bull/Bear Spread** | Medium | Negative | Low | Directional with limited risk |
| **Iron Condor** | ~0 | Positive | Negative | Range-bound, collect premium |
| **Calendar Spread** | ~0 | Positive | Varies | Time decay, volatility arbitrage |

## Risk Management Using Greeks

### Position Greeks Monitoring
```bash
# Get Greeks for all open positions
curl -X POST http://localhost:5010/greeks/batch -d '{
  "tickers": [
    "NIFTY26MAR24000CE:NFO",
    "NIFTY26MAR24500CE:NFO"
  ]
}'

# Calculate net Greeks:
Net Delta = Sum of all deltas
Net Gamma = Sum of all gammas
Net Theta = Sum of all thetas
Net Vega = Sum of all vegas
```

### Risk Limits
- **Delta Limit**: Max directional exposure (e.g., ±5,000)
- **Gamma Limit**: Max delta acceleration (e.g., ±500)
- **Vega Limit**: Max volatility exposure (e.g., ±10,000)
- **Theta Goal**: Target daily profit from decay (e.g., +₹5,000/day)

### Adjustment Triggers
- **Delta > Limit**: Add opposite-direction options or hedge with futures
- **Gamma Too High**: Move strikes away from ATM
- **Vega Too High**: Reduce long options or add short options
- **Theta Too Negative**: Close long options near expiry

## Configuration

### Set Risk-Free Rate
```bash
# Environment variable
export RISK_FREE_RATE=0.065  # 6.5% for India

# Or in docker-compose.yml
environment:
  - RISK_FREE_RATE=0.065
```

### Default: 6.5% (India 10-year G-Sec rate)

## Response Time

- Single option Greeks: ~200-500ms
- Batch (10 options): ~2-3 seconds
- With /ltp: +300ms per option
- With /historical_data: +300ms per option

## Troubleshooting

### "Failed to calculate Greeks"
- Check if option expired (expiry date < today)
- Verify option exists in instruments cache
- Ensure underlying is tradeable

### "IV convergence failed"
- Normal for deep ITM/OTM options
- Try a different strike closer to ATM
- Check if option is liquid (volume > 0)

### Greeks seem wrong
- Compare with broker platform (Kite, Opstra)
- Check underlying price is current
- Verify days to expiry
- Ensure risk-free rate is correct

## Best Practices

1. **Monitor All Greeks**: Don't just focus on Delta
2. **Rebalance Regularly**: Greeks change as underlying moves
3. **Check IV Rank**: Know if volatility is high or low historically
4. **Use Batch Endpoint**: Efficient for multiple options
5. **Cache When Possible**: Greeks change slowly for far-dated options
6. **Validate Against Broker**: Cross-check important calculations
7. **Understand Limitations**: Black-Scholes assumes European options
8. **Plan Adjustments**: Know your Greeks limits before entering

## Greek Relationships

- **Delta ↑ when**: Underlying ↑ (calls), Underlying ↓ (puts), Time passes (ITM)
- **Gamma ↑ when**: Near ATM, Near expiry
- **Theta ↑ when**: Near expiry, ATM, High volatility
- **Vega ↑ when**: ATM, Long time to expiry
- **IV ↑ when**: Market stress, Earnings ahead, Large moves expected

## Advanced: Greeks of Greeks

- **Vanna**: Change in Delta per change in IV
- **Charm**: Change in Delta per day (Delta decay)
- **Vomma**: Change in Vega per change in IV
- **Speed**: Change in Gamma per change in underlying

*Note: Not yet implemented, but planned for future release*

---

**Quick Links:**
- Full Documentation: `README.md` → "Options Greeks Calculator"
- Implementation Details: `GREEKS_IMPLEMENTATION_SUMMARY.md`
- API Base URL: `http://localhost:5010`

**Support:**
- Check logs: `docker-compose logs -f`
- Test endpoint: `GET /greeks?apikey=test&ticker=NIFTY26MAR24000CE:NFO`
