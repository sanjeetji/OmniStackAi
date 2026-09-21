// A plain-string title would reset the root "%s · RideNow" template for nested pages.
export const metadata = { title: { default: "Help centre", template: "%s · RideNow" } };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
