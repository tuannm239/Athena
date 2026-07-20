"""`athena` sync CLI — operational entrypoint for market synchronisation.

Commands:
    athena sync full          # full window resync (SYNC_LOOKBACK_DAYS back)
    athena sync incremental   # only days newer than the last published watermark
    athena sync replay --start YYYY-MM-DD --end YYYY-MM-DD
    athena sync status        # health: watermark, provider health, config
    athena provider test      # probe every supported vnstock source:
                              #   reachable / status code / response time / datasets

It builds the same persistence the API reads (SqlDatasetCatalog +
DuckDbSnapshotStore), resolves the configured price provider from the registry
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

from data_pipeline.application.sync import ProviderSyncService
from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.scheduler import MarketSyncScheduler
from data_pipeline.tickers import parse_spec, resolve_tickers
from infrastructure.config import Settings
from infrastructure.db.engine import build_engine, build_session_factory
from infrastructure.db.repositories.dataset_catalog import SqlDatasetCatalog
from infrastructure.duckdb_store import DuckDbSnapshotStore
from infrastructure.observability import configure_logging
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
        snapshots=DuckDbSnapshotStore(cfg.duckdb_dir),
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="athena", description="Athena operational CLI")
    groups = parser.add_subparsers(dest="group", required=True)

    sync = groups.add_parser("sync", help="market data synchronisation")
    actions = sync.add_subparsers(dest="action", required=True)
    for name in ("full", "incremental", "status"):
        actions.add_parser(name)
    replay = actions.add_parser("replay")
    replay.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    replay.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
    sync.add_argument("--tickers", help="comma list override (indices/exchanges/symbols)")

    provider = groups.add_parser("provider", help="data provider diagnostics")
    provider_actions = provider.add_subparsers(dest="action", required=True)
    test = provider_actions.add_parser("test", help="probe every supported vnstock source")
    test.add_argument("--source", help="comma list to test (default: all supported)")
    test.add_argument("--symbol", help="symbol to probe with (default: VCI)")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging(logging.INFO)
    args = _parser().parse_args(argv)

    if args.group == "provider":
        return _provider_test(args)

    tickers = args.tickers.split(",") if getattr(args, "tickers", None) else None
    scheduler = build_scheduler(tickers=tickers)

    if args.action == "status":
        _emit(scheduler.status())
        return 0
    if args.action == "full":
        outcome = scheduler.full()
    elif args.action == "incremental":
        outcome = scheduler.incremental()
    elif args.action == "replay":
        outcome = scheduler.replay(date.fromisoformat(args.start), date.fromisoformat(args.end))
    else:  # pragma: no cover — argparse guarantees a valid action
        raise SystemExit(2)

    _emit(outcome.as_dict())
    return 0 if outcome.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
