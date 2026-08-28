import { useState } from "react";
import { api } from "../api/client";
import { Icon } from "./Icon";
import { Modal } from "./Modal";

export function AddServerDialog({ onClose, onCreated, notify }) {
  const [step, setStep] = useState(1);
  const [address, setAddress] = useState("");
  const [port, setPort] = useState(22);
  const [probe, setProbe] = useState(null);
  const [name, setName] = useState("");
  const [credentialType, setCredentialType] = useState("private_key");
  const [secret, setSecret] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);

  async function runProbe(event) {
    event.preventDefault(); setLoading(true);
    try { const result = await api.probe({ address, port: Number(port) }); setProbe(result); setName(address.replace(/[^A-Za-z0-9_.-]/g, "-")); setStep(2); }
    catch (error) { notify(error.message, "error"); } finally { setLoading(false); }
  }

  async function create(event) {
    event.preventDefault(); setLoading(true);
    const credential = credentialType === "password" ? { type: "password", password: secret } : { type: "private_key", private_key: secret, ...(passphrase ? { passphrase } : {}) };
    try {
      const server = await api.createServer({ name, probe_id: probe.id, confirmed_fingerprint: probe.fingerprint, username: "root", credential });
      onCreated(server); notify(`Сервер ${server.name} добавлен`); onClose();
    } catch (error) { notify(error.message, "error"); } finally { setLoading(false); }
  }

  return (
    <Modal title="Добавить сервер" subtitle={step === 1 ? "Шаг 1 из 2 · Проверка SSH-ключа" : "Шаг 2 из 2 · Доступ и подтверждение"} onClose={onClose}>
      {step === 1 ? <form className="modal__body form-stack" onSubmit={runProbe}>
        <div className="field-row"><label>Адрес сервера<input value={address} onChange={(event) => setAddress(event.target.value)} placeholder="10.20.0.42" required autoFocus /></label><label className="field-small">SSH-порт<input type="number" min="1" max="65535" value={port} onChange={(event) => setPort(event.target.value)} required /></label></div>
        <div className="info-box"><Icon name="shield"/><p><b>Сначала проверим host key.</b><br/>Сверьте полученный fingerprint с доверенным источником вне контроллера.</p></div>
        <footer className="modal__footer"><button type="button" className="button" onClick={onClose}>Отмена</button><button className="button button--primary" disabled={loading}>{loading ? "Подключаемся…" : "Получить fingerprint"}</button></footer>
      </form> : <form className="modal__body form-stack" onSubmit={create}>
        <div className="fingerprint"><span>SSH fingerprint · {probe.host_key_algorithm}</span><code>{probe.fingerprint}</code><label className="check-label"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span>Fingerprint сверен по доверенному каналу</span></label></div>
        <label>Имя сервера<input value={name} onChange={(event) => setName(event.target.value)} pattern={"[A-Za-z0-9_.\\-]+"} autoComplete="off" required /></label>
        <fieldset><legend>Способ подключения</legend><div className="segmented"><button type="button" className={credentialType === "private_key" ? "active" : ""} onClick={() => setCredentialType("private_key")}>Приватный ключ</button><button type="button" className={credentialType === "password" ? "active" : ""} onClick={() => setCredentialType("password")}>Пароль</button></div></fieldset>
        <label>{credentialType === "password" ? "Пароль root" : "Приватный SSH-ключ"}{credentialType === "password" ? <input type="password" value={secret} onChange={(event) => setSecret(event.target.value)} autoComplete="new-password" required /> : <textarea value={secret} onChange={(event) => setSecret(event.target.value)} placeholder="-----BEGIN OPENSSH PRIVATE KEY-----" autoComplete="off" required rows="4" />}</label>
        {credentialType === "private_key" ? <label>Passphrase <span className="optional">необязательно</span><input type="password" value={passphrase} onChange={(event) => setPassphrase(event.target.value)} autoComplete="new-password" /></label> : null}
        <footer className="modal__footer"><button type="button" className="button" onClick={() => setStep(1)}>Назад</button><button className="button button--primary" disabled={loading || !confirmed}>{loading ? "Проверяем доступ…" : "Добавить сервер"}</button></footer>
      </form>}
    </Modal>
  );
}
