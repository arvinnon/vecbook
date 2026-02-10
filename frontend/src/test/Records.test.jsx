import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";

import Records from "../Records";
import { ThemeProvider } from "../ThemeProvider";
import { fetchAttendance, fetchSummary, resetAttendance } from "../api";

vi.mock("../api", () => ({
  fetchAttendance: vi.fn(),
  fetchSummary: vi.fn(),
  resetAttendance: vi.fn(),
}));

function renderRecords() {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <Records />
      </ThemeProvider>
    </MemoryRouter>
  );
}

const rows = [
  {
    id: 1,
    full_name: "Ada Lovelace",
    department: "Math",
    date: "2026-02-10",
    time_in: "07:45:00",
    time_out: "17:05:00",
    status: "On-Time",
  },
];

beforeEach(() => {
  fetchAttendance.mockReset();
  fetchSummary.mockReset();
  resetAttendance.mockReset();
});

test("renders attendance rows from API", async () => {
  fetchAttendance.mockResolvedValueOnce(rows);

  renderRecords();

  expect(fetchAttendance).toHaveBeenCalledWith(null);
  expect(await screen.findByText("Ada Lovelace")).toBeInTheDocument();
  expect(screen.getByText("On-Time")).toBeInTheDocument();
  expect(screen.getByText("17:05:00")).toBeInTheDocument();
});

test("filters by date and shows summary", async () => {
  fetchAttendance
    .mockResolvedValueOnce([]) // initial load
    .mockResolvedValueOnce(rows); // after filter
  fetchSummary.mockResolvedValueOnce({ total: 1, on_time: 1, late: 0 });

  renderRecords();

  await screen.findByText("No records found.");

  const input = screen.getByPlaceholderText("YYYY-MM-DD");
  fireEvent.change(input, { target: { value: "2026-02-10" } });
  fireEvent.click(screen.getByText("Filter"));

  expect(await screen.findByText("Ada Lovelace")).toBeInTheDocument();
  expect(fetchAttendance).toHaveBeenCalledWith("2026-02-10");
  expect(fetchSummary).toHaveBeenCalledWith("2026-02-10");
  expect(
    screen.getByText("Total: 1 | On-Time: 1 | Late: 0")
  ).toBeInTheDocument();
});
