import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../context/AuthContext";

function SectionError({ message }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </div>
  );
}

function CardSkeleton() {
  return <div className="h-28 animate-pulse rounded-lg bg-slate-200" />;
}

function FeedSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="h-14 animate-pulse rounded-lg bg-slate-200" />
      ))}
    </div>
  );
}

export default function Dashboard() {
  const { apiClient, user: authUser } = useAuth();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["current-user-dashboard"],
    queryFn: async () => {
      const response = await apiClient.get("/users/me");
      return response?.data?.data || {};
    },
  });

  const user = useMemo(() => data?.user || authUser || {}, [data, authUser]);

  const stats = useMemo(
    () => ({
      totalUsers: data?.stats?.total_users ?? 0,
      activeSubscriptions: data?.stats?.active_subscriptions ?? 0,
      monthlyRevenue: data?.stats?.monthly_revenue ?? 0,
    }),
    [data],
  );

  const activity = useMemo(
    () => data?.recent_activity || data?.audit_logs || [],
    [data],
  );

  const currentPlan =
    data?.subscription?.plan?.name || data?.plan?.name || user?.plan?.name || "free";
  const showUpgradeBanner = String(currentPlan).toLowerCase() === "free";

  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-white p-5 shadow-sm">
        {isLoading ? (
          <div className="h-8 w-64 animate-pulse rounded bg-slate-200" />
        ) : isError ? (
          <SectionError message="Unable to load welcome banner." />
        ) : (
          <h2 className="text-xl font-semibold text-slate-900">
            Welcome back, {user?.first_name || "User"}
          </h2>
        )}
      </section>

      {showUpgradeBanner && !isLoading && !isError ? (
        <section className="rounded-xl border border-indigo-200 bg-indigo-50 p-5">
          <p className="text-sm text-indigo-800">
            You are currently on the Free plan. Upgrade to unlock premium features.
          </p>
        </section>
      ) : null}

      <section>
        <h3 className="mb-3 text-lg font-semibold text-slate-900">Summary Stats</h3>
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : isError ? (
          <SectionError message="Unable to load summary stats." />
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg bg-white p-5 shadow-sm">
              <p className="text-sm text-slate-500">Total Users</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{stats.totalUsers}</p>
            </div>
            <div className="rounded-lg bg-white p-5 shadow-sm">
              <p className="text-sm text-slate-500">Active Subscriptions</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{stats.activeSubscriptions}</p>
            </div>
            <div className="rounded-lg bg-white p-5 shadow-sm">
              <p className="text-sm text-slate-500">Monthly Revenue</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">${stats.monthlyRevenue}</p>
            </div>
          </div>
        )}
      </section>

      <section>
        <h3 className="mb-3 text-lg font-semibold text-slate-900">Recent Activity</h3>
        {isLoading ? (
          <FeedSkeleton />
        ) : isError ? (
          <SectionError message={error?.message || "Unable to load activity feed."} />
        ) : activity.length === 0 ? (
          <div className="rounded-lg bg-white p-5 text-sm text-slate-500 shadow-sm">
            No recent activity found.
          </div>
        ) : (
          <ul className="space-y-3">
            {activity.map((entry, index) => (
              <li key={entry.id || index} className="rounded-lg bg-white px-4 py-3 shadow-sm">
                <p className="text-sm font-medium text-slate-800">
                  {entry.action || "Activity"}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "Unknown time"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
