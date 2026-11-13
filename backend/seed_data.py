"""
CrisisLens Database Seed Script
Populates initial baseline incidents from the API Contract into Supabase.
Allows immediate end-to-end testing with Member 1's frontend.
"""
from app.database.supabase_client import get_supabase_client
from app.utils.datetime_utils import now_utc_iso


def seed_database():
    supabase = get_supabase_client()
    now = now_utc_iso()

    incidents = [
        {
            "id": "inc_001",
            "title": "Flooding near Bellandur lake road",
            "type": "flood",
            "lat": 12.9304,
            "lng": 77.6784,
            "location_label": "Lake Road, Bellandur",
            "severity": "critical",
            "status": "active",
            "report_count": 4,
            "independent_source_count": 3,
            "first_reported_at": "2026-11-11T13:50:00Z",
            "last_updated_at": now,
            "timeline": [
                {
                    "timestamp": "2026-11-11T13:50:00Z",
                    "severity": "medium",
                    "status": "active",
                    "report_count": 1,
                    "affected_radius_m": 200,
                    "summary": "First report of water entering homes"
                },
                {
                    "timestamp": "2026-11-11T14:15:00Z",
                    "severity": "high",
                    "status": "active",
                    "report_count": 2,
                    "affected_radius_m": 400,
                    "summary": "Water level rising, ground floors inundated"
                },
                {
                    "timestamp": "2026-11-11T14:30:00Z",
                    "severity": "critical",
                    "status": "active",
                    "report_count": 4,
                    "affected_radius_m": 600,
                    "summary": "Ward officer on site confirms 1.2 m water, 40 residents stranded"
                }
            ]
        },
        {
            "id": "inc_002",
            "title": "Reported structural collapse, Koramangala",
            "type": "structural",
            "lat": 12.9352,
            "lng": 77.6245,
            "location_label": "4th Block, Koramangala",
            "severity": "high",
            "status": "active",
            "report_count": 3,
            "independent_source_count": 2,
            "first_reported_at": "2026-11-11T14:00:00Z",
            "last_updated_at": now,
            "timeline": [
                {
                    "timestamp": "2026-11-11T14:00:00Z",
                    "severity": "high",
                    "status": "active",
                    "report_count": 1,
                    "affected_radius_m": 100,
                    "summary": "Report of building collapse and trapped persons"
                }
            ]
        },
        {
            "id": "inc_003",
            "title": "Electrical transformer fire, Whitefield",
            "type": "fire",
            "lat": 12.9698,
            "lng": 77.7500,
            "location_label": "Main Road, Whitefield",
            "severity": "medium",
            "status": "monitoring",
            "report_count": 2,
            "independent_source_count": 2,
            "first_reported_at": "2026-11-11T14:10:00Z",
            "last_updated_at": now,
            "timeline": [
                {
                    "timestamp": "2026-11-11T14:10:00Z",
                    "severity": "medium",
                    "status": "monitoring",
                    "report_count": 2,
                    "affected_radius_m": 150,
                    "summary": "Transformer spark and minor fire reported"
                }
            ]
        }
    ]

    print("Seeding incidents into Supabase...")
    for inc in incidents:
        # Upsert incident
        supabase.table("incidents").upsert(inc).execute()
        print(f"  [✓] Seeded incident {inc['id']}: {inc['title']}")

    print("\nDatabase seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
