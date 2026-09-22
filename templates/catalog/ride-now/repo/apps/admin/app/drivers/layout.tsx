// A plain-string title would reset the root "%s · RideNow Ops" template for the nested detail page.
export const metadata = { title: { default: "Drivers", template: "%s · RideNow Ops" } };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
