from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class DynacardPoint(BaseModel):
    pos: float
    load: float


class DynacardPayload(BaseModel):
    surface_up: List[DynacardPoint]
    surface_dn: List[DynacardPoint]
    downhole_up: List[DynacardPoint]
    downhole_dn: List[DynacardPoint]
    plunger_stroke_in: float
    card_area_joules: float
    surface_peak_load: float
    surface_min_load: float


class EconomicMetrics(BaseModel):
    oil_price_usd_bbl: float          # Pegged to PPAC Indian Crude Basket (~$76.5/bbl)
    steam_cost_usd_ton: float         # Pegged to US EIA scaled by Indian NG tariff (~$24.2/ton)
    daily_oil_bpd: float
    daily_steam_tons: float
    current_sor: float                # Steam-Oil Ratio (tons steam / bbl oil)
    economic_cutoff_sor: float        # Breakeven SOR where oil revenue == steam cost
    net_daily_margin_usd: float       # Daily net cash flow per well
    days_to_sor_cutoff: int           # Predictive time to steam shutoff recommendation


class DepthPoint(BaseModel):
    depth_m: float
    temp_c: float
    visc_cp: float


class WellboreProfile(BaseModel):
    depth_points: List[DepthPoint]
    pump_depth_m: float = 1000.0
    perforations_top_m: float = 1150.0
    perforations_bottom_m: float = 1200.0


class SurfaceFacilityMetrics(BaseModel):
    boiler_steam_rate_tpd: float       # Central OTSG capacity (~300 t/d)
    boiler_fuel_gas_mmscfd: float      # Natural gas fuel rate
    boiler_thermal_eff_pct: float      # Boiler efficiency (~82%)
    steam_header_pressure_mpa: float   # Main trunk steam pressure (~16.2 MPa)
    steam_header_temp_c: float         # Steam header temperature (~348°C)
    steam_quality_pct: float           # Steam quality delivered to wellpads (~78.5%)
    total_field_oil_bpd: float         # Aggregated field production delivered to GGS
    total_field_water_cut_pct: float   # Water cut entering GGS
    flowline_gel_risk: Dict[str, str]  # Flowline status per well: NORMAL | ELEVATED | CRITICAL_GEL_HAZARD
    flowline_temps_c: Dict[str, float] # Delivery temp at GGS manifold


class TelemetryData(BaseModel):
    timestamp: str
    well_id: str
    load: float                       # Polished Rod Load (lbs)
    position: float                   # Plunger position (inches)
    temperature: float                # Bottomhole temperature (°C)
    viscosity: float                  # Estimated viscosity (cP)
    spm: float                        # Actual pump strokes-per-minute
    diagnosis: str                    # ML classifier output: normal | rod_floating | fluid_pound
    confidence: float                 # Classifier confidence (0–1)
    phase: str                        # CSS phase: Injection | Soak | Production
    cycle_number: int = 1             # CSS Cycle index (1, 2, 3...)
    water_cut_pct: float = 35.0       # Water cut rising with cycles
    phase_day: float = 0.0
    tubing_psi: float = 142.0
    casing_psi: float = 86.0
    dynacard: Optional[DynacardPayload] = None
    economics: Optional[EconomicMetrics] = None
    wellbore_profile: Optional[WellboreProfile] = None


class SetPointCommand(BaseModel):
    well_id: str
    spm_override: Optional[float] = None
    auto_mode: bool = True
    emergency_shutoff: bool = False


class CycleTransition(BaseModel):
    well_id: str
    current_phase: str
    sor: float
    recommendation: str
    timestamp: str
    economic_loss_usd_day: Optional[float] = 0.0


class WellStatus(BaseModel):
    well_id: str
    status: str
    temperature: float
    viscosity: float
    phase: str
    cycle_number: int = 1
    water_cut_pct: float = 35.0
    diagnosis: str
    last_seen: str
    sor: float
    daily_margin: float
