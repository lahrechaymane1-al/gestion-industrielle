import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layout/AppLayout";
import HomeDashboardPage from "./pages/HomeDashboardPage";
import AbsenceListPage from "./pages/absence/AbsenceListPage";
import EffectifListPage from "./pages/effectif/EffectifListPage";
import ModeDegradeListPage from "./pages/modeDegrade/ModeDegradeListPage";
import BerceauProductionPage from "./pages/production/BerceauProductionPage";
import CcbProductionPage from "./pages/production/CcbProductionPage";
import AlertePanneBerceauPage from "./pages/arret/AlertePanneBerceauPage";
import ProductionDashboardPage from "./pages/dashboard/ProductionDashboardPage";
import StockJournalPage from "./pages/stock/StockJournalPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<HomeDashboardPage />} />
        <Route path="berceau/production" element={<BerceauProductionPage />} />
        <Route path="berceau/dashboard" element={<ProductionDashboardPage />} />
        <Route path="berceau/absence" element={<AbsenceListPage equipe="Berceau" />} />
        <Route path="berceau/effectif" element={<EffectifListPage equipe="Berceau" />} />
        <Route path="berceau/mode-degrade" element={<ModeDegradeListPage equipe="Berceau" />} />
        <Route path="berceau/stock" element={<StockJournalPage equipe="Berceau" />} />
        <Route path="berceau/arret" element={<AlertePanneBerceauPage equipe="Berceau" />} />
        <Route path="ccb/production" element={<CcbProductionPage />} />
        <Route path="ccb/absence" element={<AbsenceListPage equipe="CCB" />} />
        <Route path="ccb/effectif" element={<EffectifListPage equipe="CCB" />} />
        <Route path="ccb/mode-degrade" element={<ModeDegradeListPage equipe="CCB" />} />
        <Route path="ccb/stock" element={<StockJournalPage equipe="CCB" />} />
        <Route path="ccb/arret" element={<AlertePanneBerceauPage equipe="CCB" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
