import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PRAXIS InterviewOS",
  description: "Realtime AI interview intelligence platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
