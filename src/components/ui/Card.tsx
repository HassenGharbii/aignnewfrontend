import type { ReactNode } from 'react';

export function Card({
  title,
  subtitle,
  action,
  children,
  className = '',
  accent = 'from-cyan-500/40 via-indigo-500/30 to-transparent',
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  accent?: string;
}) {
  return (
    <div
      className={`group relative flex h-full flex-col overflow-hidden rounded-3xl border border-white/8 bg-white/[0.03] p-5 shadow-xl shadow-black/30 backdrop-blur-sm transition-colors hover:border-white/15 ${className}`}
    >
      <div className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r ${accent}`} />
      {(title || action) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h3 className="text-sm font-bold text-slate-100">{title}</h3>}
            {subtitle && <p className="mt-0.5 text-[11px] text-slate-500">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
