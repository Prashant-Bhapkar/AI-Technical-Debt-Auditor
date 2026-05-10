import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/Home";
import AuditReport from "./pages/AuditReport";
import Trends from "./pages/Trends";
import ApiKeyBar from "./components/ApiKeyBar";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 flex flex-col">
        <ApiKeyBar />
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/report/:auditId" element={<AuditReport />} />
            <Route path="/trends" element={<Trends />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
