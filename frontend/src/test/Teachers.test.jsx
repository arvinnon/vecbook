import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";

import Teachers from "../Teachers";
import { ThemeProvider } from "../ThemeProvider";
import { fetchTeachers, hardReset } from "../api";

vi.mock("../api", () => ({
  fetchTeachers: vi.fn(),
  hardReset: vi.fn(),
}));

function renderTeachers() {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <Teachers />
      </ThemeProvider>
    </MemoryRouter>
  );
}

const rows = [
  {
    id: 1,
    full_name: "Ada Lovelace",
    department: "Math",
    employee_id: "EMP001",
    created_at: "2026-02-10",
  },
  {
    id: 2,
    full_name: "Grace Hopper",
    department: "Physics",
    employee_id: "EMP002",
    created_at: "2026-02-10",
  },
];

beforeEach(() => {
  fetchTeachers.mockReset();
  hardReset.mockReset();
});

test("renders teachers from API", async () => {
  fetchTeachers.mockResolvedValue(rows);

  renderTeachers();

  expect(fetchTeachers).toHaveBeenCalledTimes(1);
  expect(await screen.findByText("Ada Lovelace")).toBeInTheDocument();
  expect(screen.getByText("Grace Hopper")).toBeInTheDocument();
});

test("filters by search input", async () => {
  fetchTeachers.mockResolvedValue(rows);

  renderTeachers();

  await screen.findByText("Ada Lovelace");

  const input = screen.getByPlaceholderText(
    "Search by name, department, or employee ID..."
  );
  fireEvent.change(input, { target: { value: "math" } });

  expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
  expect(screen.queryByText("Grace Hopper")).toBeNull();
});

test("shows an error toast when teacher load fails", async () => {
  fetchTeachers.mockRejectedValueOnce(new Error("Unauthorized"));

  renderTeachers();

  expect(await screen.findByText("Unauthorized")).toBeInTheDocument();
  expect(screen.getByText("No teachers found.")).toBeInTheDocument();
});
