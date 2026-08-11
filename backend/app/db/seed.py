"""Dev/demo seed: 1 company, 2 plants, 6 lines, 10 machines (visual
inspection systems), QR tokens per machine, 4 users (one per key role),
and known_errors for the machine type. Idempotent — re-running skips work
if the demo company already exists.

Run via `make seed` (executes inside the api container).
"""

import asyncio
from datetime import date

from passlib.context import CryptContext
from sqlalchemy import select

from app.core.security import generate_qr_token
from app.db.engine import AsyncSessionLocal
from app.db.enums import IssueCategory, MachineType, OsType, TicketPriority, UserRole
from app.db.models import Company, KnownError, Line, Machine, Plant, QrToken, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COMPANY_CODE = "JBM"

KNOWN_ERROR_SEEDS: list[dict] = [
    {
        "category": IssueCategory.camera_image,
        "title": "Camera feed blank/black",
        "error_signature": (
            r"(?i)(no\s*video\s*signal|camera\s*disconnected|frame\s*grab\s*timeout)"
        ),
        "probable_cause": "Camera cable loose or camera lost power.",
        "operator_fix_steps": (
            "1. Check the camera cable is firmly connected.\n"
            "2. Check the camera's LED is lit.\n"
            "3. If dark, power-cycle the camera unit only."
        ),
        "severity": TicketPriority.high,
    },
    {
        "category": IssueCategory.connectivity,
        "title": "Vision inspection engine cannot reach API server",
        "error_signature": (
            r"(?i)(connection\s*refused|api\s*unreachable|network\s*is\s*unreachable)"
        ),
        "probable_cause": "Network link to the central server is down.",
        "operator_fix_steps": (
            "1. Check the network switch LED lights.\n"
            "2. Check the router/SIM signal light.\n"
            "3. Note the error text shown on screen."
        ),
        "severity": TicketPriority.medium,
    },
    {
        "category": IssueCategory.app_crash,
        "title": "Vision inspection service crashed",
        "error_signature": r"(?i)(segmentation\s*fault|process\s*exited|vision-engine.*crash)",
        "probable_cause": "Inspection engine process terminated unexpectedly.",
        "operator_fix_steps": (
            "1. Power-cycle the inspection controller unit.\n"
            "2. Wait 2 minutes and check if the camera LED turns steady green."
        ),
        "severity": TicketPriority.high,
    },
    {
        "category": IssueCategory.camera_image,
        "title": "Lens obstruction / dirty glass",
        "error_signature": r"(?i)(low\s*image\s*contrast|lens\s*obstruction|blurred\s*frame)",
        "probable_cause": "Dust, oil mist, or debris on the camera lens.",
        "operator_fix_steps": (
            "1. Clean the camera glass gently with a dry microfiber cloth.\n"
            "2. Confirm the LED turns green after cleaning."
        ),
        "severity": TicketPriority.low,
    },
    {
        "category": IssueCategory.data_mismatch,
        "title": "Part count mismatch vs PLC counter",
        "error_signature": r"(?i)(part\s*count\s*mismatch|counter\s*out\s*of\s*sync)",
        "probable_cause": "PLC trigger or conveyor sensor misaligned.",
        "operator_fix_steps": (
            "1. Note the error text on screen.\n"
            "2. Check sensor cable connections are seated.\n"
            "3. Do not adjust the sensor position yourself."
        ),
        "severity": TicketPriority.medium,
    },
    {
        "category": IssueCategory.hardware,
        "title": "Reject gate / actuator not responding",
        "error_signature": (r"(?i)(actuator\s*offline|reject\s*gate\s*not\s*responding)"),
        "probable_cause": "Actuator lost power or cable fault.",
        "operator_fix_steps": (
            "1. Check the actuator junction box cable.\n2. Check the actuator's status LED."
        ),
        "severity": TicketPriority.high,
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Company).where(Company.code == COMPANY_CODE))
        if existing:
            print(f"Seed data already present (company {COMPANY_CODE}); skipping.")
            return

        company = Company(
            code=COMPANY_CODE,
            name="JBM",
            contact_name="Ramesh Iyer",
            contact_phone="+919800000001",
            contact_email="ramesh.iyer@example.com",
        )
        session.add(company)
        await session.flush()

        plant1 = Plant(
            company_id=company.id,
            code="JBM-3XO-NSK",
            name="3xo Nashik",
            address="MIDC, Nashik, Maharashtra",
            latitude=19.9975,
            longitude=73.7898,
        )
        plant2 = Plant(
            company_id=company.id,
            code="JBM-3XO-PNQ",
            name="3xo Pune",
            address="MIDC, Pune, Maharashtra",
            latitude=18.5204,
            longitude=73.8567,
        )
        session.add_all([plant1, plant2])
        await session.flush()

        lines: list[Line] = []
        for plant in (plant1, plant2):
            for line_number in (1, 2, 3):
                lines.append(
                    Line(
                        plant_id=plant.id,
                        line_number=line_number,
                        name=f"Line {line_number}",
                    )
                )
        session.add_all(lines)
        await session.flush()

        # 10 machines, all visual inspection: 4 line-level per plant (8 total)
        # + 1 plant-level machine per plant (2 total) = 10.
        machines: list[Machine] = []
        plant_lines = {plant1.id: lines[0:3], plant2.id: lines[3:6]}
        for plant in (plant1, plant2):
            plant_code = plant.code
            for i in range(4):
                line = plant_lines[plant.id][i % 3]
                machines.append(
                    Machine(
                        plant_id=plant.id,
                        line_id=line.id,
                        machine_type=MachineType.VISUAL_INSPECTION,
                        name=f"VI {10 + i} parts inspection system - {plant_code}",
                        hostname=f"vi{10 + i}-{plant_code.lower()}-l{line.line_number}",
                        os=OsType.linux,
                        app_version="1.4.2",
                        device_model="Basler ace2",
                        log_labels={
                            "plant": plant_code,
                            "line": str(line.line_number),
                            "machine": f"vi{10 + i}",
                        },
                        installed_at=date(2024, 6, 1),
                    )
                )
            # one plant-level machine, no line
            machines.append(
                Machine(
                    plant_id=plant.id,
                    line_id=None,
                    machine_type=MachineType.VISUAL_INSPECTION,
                    name=f"VI 99 final inspection system - {plant_code}",
                    hostname=f"vi99-{plant_code.lower()}-final",
                    os=OsType.linux,
                    app_version="2.1.0",
                    device_model="Vision Edge Server R2",
                    log_labels={"plant": plant_code, "machine": "vi99"},
                    installed_at=date(2024, 6, 1),
                )
            )
        session.add_all(machines)
        await session.flush()

        qr_tokens = [
            QrToken(machine_id=machine.id, token=generate_qr_token()) for machine in machines
        ]
        session.add_all(qr_tokens)

        users = [
            User(
                phone="+919800000010",
                full_name="Operator One",
                role=UserRole.operator,
                language="en",
            ),
            User(
                phone="+919800000011",
                full_name="Field Tech / Plant Manager",
                role=UserRole.plant_manager,
                language="en",
            ),
            User(
                email="support@example.com",
                full_name="Support L2 Engineer",
                role=UserRole.support_l2,
                password_hash=pwd_context.hash("password123"),
                language="en",
            ),
            User(
                email="admin@example.com",
                full_name="Platform Admin",
                role=UserRole.admin,
                password_hash=pwd_context.hash("password123"),
                language="en",
            ),
        ]
        session.add_all(users)

        known_errors = [
            KnownError(
                machine_type=MachineType.VISUAL_INSPECTION,
                category=spec["category"],
                title=spec["title"],
                error_signature=spec["error_signature"],
                probable_cause=spec["probable_cause"],
                operator_fix_steps=spec["operator_fix_steps"],
                severity=spec["severity"],
            )
            for spec in KNOWN_ERROR_SEEDS
        ]
        session.add_all(known_errors)

        await session.commit()
        print(
            f"Seeded: 1 company, 2 plants, {len(lines)} lines, {len(machines)} machines, "
            f"{len(qr_tokens)} QR tokens, {len(users)} users, {len(known_errors)} known_errors."
        )


if __name__ == "__main__":
    asyncio.run(seed())
