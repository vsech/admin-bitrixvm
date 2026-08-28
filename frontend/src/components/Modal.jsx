import { Icon } from "./Icon";

export function Modal({ title, subtitle, onClose, children, size = "medium" }) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className={`modal modal--${size}`} role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <header className="modal__header">
          <div><h2 id="modal-title">{title}</h2>{subtitle ? <p>{subtitle}</p> : null}</div>
          <button className="icon-button" onClick={onClose} aria-label="Закрыть"><Icon name="close" /></button>
        </header>
        {children}
      </section>
    </div>
  );
}
