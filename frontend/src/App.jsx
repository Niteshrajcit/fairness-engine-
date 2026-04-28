import { useEffect, useState } from "react";
import {
  applyStrategy,
  cancelStream,
  exportJsonUrl,
  exportPdfUrl,
  fetchReplay,
  getSession,
  listSessions,
  resumeSession,
  runWhatIf,
  streamPipeline,
  uploadDataset,
} from "./api";
import MessageBubble from "./components/MessageBubble";
import OutcomeChart from "./components/OutcomeChart";
import ReplayTimeline from "./components/ReplayTimeline";
import RiskScoreCard from "./components/RiskScoreCard";
import StatusBadge from "./components/StatusBadge";
import StrategyCard from "./components/StrategyCard";
import TypingDots from "./components/TypingDots";
import SessionHistoryPanel from "./components/SessionHistoryPanel";
import WhatIfPanel from "./components/WhatIfPanel";

export default function App() {
  const [messages, setMessages] = useState([
    { role: "system", text: "Upload a CSV to begin fairness intelligence analysis." },
  ]);
  const [loading, setLoading] = useState(false);
  const [strategies, setStrategies] = useState([]);
  const [risk, setRisk] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [outcomes, setOutcomes] = useState({ before: [], after: [] });
  const [badges, setBadges] = useState([]);
  const [activeSource, setActiveSource] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);

  const addMessage = (role, text) => setMessages((prev) => [...prev, { role, text }]);
  const addBadge = (label, tone) =>
    setBadges((prev) => {
      if (prev.some((b) => b.label === label)) return prev;
      return [...prev, { label, tone }];
    });
  const refreshSessions = async () => {
    const data = await listSessions();
    setSessions(data.sessions || []);
  };
  useEffect(() => {
    refreshSessions();
  }, []);

  const startStream = async (sid, resumeFromLastStep = false) => {
    const source = streamPipeline({
      sessionId: sid,
      resumeFromLastStep,
      onStep: (step) => {
        setTimeline((prev) => [...prev, step]);
        addMessage("system", step.message);
        if (step.step === "simulation") addBadge("Simulation Complete", "purple");
      },
      onAnalysis: (analysis) => {
        addMessage(
          "system",
          `Primary sensitive attribute: ${analysis.sensitive_attribute} | Risk: ${analysis.risk.toUpperCase()}`
        );
        if (analysis.intersectional_bias?.attributes?.length) {
          addMessage(
            "system",
            `Intersectional fairness (${analysis.intersectional_bias.attributes.join(
              " + "
            )}) DI: ${analysis.intersectional_bias.disparate_impact}`
          );
        }
        addMessage(
          "system",
          `Disparate Impact: ${analysis.disparate_impact} | SPD: ${analysis.statistical_parity_difference}`
        );
        if (analysis.bias_detected) addBadge("Bias Detected", "red");
      },
      onSimulation: (simulation) => {
        addMessage(
          "system",
          simulation.bias_confirmed
            ? "[OK] Bias confirmed through counterfactuals"
            : "Counterfactual impact was limited"
        );
        setRisk({
          score: simulation.bias_risk_score,
          level: simulation.bias_risk_level,
          explanation: simulation.bias_risk_explanation,
        });
      },
      onStrategies: (payload) => {
        setStrategies(payload.strategies || []);
        if (payload.recommendation) {
          addMessage(
            "system",
            `[IDEA] Recommended: ${payload.recommendation.strategy} | ${payload.recommendation.tradeoff}`
          );
        }
        addMessage("system", "Select one strategy to retrain and improve fairness.");
      },
      onCancelled: (payload) => {
        addMessage("system", `[WARN] Stream cancelled at: ${payload.last_step}`);
        setActiveSource(null);
        setLoading(false);
      },
      onDone: async (payload) => {
        setTimeline(payload.replay_logs || []);
        const replay = await fetchReplay();
        if (replay.timeline?.length) setTimeline(replay.timeline);
        await refreshSessions();
        setActiveSource(null);
        setLoading(false);
      },
      onError: () => {
        addMessage("system", "Streaming error occurred.");
        setActiveSource(null);
        setLoading(false);
      },
    });
    setActiveSource(source);
  };

  const processDataset = async (file) => {
    if (activeSource) {
      activeSource.close();
      setActiveSource(null);
    }
    setLoading(true);
    setStrategies([]);
    setRisk(null);
    setTimeline([]);
    setOutcomes({ before: [], after: [] });
    setBadges([]);

    try {
      addMessage("user", `Uploaded: ${file.name}`);
      const uploaded = await uploadDataset(file);
      setSessionId(uploaded.session_id);
      await refreshSessions();
      addMessage("system", "[OK] Dataset received");
      addMessage("system", "[OK] Opening real-time fairness stream...");
      await startStream(uploaded.session_id, false);
    } catch (error) {
      const detail = error?.response?.data?.detail || error.message;
      addMessage("system", `Error: ${detail}`);
      setLoading(false);
    }
  };

  const onFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await processDataset(file);
  };

  const onSelectStrategy = async (strategyName) => {
    setLoading(true);
    try {
      addMessage("user", `Apply strategy: ${strategyName}`);
      const result = await applyStrategy(strategyName);
      addMessage("system", `[OK] Retrained with ${result.selected_strategy}`);
      addMessage(
        "system",
        `New accuracy: ${result.new_accuracy} | New DI: ${result.new_disparate_impact}`
      );
      addMessage("system", `Final improvement: ${result.explanation.final_improvement}`);
      if (result.before_after_outcomes) {
        setOutcomes(result.before_after_outcomes);
      }
      addBadge("Fairness Improved", "green");
    } catch (error) {
      const detail = error?.response?.data?.detail || error.message;
      addMessage("system", `Error applying strategy: ${detail}`);
    } finally {
      setLoading(false);
    }
  };
  const onCancelStream = async () => {
    if (!sessionId) return;
    await cancelStream(sessionId);
  };

  const onResumeStream = async () => {
    if (!sessionId) return;
    setLoading(true);
    await startStream(sessionId, true);
  };

  const onResumeSession = async (sid) => {
    await resumeSession(sid);
    const full = await getSession(sid);
    setSessionId(sid);
    setTimeline(full.replay_logs || []);
    setStrategies(full.strategies?.strategies || []);
    if (full.simulation?.bias_risk_score !== undefined) {
      setRisk({
        score: full.simulation.bias_risk_score,
        level: full.simulation.bias_risk_level,
        explanation: full.simulation.bias_risk_explanation,
      });
    }
    addMessage("system", `[OK] Resumed session ${sid}`);
  };

  const onWhatIf = async (featureUpdates) => {
    const result = await runWhatIf(featureUpdates);
    addMessage(
      "system",
      `[WHAT-IF] Outcome: ${result.predicted_outcome} | Probability: ${result.positive_probability}`
    );
  };

  const streamActive = Boolean(loading || activeSource);

  return (
    <div className="grid-bg relative min-h-screen overflow-hidden p-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,0.15),transparent_35%),radial-gradient(circle_at_80%_0%,rgba(168,85,247,0.12),transparent_30%)]" />
      <div className="relative mx-auto flex max-w-4xl flex-col gap-4">
        <h1 className="text-center text-2xl font-semibold text-slate-100">
          Conversational Fairness Intelligence Engine
        </h1>
        <div className="flex flex-wrap justify-center gap-2">
          {badges.map((badge) => (
            <StatusBadge key={badge.label} label={badge.label} tone={badge.tone} />
          ))}
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <button
            onClick={onCancelStream}
            className="rounded border border-rose-400/50 bg-rose-500/20 px-3 py-1 text-xs text-rose-100"
          >
            Pause Stream
          </button>
          <button
            onClick={onResumeStream}
            className="rounded border border-cyan-400/50 bg-cyan-500/20 px-3 py-1 text-xs text-cyan-100"
          >
            Resume Stream
          </button>
          {sessionId && (
            <>
              <a
                href={exportJsonUrl(sessionId)}
                target="_blank"
                rel="noreferrer"
                className="rounded border border-white/10 px-3 py-1 text-xs text-slate-200"
              >
                Export JSON
              </a>
              <a
                href={exportPdfUrl(sessionId)}
                target="_blank"
                rel="noreferrer"
                className="rounded border border-white/10 px-3 py-1 text-xs text-slate-200"
              >
                Export PDF
              </a>
            </>
          )}
        </div>

        <label className="mx-auto w-full max-w-md cursor-pointer rounded-xl border border-white/10 bg-white/5 p-4 text-center text-sm backdrop-blur-md transition hover:scale-[1.01] hover:border-cyan-400/50 hover:shadow-[0_0_30px_rgba(34,211,238,0.2)]">
          Upload CSV Dataset
          <input type="file" accept=".csv" onChange={onFileChange} className="hidden" />
        </label>

        <div className="mx-auto grid h-[72vh] w-full max-w-6xl grid-cols-1 gap-3 lg:grid-cols-3">
          <div className="lg:col-span-2 flex h-full flex-col gap-3 overflow-y-auto rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
          {streamActive && (
            <div className="h-1 w-full overflow-hidden rounded bg-white/10">
              <div className="h-full w-1/3 animate-pulse rounded bg-cyan-300" />
            </div>
          )}
          {messages.map((message, idx) => (
            <MessageBubble key={`${message.role}-${idx}`} role={message.role} text={message.text} />
          ))}
          {loading && <TypingDots />}
          {risk && (
            <RiskScoreCard score={risk.score} level={risk.level} explanation={risk.explanation} />
          )}
          {strategies.length > 0 && (
            <div className="mt-2 space-y-2">
              {strategies.map((strategy) => (
                <StrategyCard key={strategy.name} strategy={strategy} onSelect={onSelectStrategy} />
              ))}
            </div>
          )}
            <OutcomeChart before={outcomes.before} after={outcomes.after} />
            <ReplayTimeline timeline={timeline} />
            <WhatIfPanel onRun={onWhatIf} />
          </div>
          <SessionHistoryPanel
            sessions={sessions}
            activeSessionId={sessionId}
            onResume={onResumeSession}
          />
        </div>
      </div>
    </div>
  );
}
