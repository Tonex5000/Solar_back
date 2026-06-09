"""
Solar System Sizing Calculator API

A FastAPI backend for calculating solar system components based on load requirements.
"""

from math import ceil
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Constants
VALID_BATTERY_VOLTAGES = [12, 24, 48]
SYSTEM_LOSS_FACTOR = 1.2  # 20% system loss
BATTERY_RATED_VOLTAGE = 12  # 12V batteries for battery count estimation
BATTERY_RATED_CAPACITY = 200  # 200Ah batteries


class SolarCalculationInput(BaseModel):
    """Input model for solar system sizing calculation."""

    load: float = Field(
        ...,
        gt=0,
        description="Total load in watts",
        examples=[1000, 2500, 5000],
    )
    backup_hours: float = Field(
        ...,
        ge=1,
        le=12,
        description="Number of hours the system should run (1-12)",
        examples=[4, 8, 12],
    )
    battery_voltage: Literal[12, 24, 48] = Field(
        ...,
        description="System voltage (12, 24, or 48)",
        examples=[24, 48],
    )
    charging_hours: float = Field(
        ...,
        ge=1,
        le=12,
        description="Number of hours available to charge battery (1-12)",
        examples=[4, 6, 8],
    )
    panel_wattage: int = Field(
        ...,
        gt=0,
        description="Wattage of a single solar panel (e.g., 300, 400, 550)",
        examples=[400, 550],
    )

    @field_validator("battery_voltage")
    @classmethod
    def validate_battery_voltage(cls, v: int) -> int:
        if v not in VALID_BATTERY_VOLTAGES:
            raise ValueError(f"Battery voltage must be one of {VALID_BATTERY_VOLTAGES}")
        return v


class SolarCalculationOutput(BaseModel):
    """Output model for solar system sizing calculation."""

    inverter_watts: float = Field(
        ...,
        ge=0,
        description="Required inverter size in watts",
    )
    battery_ah: float = Field(
        ...,
        ge=0,
        description="Required battery capacity in amp-hours",
    )
    solar_watts: float = Field(
        ...,
        ge=0,
        description="Required solar array size in watts",
    )
    number_of_panels: int = Field(
        ...,
        ge=1,
        description="Number of solar panels required",
    )
    battery_count: int = Field(
        ...,
        ge=1,
        description="Number of 12V 200Ah batteries required",
    )


# Initialize FastAPI app
app = FastAPI(
    title="Solar System Sizing Calculator",
    description="API for calculating solar system components based on load requirements, backup needs, and solar panel specifications.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for frontend access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "Solar System Sizing Calculator"}


@app.post(
    "/calculate",
    response_model=SolarCalculationOutput,
    tags=["Calculator"],
    summary="Calculate solar system sizing",
    description="Calculate inverter size, battery capacity, solar array size, and number of panels based on load and backup requirements.",
)
async def calculate_solar_system(input_data: SolarCalculationInput) -> SolarCalculationOutput:
    """
    Calculate solar system components.

    Performs the following calculations:
    1. Energy required (Wh) = load (W) × backup_hours
    2. Battery capacity (Ah) = energy (Wh) / battery_voltage (V)
    3. Inverter size (W) = load × 1.25 (25% headroom)
    4. Solar size (W) = adjusted_energy (Wh) / charging_hours
    5. Number of panels = ceil(solar_watts / panel_wattage)
    6. Battery count based on 12V 200Ah batteries

    All energy calculations include a 20% system loss factor.
    """
    # Extract validated inputs
    load = input_data.load
    backup_hours = input_data.backup_hours
    battery_voltage = input_data.battery_voltage
    charging_hours = input_data.charging_hours
    panel_wattage = input_data.panel_wattage

    # Validate charging hours is not zero (already validated by Pydantic, but double-check)
    if charging_hours <= 0:
        raise HTTPException(
            status_code=400,
            detail="Charging hours must be greater than zero",
        )

    # Calculate base energy requirement
    energy_wh = load * backup_hours

    # Apply 20% system loss
    energy_wh_adjusted = energy_wh * SYSTEM_LOSS_FACTOR

    # Calculate battery capacity (Ah)
    battery_ah = energy_wh_adjusted / battery_voltage

    # Calculate inverter size (with 25% headroom for surge capacity)
    inverter_watts = ((load * 2) / 0.8) / 1000

    # Calculate solar array size using adjusted energy
    solar_watts = energy_wh_adjusted / charging_hours

    # Calculate number of panels (round up)
    number_of_panels = ceil(solar_watts / panel_wattage)

    # Calculate battery count based on 12V 200Ah batteries
    # Each battery provides: 12V × 200Ah = 2400Wh
    # Total batteries needed to meet the adjusted energy requirement
    single_battery_wh = BATTERY_RATED_VOLTAGE * BATTERY_RATED_CAPACITY
    battery_count = ceil(energy_wh_adjusted / single_battery_wh)

    return SolarCalculationOutput(
        inverter_watts= round(inverter_watts, 1),
        battery_ah=round(battery_ah, 2),
        solar_watts=round(solar_watts, 2),
        number_of_panels=number_of_panels,
        battery_count=battery_count,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
