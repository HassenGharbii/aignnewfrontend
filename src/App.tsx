import { FiltersProvider } from './context/FiltersContext';
import { Header } from './components/Header';
import { KpiRow } from './components/KpiRow';
import { SecondaryStatsBar } from './components/SecondaryStatsBar';
import { FilterBar } from './components/FilterBar';
import { RecentActivityTicker } from './components/RecentActivityTicker';
import { ChartsSection } from './components/ChartsSection';
import { TunisiaMap } from './components/map/TunisiaMap';
import { EventsTable } from './components/table/EventsTable';
import { PeopleSearch } from './components/people/PeopleSearch';

function App() {
  return (
    <FiltersProvider>
      <div className="relative min-h-screen pb-16">
        <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,rgba(34,211,238,0.12),transparent),radial-gradient(ellipse_60%_40%_at_100%_20%,rgba(129,140,248,0.10),transparent)]" />
        <Header />
        <main className="flex w-full flex-col gap-7 px-4 py-6 sm:px-6 lg:px-8">
          <section id="overview" className="scroll-mt-20 flex flex-col gap-4">
            <KpiRow />
            <SecondaryStatsBar />
            <FilterBar />
            <RecentActivityTicker />
          </section>
          <ChartsSection />
          <TunisiaMap />
          <EventsTable />
          <PeopleSearch />
        </main>
      </div>
    </FiltersProvider>
  );
}

export default App;
