import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, afterEach } from "vitest";
import UploadZone from "./UploadZone";

function pdfFile(name = "book.pdf") {
  return new File(["%PDF-1.4 fake content"], name, { type: "application/pdf" });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("UploadZone", () => {
  it("stages a selected file without uploading until Upload book is clicked", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ book_id: "abc", chunks_indexed: 0 }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const onUploaded = vi.fn();

    render(<UploadZone onUploaded={onUploaded} />);
    const input = document.querySelector('input[type="file"]');
    await userEvent.upload(input, pdfFile());

    expect(screen.getByText(/book\.pdf/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /upload book/i }));

    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith({ book_id: "abc", chunks_indexed: 0 }));
    expect(screen.queryByText(/upload failed/i)).not.toBeInTheDocument();
  });

  it("shows an error and does not call onUploaded when the server rejects the upload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 413,
      statusText: "Request Entity Too Large",
      text: async () => "",
    });
    vi.stubGlobal("fetch", fetchMock);
    const onUploaded = vi.fn();

    render(<UploadZone onUploaded={onUploaded} />);
    const input = document.querySelector('input[type="file"]');
    await userEvent.upload(input, pdfFile());
    await userEvent.click(screen.getByRole("button", { name: /upload book/i }));

    await waitFor(() => expect(screen.getByText(/upload failed \(413\)/i)).toBeInTheDocument());
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("the upload button is disabled until a file is staged", () => {
    render(<UploadZone onUploaded={vi.fn()} />);
    expect(screen.getByRole("button", { name: /upload book/i })).toBeDisabled();
  });
});
