import { LineChart } from "lucide-react";
import { PendingFeature } from "@/features/shared/pending-feature";

export default function Page() {
  return (
    <PendingFeature
      title="Backtest"
      description="Strategy simulation with SPEC-09 metrics."
      icon={LineChart}
      awaits="The backtest engine is implemented; the /backtests API returns 501 until a strategy-run endpoint and data feed land."
      scope={["Strategy Selection","Parameters","Simulation","Equity Curve","Trades","Metrics","Benchmark","Export"]}
    />
  );
}
