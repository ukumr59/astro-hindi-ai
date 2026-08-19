from datetime import datetime, timedelta, timezone
from pathlib import Path

from .ephemeris import RealEphemeris
from .detector import detect_sign_changes
from .rules import SIGN_HI, PLANET_HI
from content_engine.script import build_daily_script


OUT = Path("output")
OUT.mkdir(exist_ok=True)


def format_position(position):
    planet = PLANET_HI.get(
        position.planet,
        position.planet
    )

    sign = SIGN_HI[position.sign_index]

    retrograde = " (वक्री)" if position.retrograde else ""

    return (
        f"{planet}: "
        f"{position.longitude:.2f}° "
        f"{sign}{retrograde}"
    )


def build_report(now, positions, events):
    lines = []

    lines.append(
        f"दैनिक ग्रह स्थिति रिपोर्ट — "
        f"{now.strftime('%d-%m-%Y %H:%M UTC')}"
    )

    lines.append("")
    lines.append("वर्तमान ग्रह स्थिति:")
    lines.append("")

    for position in positions:
        lines.append(
            format_position(position)
        )

    lines.append("")
    lines.append("आज के महत्वपूर्ण ग्रह परिवर्तन:")

    if events:

        for event in events:

            lines.append(
                f"- {event.description_hi}"
            )

    else:

        lines.append(
            "आज किसी ग्रह का प्रमुख राशि परिवर्तन "
            "नहीं पाया गया।"
        )

    return "\n".join(lines)


def run():

    now = datetime.now(timezone.utc)

    backend = RealEphemeris()

    current_positions = backend.positions(
        now
    )

    previous_positions = backend.positions(
        now - timedelta(days=1)
    )

    events = detect_sign_changes(
        previous_positions,
        current_positions
    )

    report = build_report(
        now,
        current_positions,
        events
    )

    report_file = OUT / "planetary_report.txt"

    report_file.write_text(
        report,
        encoding="utf-8"
    )

    script = build_daily_script(
        now,
        current_positions,
        events
    )

    script_file = OUT / "daily_script.md"

    script_file.write_text(
        script,
        encoding="utf-8"
    )

    print("=" * 70)
    print("REAL PLANETARY ENGINE")
    print("=" * 70)
    print(report)
    print("=" * 70)
    print(
        f"Generated: {report_file}"
    )
    print(
        f"Generated: {script_file}"
    )


if __name__ == "__main__":
    run()
