import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";

import Teachers from "../Teachers";
import { ThemeProvider } from "../ThemeProvider";
import { deleteTeacher, fetchTeachers, hardReset } from "../api";

vi.mock("../api", () => ({
  deleteTeacher: vi.fn(),
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
  deleteTeacher.mockReset();
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

test("deletes a teacher after confirmation", async () => {
  fetchTeachers.mockResolvedValueOnce(rows).mockResolvedValueOnce(rows.slice(1));
  deleteTeacher.mockResolvedValue({ ok: true, id: 1 });

  renderTeachers();

  await screen.findByText("Ada Lovelace");
  fireEvent.click(screen.getAllByRole("button", { name: "Delete" })[0]);

  expect(screen.getByText("Delete this teacher?")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Yes, delete teacher" }));

  await waitFor(() => expect(deleteTeacher).toHaveBeenCalledWith(1));
  await waitFor(() => expect(fetchTeachers).toHaveBeenCalledTimes(2));
  expect(await screen.findByText("Ada Lovelace deleted.")).toBeInTheDocument();
});
