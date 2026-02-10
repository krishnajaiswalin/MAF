from dataclasses import dataclass
from typing import Dict, Any

_ALLOWED_FLEETS = {"Airbus", "ATR"}
_ALLOWED_STATIONS = {"Metro", "Non-Metro"}
_ALLOWED_CREW_TYPES = {"CP", "FO", "CC"}


@dataclass(frozen=True)
class OrchestratorParams:
    fleet: str
    stationCategory: str
    crewType: str


class OrchestratorAgent:
    def __init__(self, default_fleet: str = "Airbus", default_station: str = "Metro", default_crew: str = "CP") -> None:
        self._defaults = {
            "fleet": default_fleet,
            "stationCategory": default_station,
            "crewType": default_crew,
        }

    def decide(self, prompt: str) -> OrchestratorParams:
        p = (prompt or "").lower()

        fleet = (
            "Airbus" if "airbus" in p else
            "ATR" if "atr" in p else
            self._defaults["fleet"]
        )
        station = (
            "Metro" if "metro" in p else
            "Non-Metro" if "non-metro" in p or "nonmetro" in p else
            self._defaults["stationCategory"]
        )
        crew = (
            "CP" if "cp" in p else
            "FO" if "fo" in p else
            "CC" if "cc" in p else
            self._defaults["crewType"]
        )

        params = {"fleet": fleet, "stationCategory": station, "crewType": crew}
        self._validate(params)
        return OrchestratorParams(**params)

    def _validate(self, params: Dict[str, str]) -> None:
        if params["fleet"] not in _ALLOWED_FLEETS:
            raise ValueError(f"Unsupported fleet: {params['fleet']}")
        if params["stationCategory"] not in _ALLOWED_STATIONS:
            raise ValueError(f"Unsupported stationCategory: {params['stationCategory']}")
        if params["crewType"] not in _ALLOWED_CREW_TYPES:
            raise ValueError(f"Unsupported crewType: {params['crewType']}")
