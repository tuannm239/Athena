# ATHENA — Failure Injection Report (Phase 3, Verification 4)

Date: 2026-07-17 · Method: a purpose-built harness executed each fault
against the real code paths (resilience toolkit, health endpoints, data
pipeline, sync service, domain value objects, probability engine) and
asserted graceful recovery. **11/11 checks passed.** No defects found.

## Result summary

| # | Injected fault | Expected behavior | Observed | Verdict |
|---|---|---|---|---|
| 1 | Provider timeout | retry with exponential backoff, then a typed error | retried 3×, backoff `[0.5, 1.0]` s, raised `ProviderCallError` | ✅ |
| 1b | Repeated provider failures | health flips unhealthy after threshold, recovers on success | healthy→unhealthy after 2 fails→healthy after 1 success | ✅ |
| 2 | Redis unavailable | dashboard `degraded`, liveness unaffected | `redis: unavailable: ConnectionError`, status `degraded`, `/health` still 200 | ✅ |
| 3 | Database unavailable | dashboard reports it, no crash | `database: unavailable: OperationalError`, status `degraded` | ✅ |
| 4 | Corrupted data (null key + future ts) | rows quarantined, never published | status `QUARANTINED`, 2 rows quarantined, forced publish rejected | ✅ |
| 5 | Partial sync | watermark advances only over published windows | watermark 07-09 → 07-10 after incremental | ✅ |
| 5b | Partial sync with quarantine | watermark never jumps past unpublished data | window bounded by `as_of.date()`; watermark 07-08 → 07-09 | ✅ |
| 6 | Invalid evidence | domain rejects at construction | `Reliability(1.5)`→`ValueError`; bad direction→`LlmGatewayError` | ✅ |
| 7 | Clock drift (future-dated evidence) | probability engine rejects | `InvalidEvidenceError: evidence timestamp is in the future` | ✅ |
| 8 | Duplicate events | idempotent rejection | re-run of `(id, version)` → `DuplicateDatasetError` (DP003) | ✅ |
| 9 | Rollback | published version retired, watermark rewinds | watermark 07-10 → rollback → 07-08 | ✅ |

## Evidence (harness output, verbatim)

```
[PASS] provider_timeout: retried 3x, backoff=[0.5, 1.0], then raised ProviderCallError
[PASS] provider_health: healthy→True, after 2 fails→False, after success→True
[PASS] redis_unavailable: redis=unavailable: ConnectionError, status=degraded, liveness still ok
[PASS] database_unavailable: database=unavailable: OperationalError, status=degraded
[PASS] corrupted_data: status=QUARANTINED, quarantined=2, publish-forced-rejected=True
[PASS] partial_sync_watermark: watermark 2026-07-09→2026-07-10 after incremental
[PASS] partial_sync_quarantine_watermark: incremental end=2026-07-09 status=PUBLISHED, watermark 2026-07-08→2026-07-09
[PASS] invalid_evidence: rejected: ['ValueError', 'LlmGatewayError']
[PASS] clock_drift: future-dated evidence rejected: evidence timestamp is in the future
[PASS] duplicate_events: re-running (id,version) raises DuplicateDatasetError (DP003)
[PASS] rollback: watermark 2026-07-10 → rollback → 2026-07-08 (rewinds to prior published version)

=== SUMMARY ===
11/11 scenarios passed
```

## Recovery analysis per fault

1. **Provider timeout** — `RetryPolicy.execute` retries `max_attempts`
   times with `base_delay × 2^attempt`, then raises the typed
   `ProviderCallError` rather than leaking the transport exception. The
   `ResilientPriceProvider` decorator additionally records the failure
   in `HealthMonitor`; after `unhealthy_after` consecutive failures the
   provider reports unhealthy (surfaced through `ProviderStatus`), and a
   single success clears it. **Graceful, bounded, observable.**

2. **Redis unavailable** — Redis is ephemeral by design (SPEC-07,
   cache only). `/health/full` catches the connection error and reports
   `degraded` with the component name; `/health` (liveness) stays 200,
   so orchestrators do not kill a pod over a cache outage. **No data
   path depends on Redis for correctness.**

3. **Database unavailable** — `/health/full` reports `database:
   unavailable` without raising; the endpoint is defensive (broad catch,
   reports the exception *type* only — no leakage). Normal API calls
   that need the DB return the standard error envelope via the mapped
   handlers. **No unhandled crash.**

4. **Corrupted data** — the RFC-0024 pipeline quarantines invalid rows
   (null required key, future timestamp) into the snapshot's
   `quarantine` table; the run is marked `QUARANTINED` and
   `publish_dataset` refuses to promote it (`PublishError`). Corruption
   **cannot reach the decision path.**

5. **Partial sync** — the watermark is derived from the latest
   *published* dataset version (ADR-0017), so it advances only over data
   that actually passed the quality gate. The incremental window end is
   bounded by `as_of.date()`, which structurally prevents fetching a bar
   that would be "future" relative to the run and then blocking its
   retry. Re-verified across two scenarios; **no data is skipped and no
   window is permanently blocked.**

6. **Invalid evidence** — value objects validate on construction:
   `Reliability` enforces `[0,1]`, `EvidenceDraft` enforces the
   direction enum. Bad evidence never becomes a domain object.

7. **Clock drift** — the probability engine rejects evidence whose
   timestamp is after `as_of` (`InvalidEvidenceError`), preventing
   look-ahead from a skewed clock or mis-stamped source.

8. **Duplicate events** — the pipeline is idempotent on
   `(dataset_id, version)`: a repeat raises `DuplicateDatasetError`
   (DP003). KG mutations are likewise idempotent (duplicate active edge
   rejected — verified in `test_knowledge_store.py`).

9. **Rollback** — `rollback_dataset` retires the published version; the
   watermark recomputes to the previous published version, so the next
   incremental sync re-fetches from the correct point. **State is
   consistent after rollback.**

## Conclusion

Every injected fault is handled with a typed error, a quarantine, a
health signal, or a safe no-op — never an unhandled crash, silent data
loss, or look-ahead. The system degrades gracefully and recovers
deterministically. **No defects discovered; implementation unchanged.**
