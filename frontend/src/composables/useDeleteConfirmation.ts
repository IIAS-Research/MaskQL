import { useConfirm } from "primevue/useconfirm";

let returnFocus: HTMLElement | null = null;

export function clearConfirmationFocus() {
  returnFocus = null;
}

export function restoreConfirmationFocus() {
  const target = returnFocus;
  returnFocus = null;
  if (!target) return;
  if (target.isConnected && !target.matches(":disabled")) {
    target.focus();
  } else {
    document.querySelector<HTMLInputElement>('main input[type="search"]')?.focus();
  }
}

export function useDeleteConfirmation() {
  const confirmation = useConfirm();
  return (options: {
    header: string;
    message: string;
    acceptLabel: string;
    target: HTMLElement;
    accept: () => void;
  }) => {
    returnFocus = options.target;
    confirmation.require({
      group: "delete",
      header: options.header,
      message: options.message,
      acceptLabel: options.acceptLabel,
      rejectLabel: "Cancel",
      defaultFocus: "reject",
      blockScroll: true,
      accept: options.accept,
    });
  };
}
