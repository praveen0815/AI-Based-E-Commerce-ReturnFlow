import { Component, type ErrorInfo, type ReactNode } from "react";

import { Alert } from "./ui/Alert";

interface State {
  failed: boolean;
}

export class AppErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ui_render_failed", error, info.componentStack);
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="min-h-screen bg-navy-950 p-6 text-ink">
          <Alert tone="danger" title="The interface hit an unexpected error">
            Reload the page. The technical detail is in the browser console.
          </Alert>
        </div>
      );
    }
    return this.props.children;
  }
}
