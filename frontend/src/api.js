import axios from "axios";

const client = axios.create({
  baseURL: "http://localhost:8001/api",
});

export const uploadDataset = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await client.post("/upload", formData);
  return data;
};

export const applyStrategy = async (strategyName) => {
  const { data } = await client.post("/strategy/apply", { strategy_name: strategyName });
  return data;
};

export const fetchReplay = async () => {
  const { data } = await client.get("/replay");
  return data;
};

export const streamPipeline = ({
  sessionId,
  resumeFromLastStep = false,
  onStep,
  onAnalysis,
  onSimulation,
  onStrategies,
  onDone,
  onCancelled,
  onError,
}) => {
  const qs = new URLSearchParams();
  if (sessionId) qs.set("session_id", sessionId);
  if (resumeFromLastStep) qs.set("resume_from_last_step", "true");
  const source = new EventSource(`http://localhost:8000/api/stream/pipeline?${qs.toString()}`);
  source.addEventListener("step", (evt) => onStep?.(JSON.parse(evt.data)));
  source.addEventListener("analysis", (evt) => onAnalysis?.(JSON.parse(evt.data)));
  source.addEventListener("simulation", (evt) => onSimulation?.(JSON.parse(evt.data)));
  source.addEventListener("strategies", (evt) => onStrategies?.(JSON.parse(evt.data)));
  source.addEventListener("cancelled", (evt) => {
    onCancelled?.(JSON.parse(evt.data));
    source.close();
  });
  source.addEventListener("done", (evt) => {
    onDone?.(JSON.parse(evt.data));
    source.close();
  });
  source.addEventListener("error", (evt) => {
    onError?.(evt);
    source.close();
  });
  return source;
};

export const cancelStream = async (sessionId) => {
  const { data } = await client.post(`/stream/cancel?session_id=${encodeURIComponent(sessionId)}`);
  return data;
};

export const listSessions = async () => {
  const { data } = await client.get("/sessions");
  return data;
};

export const getSession = async (sessionId) => {
  const { data } = await client.get(`/session/${sessionId}`);
  return data;
};

export const resumeSession = async (sessionId) => {
  const { data } = await client.post("/session/resume", { session_id: sessionId });
  return data;
};

export const exportJsonUrl = (sessionId) => `http://localhost:8000/api/session/${sessionId}/export/json`;
export const exportPdfUrl = (sessionId) => `http://localhost:8000/api/session/${sessionId}/export/pdf`;

export const runWhatIf = async (featureUpdates) => {
  const { data } = await client.post("/simulate/what-if", { feature_updates: featureUpdates });
  return data;
};
