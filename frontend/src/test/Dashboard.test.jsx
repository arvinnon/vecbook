import { render, screen, fireEvent } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";
import { MemoryRouter } from "react-router-dom";

import Dashboard from "../Dashboard";
import { ThemeProvider, useTheme } from "../ThemeProvider";

function renderDashboard() {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <Dashboard />
      </ThemeProvider>
    </MemoryRouter>
  );
}

function ModeProbe() {
  const { mode, toggle } = useTheme();
  return (
    <div>
      <span>{mode}</span>
      <button onClick={toggle}>Toggle</button>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
});

test("renders dashboard cards", () => {
  renderDashboard();

  expect(screen.getByText("VECBOOK")).toBeInTheDocument();
  expect(screen.getByText("Register Teacher")).toBeInTheDocument();
  expect(screen.getByText("Start Attendance")).toBeInTheDocument();
  expect(screen.getByText("Teacher List")).toBeInTheDocument();
  expect(screen.getByText("Attendance Records")).toBeInTheDocument();
});

test("theme provider toggles mode", () => {
  render(
    <ThemeProvider>
      <ModeProbe />
    </ThemeProvider>
  );

  expect(screen.getByText("light")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Toggle"));
  expect(screen.getByText("dark")).toBeInTheDocument();
});
