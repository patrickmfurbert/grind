import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom doesn't implement ResizeObserver, which React Flow relies on for pane sizing.
global.ResizeObserver =
  global.ResizeObserver ||
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

// Monaco's editor needs canvas/worker APIs jsdom doesn't provide; stub it for component tests.
vi.mock("@monaco-editor/react", () => ({
  default: ({ value, onChange }) => (
    <textarea data-testid="monaco-stub" value={value} onChange={(event) => onChange(event.target.value)} />
  ),
}));
