"""`athena` sync CLI — operational entrypoint for market synchronisation.

Commands:
    athena sync full          # full window resync (SYNC_LOOKBACK_DAYS back)
    athena sync incremental   # only days newer than the last published watermark
    athena sync ensure        # self-heal: full backfill if no readable prices, else incremental
    athena sync market        # indices only — fast; safe every 5-15 min
    athena sync universe      # the configured symbol universe (SYNC_UNIVERSE)
    athena sync symbol FPT    # a single symbol
    athena sync replay --start YYYY-MM-DD --end YYYY-MM-DD
    athena sync status        # health: watermark, provider health, config
    athena provider test      # probe every supported vnstock source
    athena provider datasets  # vnstock dataset capability catalog (SUPPORTED/NOT_SUPPORTED)
    athena provider diagnose  # deep DNS/TCP/TLS + probe diagnostics (observability)

It builds the same persistence the API reads (SqlDatasetCatalog + the
configured snapshot store — SNAPSHOT_BACKEND), resolves the price provider
(default: vnstock, VN market), and drives `MarketSyncScheduler`. It never
fetches data itself — every fetch goes through `ProviderSyncService`.

Configuration (environment):
    SYNC_MODE            FULL | INCREMENTAL | MANUAL   (used by the entrypoint)
    SYNC_TICKERS         comma list; default "VNINDEX,VN30,HOSE,HNX,UPCOM"
    SYNC_LOOKBACK_DAYS   default 365
    SYNC_MAX_RETRIES     default 3
    plus DATABASE_URL / DUCKDB_DIR from the standard Settings.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date

from data_pipeline.application.sync import PRICES_DATASET, ProviderSyncService
from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.scheduler import MarketSyncScheduler
from data_pipeline.tickers import (
    market_scope,
    parse_spec,
    resolve_tickers,
    symbol_scope,
    universe_scope,
)
from infrastructure.config import Settings
from infrastructure.db.engine import build_engine, build_session_factory
from infrastructure.db.repositories.dataset_catalog import SqlDatasetCatalog
from infrastructure.observability import configure_logging
from infrastructure.sql_snapshot_store import build_snapshot_store
from providers.connectors.vnstock_datasets import Support, catalog_as_dicts
from providers.connectors.vnstock_diagnostics import diagnose_hosts
from providers.connectors.vnstock_source import (
    SourceProbe,
    probe_source,
    resolve_source,
    supported_sources,
)
from providers.registry_config import DEFAULT_SELECTION, build_registry
from providers.sdk.ports import PriceProvider
from providers.sdk.registry import Capability


def _resolve_price_provider() -> PriceProvider:
    """The configured market price provider (default vnstock) from the registry."""
    provider = build_registry().resolve(Capability.PRICE, DEFAULT_SELECTION)
    return provider  # type: ignore[return-value]  # registry returns a PriceProvider


def build_scheduler(
    *,
    settings: Settings | None = None,
    provider: PriceProvider | None = None,
    tickers: list[str] | None = None,
) -> MarketSyncScheduler:
    cfg = settings or Settings.from_env()
    sessions = build_session_factory(build_engine(cfg))
    pipeline = DataPipelineUseCases(
        catalog=SqlDatasetCatalog(sessions),
        snapshots=build_snapshot_store(cfg, sessions),
    )
    sync = ProviderSyncService(pipeline=pipeline, source="provider:vnstock")
    resolved = (
        tuple(tickers) if tickers else resolve_tickers(parse_spec(os.environ.get("SYNC_TICKERS")))
    )
    return MarketSyncScheduler(
        sync=sync,
        provider=provider or _resolve_price_provider(),
        tickers=resolved,
        lookback_days=int(os.environ.get("SYNC_LOOKBACK_DAYS", "365")),
        max_retries=int(os.environ.get("SYNC_MAX_RETRIES", "3")),
    )


def _emit(payload: dict[str, object]) -> None:
    """Machine-readable line for cron/log scraping."""
    print(json.dumps(payload, default=str))


def published_prices_present(settings: Settings | None = None) -> bool:
    """True iff the published PRICES snapshot is currently readable and non-empty.

    Uses the *configured* snapshot backend, so it correctly reports "missing"
    when a prior sync wrote to an ephemeral DuckDB file that a restart wiped
    (the catalog watermark can survive while the snapshot data does not).
    """
    cfg = settings or Settings.from_env()
    sessions = build_session_factory(build_engine(cfg))
    pipeline = DataPipelineUseCases(
        catalog=SqlDatasetCatalog(sessions),
        snapshots=build_snapshot_store(cfg, sessions),
    )
    try:
        frame = pipeline.read_published(PRICES_DATASET)
    except Exception:  # noqa: BLE001 — any read failure means "not present"
        return False
    return frame.height > 0


def run_provider_test(
    *, sources: list[str] | None = None, symbol: str = "VCI"
) -> list[SourceProbe]:
    """Probe each requested source (default: every supported source)."""
    targets = [s.strip().lower() for s in sources] if sources else list(supported_sources())
    return [probe_source(s, symbol=symbol) for s in targets]


def _provider_test(args: argparse.Namespace) -> int:
    requested = args.source.split(",") if getattr(args, "source", None) else None
    probes = run_provider_test(sources=requested, symbol=getattr(args, "symbol", None) or "VCI")
    configured = resolve_source(os.environ.get("VNSTOCK_SOURCE"))
    _emit(
        {
            "command": "provider.test",
            "configured_source": configured,
            "supported_sources": list(supported_sources()),
            "results": [p.as_dict() for p in probes],
        }
    )
    # Exit 0 iff the configured source is reachable (the one a sync would use).
    configured_probe = next((p for p in probes if p.source == configured), None)
    return 0 if configured_probe is not None and configured_probe.reachable else 1


def _provider_datasets(args: argparse.Namespace) -> int:
    """Print the vnstock dataset capability catalog (SUPPORTED / NOT_SUPPORTED)."""
    source = resolve_source(getattr(args, "source", None) or os.environ.get("VNSTOCK_SOURCE"))
    rows = catalog_as_dicts(source)
    _emit(
        {
            "command": "provider.datasets",
            "source": source,
            "supported": sum(1 for r in rows if r["support"] == Support.SUPPORTED.value),
            "total": len(rows),
            "datasets": rows,
        }
    )
    return 0


def _provider_diagnose(args: argparse.Namespace) -> int:
    """Deep connectivity diagnostics (DNS/TCP/TLS + a live probe) — fully logged."""
    configured = resolve_source(os.environ.get("VNSTOCK_SOURCE"))
    hosts = diagnose_hosts()
    probe = probe_source(configured, symbol=getattr(args, "symbol", None) or "VCI")
    payload: dict[str, object] = {
        "command": "provider.diagnose",
        "configured_source": configured,
        "hosts": [h.as_dict() for h in hosts],
        "probe": probe.as_dict(),
    }
    _emit(payload)
    # Log each stage as its own line too, so failures are grep-able in the logs.
    log = logging.getLogger("athena.cli.diagnose")
    for host in hosts:
        for stage in host.stages:
            level = logging.INFO if stage.ok else logging.ERROR
            log.log(
                level,
                "diagnose %s %s ok=%s %.1fms: %s",
                host.host,
                stage.stage,
                stage.ok,
                stage.ms,
                stage.detail,
            )
    return 0 if probe.reachable else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="athena", description="Athena operational CLI")
    groups = parser.add_subparsers(dest="group", required=True)

    sync = groups.add_parser("sync", help="market data synchronisation")
    actions = sync.add_subparsers(dest="action", required=True)
    for name in ("full", "incremental", "status", "market", "universe", "ensure"):
        actions.add_parser(name)
    replay = actions.add_parser("replay")
    replay.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    replay.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
    symbol = actions.add_parser("symbol", help="sync a single symbol, e.g. `sync symbol FPT`")
    symbol.add_argument("symbol", help="ticker to sync (e.g. FPT)")
    sync.add_argument("--tickers", help="comma list override (indices/exchanges/symbols)")

    provider = groups.add_parser("provider", help="data provider diagnostics")
    provider_actions = provider.add_subparsers(dest="action", required=True)
    test = provider_actions.add_parser("test", help="probe every supported vnstock source")
    test.add_argument("--source", help="comma list to test (default: all supported)")
    test.add_argument("--symbol", help="symbol to probe with (default: VCI)")
    datasets = provider_actions.add_parser(
        "datasets", help="print the vnstock dataset capability catalog"
    )
    datasets.add_argument("--source", help="vnstock source (default: VNSTOCK_SOURCE)")
    diagnose = provider_actions.add_parser(
        "diagnose", help="deep DNS/TCP/TLS + probe diagnostics for the VN data hosts"
    )
    diagnose.add_argument("--symbol", help="symbol to probe with (default: VCI)")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging(logging.INFO)
    args = _parser().parse_args(argv)

    if args.group == "provider":
        if args.action == "datasets":
            return _provider_datasets(args)
        if args.action == "diagnose":
            return _provider_diagnose(args)
        return _provider_test(args)

    # Sync scope: an explicit --tickers override wins; otherwise the scope of
    # the chosen action selects which tickers to cover. All scopes run through
    # the same (unchanged) scheduler → ProviderSyncService → Data Pipeline.
    if getattr(args, "tickers", None):
        tickers: list[str] | None = args.tickers.split(",")
    elif args.action == "market":
        tickers = list(market_scope())
    elif args.action == "universe":
        tickers = list(universe_scope(os.environ.get("SYNC_UNIVERSE")))
    elif args.action == "symbol":
        tickers = list(symbol_scope(args.symbol))
    else:
        tickers = None
    scheduler = build_scheduler(tickers=tickers)

    if args.action == "status":
        _emit(scheduler.status())
        return 0
    if args.action == "full":
        outcome = scheduler.full()
    elif args.action == "ensure":
        # Self-healing boot sync: if the published prices are readable, top up
        # incrementally; if they are missing (e.g. the snapshot's ephemeral disk
        # was wiped on a restart while the catalog watermark survived), the
        # incremental window would fetch nothing, so force a full backfill.
        if published_prices_present():
            outcome = scheduler.incremental()
        else:
            outcome = scheduler.full()
    elif args.action in ("incremental", "market", "universe", "symbol"):
        # market/universe/symbol are incremental syncs over a scoped ticker set
        # (only data newer than the persisted watermark is fetched).
        outcome = scheduler.incremental()
    elif args.action == "replay":
        outcome = scheduler.replay(date.fromisoformat(args.start), date.fromisoformat(args.end))
    else:  # pragma: no cover — argparse guarantees a valid action
        raise SystemExit(2)

    _emit(outcome.as_dict())
    return 0 if outcome.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
