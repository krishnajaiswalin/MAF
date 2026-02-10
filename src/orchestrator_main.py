import argparse
import json
import os
from typing import Dict, Any

import pandas as pd

from agents.orchestrator import OrchestratorAgent

METRO_AIRPORTS = {"DEL", "BOM", "BLR", "HYD", "MAA", "CCU", "PNQ", "COK", "GOI"}


def run(prompt: str) -> dict:
    agent = OrchestratorAgent()
    params = agent.decide(prompt)
    return {
        "fleet": params.fleet,
        "stationCategory": params.stationCategory,
        "crewType": params.crewType,
    }


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["PairingStartDate", "DutyDay", "STD", "STA", "ATD", "ATA", "Reporting", "Debrief"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    return df


def _station_category(dep: str) -> str:
    code = (dep or "").strip().upper()
    return "Metro" if code in METRO_AIRPORTS else "Non-Metro"


def _crew_type_from_pos(pos_val: Any) -> str:
    try:
        iv = int(pos_val)
        return "CP" if iv == 1 else ("FO" if iv == 2 else "CC")
    except Exception:
        return "CP"  # default


def load_and_filter_roster(excel_path: str, date_from: str, date_to: str, params: Dict[str, str]) -> pd.DataFrame:
    df = pd.read_excel(excel_path, engine="openpyxl")
    df = _parse_dates(df)

    # Date filter: use DutyDay if present, else PairingStartDate
    date_col = "DutyDay" if "DutyDay" in df.columns else ("PairingStartDate" if "PairingStartDate" in df.columns else None)
    if date_col is None:
        raise ValueError("Roster Excel must include DutyDay or PairingStartDate column")

    start_dt = pd.to_datetime(date_from, errors="coerce")
    end_dt = pd.to_datetime(date_to, errors="coerce")
    if pd.isna(start_dt) or pd.isna(end_dt):
        raise ValueError("Invalid --from/--to date; expected YYYY-MM-DD")

    df = df[(df[date_col] >= start_dt) & (df[date_col] <= end_dt)]

    # Fleet filter
    if "Fleet" in df.columns:
        df = df[df["Fleet"].astype(str).str.contains(params["fleet"], case=False, na=False)]

    # Station Category filter via DEP code
    if "DEP" in df.columns:
        df["StationCategory"] = df["DEP"].astype(str).str.strip().str.upper().map(lambda x: _station_category(x))
        df = df[df["StationCategory"] == params["stationCategory"]]

    # Crew type filter via Pos column if available
    if "Pos" in df.columns:
        df["CrewType"] = df["Pos"].map(_crew_type_from_pos)
        df = df[df["CrewType"] == params["crewType"]]

    # Keep a clean subset of useful columns
    cols = [c for c in [
        "Publact","ID","CWBASE","Pos","PairingStartDate","DutyDay","TripCode","DutyCode","FLT",
        "DEP","DEPTERM","ARR","ARRTERM","STD","STA","ATD","ATA","REG","PAX","DHD","DOM_INT",
        "Fleet","FleetType","Subfleet","FType","Fstatus","TRNFACIL","TrainingIndicator","Seq","Seq1",
        "Reporting","Debrief","Tabindex","PairingStartDEP","StationCategory","CrewType"
    ] if c in df.columns]

    return df[cols].reset_index(drop=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Orchestrator Agent and filter roster Excel")
    parser.add_argument("--prompt", type=str, required=True, help="Prompt containing fleet/station/crew")
    parser.add_argument("--excel", type=str, required=True, help="Path to roster Excel file")
    parser.add_argument("--from", dest="date_from", type=str, required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", type=str, required=True, help="End date YYYY-MM-DD")
    args = parser.parse_args()

    params = run(args.prompt)
    print("[Orchestrator]", params)

    filtered = load_and_filter_roster(args.excel, args.date_from, args.date_to, params)
    print(f"[Filter] rows={len(filtered)} cols={list(filtered.columns)}")

    os.makedirs("out", exist_ok=True)
    filtered_path = "out/filtered_roster.csv"
    filtered.to_csv(filtered_path, index=False)
    with open("out/orchestrator_params.json", "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
    print(f"[Output] Saved: {filtered_path} and out/orchestrator_params.json")
