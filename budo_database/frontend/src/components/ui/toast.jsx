"use client"

import { Toast as ToastPrimitive } from "@base-ui/react/toast"

const toast = ToastPrimitive.createToastManager()

const toastIcons = {
  error: "!",
  info: "i",
  success: "✓",
  warning: "!",
}

function ToastList() {
  const { toasts } = ToastPrimitive.useToastManager()

  return toasts.map((toastItem) => (
    <ToastPrimitive.Root
      className="app-toast"
      data-type={toastItem.type || "info"}
      key={toastItem.id}
      swipeDirection={["up", "right"]}
      toast={toastItem}
    >
      <ToastPrimitive.Content className="app-toast-content">
        {toastIcons[toastItem.type] && (
          <span className="app-toast-icon" aria-hidden="true">{toastIcons[toastItem.type]}</span>
        )}
        <div className="app-toast-message">
          <ToastPrimitive.Title className="app-toast-title" />
          <ToastPrimitive.Description className="app-toast-description" />
        </div>
        <ToastPrimitive.Action className="app-toast-action" />
        <ToastPrimitive.Close className="app-toast-close" aria-label="Benachrichtigung schließen">
          <span aria-hidden="true">×</span>
        </ToastPrimitive.Close>
      </ToastPrimitive.Content>
    </ToastPrimitive.Root>
  ))
}

function Toaster({ children, toastManager, ...props }) {
  const managerProps = toastManager ? { toastManager } : {}

  return (
    <ToastPrimitive.Provider {...managerProps} {...props}>
      {children}
      <ToastPrimitive.Portal>
        <ToastPrimitive.Viewport className="app-toast-viewport" aria-label="Benachrichtigungen">
          <ToastList />
        </ToastPrimitive.Viewport>
      </ToastPrimitive.Portal>
    </ToastPrimitive.Provider>
  )
}

const createToastManager = ToastPrimitive.createToastManager
const useToastManager = ToastPrimitive.useToastManager

export { createToastManager, toast, Toaster, useToastManager }
