/** Etiquetas de servicio para dominios observados pasivamente.

Solo metadatos: mapea un hostname/DNS a una categoría visible. No descifra TLS.
*/

const SERVICE_RULES: Array<{ match: (host: string) => boolean; label: string; tone: string }> = [
  { match: (h) => /(^|\.)youtube\.com$/.test(h) || /(^|\.)googlevideo\.com$/.test(h) || /(^|\.)ytimg\.com$/.test(h) || /(^|\.)ggpht\.com$/.test(h), label: 'YouTube', tone: 'border-rose-500/40 bg-rose-500/10 text-rose-300' },
  { match: (h) => /(^|\.)google\.com$/.test(h) || /(^|\.)gstatic\.com$/.test(h) || /(^|\.)googleapis\.com$/.test(h), label: 'Google', tone: 'border-blue-500/40 bg-blue-500/10 text-blue-300' },
  { match: (h) => /(^|\.)facebook\.com$/.test(h) || /(^|\.)fbcdn\.net$/.test(h) || /(^|\.)instagram\.com$/.test(h), label: 'Meta', tone: 'border-indigo-500/40 bg-indigo-500/10 text-indigo-300' },
  { match: (h) => /(^|\.)whatsapp\.com$/.test(h) || /(^|\.)whatsapp\.net$/.test(h), label: 'WhatsApp', tone: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' },
  { match: (h) => /(^|\.)twitter\.com$/.test(h) || /(^|\.)x\.com$/.test(h) || /(^|\.)twimg\.com$/.test(h), label: 'X / Twitter', tone: 'border-sky-500/40 bg-sky-500/10 text-sky-300' },
  { match: (h) => /(^|\.)github\.com$/.test(h) || /(^|\.)githubusercontent\.com$/.test(h), label: 'GitHub', tone: 'border-slate-500/40 bg-slate-500/10 text-slate-300' },
  { match: (h) => /(^|\.)microsoft\.com$/.test(h) || /(^|\.)live\.com$/.test(h) || /(^|\.)office\.com$/.test(h), label: 'Microsoft', tone: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300' },
  { match: (h) => /(^|\.)cloudflare\.com$/.test(h) || /(^|\.)cloudflare-dns\.com$/.test(h), label: 'Cloudflare', tone: 'border-orange-500/40 bg-orange-500/10 text-orange-300' },
  { match: (h) => /(^|\.)amazonaws\.com$/.test(h) || /(^|\.)amazon\.com$/.test(h), label: 'AWS / Amazon', tone: 'border-amber-500/40 bg-amber-500/10 text-amber-300' },
  { match: (h) => /(^|\.)netflix\.com$/.test(h) || /(^|\.)nflxvideo\.net$/.test(h), label: 'Netflix', tone: 'border-red-500/40 bg-red-500/10 text-red-300' },
  { match: (h) => /(^|\.)spotify\.com$/.test(h) || /(^|\.)scdn\.co$/.test(h), label: 'Spotify', tone: 'border-green-500/40 bg-green-500/10 text-green-300' },
  { match: (h) => /(^|\.)tiktok\.com$/.test(h) || /(^|\.)tiktokcdn\.com$/.test(h), label: 'TikTok', tone: 'border-pink-500/40 bg-pink-500/10 text-pink-300' }
]

export function serviceLabelFor(host: string | undefined | null): { label: string; tone: string } | null {
  if (!host) return null
  const normalized = host.trim().toLowerCase().replace(/\.$/, '')
  if (!normalized) return null
  for (const rule of SERVICE_RULES) {
    if (rule.match(normalized)) return { label: rule.label, tone: rule.tone }
  }
  return null
}
