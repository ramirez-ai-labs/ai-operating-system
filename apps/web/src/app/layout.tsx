import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Operating System',
  description:
    'Local-first multi-domain AI system that synthesizes your notes into grounded, traceable executive output.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-serif text-aios-ink">{children}</body>
    </html>
  )
}
