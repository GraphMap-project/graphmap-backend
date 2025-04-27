import csv

from sqlmodel import Session
from models.settlement import Settlement
from sqlalchemy import select, func

VALID_SETTLEMENT_TYPES = ['PPL', 'PPLA', 'PPLA2',
                          'PPLA3', 'PPLA4', 'PPLC', 'PPLX', 'PPLF']


def load_settlements_from_geonames(session: Session):
    settlements_count = session.exec(
        select(func.count(Settlement.id))).one()[0]
    if settlements_count > 0:
        print(
            f"Skipped loading settlements: Settlements table currently contains {settlements_count} records.")
        return

    print("No settlements found, loading from cities.txt...")
    csv_file = "cities.txt"

    with open(csv_file, 'r', encoding="utf-8") as file:
        reader = csv.reader(file, delimiter='\t')
        for row in reader:
            geoname_id, name, _, _, lat, lon, *_ = row

            settlement = Settlement(
                geoname_id=int(geoname_id),
                name=name,
                lat=float(lat),
                lon=float(lon),
                type=row[7],
            )

            session.add(settlement)
        session.commit()
        print(f"Loaded settlements successfully.")


def find_nearest_settlement(session: Session, lat: float, lon: float, radius_km: float = 10) -> str | None:
    """Пошук найближчого міста до даних координат"""

    earth_radius_km = 6371

    distance_expr = (
        earth_radius_km * func.acos(
            func.cos(func.radians(lat)) *
            func.cos(func.radians(Settlement.lat)) *
            func.cos(func.radians(Settlement.lon) - func.radians(lon)) +
            func.sin(func.radians(lat)) *
            func.sin(func.radians(Settlement.lat))
        )
    )

    stmt = (
        select(Settlement.name)
        .where(Settlement.type.in_(VALID_SETTLEMENT_TYPES))
        .order_by(distance_expr)
        .limit(1)
    )

    result = session.exec(stmt).first()
    if result:
        return result[0]
    return None
