import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmModal } from "../app/components/ConfirmModal";

const defaultProps = {
  isOpen: true,
  title: "Delete product?",
  message: "This action cannot be undone.",
  confirmLabel: "Delete",
  cancelLabel: "Keep",
  onCancel: jest.fn(),
  onConfirm: jest.fn(),
};

describe("ConfirmModal", () => {
  beforeEach(() => {
    defaultProps.onCancel.mockClear();
    defaultProps.onConfirm.mockClear();
    document.body.style.overflow = "auto";
    jest.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      callback();
      return 1;
    });
    jest.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("renders nothing while closed", () => {
    render(<ConfirmModal {...defaultProps} isOpen={false} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe("auto");
  });

  it("labels the modal, locks scrolling and invokes both actions", async () => {
    const user = userEvent.setup();
    render(<ConfirmModal {...defaultProps} />);

    const dialog = screen.getByRole("dialog", { name: "Delete product?" });
    expect(dialog).toHaveAccessibleDescription("This action cannot be undone.");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(document.body.style.overflow).toBe("hidden");
    expect(screen.getAllByRole("button", { name: "Keep" })[0]).toHaveFocus();

    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);

    await user.click(screen.getAllByRole("button", { name: "Keep" })[1]);
    expect(defaultProps.onCancel).toHaveBeenCalledTimes(1);
  });

  it("cancels on Escape and backdrop mouse down, but not inside the dialog", () => {
    const { container } = render(<ConfirmModal {...defaultProps} />);
    const backdrop = container.firstChild;

    fireEvent.keyDown(document, { key: "Escape" });
    fireEvent.mouseDown(screen.getByRole("dialog"));
    fireEvent.mouseDown(backdrop);

    expect(defaultProps.onCancel).toHaveBeenCalledTimes(2);
  });

  it("cycles keyboard focus inside the dialog", () => {
    render(<ConfirmModal {...defaultProps} />);
    const cancelIcon = screen.getAllByRole("button", { name: "Keep" })[0];
    const confirmButton = screen.getByRole("button", { name: "Delete" });

    confirmButton.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(cancelIcon).toHaveFocus();

    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(confirmButton).toHaveFocus();
  });

  it("restores body scrolling and the previous focus on close", () => {
    const previousButton = document.createElement("button");
    document.body.appendChild(previousButton);
    previousButton.focus();

    const { rerender } = render(<ConfirmModal {...defaultProps} />);
    expect(previousButton).not.toHaveFocus();

    rerender(<ConfirmModal {...defaultProps} isOpen={false} />);

    expect(document.body.style.overflow).toBe("auto");
    expect(previousButton).toHaveFocus();
    previousButton.remove();
  });
});
