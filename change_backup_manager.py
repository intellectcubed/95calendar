import csv
import io
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
# This ensures SUPABASE_URL and SUPABASE_KEY are available
load_dotenv()


class ChangeBackupManager:
    """
    A simple versioned backup manager for saving, reverting, and cleaning
    up 10x4 grid snapshots in Supabase.
    """

    def __init__(self, default_ttl_days=30):
        self.ttl_days = default_ttl_days

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise EnvironmentError(
                "❌ Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_KEY."
            )

        self.supabase: Client = create_client(supabase_url, supabase_key)

    # -------------------------
    # Internal utilities
    # -------------------------
    @staticmethod
    def _grid_to_csv(grid):
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerows(grid)
        return buf.getvalue()

    @staticmethod
    def _csv_to_grid(csv_text):
        reader = csv.reader(io.StringIO(csv_text))
        return [row for row in reader]

    # -------------------------
    # Core methods
    # -------------------------
    def save_grid(self, day, grid, description="", command="", ttl_days=None):
        """Save a grid snapshot and return its UUID."""
        ttl = ttl_days or self.ttl_days
        csv_data = self._grid_to_csv(grid)
        expires_at = (datetime.utcnow() + timedelta(days=ttl)).isoformat()

        data = {
            "day": day,
            "description": description,
            "command": command,
            "csv_data": csv_data,
            "expires_at": expires_at,
        }

        res = self.supabase.table("day_snapshots").insert(data).execute()
        snapshot_id = res.data[0]["id"]
        print(f"✅ Saved snapshot {snapshot_id} for day {day}")
        return snapshot_id

    def revert_to_snapshot(self, snapshot_id):
        """Fetch a snapshot by UUID and return its grid."""
        res = (
            self.supabase.table("day_snapshots")
            .select("*")
            .eq("id", str(snapshot_id))
            .execute()
        )
        if not res.data:
            raise ValueError(f"No snapshot found with id {snapshot_id}")
        csv_data = res.data[0]["csv_data"]
        grid = self._csv_to_grid(csv_data)
        print(f"✅ Reverted to snapshot {snapshot_id}")
        return grid

    def cleanup_expired_snapshots(self):
        """Delete snapshots past their TTL (expires_at < now)."""
        now = datetime.utcnow().isoformat()
        res = self.supabase.table("day_snapshots").delete().lt("expires_at", now).execute()
        deleted_count = len(res.data) if res.data else 0
        print(f"🧹 Deleted {deleted_count} expired snapshots.")
        return deleted_count

    def list_snapshots(self, day):
        """List all snapshots for a given day in chronological order."""
        res = (
            self.supabase.table("day_snapshots")
            .select("id, created_at, description, command, expires_at")
            .eq("day", str(day))
            .order("created_at", desc=False)
            .execute()
        )
        snapshots = res.data or []
        print(f"📜 Found {len(snapshots)} snapshots for day {day}")
        return snapshots


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    manager = ChangeBackupManager(default_ttl_days=30)

    # Example grid (10x4)
    grid = [[f"R{r}C{c}" for c in range(4)] for r in range(10)]
    day = "2025-11-12"

    # Save snapshot
    snapshot_id = manager.save_grid(
        day=day,
        grid=grid,
        description="Before daily edit",
        command="update_cells",
    )

    # List snapshots for the day
    snapshots = manager.list_snapshots(day)
    print("All snapshots:")
    for s in snapshots:
        print(f"- {s['created_at']} | {s['id']} | {s['description']}")

    # Revert to last snapshot
    last_id = snapshots[-1]["id"]
    restored_grid = manager.revert_to_snapshot(last_id)
    print("Restored Grid:", restored_grid)

    # Cleanup expired backups
    manager.cleanup_expired_snapshots()
