import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import App from "../App";
import { ThemeProvider } from "../ThemeProvider";

function renderAt(path) {
  window.history.pushState({}, "", path);
  return render(
    <ThemeProvider>
      <App />
    </ThemeProvider>
  );
}

test("routes / to Splash", () => {
  renderAt("/");
  expect(screen.getByText("VECBOOK")).toBeInTheDocument();
});

test("routes /home to Dashboard", () => {
  renderAt("/home");
  expect(screen.getByText("Register Teacher")).toBeInTheDocument();
});

test("routes unknown paths to Splash", () => {
  renderAt("/does-not-exist");
  expect(screen.getByText("VECBOOK")).toBeInTheDocument();
});
