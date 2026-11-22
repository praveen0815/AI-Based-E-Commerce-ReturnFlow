import { BrowserRouter, Route, Routes } from "react-router-dom";

import { GuestOnly, RequireAuth, RequireStore } from "./components/RequireAuth";
import { AuthProvider } from "./hooks/useAuth";
import { PreferencesProvider } from "./hooks/usePreferences";
import { AuthLayout } from "./layouts/AuthLayout";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { ActivityPage } from "./pages/ActivityPage";
import { OrderDetailPage } from "./pages/OrderDetailPage";
import { OrdersPage } from "./pages/OrdersPage";
import { AuditPage } from "./pages/AuditPage";
import { DashboardPage } from "./pages/DashboardPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { PolicyChatPage } from "./pages/PolicyChatPage";
import { LoginPage } from "./pages/LoginPage";
import { MembersPage } from "./pages/MembersPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { PreferencesPage } from "./pages/PreferencesPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RegisterPage } from "./pages/RegisterPage";
import { ReturnCreatePage } from "./pages/ReturnCreatePage";
import { ReturnDetailPage } from "./pages/ReturnDetailPage";
import { ReturnQueuePage } from "./pages/ReturnQueuePage";
import { ReturnsPage } from "./pages/ReturnsPage";
import { StoreSelectPage } from "./pages/StoreSelectPage";
import { SystemPage } from "./pages/SystemPage";

export function App() {
  return (
    <BrowserRouter>
      <PreferencesProvider>
        <AuthProvider>
          <Routes>
            <Route element={<GuestOnly />}>
              <Route element={<AuthLayout />}>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
              </Route>
            </Route>
            <Route element={<RequireAuth />}>
              <Route element={<DashboardLayout />}>
                <Route path="/onboarding" element={<OnboardingPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/stores" element={<StoreSelectPage />} />
                <Route path="/system" element={<SystemPage />} />
                <Route path="/preferences" element={<PreferencesPage />} />
                <Route element={<RequireStore />}>
                  <Route index element={<DashboardPage />} />
                  <Route path="activity" element={<ActivityPage />} />
                  <Route path="orders" element={<OrdersPage />} />
                  <Route path="orders/:orderId" element={<OrderDetailPage />} />
                  <Route path="orders/:orderId/return" element={<ReturnCreatePage />} />
                  <Route path="returns" element={<ReturnsPage />} />
                  <Route path="returns/queue" element={<ReturnQueuePage />} />
                  <Route path="returns/:returnId" element={<ReturnDetailPage />} />
                  <Route path="members" element={<MembersPage />} />
                  <Route path="audit" element={<AuditPage />} />
                  <Route path="knowledge" element={<KnowledgePage />} />
                  <Route path="policy" element={<PolicyChatPage />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Route>
            </Route>
          </Routes>
        </AuthProvider>
      </PreferencesProvider>
    </BrowserRouter>
  );
}
