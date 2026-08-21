from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json

from .ephemeris import RealEphemeris
from .detector import detect_sign_changes
from .future_transits import find_major_transits
from .rules import SIGN_HI, PLANET_HI
from content_engine.script import build_daily_script


OUT = Path("output")
OUT.mkdir(exist_ok=True)
IST = ZoneInfo("Asia/Kolkata")


def format_position(position):
    planet = PLANET_HI.get(position.planet, position.planet)
    sign = SIGN_HI[position.sign_index]
    retrograde = " (वक्री)" if position.retrograde else ""
    return f"{planet}: {position.longitude:.2f}° {sign}{retrograde}"


def build_report(now, positions, events, target_date):
    lines = []
    lines.append(f"दैनिक ग्रह स्थिति रिपोर्ट — {target_date.strftime('%d-%m-%Y')} (अगले दिन का प्रकाशन)")
    lines.append("")
    lines.append("निर्धारित ग्रह स्थिति:")
    lines.append("")
    for position in positions:
        lines.append(format_position(position))
    lines.append("")
    lines.append("अगले दिन के महत्वपूर्ण ग्रह परिवर्तन:")
    if events:
        for event in events:
            lines.append(f"- {event.description_hi}")
    else:
        lines.append("अगले दिन किसी ग्रह का प्रमुख राशि परिवर्तन नहीं पाया गया।")
    return "\n".join(lines)


def run():
    run_time_ist = datetime.now(IST)
    target_date = run_time_ist.date() + timedelta(days=1)
    target_noon = datetime.combine(target_date, datetime.min.time(), tzinfo=IST).replace(hour=12)
    previous_noon = target_noon - timedelta(days=1)

    backend = RealEphemeris()
    current_positions = backend.positions(target_noon)
    previous_positions = backend.positions(previous_noon)
    events = detect_sign_changes(previous_positions, current_positions)

    report = build_report(run_time_ist, current_positions, events, target_date)
    report_file = OUT / "planetary_report.txt"
    report_file.write_text(report, encoding="utf-8")

    script = build_daily_script(target_noon, current_positions, events)
    script_file = OUT / "daily_script.md"
    script_file.write_text(script, encoding="utf-8")

    # Find all major transits occurring in the next seven days and mark the
    # exact calendar date on which their seven-day advance video should go live.
    future = find_major_transits(run_time_ist, days=7)
    future_file = OUT / "future_transits.json"
    future_file.write_text(json.dumps({
        "generated_at_ist": run_time_ist.isoformat(),
        "lead_days": 7,
        "major_planets": ["Jupiter", "Saturn", "Rahu", "Ketu", "Mars", "Mercury", "Venus"],
        "events": future,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    publish_today = run_time_ist.date().isoformat()
    lead_events = [e for e in future if e["publish_on_ist"] == publish_today]
    lead_file = OUT / "transit_publish_queue.json"
    lead_file.write_text(json.dumps({
        "publish_date_ist": publish_today,
        "lead_days": 7,
        "events": lead_events,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 70)
    print("REAL PLANETARY ENGINE")
    print("=" * 70)
    print(report)
    print("=" * 70)
    print(f"Generated next-day content for: {target_date.isoformat()}")
    print(f"Generated future transit schedule: {future_file}")
    print(f"Seven-day transit videos due tonight: {len(lead_events)}")
    for event in lead_events:
        print(f"TRANSIT ALERT: {event['description_hi']} on {event['occurrence_ist']}")
    print(f"Generated: {report_file}")
    print(f"Generated: {script_file}")


if __name__ == "__main__":
    run()
