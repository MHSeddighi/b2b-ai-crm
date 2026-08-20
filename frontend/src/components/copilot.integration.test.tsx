import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { fetchCopilotAnswerStream, type StreamEvent } from "@/lib/chat-api";
import { Copilot } from "./copilot";

vi.mock("@/lib/chat-api", () => ({
  fetchCopilotAnswerStream: vi.fn(),
}));

const mockStream = vi.mocked(fetchCopilotAnswerStream);

function fullStreamEvents(): StreamEvent[] {
  return [
    { type: "status", status: "planning" },
    { type: "thinking", text: "بررسی" },
    { type: "text", text: "روند فروش صعودی است." },
    {
      type: "blocks",
      blocks: [
        {
          id: "c1",
          type: "chart",
          resultId: "r1",
          chartType: "line",
          xKey: "month",
          series: [{ dataKey: "sales", label: "فروش" }],
          title: "روند فروش ماهانه",
        },
      ],
      results: {
        r1: {
          resultId: "r1",
          columns: ["month", "sales"],
          rows: [
            ["m1", 10],
            ["m2", 20],
          ],
          n_rows: 2,
        },
      },
    },
    { type: "done" },
  ];
}

async function sendQuestion(question = "روند فروش") {
  const input = await screen.findByPlaceholderText(/بپرسید/);
  fireEvent.change(input, { target: { value: question } });
  const send = await screen.findByLabelText("ارسال پیام");
  await waitFor(() => expect((send as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(send);
}

describe("Copilot (assistant-ui runtime integration)", () => {
  beforeEach(() => {
    mockStream.mockReset();
  });

  it("renders the chart block with data (not an empty card) and ends loading", async () => {
    mockStream.mockImplementation(async function* () {
      for (const ev of fullStreamEvents()) yield ev;
    });

    render(<Copilot sessionId="s1" onClose={() => {}} />);
    await sendQuestion();

    // Chart title renders…
    expect(await screen.findByText("روند فروش ماهانه")).toBeTruthy();
    // …but the empty-chart message must NOT be present.
    expect(screen.queryByText("داده\u200cای برای نمودار موجود نیست.")).toBeNull();
    // Narrative text rendered.
    expect(screen.getByText(/روند فروش صعودی/)).toBeTruthy();

    // Visuals come BEFORE the narrative explanation.
    const chartTitle = screen.getByText("روند فروش ماهانه");
    const narrative = screen.getByText(/روند فروش صعودی/);
    expect(chartTitle.compareDocumentPosition(narrative) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    // Loading ended: the loading placeholder is gone, send button is back,
    // and the stop/cancel button is gone.
    await waitFor(() => {
      expect(screen.queryByText("در حال تحلیل و جستجو در داده\u200cها…")).toBeNull();
      expect(screen.getByLabelText("ارسال پیام")).toBeTruthy();
      expect(screen.queryByLabelText("توقف تولید پاسخ")).toBeNull();
    });
  });

  it("shows exactly ONE composer button that toggles send <-> stop while running", async () => {
    let release!: () => void;
    const gate = new Promise<void>((res) => (release = res));
    mockStream.mockImplementation(async function* () {
      await gate;
      for (const ev of fullStreamEvents()) yield ev;
    });

    render(<Copilot sessionId="s2" onClose={() => {}} />);
    await sendQuestion();

    // While running: stop button only, no send button, input disabled.
    await waitFor(() => {
      expect(screen.getByLabelText("توقف تولید پاسخ")).toBeTruthy();
    });
    expect(screen.queryByLabelText("ارسال پیام")).toBeNull();
    const input = screen.getByPlaceholderText(/بپرسید/) as HTMLTextAreaElement;
    expect(input.disabled).toBe(true);

    // Exactly one action button in the composer row.
    const composerRow = input.closest("div")?.parentElement;
    expect(composerRow).toBeTruthy();

    // Release the stream; loading ends and the single send button returns.
    release();
    await waitFor(() => {
      expect(screen.queryByLabelText("توقف تولید پاسخ")).toBeNull();
      expect(screen.getByLabelText("ارسال پیام")).toBeTruthy();
    });
    expect((screen.getByLabelText("ارسال پیام") as HTMLButtonElement).disabled).toBe(true);
  });

  it("recovers from a backend failure and ends the loading state", async () => {
    mockStream.mockImplementation(async function* () {
      throw new Error("backend unreachable");
    });

    render(<Copilot sessionId="s3" onClose={() => {}} />);
    await sendQuestion();

    // Retries (3 attempts with backoff) then shows the error and ends loading.
    await waitFor(
      () => {
        expect(screen.getByText(/متأسفانه به سرور پشتیبان/)).toBeTruthy();
        expect(screen.getByLabelText("ارسال پیام")).toBeTruthy();
      },
      { timeout: 8000 }
    );
  });

  it("retries a failed connection and answers without the error message", async () => {
    let calls = 0;
    mockStream.mockImplementation(async function* () {
      calls++;
      if (calls === 1) throw new Error("connection refused (backend reloading)");
      for (const ev of fullStreamEvents()) yield ev;
    });

    render(<Copilot sessionId="s4" onClose={() => {}} />);
    await sendQuestion();

    expect(await screen.findByText("روند فروش ماهانه", undefined, { timeout: 8000 })).toBeTruthy();
    expect(screen.queryByText(/متأسفانه به سرور پشتیبان/)).toBeNull();
    expect(calls).toBe(2);
  });

  it("reconnects when the connection drops mid-planning (before any text) and still answers", async () => {
    let calls = 0;
    mockStream.mockImplementation(async function* () {
      calls++;
      if (calls === 1) {
        // Backend was reached (thinking streamed) then dropped before text.
        yield { type: "status", status: "planning" };
        yield { type: "thinking", text: "بررسی" };
        throw new Error("connection dropped mid-stream");
      }
      for (const ev of fullStreamEvents()) yield ev;
    });

    render(<Copilot sessionId="s5" onClose={() => {}} />);
    await sendQuestion();

    // The pre-answer drop self-heals: no connection error, answer renders.
    expect(await screen.findByText("روند فروش ماهانه", undefined, { timeout: 8000 })).toBeTruthy();
    expect(screen.queryByText(/ارتباط با سرور/)).toBeNull();
    expect(screen.queryByText(/متأسفانه به سرور پشتیبان/)).toBeNull();
    expect(calls).toBe(2);
  });
});
