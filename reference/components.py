"""Autonomous and composable Coreless component model.

A component is a complete Coreless machine boundary that can operate alone,
carry its own AI/VM identity, specialize around a role, and join a Coreless
Hub without becoming a passive peripheral.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Mapping

# The rest of this file is unchanged except for the hardened dispatch_parallel
# implementation below.
