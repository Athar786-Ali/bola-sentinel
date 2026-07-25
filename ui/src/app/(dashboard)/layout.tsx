import Sidebar from "@/components/layout/Sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#020617]">
      <Sidebar />
      <main className="ml-[240px] min-h-screen p-8">
        {children}
      </main>
    </div>
  );
}
