"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AUTH_STORAGE_KEY = "dsg_access_token";
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".csv", ".parquet", ".json", ".xml"];
const PROCESSING_STATUSES = [
  "UPLOADED",
  "SENT_TO_N8N",
  "ANALYZING",
  "GENERATING_SCRIPT",
  "VALIDATING_SCRIPT",
  "COMPLETED",
  "FAILED",
];

type AuthMode = "login" | "register";
type MainView = "processing" | "history";

type UserResponse = {
  id: string;
  username: string;
  created_at: string;
};

type AuthResponse = {
  access_token: string;
  token_type: string;
  user: UserResponse;
};

type UploadResponse = {
  job_id: string;
  status: string;
  message: string;
};

type AnalysisIssue = {
  type?: string;
  message?: string;
  description?: string;
  column?: string;
  columns?: string[];
  severity?: string;
};

type AnalysisJson = {
  rows?: number;
  columns?: number;
  issues?: AnalysisIssue[];
};

type JobResponse = {
  id: string;
  job_name: string;
  file_name: string;
  file_fingerprint: string;
  file_type: string;
  file_size: number;
  status: string;
  raw_file_url: string;
  result_package_url?: string | null;
  analysis_json?: AnalysisJson | null;
  generated_script?: string | null;
  generated_manual?: string | null;
  requirements_txt?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

type AlertState = {
  type: "success" | "error" | "info";
  message: string;
};

export default function Home() {
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobName, setJobName] = useState("");
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [jobStatus, setJobStatus] = useState<JobResponse | null>(null);
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [activeView, setActiveView] = useState<MainView>("processing");
  const [alert, setAlert] = useState<AlertState | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const canUpload = useMemo(
    () => selectedFile !== null && jobName.trim().length > 0 && !isUploading && accessToken !== null,
    [selectedFile, jobName, isUploading, accessToken],
  );

  useEffect(() => {
    const savedToken = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!savedToken) {
      setIsBootstrapping(false);
      return;
    }

    setAccessToken(savedToken);
    loadSession(savedToken).finally(() => setIsBootstrapping(false));
  }, []);

  async function loadSession(token: string) {
    try {
      const response = await apiFetch("/api/auth/me", { method: "GET" }, token);
      const user = await parseApiResponse<UserResponse>(response);
      if (!response.ok) {
        throw new Error(getApiErrorMessage(user, "Sessao expirada."));
      }

      setCurrentUser(user);
      await loadJobs(token);
    } catch {
      clearSession();
    }
  }

  async function loadJobs(token = accessToken) {
    if (!token) {
      return;
    }

    setIsLoadingHistory(true);
    try {
      const response = await apiFetch("/api/jobs?limit=50", { method: "GET" }, token);
      const data = await parseApiResponse<JobResponse[]>(response);
      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, "Falha ao carregar historico."));
      }
      
      const loadedJobs = Array.isArray(data) ? data : [];
      setJobs(loadedJobs);
      
      setJobStatus((currentJobStatus) => {
        if (!currentJobStatus && loadedJobs.length > 0) {
          return loadedJobs[0];
        }
        return currentJobStatus;
      });
    } catch (error) {
      setAlert({ type: "error", message: getFriendlyError(error) });
    } finally {
      setIsLoadingHistory(false);
    }
  }

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsAuthenticating(true);
    setAlert(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/${authMode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await parseApiResponse<AuthResponse>(response);
      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, "Nao foi possivel autenticar."));
      }

      window.localStorage.setItem(AUTH_STORAGE_KEY, data.access_token);
      setAccessToken(data.access_token);
      setCurrentUser(data.user);
      setPassword("");
      setAlert({ type: "success", message: authMode === "login" ? "Login realizado." : "Usuario criado." });
      await loadJobs(data.access_token);
    } catch (error) {
      setAlert({ type: "error", message: getFriendlyError(error) });
    } finally {
      setIsAuthenticating(false);
    }
  }

  async function handleLogout() {
    if (accessToken) {
      await apiFetch("/api/auth/logout", { method: "POST" }, accessToken).catch(() => undefined);
    }
    clearSession();
  }

  function clearSession() {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    setAccessToken(null);
    setCurrentUser(null);
    setJobs([]);
    setSelectedFile(null);
    setJobName("");
    setUploadResult(null);
    setJobStatus(null);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setUploadResult(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const validationError = validateFile(file);
    if (validationError) {
      setSelectedFile(null);
      setAlert({ type: "error", message: validationError });
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
    if (!jobName.trim()) {
      setJobName(file.name.replace(/\.[^.]+$/, ""));
    }
    setAlert({ type: "info", message: "Arquivo pronto para envio." });
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile || !accessToken || !jobName.trim()) {
      setAlert({ type: "error", message: "Informe um nome para o processamento e selecione um arquivo." });
      return;
    }

    setIsUploading(true);
    setAlert(null);
    setUploadResult(null);
    setJobStatus(null);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("job_name", jobName.trim());

    try {
      const response = await apiFetch(
        "/api/files/upload",
        {
          method: "POST",
          body: formData,
        },
        accessToken,
      );

      const data = await parseApiResponse<UploadResponse>(response);
      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, "Falha ao enviar arquivo."));
      }

      setUploadResult(data);
      setAlert({ type: "success", message: data.message || "Arquivo enviado com sucesso." });
      setActiveView("processing");
      setJobName("");
      setSelectedFile(null);
      await loadJobs(accessToken);
    } catch (error) {
      setAlert({ type: "error", message: getFriendlyError(error) });
    } finally {
      setIsUploading(false);
    }
  }

  async function handleCheckStatus(jobId?: string) {
    const targetJobId = jobId ?? jobStatus?.id ?? uploadResult?.job_id;
    if (!targetJobId || !accessToken) {
      return;
    }

    setIsCheckingStatus(true);
    setAlert(null);

    try {
      const response = await apiFetch(`/api/jobs/${targetJobId}`, { method: "GET" }, accessToken);
      const data = await parseApiResponse<JobResponse>(response);
      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, "Falha ao consultar status."));
      }

      setJobStatus(data);
      setUploadResult(null);
      setAlert({ type: "success", message: "Status atualizado." });
      await loadJobs(accessToken);
      setActiveView("history");
    } catch (error) {
      setAlert({ type: "error", message: getFriendlyError(error) });
    } finally {
      setIsCheckingStatus(false);
    }
  }

  async function handleDeleteJob(job: JobResponse) {
    if (!accessToken) {
      return;
    }

    const shouldDelete = window.confirm(`Excluir "${job.job_name}" do historico?`);
    if (!shouldDelete) {
      return;
    }

    try {
      const response = await apiFetch(`/api/jobs/${job.id}`, { method: "DELETE" }, accessToken);
      const data = await parseApiResponse<{ message?: string }>(response);
      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, "Falha ao excluir registro."));
      }

      setJobs((currentJobs) => currentJobs.filter((item) => item.id !== job.id));
      if (jobStatus?.id === job.id) {
        setJobStatus(null);
      }
      if (uploadResult?.job_id === job.id) {
        setUploadResult(null);
      }
      setAlert({ type: "success", message: data.message ?? "Registro removido do historico." });
    } catch (error) {
      setAlert({ type: "error", message: getFriendlyError(error) });
    }
  }

  if (isBootstrapping) {
    return (
      <main className="dataflow-bg grid min-h-screen place-items-center px-6">
        <div className="dataflow-panel rounded-lg px-5 py-4 font-mono text-sm text-rose-300">
          Carregando sessao...
        </div>
      </main>
    );
  }

  if (!currentUser || !accessToken) {
    return (
      <main className="dataflow-bg min-h-screen text-zinc-100">
        <section className="mx-auto grid min-h-screen w-full max-w-6xl items-center gap-8 px-6 py-10 lg:grid-cols-[1fr_420px] lg:items-center">
          <BrandIntro />

          <AuthPanel
            mode={authMode}
            username={username}
            password={password}
            alert={alert}
            isLoading={isAuthenticating}
            onModeChange={setAuthMode}
            onUsernameChange={setUsername}
            onPasswordChange={setPassword}
            onSubmit={handleAuth}
          />
        </section>
      </main>
    );
  }

  return (
    <main className="dataflow-bg min-h-screen text-zinc-100">
      <section className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-6 sm:px-8 lg:px-10">
        <header className="mb-6 flex flex-col gap-4 border-b border-rose-500/20 pb-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <LogoLockup />
            <nav className="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setActiveView("processing")}
                className={`h-10 rounded-md border px-4 text-sm font-semibold transition ${
                  activeView === "processing"
                    ? "border-rose-500 bg-rose-500 text-zinc-950"
                    : "border-zinc-700 bg-zinc-950/20 backdrop-blur-[2px] text-zinc-300 hover:border-rose-500/60 hover:text-rose-300"
                }`}
              >
                Processamento
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveView("history");
                  loadJobs();
                }}
                className={`h-10 rounded-md border px-4 text-sm font-semibold transition ${
                  activeView === "history"
                    ? "border-rose-500 bg-rose-500 text-zinc-950"
                    : "border-zinc-700 bg-zinc-950/20 backdrop-blur-[2px] text-zinc-300 hover:border-rose-500/60 hover:text-rose-300"
                }`}
              >
                Historico
              </button>
            </nav>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-md border border-zinc-700/80 bg-zinc-950/20 backdrop-blur-[2px] px-3 py-2 font-mono text-sm text-zinc-300">
              user:<span className="ml-1 font-semibold text-red-500">{currentUser.username}</span>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="h-10 rounded-md border border-zinc-700 bg-zinc-950/30 backdrop-blur-[2px] px-4 text-sm font-semibold text-zinc-200 transition hover:border-rose-500/60 hover:bg-rose-500/10"
            >
              Sair
            </button>
          </div>
        </header>

        {activeView === "processing" ? (
          <div className="grid gap-6">
            <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
              <UploadPanel
                selectedFile={selectedFile}
                jobName={jobName}
                canUpload={canUpload}
                isUploading={isUploading}
                onJobNameChange={setJobName}
                onFileChange={handleFileChange}
                onUpload={handleUpload}
              />

              <JobPanel
                selectedFileName={selectedFile?.name}
                uploadResult={uploadResult}
                jobStatus={jobStatus}
                alert={alert}
                isCheckingStatus={isCheckingStatus}
                onCheckStatus={() => handleCheckStatus()}
              />
            </div>
          </div>
        ) : (
          <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
            <HistoryPanel
              jobs={jobs}
              activeJobId={jobStatus?.id ?? uploadResult?.job_id}
              isLoading={isLoadingHistory}
              onRefresh={() => loadJobs()}
              onSelectJob={(job) => {
                setJobStatus(job);
                setUploadResult(null);
                setAlert(null);
              }}
              onDeleteJob={handleDeleteJob}
            />

            {jobStatus ? <JobResult job={jobStatus} /> : <EmptyHistorySelection />}
          </div>
        )}
      </section>
    </main>
  );
}

