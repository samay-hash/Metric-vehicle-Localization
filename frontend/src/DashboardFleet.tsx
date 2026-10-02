import type { ReactNode } from 'react';
import type { CameraPage, FleetHealth } from './types';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getDashboardFleetHealth, getDashboardRegistryCameras } from './api';
import { useAuthenticatedDashboard } from './DashboardAuth';
import { errorMessage } from './lib/errors';

interface FleetState {
  inventory: CameraPage | null;
  fleet: FleetHealth | null;
  inventoryError: string;
  healthError: string;
  loading: boolean;
}

const DashboardFleetContext = createContext<(FleetState & { refresh: () => void }) | null>(null);

/** One scoped registry snapshot shared by the sidebar, overview and operations page. */
export function DashboardFleetProvider({ children }: { children: ReactNode }) {
  const { session } = useAuthenticatedDashboard();
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<FleetState>({
    inventory: null, fleet: null, inventoryError: '', healthError: '', loading: true,
  });
  const refresh = useCallback(() => setRevision(value => value + 1), []);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      setState(previous => ({ ...previous, loading: true }));
      const [inventory, health] = await Promise.allSettled([
        getDashboardRegistryCameras(session.token), getDashboardFleetHealth(session.token),
      ]);
      if (!active) return;
      setState({
        inventory: inventory.status === 'fulfilled' ? inventory.value : null,
        fleet: health.status === 'fulfilled' ? health.value : null,
        inventoryError: inventory.status === 'rejected' ? errorMessage(inventory.reason) : '',
        healthError: health.status === 'rejected' ? errorMessage(health.reason) : '',
        loading: false,
      });
      timer = setTimeout(load, 30000);
    }
    void load();
    return () => { active = false; clearTimeout(timer); };
  }, [session.token, revision]);

  return <DashboardFleetContext.Provider value={{ ...state, refresh }}>{children}</DashboardFleetContext.Provider>;
}

export function useDashboardFleet() {
  const value = useContext(DashboardFleetContext);
  if (!value) throw new Error('DashboardFleetProvider is missing');
  return value;
}
