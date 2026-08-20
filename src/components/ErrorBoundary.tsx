import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  label: string;
}

interface State {
  error: Error | null;
}

/** Keeps one section's crash (e.g. a bad map tile config) from blanking the
 * whole dashboard — every top-level section in App.tsx is wrapped in one. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error(`[${this.props.label}] crashed:`, error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          تعذّر عرض قسم "{this.props.label}" — {this.state.error.message}
        </div>
      );
    }
    return this.props.children;
  }
}
