import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navbar } from "@/components/layout/Navbar";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { AuctionListPage } from "@/features/auctions/AuctionListPage";
import { CreateRFQPage } from "@/features/auctions/CreateRFQPage";
import { AuctionDetailPage } from "@/features/auctions/AuctionDetailPage";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
          <Navbar />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/auctions" element={<AuctionListPage />} />
              <Route path="/rfqs/new" element={<CreateRFQPage />} />
              <Route path="/auctions/:id" element={<AuctionDetailPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
            British Auction RFQ System • Enterprise Reverse Bidding Engine
          </footer>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
