"""Central configuration for the Market Data + Signal Engine module.

Every threshold, weight and scaling constant used by the signal calculators and
the engine lives here. Nothing in this module should be duplicated elsewhere in
the codebase -- calculators import from here so a judge (or a teammate) can
change one number and see the whole engine respond consistently.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Service identity
# --------------------------------------------------------------------------
SERVICE_NAME = "market-signal-engine"
SERVICE_VERSION = "1.0.0"
DEFAULT_CURRENCY = "INR"

# --------------------------------------------------------------------------
# Mock data generation
# --------------------------------------------------------------------------
DEFAULT_HISTORY_LENGTH = 120

# --------------------------------------------------------------------------
# Signal 1 -- Price momentum
# --------------------------------------------------------------------------
MOMENTUM_LOOKBACK = 5
MOMENTUM_BULLISH_THRESHOLD = 2.0  # percent
MOMENTUM_BEARISH_THRESHOLD = -2.0  # percent

# Percentage move beyond the classification threshold at which a directional
# momentum signal reaches full confidence (1.0).
MOMENTUM_FULL_SCALE = 6.0
# Distance from 0% at which a NEUTRAL momentum reading drops to minimum
# confidence. Equals the bullish threshold so confidence is continuous at the
# classification boundary.
MOMENTUM_NEUTRAL_SCALE = 2.0

MOMENTUM_LOOKBACK_MIN = 1
MOMENTUM_LOOKBACK_MAX = 60

# --------------------------------------------------------------------------
# Signal 2 -- Volume anomaly
# --------------------------------------------------------------------------
VOLUME_LOOKBACK = 20
VOLUME_HIGH_RATIO = 1.5
VOLUME_LOW_RATIO = 0.67
# Number of periods used to establish the price direction that gives an
# elevated-volume reading its bullish or bearish sign.
VOLUME_PRICE_LOOKBACK = 1

# Ratio distance beyond VOLUME_HIGH_RATIO at which an elevated-volume signal
# reaches full confidence.
VOLUME_HIGH_FULL_SCALE = 1.5
# Ratio distance from the nearest threshold at which a NEUTRAL volume reading
# reaches full confidence.
VOLUME_NEUTRAL_SCALE = 0.4

# --------------------------------------------------------------------------
# Signal 3 -- RSI (Wilder)
# --------------------------------------------------------------------------
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70.0
RSI_OVERSOLD = 30.0
# RSI points beyond the overbought/oversold threshold at which the signal
# reaches full confidence (70 -> 90 and 30 -> 10).
RSI_EXTREME_SCALE = 20.0
# RSI points away from 50 at which a NEUTRAL reading drops to minimum
# confidence. Equals the distance from 50 to the thresholds, so confidence is
# continuous at the boundary.
RSI_NEUTRAL_SCALE = 20.0
# RSI is mathematically undefined when price never changes. We report the
# neutral midpoint and attach an explanatory warning rather than fabricating a
# directional reading.
RSI_CONSTANT_PRICE_VALUE = 50.0

# --------------------------------------------------------------------------
# Overall combination
# --------------------------------------------------------------------------
MOMENTUM_WEIGHT = 0.40
VOLUME_WEIGHT = 0.30
RSI_WEIGHT = 0.30

SIGNAL_WEIGHTS = {
    "price_momentum": MOMENTUM_WEIGHT,
    "volume_anomaly": VOLUME_WEIGHT,
    "rsi": RSI_WEIGHT,
}

OVERALL_BULLISH_THRESHOLD = 0.33
OVERALL_BEARISH_THRESHOLD = -0.33

# --------------------------------------------------------------------------
# Confidence model
# --------------------------------------------------------------------------
# Confidence assigned to a signal sitting exactly on its classification
# boundary. Confidence scales from here up to 1.0 as the reading moves away
# from the boundary in either direction.
CONFIDENCE_AT_THRESHOLD = 0.5
# Multiplier applied to overall confidence when candle-level data problems were
# detected (discarded candles, missing volume history, etc).
DEGRADED_DATA_PENALTY = 0.90
# Number of decimal places every confidence value is rounded to. Rounding is
# applied consistently so identical inputs always serialise to identical JSON.
CONFIDENCE_DECIMALS = 2
VALUE_DECIMALS = 2

# --------------------------------------------------------------------------
# Signal names -- used as dict keys in the response contract. Downstream
# consumers depend on these exact strings.
# --------------------------------------------------------------------------
SIGNAL_MOMENTUM = "price_momentum"
SIGNAL_VOLUME = "volume_anomaly"
SIGNAL_RSI = "rsi"
