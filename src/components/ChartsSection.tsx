import { GovernorateBarChart } from './charts/GovernorateBarChart';
import { CauseDonut } from './charts/CauseDonut';
import { SeverityStatusChart } from './charts/SeverityStatusChart';
import { TrendChart } from './charts/TrendChart';
import { TimingChart } from './charts/TimingChart';
import { TopSourcesChart } from './charts/TopSourcesChart';
import { KeywordCloud } from './charts/KeywordCloud';
import { PeopleDemographics } from './charts/PeopleDemographics';

export function ChartsSection() {
  return (
    <section id="charts" className="scroll-mt-20">
      <div className="mb-3 flex items-center gap-2">
        <span className="h-4 w-1 rounded-full bg-gradient-to-b from-cyan-400 to-indigo-500" />
        <h2 className="text-sm font-bold text-slate-200">التحليلات</h2>
      </div>
      <div className="grid grid-cols-1 items-stretch gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <GovernorateBarChart />
        </div>
        <CauseDonut />

        <div className="lg:col-span-2">
          <TrendChart />
        </div>
        <SeverityStatusChart />

        <div className="lg:col-span-2">
          <TimingChart />
        </div>
        <TopSourcesChart />

        <div className="lg:col-span-2">
          <PeopleDemographics />
        </div>
        <KeywordCloud />
      </div>
    </section>
  );
}
