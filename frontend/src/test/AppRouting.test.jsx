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
  window.localStorage.setItem("vecbook_session_token", "test-token");
  renderAt("/home");
  expect(screen.getByText("Register Teacher")).toBeInTheDocument();
});

test("routes /home to login when not authenticated", () => {
  window.localStorage.removeItem("vecbook_session_token");
  renderAt("/home");
  expect(screen.getByText("VECBOOK ADMIN")).toBeInTheDocument();
});

test("routes /teachers to login when not authenticated", () => {
  window.localStorage.removeItem("vecbook_session_token");
  renderAt("/teachers");
  expect(screen.getByText("VECBOOK ADMIN")).toBeInTheDocument();
});

test("routes /records to login when not authenticated", () => {
  window.localStorage.removeItem("vecbook_session_token");
  renderAt("/records");
  expect(screen.getByText("VECBOOK ADMIN")).toBeInTheDocument();
});

test("routes unknown paths to Splash", () => {
  renderAt("/does-not-exist");
  expect(screen.getByText("VECBOOK")).toBeInTheDocument();
});
