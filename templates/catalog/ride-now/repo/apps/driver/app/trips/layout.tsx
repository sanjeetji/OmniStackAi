// A plain-string title would reset the root "%s · RideNow Driver" template for nested pages.
export const metadata = { title: { default: "Trips", template: "%s · RideNow Driver" } };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
