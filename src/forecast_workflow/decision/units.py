"""Physical-unit accessors with strict compatibility for the frozen MW release."""

import numpy as np


def capacity_units(contract):
    """Return scale/grid; reject conflicting aliases and incomplete new schemas."""
    generic = "scale" in contract or "capacity_grid" in contract
    if generic:
        if not isinstance(contract.get("unit"), str) or not contract["unit"].strip():
            raise ValueError("A physical unit is required for generic capacity contracts")
        scale, grid = contract["scale"], contract["capacity_grid"]
        if "scale_mw" in contract or "capacity_grid_mw" in contract:
            if (
                contract["unit"] != "MW"
                or scale != contract.get("scale_mw")
                or grid != contract.get("capacity_grid_mw")
            ):
                raise ValueError("Conflicting legacy and generic capacity units")
    else:
        scale, grid = contract["scale_mw"], contract["capacity_grid_mw"]
    grid = np.asarray(grid, dtype=float)
    if isinstance(scale, bool) or not np.isfinite(scale) or scale <= 0:
        raise ValueError("Capacity scale must be finite and positive")
    if grid.ndim != 1 or not np.isfinite(grid).all() or np.any(np.diff(grid) <= 0):
        raise ValueError("Capacity grid must be finite and increasing")
    return float(scale), grid
