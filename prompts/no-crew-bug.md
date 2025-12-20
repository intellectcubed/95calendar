## Bug Summary

The 95 calendar service incorrectly handles a squad transitioning from **No Crew** to **Active Crew for a partial shift** when the squad already exists on the physical calendar. As a result, calling `addCrew` does not update the schedule as expected unless the squad is fully removed from the calendar first.

---

## Actors

* **Squad 35**
* **Squad 42**

---

## Initial State

* Both Squad 35 and Squad 42 are scheduled for a shift from **18:00–06:00**
* Territories are initially assigned to both squads
* The physical calendar reflects both squads on duty

---

## Step-by-Step Reproduction

1. **Initial Schedule**

   * Squad 35: 18:00–06:00 (with crew)
   * Squad 42: 18:00–06:00 (with crew)
   * Territories assigned normally

2. **Squad 35 switches to No Crew**

   * Squad 35 changes status to **No Crew** for the entire shift
   * As a result:

     * Squad 42 is assigned **all territories**
     * Squad 35 remains listed on the physical calendar, but with a "No Crew" designation

3. **Squad 35 regains crew for partial shift**

   * Squad 35 indicates they will have a crew from **22:00–06:00**
   * `addCrew(35, 22:00–06:00)` is invoked

4. **Observed Behavior (Bug)**

   * The calendar is **not updated**
   * Squad 35 is not restored for 22:00–06:00
   * Territories remain unchanged

5. **Workaround That Works**

   * Remove Squad 35 entirely from the physical calendar
   * Calendar now shows only Squad 42 covering all territories
   * Invoke `addCrew(35, 22:00–06:00)`
   * This time, the calendar updates correctly

6. **Problem With the Workaround**

   * Removing Squad 35 loses the fact that Squad 35 was originally scheduled for the shift
   * This historical scheduling information is important and should be preserved

---

## Why This Happens (Root Cause Analysis)

### How the 95 Calendar Service Works

1. Crews are assigned to shifts first (day + start/end times)
2. Territories are assigned later
3. Internally, the service:

   * Builds a **time × squad matrix**

     * Y-axis: time slots
     * X-axis: squads
   * Fills the matrix based only on start/end times
   * Later collapses the matrix into a summarized schedule
   * Finally applies territory assignments

### Example

If Squads 35 and 42 are scheduled from 08:00–10:00:

* Matrix contains:

  * 08:00 → 35, 42
  * 09:00 → 35, 42
  * 10:00 → 35, 42
* Collapsed summary:

  * 08:00–10:00 → 35, 42
* Territories are assigned afterward

---

## Actual Bug Logic

* When Squad 35 is marked **No Crew**, it is still:

  * Present on the physical calendar
  * Converted into an internal object with `active = false`
* During matrix construction:

  * The **active flag is ignored**
  * Territory assignments are also ignored at this stage
  * Squad 35 is still expanded into the matrix for all time slots
* When `addCrew(35, 22:00–06:00)` is called:

  * The logic sees Squad 35 already present in the matrix
  * No changes are made
  * The update is silently ignored

---

## Root Cause

The translation from **physical calendar → internal object** correctly sets an `active` flag, but:

> **The matrix-building logic does not respect the `active` flag and expands inactive (No Crew) squads into the matrix.**

---

## Expected Behavior

* Squads marked as **inactive / No Crew** should:

  * Not be expanded into the internal matrix
  * Be eligible for reactivation via `addCrew` without requiring removal from the calendar
* Historical scheduling information should be preserved

---

## Suggested Fix

### Required Change

When building the internal time × squad matrix:

* **Exclude squads where `active === false`**
* Only expand squads that are actively crewed for the given time range

### Implementation Guidance

One of the following must be enforced consistently:

1. Filter inactive squads **before** matrix expansion
2. Or treat inactive squads as non-existent for matrix purposes
3. Or make `addCrew` explicitly re-activate inactive squads already present on the calendar

### Preferred Solution

Respect the `active` flag during matrix construction.
This aligns with the intended data model and avoids destructive calendar edits.

---

## Impact

* Fixes partial-shift crew restoration
* Preserves historical scheduling
* Prevents silent failures in `addCrew`
* Makes calendar state transitions consistent and predictable
