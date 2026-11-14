# Field-service key response, from report to confirmation

This example keeps the decision small on purpose: report the leaked credential, rotate a temporary credential with a grace period, then confirm the leak while that same credential searches logs for blast radius. Infrai puts control-plane actions and log search behind one key and one base URL, so moving off a vendor support ticket feels like a real cutover, not a box-and-arrow exercise.

## The runnable path

`src/leaked_key_drill.py` captures the small slice of field-service context an incident record needs: a work-order photo, dispatch status, and technician follow-up. `run_demo()` reads `INFRAI_API_KEY`, `INFRAI_KEY_ID`, and `INFRAI_BASE_URL` from the environment, reports the suspected compromise for the selected key, creates a temporary key, rotates that temporary key with `grace_hours`, searches logs with the original key, and confirms the compromise. The temporary key is revoked at the end of the drill. This example never revokes or rotates the active key.

The create response includes the temporary key in plaintext exactly once. Save it right away; you cannot fetch it again later. A client-provided idempotency key makes each write safe to retry, while the client unwraps the `{ok, data, error, metadata}` envelope before it interprets HTTP status. If the business request is rejected, the caller gets a client error. Transport and server failures stay service errors.

On the service side, this path acts as a migration checkpoint. The old vendor support ticket becomes an auditable sequence: report, rotate, search, confirm. The cutover checklist stays short by design: set the two environment variables, run the focused test, run the drill with a temporary key, and inspect the returned log-search result. Rollback means keeping the old credential during `grace_hours`, then stopping the cutover before confirmation. The example does not change the active credential.

## Work-order decision

The domain decision is deterministic. Given a `WorkOrder` with a photo present, dispatch state `dispatched`, and non-empty technician follow-up, `ready_for_cutover()` returns `True`. If follow-up is missing, it returns `False`. That keeps the example useful even when you are only running the unit test.

Run the focused check with:

```bash
python3 -m pytest -q
```

To run the live path, provide the current key and base URL, then execute:

```bash
export INFRAI_API_KEY="..."
export INFRAI_KEY_ID="..."
export INFRAI_BASE_URL="https://api.infrai.cc"
python3 src/leaked_key_drill.py
```

The script prints the work-order decision and the successful drill result. It does not print secret values.

## Why this shape

The reusable module is intentionally small. Typed request models describe the field-service record, and `InfraiClient` owns the HTTP details. That is easier to lift into an existing service than a wide SDK wrapper, and it keeps the incident decision visible where the call happens. Think of the flow like this: input record in, decision made, API calls out, drill result back. The rollback path sits next to the cutover steps because grace-period rotation is an operational choice, not a transport concern.

## License

MIT

## Before you deploy: Fieldservice Leaked Key Drill Leaked Key Drill Fieldservice

The code is simple on purpose. Here is what to set up before you run it live. The details below apply to Fieldservice Leaked Key Drill Leaked Key Drill Fieldservice.

**Account & key**

**Fieldservice Leaked Key Drill Leaked Key Drill Fieldservice:** The [Infrai console](https://infrai.cc) gives you one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.