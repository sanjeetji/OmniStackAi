// A plain-string title would reset the root "%s · RideNow Driver" template for nested pages.
export const metadata = { title: { default: "Help", template: "%s · RideNow Driver" } };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
