# Testing messages for manual command line testing of calendar_commands.py



```shell
curl 'http://localhost:8000/?action=addShift&date=20260315&&shift_start=0700&shift_end=0800&squad=43&preview=True'
curl 'http://localhost:8000/?action=addShift&date=20260315&&shift_start=0700&shift_end=0800&squad=43&preview=False'
curl 'http://localhost:8000/?action=noCrew&date=20260315&&shift_start=0700&shift_end=0800&squad=43&preview=False'
curl 'http://localhost:8000/?action=obliterateShift&date=20260315&&shift_start=0700&shift_end=0800&squad=43&preview=False'
```

# Add 11-12 35 (Preview)
```shell
curl -X POST http://localhost:8000/calendar/day/20260315/preview \
  -H 'Content-Type: application/json' \
  -d '{"action": "addShift", "date": "20260315", "shift_start": "1100", "shift_end": "1200", "squad": 42, "day_schedule": "{\"day\": \"Sunday 2026-03-15\", \"shifts\": [{\"name\": \"Night Shift\", \"start_time\": \"18:00\", \"end_time\": \"06:00\", \"segments\": [{\"start_time\": \"18:00\", \"end_time\": \"06:00\", \"squads\": [{\"id\": 42, \"territories\": [35, 42, 54], \"active\": true}, {\"id\": 43, \"territories\": [34, 43], \"active\": true}]}], \"tango\": 42}, {\"name\": \"06:00 - 07:00 Shift\", \"start_time\": \"06:00\", \"end_time\": \"07:00\", \"segments\": [{\"start_time\": \"06:00\", \"end_time\": \"07:00\", \"squads\": [{\"id\": 54, \"territories\": [34, 35, 42, 43, 54], \"active\": true}]}], \"tango\": 54}, {\"name\": \"07:00 - 08:00 Shift\", \"start_time\": \"07:00\", \"end_time\": \"08:00\", \"segments\": [{\"start_time\": \"07:00\", \"end_time\": \"08:00\", \"squads\": [{\"id\": 43, \"territories\": [34, 43], \"active\": true}, {\"id\": 54, \"territories\": [35, 42, 54], \"active\": true}]}], \"tango\": 43}, {\"name\": \"08:00 - 18:00 Shift\", \"start_time\": \"08:00\", \"end_time\": \"18:00\", \"segments\": [{\"start_time\": \"08:00\", \"end_time\": \"18:00\", \"squads\": [{\"id\": 54, \"territories\": [34, 35, 42, 43, 54], \"active\": true}]}], \"tango\": 54}]}"}'
```

# Take response and now we post it (apply)
```shell
curl -X POST http://localhost:8000/calendar/day/20260315/apply \
  -H 'Content-Type: application/json' \
  -d '{"DaySchedule": "{\"day\": \"Sunday 2026-03-15\", \"shifts\": [{\"name\": \"Night Shift\", \"start_time\": \"18:00\", \"end_time\": \"06:00\", \"segments\": [{\"start_time\": \"18:00\", \"end_time\": \"06:00\", \"squads\": [{\"id\": 42, \"territories\": [35, 42, 54], \"active\": true}, {\"id\": 43, \"territories\": [34, 43], \"active\": true}]}], \"tango\": 42}, {\"name\": \"06:00 - 07:00 Shift\", \"start_time\": \"06:00\", \"end_time\": \"07:00\", \"segments\": [{\"start_time\": \"06:00\", \"end_time\": \"07:00\", \"squads\": [{\"id\": 54, \"territories\": [34, 35, 42, 43, 54], \"active\": true}]}], \"tango\": 54}, {\"name\": \"07:00 - 08:00 Shift\", \"start_time\": \"07:00\", \"end_time\": \"08:00\", \"segments\": [{\"start_time\": \"07:00\", \"end_time\": \"08:00\", \"squads\": [{\"id\": 43, \"territories\": [34, 43], \"active\": true}, {\"id\": 54, \"territories\": [35, 42, 54], \"active\": true}]}], \"tango\": 43}, {\"name\": \"08:00 - 11:00 Shift\", \"start_time\": \"08:00\", \"end_time\": \"11:00\", \"segments\": [{\"start_time\": \"08:00\", \"end_time\": \"11:00\", \"squads\": [{\"id\": 54, \"territories\": [34, 35, 42, 43, 54], \"active\": true}]}], \"tango\": 54}, {\"name\": \"11:00 - 12:00 Shift\", \"start_time\": \"11:00\", \"end_time\": \"12:00\", \"segments\": [{\"start_time\": \"11:00\", \"end_time\": \"12:00\", \"squads\": [{\"id\": 54, \"territories\": [34, 43, 54], \"active\": true}, {\"id\": 42, \"territories\": [35, 42], \"active\": true}]}], \"tango\": 54}, {\"name\": \"12:00 - 18:00 Shift\", \"start_time\": \"12:00\", \"end_time\": \"18:00\", \"segments\": [{\"start_time\": \"12:00\", \"end_time\": \"18:00\", \"squads\": [{\"id\": 54, \"territories\": [34, 35, 42, 43, 54], \"active\": true}]}], \"tango\": 54}]}" }'
```

# Restore a previously saved snapshot
```shell
curl 'http://localhost:8000/?action=rollback&date=20260315&change_id=1167b1f1-d252-4aca-b517-a036f059925c'
```