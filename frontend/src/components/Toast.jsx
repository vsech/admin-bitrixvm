import { Icon } from "./Icon";

export function Toast({ toast, onClose }) {
  if (!toast) return null;
  return <div className={`toast toast--${toast.type || "success"}`} role="status"><Icon name={toast.type === "error" ? "alert" : "check"}/><span>{toast.message}</span><button onClick={onClose} aria-label="Закрыть"><Icon name="close" size={16}/></button></div>;
}