function LogoMark({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const boxSize = size === "lg" ? "h-14 w-14" : size === "sm" ? "h-9 w-9" : "h-11 w-11";

  return (
    <div
      className={`${boxSize} grid place-items-center rounded-xl border border-red-500/30 bg-zinc-950/30 backdrop-blur-[2px] p-1 shadow-[0_0_32px_rgba(244,63,94,0.18)]`}
    >
      <img src="/dataflow-logo.svg" alt="DataFlow" className="h-full w-full rounded-lg" />
    </div>
  );
}

function LogoLockup() {
  return (
    <div className="flex items-center gap-4">
      <LogoMark size="lg" />
      <div>
        <h1 className="text-3xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-orange-500 sm:text-4xl">DataFlow</h1>
      </div>
    </div>
  );
}

function BrandIntro() {
  return (
    <div>
      <div className="inline-flex items-center gap-4 rounded-2xl border border-red-500/20 bg-zinc-950/20 backdrop-blur-[2px] p-3 pr-6 shadow-[0_0_44px_rgba(244,63,94,0.14)]">
        <LogoMark size="lg" />
        <div>
          <p className="text-3xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-orange-500 sm:text-4xl">DataFlow</p>
        </div>
      </div>

      <h1 className="mt-8 max-w-3xl text-4xl font-semibold leading-tight text-zinc-50 sm:text-5xl">
        Do arquivo bruto ao script Python pronto para uso.
      </h1>
      <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-300">
        Organize uploads, acompanhe cada processamento e mantenha um historico seguro dos scripts gerados para seus arquivos CSV, Parquet, JSON e XML.
      </p>

      <div className="dataflow-terminal mt-8 max-w-2xl rounded-lg p-4 font-mono text-sm text-zinc-300">
        <div className="mb-4 flex items-center gap-2 border-b border-rose-500/10 pb-3">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
          <span className="ml-2 text-xs text-zinc-500">pipeline.preview</span>
        </div>
        <p>
          <span className="text-red-500">$</span> upload clientes.csv
        </p>
        <p className="mt-2 text-zinc-400">status: analyzing_schema - detecting_missing_values</p>
        <p className="mt-2 text-sky-300">output: script_tratamento.py + README.md + requirements.txt</p>
      </div>
    </div>
  );
}

function AuthPanel({
  mode,
  username,
  password,
  alert,
  isLoading,
  onModeChange,
  onUsernameChange,
  onPasswordChange,
  onSubmit,
}: {
  mode: AuthMode;
  username: string;
  password: string;
  alert: AlertState | null;
  isLoading: boolean;
  onModeChange: (mode: AuthMode) => void;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form onSubmit={onSubmit} className="dataflow-panel relative overflow-hidden rounded-2xl p-6 lg:self-center lg:tranzinc-y-[27px]">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-red-500/70 to-transparent" />
      <div className="mb-5 flex items-center gap-3 border-b border-zinc-800 pb-4">
        <LogoMark size="sm" />
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-red-500">Acesso DataFlow</p>
          <h2 className="mt-1 text-xl font-semibold text-zinc-50">
            {mode === "login" ? "Entre na sua area" : "Crie seu acesso"}
          </h2>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 rounded-md border border-zinc-700 bg-zinc-950/30 backdrop-blur-[2px] p-1">
        <button
          type="button"
          onClick={() => onModeChange("login")}
          className={`h-10 rounded px-3 text-sm font-semibold ${mode === "login" ? "bg-rose-500 text-zinc-950" : "text-zinc-400 hover:text-zinc-100"}`}
        >
          Entrar
        </button>
        <button
          type="button"
          onClick={() => onModeChange("register")}
          className={`h-10 rounded px-3 text-sm font-semibold ${mode === "register" ? "bg-rose-500 text-zinc-950" : "text-zinc-400 hover:text-zinc-100"}`}
        >
          Criar usuario
        </button>
      </div>

      <label className="text-sm font-medium text-zinc-200" htmlFor="username">
        Nome de usuario
      </label>
      <input
        id="username"
        value={username}
        onChange={(event) => onUsernameChange(event.target.value)}
        className="mt-2 h-11 w-full rounded-md border border-zinc-700 bg-zinc-950/40 backdrop-blur-[2px] px-3 font-mono text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-rose-500"
        autoComplete="username"
        placeholder="ex: analista_dados"
      />

      <label className="mt-3 block text-sm font-medium text-zinc-200" htmlFor="password">
        Senha
      </label>
      <input
        id="password"
        value={password}
        onChange={(event) => onPasswordChange(event.target.value)}
        className="mt-2 h-11 w-full rounded-md border border-zinc-700 bg-zinc-950/40 backdrop-blur-[2px] px-3 font-mono text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-rose-500"
        type="password"
        autoComplete={mode === "login" ? "current-password" : "new-password"}
        placeholder="minimo 6 caracteres"
      />

      {alert ? <StatusAlert alert={alert} /> : null}

      <button
        type="submit"
        disabled={isLoading}
        className="mt-5 inline-flex h-11 w-full items-center justify-center rounded-md bg-rose-500 px-5 text-sm font-bold text-zinc-950 shadow-[0_0_24px_rgba(244,63,94,0.18)] transition hover:bg-red-500 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-400"
      >
        {isLoading ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
      </button>
    </form>
  );
}

function HistoryPanel({
  jobs,
  activeJobId,
  isLoading,
  onRefresh,
  onSelectJob,
  onDeleteJob,
}: {
  jobs: JobResponse[];
  activeJobId?: string;
  isLoading: boolean;
  onRefresh: () => void;
  onSelectJob: (job: JobResponse) => void;
  onDeleteJob: (job: JobResponse) => void;
}) {
  return (
    <aside className="dataflow-panel rounded-lg p-4 xl:sticky xl:top-6 xl:max-h-[calc(100vh-48px)] xl:overflow-auto">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-zinc-100">Historico</h2>
          <p className="mt-1 font-mono text-xs text-zinc-500">{jobs.length} jobs encontrados</p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="h-9 rounded-md border border-zinc-700 bg-zinc-950/30 backdrop-blur-[2px] px-3 text-xs font-semibold text-zinc-300 transition hover:border-rose-500/60 hover:text-rose-300"
        >
          {isLoading ? "..." : "Atualizar"}
        </button>
      </div>

      <div className="mt-4 space-y-2">
        {jobs.length === 0 ? (
          <div className="rounded-md border border-dashed border-zinc-700 bg-zinc-950/20 backdrop-blur-[2px] p-4 text-sm text-zinc-500">
            Nenhum processamento ainda.
          </div>
        ) : (
          jobs.map((job) => (
            <div
              key={job.id}
              className={`w-full rounded-md border p-3 text-left transition ${
                activeJobId === job.id
                  ? "border-rose-500 bg-rose-500/10"
                  : "border-zinc-800 bg-zinc-950/20 backdrop-blur-[2px] hover:border-zinc-600 hover:bg-zinc-900/30 backdrop-blur-[2px]"
              }`}
            >
              <button type="button" onClick={() => onSelectJob(job)} className="w-full text-left">
                <div className="flex items-start justify-between gap-2">
                  <p className="line-clamp-2 text-sm font-semibold text-zinc-100">{job.job_name}</p>
                  <StatusBadge status={job.status} />
                </div>
                <p className="mt-1 line-clamp-1 text-xs text-zinc-500">{job.file_name}</p>
                <p className="mt-2 font-mono text-xs text-zinc-500">
                  {job.file_type.toUpperCase()} | {formatBytes(job.file_size)}
                </p>
                <p className="mt-1 text-xs text-zinc-600">{formatDate(job.created_at)}</p>
              </button>
              <div className="mt-3 flex justify-end gap-2 border-t border-zinc-800 pt-2">
                {job.raw_file_url ? (
                  <a
                    href={job.raw_file_url}
                    target="_blank"
                    rel="noreferrer"
                    download={job.file_name}
                    className="rounded-md border border-zinc-600 px-2.5 py-1.5 text-xs font-semibold text-zinc-300 transition hover:bg-zinc-800 hover:text-zinc-100"
                  >
                    Baixar Original
                  </a>
                ) : null}
                <button
                  type="button"
                  onClick={() => onDeleteJob(job)}
                  className="rounded-md border border-red-400/30 px-2.5 py-1.5 text-xs font-semibold text-red-200 transition hover:bg-red-950/20 backdrop-blur-[2px]"
                >
                  Excluir
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}

function UploadPanel({
  selectedFile,
  jobName,
  canUpload,
  isUploading,
  onJobNameChange,
  onFileChange,
  onUpload,
}: {
  selectedFile: File | null;
  jobName: string;
  canUpload: boolean;
  isUploading: boolean;
  onJobNameChange: (value: string) => void;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form onSubmit={onUpload} className="dataflow-panel flex flex-col rounded-lg p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Nome do processo</h2>
          <p className="mt-1 text-sm text-zinc-500">Envie CSV, Parquet, JSON ou XML ate 50 MB.</p>
        </div>
      </div>

      <div className="mt-5 rounded-lg border border-rose-500/25 bg-rose-500/[0.04] p-4">
        <label className="text-sm font-semibold text-zinc-100" htmlFor="job-name">
          Nome do processamento
        </label>
        <input
          id="job-name"
          value={jobName}
          onChange={(event) => onJobNameChange(event.target.value)}
          className="mt-2 h-11 w-full rounded-md border border-zinc-700 bg-zinc-950/40 backdrop-blur-[2px] px-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-rose-500"
          maxLength={255}
          placeholder="Ex: Limpeza de clientes - maio"
        />
        <p className="mt-2 text-xs text-zinc-500">Nome do Processamento</p>
      </div>

      <div className="dataflow-terminal mt-5 flex min-h-44 flex-col items-center justify-center rounded-lg border-dashed px-4 py-8 text-center">
        <input
          id="file-upload"
          name="file"
          type="file"
          accept=".csv,.parquet,.json,.xml"
          onChange={onFileChange}
          className="w-full max-w-sm cursor-pointer rounded-md border border-zinc-700 bg-zinc-950/40 backdrop-blur-[2px] text-sm text-zinc-300 file:mr-4 file:border-0 file:bg-rose-500 file:px-4 file:py-3 file:text-sm file:font-bold file:text-zinc-950 hover:file:bg-red-500"
        />
      </div>

      <div className="mt-5 rounded-lg border border-zinc-800 bg-zinc-950/20 backdrop-blur-[2px] p-4">
        <p className="font-mono text-xs font-semibold uppercase tracking-wide text-zinc-500">Selecionado</p>
        <p className="mt-2 break-words text-sm font-medium text-zinc-100">
          {selectedFile ? selectedFile.name : "Nenhum arquivo selecionado"}
        </p>
        {selectedFile ? <p className="mt-1 font-mono text-sm text-red-500">{formatBytes(selectedFile.size)}</p> : null}
      </div>

      <button
        type="submit"
        disabled={!canUpload}
        className="mt-6 inline-flex h-11 items-center justify-center rounded-md bg-rose-500 px-5 text-sm font-bold text-zinc-950 shadow-[0_0_24px_rgba(244,63,94,0.18)] transition hover:bg-red-500 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-400"
      >
        {isUploading ? "Enviando..." : "Enviar arquivo"}
      </button>
    </form>
  );
}

function JobPanel({
  selectedFileName,
  uploadResult,
  jobStatus,
  alert,
  isCheckingStatus,
  onCheckStatus,
}: {
  selectedFileName?: string;
  uploadResult: UploadResponse | null;
  jobStatus: JobResponse | null;
  alert: AlertState | null;
  isCheckingStatus: boolean;
  onCheckStatus: () => void;
}) {
  const currentStatus = jobStatus?.status ?? uploadResult?.status ?? "UPLOADED";

  return (
    <aside className="dataflow-panel rounded-lg p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Ultimo Job Processado</h2>
          <p className="mt-1 text-sm text-zinc-500">Acompanhe o processamento e abra resultados do historico.</p>
        </div>
        <StatusBadge status={currentStatus} />
      </div>

      {alert ? <StatusAlert alert={alert} /> : null}

      <dl className="mt-5 grid gap-4 sm:grid-cols-2">
        <ResultRow label="Job ID" value={jobStatus?.id ?? uploadResult?.job_id ?? "-"} />
        <ResultRow label="Status" value={jobStatus?.status ?? uploadResult?.status ?? "-"} />
        <ResultRow label="Registro" value={jobStatus?.job_name ?? "-"} />
        <ResultRow label="Arquivo" value={jobStatus?.file_name ?? selectedFileName ?? "-"} />
        <ResultRow label="Criado em" value={jobStatus ? formatDate(jobStatus.created_at) : "-"} />
      </dl>

      <StatusTimeline currentStatus={currentStatus} />

      {uploadResult || jobStatus ? (
        <button
          type="button"
          onClick={onCheckStatus}
          disabled={isCheckingStatus}
          className="mt-6 inline-flex h-10 w-full items-center justify-center rounded-md border border-zinc-700 bg-zinc-950/30 backdrop-blur-[2px] px-4 text-sm font-semibold text-zinc-200 transition hover:border-rose-500/60 hover:bg-rose-500/10 disabled:cursor-not-allowed disabled:text-zinc-600"
        >
          {isCheckingStatus ? "Consultando..." : "Consultar status"}
        </button>
      ) : null}
    </aside>
  );
}

function JobResult({ job }: { job: JobResponse }) {
  const isCompleted = job.status === "COMPLETED";
  const isFailed = job.status === "FAILED" || job.status === "N8N_ERROR";

  return (
    <section className="dataflow-panel rounded-lg p-6">
      <div className="flex flex-col gap-2 border-b border-zinc-800 pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Artefatos do processamento</h2>
          <p className="mt-1 text-sm text-zinc-500">Script, manual e resumo da analise retornados pelo backend.</p>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {isFailed ? <FailedState errorMessage={job.error_message} /> : null}

      {job.analysis_json ? <AnalysisSummary analysis={job.analysis_json} /> : null}

      {isCompleted ? (
        <div className="mt-6 grid gap-6 xl:grid-cols-2">
          {job.generated_script ? (
            <ArtifactViewer
              title="script_tratamento.py"
              content={job.generated_script}
              actions={[
                { label: "Copiar script", onClick: () => copyText(job.generated_script ?? "") },
                {
                  label: "Baixar script",
                  onClick: () => downloadTextFile("script_tratamento.py", job.generated_script ?? ""),
                },
              ]}
            />
          ) : null}

          {job.generated_manual ? (
            <ArtifactViewer
              title="README.md"
              content={job.generated_manual}
              actions={[
                { label: "Copiar README", onClick: () => copyText(job.generated_manual ?? "") },
                {
                  label: "Baixar README",
                  onClick: () => downloadTextFile("README.md", job.generated_manual ?? ""),
                },
              ]}
            />
          ) : null}

          {job.requirements_txt ? (
            <ArtifactViewer
              title="requirements.txt"
              content={job.requirements_txt}
              actions={[
                {
                  label: "Baixar requirements",
                  onClick: () => downloadTextFile("requirements.txt", job.requirements_txt ?? ""),
                },
              ]}
            />
          ) : null}

          {job.result_package_url ? (
            <a
              href={job.result_package_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-11 items-center justify-center rounded-md border border-rose-500/60 bg-rose-500/10 px-4 text-sm font-semibold text-rose-300 transition hover:bg-rose-500/20 xl:col-span-2"
            >
              Abrir pacote ZIP
            </a>
          ) : null}

          {!job.generated_script && !job.generated_manual && !job.requirements_txt ? <EmptyArtifacts /> : null}
        </div>
      ) : null}
    </section>
  );
}

function AnalysisSummary({ analysis }: { analysis: AnalysisJson }) {
  const issues = Array.isArray(analysis.issues) ? analysis.issues : [];

  return (
    <div className="mt-6 grid gap-4 lg:grid-cols-[240px_1fr]">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-1">
        <MetricCard label="Total de linhas" value={formatNumber(analysis.rows)} />
        <MetricCard label="Total de colunas" value={formatNumber(analysis.columns)} />
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-950/20 backdrop-blur-[2px] p-4">
        <h3 className="text-sm font-semibold text-zinc-100">Inconsistencias detectadas</h3>
        {issues.length > 0 ? (
          <ul className="mt-3 space-y-3">
            {issues.map((issue, index) => (
              <li key={`${issue.type ?? "issue"}-${index}`} className="rounded-md border border-zinc-800 bg-zinc-900/30 backdrop-blur-[2px] p-3">
                <p className="text-sm font-medium text-zinc-100">
                  {issue.description ?? issue.message ?? issue.type ?? "Inconsistencia"}
                </p>
                <p className="mt-1 font-mono text-xs uppercase tracking-wide text-zinc-500">
                  {[issue.severity, issue.column, issue.columns?.join(", ")].filter(Boolean).join(" | ") || "Sem detalhes"}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-zinc-500">Nenhuma inconsistencia foi retornada na analise.</p>
        )}
      </div>
    </div>
  );
}

function ArtifactViewer({
  title,
  content,
  actions,
}: {
  title: string;
  content: string;
  actions: Array<{ label: string; onClick: () => void }>;
}) {
  return (
    <div className="rounded-lg border border-rose-500/20 bg-zinc-950/30 backdrop-blur-[2px]">
      <div className="flex flex-col gap-3 border-b border-rose-500/10 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="font-mono text-sm font-semibold text-rose-300">{title}</h3>
        <div className="flex flex-wrap gap-2">
          {actions.map((action) => (
            <button
              key={action.label}
              type="button"
              onClick={action.onClick}
              className="rounded-md border border-zinc-700 px-3 py-2 text-xs font-semibold text-zinc-100 transition hover:border-rose-500/60 hover:bg-rose-500/10"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
      <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words p-4 font-mono text-xs leading-6 text-zinc-100">
        <code>{content}</code>
      </pre>
    </div>
  );
}

function FailedState({ errorMessage }: { errorMessage?: string | null }) {
  return (
    <div className="mt-6 rounded-lg border border-red-400/30 bg-red-950/20 backdrop-blur-[2px] p-4 text-sm text-red-100">
      <p className="font-semibold">O processamento falhou.</p>
      <p className="mt-1">{errorMessage || "Nenhuma mensagem de erro foi retornada."}</p>
    </div>
  );
}

function EmptySelection() {
  return (
    <div className="dataflow-panel-soft rounded-lg border-dashed p-6 text-sm text-zinc-500">
      Envie um novo arquivo para acompanhar o processamento e visualizar os resultados aqui.
    </div>
  );
}

function EmptyHistorySelection() {
  return (
    <div className="dataflow-panel-soft rounded-lg border-dashed p-6 text-sm text-zinc-500">
      Selecione um job no historico para visualizar os artefatos gerados.
    </div>
  );
}

function EmptyArtifacts() {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/20 backdrop-blur-[2px] p-4 text-sm text-zinc-500 xl:col-span-2">
      O job esta completo, mas nenhum artefato foi retornado ainda.
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/20 backdrop-blur-[2px] p-4">
      <p className="font-mono text-xs font-semibold uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-red-500">{value}</p>
    </div>
  );
}

function StatusTimeline({ currentStatus }: { currentStatus: string }) {
  const currentIndex = PROCESSING_STATUSES.indexOf(currentStatus);

  return (
    <div className="mt-6">
      <p className="font-mono text-xs font-semibold uppercase tracking-wide text-zinc-500">Pipeline</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {PROCESSING_STATUSES.map((statusName, index) => {
          const isActive = statusName === currentStatus;
          const isDone = currentIndex >= 0 && index < currentIndex && currentStatus !== "FAILED";
          return (
            <div
              key={statusName}
              className={`rounded-md border px-3 py-2 text-xs font-semibold ${
                isActive
                  ? getStatusClasses(statusName)
                  : isDone
                    ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                    : "border-zinc-800 bg-zinc-950/20 backdrop-blur-[2px] text-zinc-500"
              }`}
            >
              {statusName}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${getStatusClasses(status)}`}>
      {status}
    </span>
  );
}

function ResultRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-mono text-xs font-semibold uppercase tracking-wide text-zinc-500">{label}</dt>
      <dd className="mt-1 break-words text-sm text-zinc-100">{value}</dd>
    </div>
  );
}

function StatusAlert({ alert }: { alert: AlertState }) {
  const className =
    alert.type === "success"
      ? "border-rose-500/30 bg-rose-500/10 text-rose-200"
      : alert.type === "error"
        ? "border-red-400/30 bg-red-950/20 backdrop-blur-[2px] text-red-100"
        : "border-sky-400/30 bg-sky-950/20 backdrop-blur-[2px] text-sky-100";

  return <div className={`mt-4 rounded-md border px-4 py-3 text-sm ${className}`}>{alert.message}</div>;
}

function validateFile(file: File): string | null {
  const extension = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;

  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return "Formato nao suportado. Use CSV, Parquet, JSON ou XML.";
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return "O arquivo ultrapassa o limite de 50 MB.";
  }

  return null;
}

async function apiFetch(path: string, init: RequestInit, accessToken: string): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(`${API_BASE_URL}${path}`, { ...init, headers });
}

async function parseApiResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  const text = await response.text();
  return { detail: text } as T;
}

function getApiErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === "object" && data !== null && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return "Verifique os campos informados.";
    }
  }

  return fallback;
}

function getFriendlyError(error: unknown): string {
  if (error instanceof TypeError) {
    return `Nao foi possivel conectar ao backend em ${API_BASE_URL}.`;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Ocorreu um erro inesperado.";
}

function getStatusClasses(status: string): string {
  if (status === "COMPLETED") {
    return "border-rose-500/30 bg-rose-500/10 text-rose-200";
  }
  if (status === "FAILED" || status === "N8N_ERROR") {
    return "border-red-400/30 bg-red-950/20 backdrop-blur-[2px] text-red-100";
  }
  if (status === "VALIDATING_SCRIPT" || status === "GENERATING_SCRIPT") {
    return "border-amber-300/30 bg-amber-950/20 backdrop-blur-[2px] text-amber-100";
  }
  if (status === "ANALYZING" || status === "SENT_TO_N8N") {
    return "border-sky-400/30 bg-sky-950/20 backdrop-blur-[2px] text-sky-100";
  }
  return "border-zinc-700 bg-zinc-900/30 backdrop-blur-[2px] text-zinc-300";
}

function formatBytes(bytes: number): string {
  if (bytes === 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatNumber(value?: number): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  return new Intl.NumberFormat("pt-BR").format(value);
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

async function copyText(content: string) {
  if (!content) {
    return;
  }

  await navigator.clipboard.writeText(content);
}

function downloadTextFile(fileName: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
