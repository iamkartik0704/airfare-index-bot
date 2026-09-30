import { useHeadline } from "@/api/queries";
import { IndicativeNote, OriginBadge } from "@/components/honesty";
import { PageHeader, Tag } from "@/components/neo";
import { DailySeriesPanel } from "@/components/overview/DailySeriesPanel";
import { HeadlineCards } from "@/components/overview/HeadlineCards";
import { PeriodPanel, TopRoutesPanel } from "@/components/overview/PeriodAndRoutes";
import { SubIndexPanel } from "@/components/overview/SubIndexPanel";
import { QueryState } from "@/components/states";
import { date } from "@/lib/format";

export default function Overview() {
  const headline = useHeadline();
  return (
    <div className="neo-in space-y-5">
      <PageHeader
        kicker="Real-time airfare price index · daily release"
        title={
          <>
            Domestic airfare, <span className="text-blue">measured daily</span>
          </>
        }
        right={
          headline.data && (
            <>
              <OriginBadge origin={headline.data.data_origin} />
              <Tag tone="ink">
                Base {headline.data.base_period ? `${date(headline.data.base_period[0])} = 100` : "period not set"}
              </Tag>
            </>
          )
        }
      />
      <QueryState
        query={headline}
        loadingLabel="Loading headline index"
        emptyLabel="No index has been computed yet"
      >
        {(h) => (
          <div className="space-y-5">
            <IndicativeNote status={h.methodology_status} />
            <HeadlineCards h={h} />
            <div className="grid gap-4 xl:grid-cols-3">
              <DailySeriesPanel latestDate={h.date} />
              <SubIndexPanel latestDate={h.date} />
            </div>
            <div className="grid gap-4 xl:grid-cols-3">
              <PeriodPanel />
              <TopRoutesPanel />
            </div>
          </div>
        )}
      </QueryState>
    </div>
  );
}
